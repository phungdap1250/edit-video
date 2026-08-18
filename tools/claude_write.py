"""Cửa DUY NHẤT để Claude ghi vào plans/*_plan.json.

Đi qua lib.validate_plan trước khi chạm đĩa. Sai schema → từ chối toàn bộ,
file cũ nguyên vẹn. Claude KHÔNG được sửa steps/, lib/, checks/, web/,
transcript.json, project.json, render_manifest.json (§7.2).

Ghi kiểu UPSERT theo id: mục trùng id trên đĩa được merge trường-theo-trường
với mục Claude gửi lên, mục khác id giữ nguyên. File chưa tồn tại (overlay,
cutaway lần đầu) → tạo mới với đúng các mục Claude gửi.

TDD: §7.4 · Lộ trình: Tuần 1
"""

from __future__ import annotations

import json
from pathlib import Path

from lib import budget, cli, config, field_path, paths, plan_io, timeline, validate_plan
from lib.errors import AIEditorError
from lib.timeline import BOF_ID, EOF_ID

# Tên trường chứa danh sách mục — caption_plan.json dùng "lines", 3 loại còn
# lại dùng "items" (TDD §3.4, §3.5).
_LIST_FIELD = {"cut": "items", "overlay": "items", "cutaway": "items", "caption": "lines"}


def main(args) -> dict:
    incoming = _load_items(Path(args.items))
    path = paths.PLAN_BY_KIND[args.kind]
    list_field = _LIST_FIELD[args.kind]

    if path.exists():
        disk, version = plan_io.load_plan(path)
    else:
        disk, version = {list_field: []}, 0

    disk_items_by_id = {item["id"]: item for item in disk.get(list_field, []) if "id" in item}
    items_by_id = dict(disk_items_by_id)
    for item in incoming:
        items_by_id[item["id"]] = _merge_item(items_by_id.get(item["id"], {}), item)
    merged_items = list(items_by_id.values())

    ctx = _build_ctx(args.kind, disk_items_by_id)
    validate_plan.raise_if_invalid(args.kind, merged_items, ctx)

    if args.dry_run:
        return {"kind": args.kind, "items": len(incoming), "dry_run": True}

    disk[list_field] = merged_items
    if args.kind != "caption":  # caption_plan.json không có bước duyệt (TDD §5.3)
        disk.setdefault("approved_at", None)
    new_version = _save(path, disk, version)

    return {
        "kind": args.kind,
        "written": len(incoming),
        "total": len(merged_items),
        "version": new_version,
    }


def _merge_item(old: dict, new: dict) -> dict:
    """Merge nông rồi PHỤC HỒI mọi đường dẫn trong `edited_fields[]` của bản cũ —
    script sinh lại kế hoạch không được ghi đè chữ người dùng đã sửa (TDD §3.4)."""
    merged = {**old, **new}
    for path in old.get("edited_fields", []):
        old_value = field_path.get_path(old, path)
        if old_value is not None:
            field_path.set_path(merged, path, old_value)
    return merged


def _load_items(path: Path) -> list[dict]:
    if not path.exists():
        raise AIEditorError(f"Không tìm thấy file --items {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise AIEditorError("File --items phải chứa một mảng JSON các mục")
    return data


def _build_ctx(kind: str, disk_items_by_id: dict | None = None) -> dict:
    ctx: dict = {}
    if paths.TRANSCRIPT.exists():
        transcript, _ = plan_io.load_plan(paths.TRANSCRIPT)
        ctx["valid_word_ids"] = {BOF_ID, EOF_ID} | {w["id"] for w in transcript["words"]}
    if kind == "cutaway":
        ctx["cfg"] = config.cut_config()
        ctx["month_used"] = budget.month_used()
    if kind == "overlay":
        ctx["disk_items_by_id"] = disk_items_by_id or {}
        ctx["timeline_map"] = _build_timeline_map()
    return ctx


def _build_timeline_map() -> dict | None:
    if not (paths.TRANSCRIPT.exists() and paths.CUT_PLAN.exists()):
        return None
    transcript, _ = plan_io.load_plan(paths.TRANSCRIPT)
    cut_plan, _ = plan_io.load_plan(paths.CUT_PLAN)
    if cut_plan.get("approved_at") is None:
        return None
    cfg = config.cut_config()
    padding_sec = cfg.silence.padding_each_side_ms / 1000.0
    return timeline.build_timeline_map(
        transcript["words"], cut_plan["items"], transcript["duration_sec"], padding_sec=padding_sec
    )


def _save(path: Path, document: dict, current_version: int) -> int:
    if path.exists():
        return plan_io.save_plan(path, document, current_version, force=True)
    return plan_io.save_plan(path, document, 0)


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    parser.add_argument("--kind", required=True, choices=["cut", "overlay", "cutaway", "caption"])
    parser.add_argument("--items", required=True, help="đường dẫn file JSON chứa items[]")
    cli.run("tools.claude_write", main, parser.parse_args())

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

from lib import budget, cli, config, paths, plan_io, validate_plan
from lib.errors import AIEditorError
from lib.timeline import BOF_ID, EOF_ID


def main(args) -> dict:
    incoming = _load_items(Path(args.items))
    path = paths.PLAN_BY_KIND[args.kind]

    if path.exists():
        disk, version = plan_io.load_plan(path)
    else:
        disk, version = {"items": []}, 0

    items_by_id = {item["id"]: item for item in disk.get("items", []) if "id" in item}
    for item in incoming:
        items_by_id[item["id"]] = {**items_by_id.get(item["id"], {}), **item}
    merged_items = list(items_by_id.values())

    ctx = _build_ctx(args.kind)
    validate_plan.raise_if_invalid(args.kind, merged_items, ctx)

    if args.dry_run:
        return {"kind": args.kind, "items": len(incoming), "dry_run": True}

    disk["items"] = merged_items
    disk.setdefault("approved_at", None)
    new_version = _save(path, disk, version)

    return {
        "kind": args.kind,
        "written": len(incoming),
        "total": len(merged_items),
        "version": new_version,
    }


def _load_items(path: Path) -> list[dict]:
    if not path.exists():
        raise AIEditorError(f"Không tìm thấy file --items {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise AIEditorError("File --items phải chứa một mảng JSON các mục")
    return data


def _build_ctx(kind: str) -> dict:
    ctx: dict = {}
    if paths.TRANSCRIPT.exists():
        transcript, _ = plan_io.load_plan(paths.TRANSCRIPT)
        ctx["valid_word_ids"] = {BOF_ID, EOF_ID} | {w["id"] for w in transcript["words"]}
    if kind == "cutaway":
        ctx["cfg"] = config.cut_config()
        ctx["month_used"] = budget.month_used()
    return ctx


def _save(path: Path, document: dict, current_version: int) -> int:
    if path.exists():
        return plan_io.save_plan(path, document, current_version, force=True)
    return plan_io.save_plan(path, document, 0)


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    parser.add_argument("--kind", required=True, choices=["cut", "overlay", "cutaway", "caption"])
    parser.add_argument("--items", required=True, help="đường dẫn file JSON chứa items[]")
    cli.run("tools.claude_write", main, parser.parse_args())

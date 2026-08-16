"""Đọc/ghi plan — ghi nguyên tử, chống ghi đè, merge 3 chiều theo trường.

TDD §3.6 + §4.2. Luật cứng §13.2: KHÔNG file nào mở plan JSON trực tiếp.

Bốn luật:
  1. Ghi bằng .tmp + os.replace() — không bao giờ có file JSON cụt.
  2. Kiểm `version` trước khi ghi.
  3. Bản nháp ghi vào .draft/, không đụng file thật.
  4. Promote là MERGE theo whitelist trường, xung đột xét ở cấp TRƯỜNG.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from lib import paths
from lib.errors import AIEditorError, PlanConflict
from lib.log import now_iso

# Bảng quyền ghi theo từng trang — TDD §4.2. Trang chỉ chép được các trường này.
WRITABLE_FIELDS: dict[str, tuple[str, ...]] = {
    "cut": ("status", "decided_by", "decided_at"),
    "cutaway": ("status", "image_path", "prompt", "regen_count", "decided_by", "decided_at"),
    "overlay": ("status", "content", "edited_fields", "position", "decided_by", "decided_at"),
}


def _read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json_atomic(path: Path, data: dict) -> None:
    """.tmp → os.replace() — nguyên tử trên cùng filesystem."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")
    os.replace(tmp, path)


def load_plan(path: Path) -> tuple[dict, int]:
    """Trả (nội dung, version lúc đọc)."""
    if not path.exists():
        raise AIEditorError(
            f"Chưa có {path.name}",
            suggestion="Chạy step sinh ra file này trước — xem docs/TDD.md §4.1",
        )
    data = _read_json(path)
    return data, int(data.get("version", 0))


def save_plan(path: Path, data: dict, expected_version: int, *, force: bool = False) -> int:
    """Ghi nguyên tử, tăng version. Lệch version → PlanConflict."""
    if path.exists():
        on_disk = int(_read_json(path).get("version", 0))
        if on_disk != expected_version and not force:
            raise PlanConflict(
                f"{path.name} đã bị ghi bởi tác nhân khác "
                f"(đĩa: v{on_disk}, bản của anh: v{expected_version})"
            )
    data["version"] = expected_version + 1
    data["updated_at"] = now_iso()
    data.setdefault("schema_version", 1)
    _write_json_atomic(path, data)
    return data["version"]


# ── Bản nháp tự lưu ───────────────────────────────────────────────
def _draft_path(kind: str) -> Path:
    return paths.DRAFT / f"{kind}.draft.json"


def _base_path(kind: str) -> Path:
    return paths.DRAFT / f"{kind}.base.json"


def snapshot_base(kind: str, plan: dict) -> None:
    """Chụp bản đĩa lúc trang duyệt nạp plan — mốc so cho merge 3 chiều."""
    _write_json_atomic(_base_path(kind), plan)


def save_draft(kind: str, data: dict) -> None:
    """Ghi .draft/<kind>.draft.json — KHÔNG đụng file thật, không tăng version."""
    _write_json_atomic(_draft_path(kind), data)


def load_draft(kind: str) -> dict | None:
    path = _draft_path(kind)
    return _read_json(path) if path.exists() else None


def clear_draft(kind: str) -> None:
    for path in (_draft_path(kind), _base_path(kind)):
        path.unlink(missing_ok=True)


def _index(items: list[dict]) -> dict[str, dict]:
    return {it["id"]: it for it in items if "id" in it}


def promote_draft(
    kind: str,
    draft_items: list[dict],
    expected_version: int,
    *,
    partial: bool = False,
    scope: list[str] | None = None,
) -> tuple[int, list[dict], dict]:
    """Người dùng bấm "Xuất quyết định".

    MERGE theo whitelist trường của `kind`, không ghi khối:
      · chỉ chép các trường trang đó được phép ghi;
      · partial=True → chỉ đụng ID trong scope, mục ngoài scope giữ NGUYÊN;
      · xung đột cấp TRƯỜNG (cả hai cùng sửa 1 trường) → mục đó bị giữ lại,
        các mục còn lại VẪN LƯU, trả về danh sách conflicts.

    Trả (version mới, conflicts[], summary).
    """
    if kind not in WRITABLE_FIELDS:
        raise AIEditorError(f"Loại plan không hợp lệ: {kind}")

    path = paths.PLAN_BY_KIND[kind]
    disk, disk_version = load_plan(path)
    base_file = _base_path(kind)
    base_items = _index(_read_json(base_file)["items"]) if base_file.exists() else {}
    disk_items = _index(disk.get("items", []))
    allowed = WRITABLE_FIELDS[kind]

    conflicts: list[dict] = []
    kept = rejected = touched = 0

    for item in draft_items:
        item_id = item.get("id")
        if item_id is None or item_id not in disk_items:
            continue
        if partial and (scope is None or item_id not in scope):
            continue

        target = disk_items[item_id]
        base = base_items.get(item_id, {})
        for field in allowed:
            if field not in item:
                continue
            mine, theirs = item[field], target.get(field)
            if mine == theirs:
                continue
            was = base.get(field)
            if was is not None and theirs != was:  # tác nhân khác cũng vừa sửa
                conflicts.append(
                    {"id": item_id, "field": field, "yours": mine, "theirs": theirs}
                )
                continue
            target[field] = mine
            touched += 1

        status = target.get("status")
        kept += status in ("accepted", "approved")
        rejected += status == "rejected"

    disk["items"] = list(disk_items.values())
    disk["approved_at"] = now_iso()
    new_version = save_plan(path, disk, disk_version)

    auto = sum(1 for it in disk["items"] if it.get("decided_by") == "auto")
    summary = {"kept": kept, "rejected": rejected, "auto": auto, "fields_written": touched}
    if expected_version != disk_version:
        summary["rebased_from"] = expected_version
    return new_version, conflicts, summary

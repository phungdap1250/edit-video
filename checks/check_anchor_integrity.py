"""Mọi anchor_* trỏ tới word.id đang tồn tại; anchor_text khớp văn bản hiện tại.

Đạt khi: 0 neo mồ côi, 0 neo lệch chữ
Phục vụ: §3.1 · TDD §12.1 · Lộ trình: Tuần 2
"""

from __future__ import annotations

import sys

from lib import paths, plan_io
from lib.timeline import BOF_ID, EOF_ID


def _load(path):
    if not path.exists():
        return None
    data, _ = plan_io.load_plan(path)
    return data


def main() -> int:
    transcript = _load(paths.TRANSCRIPT)
    if transcript is None:
        print("✓ check_anchor_integrity — chưa có transcript.json, không có gì để kiểm")
        return 0

    valid_ids = {BOF_ID, EOF_ID} | {w["id"] for w in transcript["words"]}
    text_by_id = {w["id"]: w["text"] for w in transcript["words"]}

    orphans: list[str] = []
    mismatched: list[str] = []

    for kind, path in (("cut", paths.CUT_PLAN), ("overlay", paths.OVERLAY_PLAN), ("cutaway", paths.CUTAWAY_PLAN)):
        plan = _load(path)
        if plan is None:
            continue
        for item in plan.get("items", []):
            for field in ("anchor_start", "anchor_end"):
                anchor = item.get(field)
                if anchor is None:
                    continue
                if anchor not in valid_ids:
                    orphans.append(f"{kind}:{item.get('id')} — {field}={anchor} không tồn tại")

            _check_anchor_text(kind, item, text_by_id, mismatched)

    if not orphans and not mismatched:
        print(f"✓ check_anchor_integrity — 0 neo mồ côi, 0 neo lệch chữ ({len(valid_ids)} từ)")
        return 0

    print(f"✗ check_anchor_integrity — {len(orphans)} neo mồ côi, {len(mismatched)} neo lệch chữ")
    for line in orphans + mismatched:
        print(f"  {line}")
    return 1


def _check_anchor_text(kind: str, item: dict, text_by_id: dict, mismatched: list[str]) -> None:
    """anchor_text chỉ để kiểm chứng — không dùng để neo (TDD §3.3)."""
    start, end, expected = item.get("anchor_start"), item.get("anchor_end"), item.get("anchor_text")
    if not (start and end and expected) or item.get("kind") == "silence":
        return
    if start not in text_by_id or end not in text_by_id:
        return  # đã báo ở orphans

    actual_first = text_by_id[start]
    actual_last = text_by_id[end]
    if not (expected.startswith(actual_first) or actual_first in expected):
        mismatched.append(
            f"{kind}:{item.get('id')} — anchor_text bắt đầu bằng '{expected.split()[0] if expected else ''}' "
            f"nhưng {start} hiện là '{actual_first}'"
        )
    elif not (expected.endswith(actual_last) or actual_last in expected):
        mismatched.append(
            f"{kind}:{item.get('id')} — anchor_text kết thúc khác {end}='{actual_last}'"
        )


if __name__ == "__main__":
    sys.exit(main())

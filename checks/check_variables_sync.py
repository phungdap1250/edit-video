"""hf/variables.json vs overlay_plan.json.

`renderer.read_variables()` CHỈ ĐƯỢC gọi từ đây — TDD §6.5 luật 3: đọc ngược
chỉ để SO SÁNH, không bao giờ dùng để cập nhật plan.

Đạt khi: không lệch
Phục vụ: [RND], [MGX] · TDD §12.1 · Lộ trình: Tuần 3
"""

from __future__ import annotations

import sys

from lib import overlay_content, paths, plan_io, renderer


def main() -> int:
    if not paths.OVERLAY_PLAN.exists():
        print("✓ check_variables_sync — chưa có overlay_plan.json, không có gì để kiểm")
        return 0

    overlay_plan, _ = plan_io.load_plan(paths.OVERLAY_PLAN)
    approved = [i for i in overlay_plan.get("items", []) if i.get("status") == "approved"]
    expected: dict[str, str] = {}
    for item in approved:
        expected.update(overlay_content.extract_variables(item))

    if not expected:
        print("✓ check_variables_sync — không có mục nào đã duyệt, không có gì để kiểm")
        return 0

    actual = renderer.read_variables()
    missing = {k: v for k, v in expected.items() if k not in actual}
    stale = {k: v for k, v in actual.items() if k in expected and expected[k] != v}

    if not missing and not stale:
        print(f"✓ check_variables_sync — {len(expected)} biến khớp overlay_plan.json")
        return 0

    print(f"✗ check_variables_sync — lệch {len(missing) + len(stale)} biến")
    for var_id, value in missing.items():
        print(f"  {var_id}: thiếu trong hf/variables.json (overlay_plan.json = {value!r})")
    for var_id, value in stale.items():
        print(f"  {var_id}: hf/variables.json = {value!r}, overlay_plan.json = {expected[var_id]!r}")
    print("  → Chạy: python -m tools.sync_variables")
    return 1


if __name__ == "__main__":
    sys.exit(main())

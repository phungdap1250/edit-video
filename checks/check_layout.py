"""Toạ độ đồ hoạ (overlay)/cutaway vs vùng cấm caption — TDD §5.3.

Vùng cấm đọc từ `config/caption_style.json`.`forbidden_zone` (x/y/w/h, tỉ lệ
0–1 theo khung). Chỉ kiểm được mục ĐÃ CÓ toạ độ pixel tường minh (trường
`rect: {x,y,w,h}` cùng tỉ lệ) — [MGX-01]/[JMP-01] chưa ghi trường này (overlay
chỉ có `position` dạng nhãn, cutaway chưa có toạ độ) nên hiện tại không có gì
để kiểm; script vẫn chạy đúng, chỉ chưa có việc để làm cho tới khi 2 story đó
ghi `rect`.

Đạt khi: 0 mục lấn
Phục vụ: [CAP] · TDD §12.1 · Lộ trình: Tuần 3
"""

from __future__ import annotations

import sys

from lib import config, paths, plan_io


def _load(path):
    if not path.exists():
        return None
    data, _ = plan_io.load_plan(path)
    return data


def _overlaps(a: dict, b: dict) -> bool:
    return a["x"] < b["x"] + b["w"] and a["x"] + a["w"] > b["x"] and a["y"] < b["y"] + b["h"] and a["y"] + a["h"] > b["y"]


def main() -> int:
    style = config.caption_style()
    forbidden = style.forbidden_zone

    violations: list[str] = []
    checked = 0
    for kind, path in (("overlay", paths.OVERLAY_PLAN), ("cutaway", paths.CUTAWAY_PLAN)):
        plan = _load(path)
        if plan is None:
            continue
        for item in plan.get("items", []):
            rect = item.get("rect")
            if not rect:
                continue  # chưa có toạ độ pixel — không suy đoán, bỏ qua có chủ đích
            checked += 1
            if _overlaps(rect, forbidden):
                violations.append(f"{kind}:{item.get('id')} — rect={rect} lấn vùng cấm caption")

    if not violations:
        print(f"✓ check_layout — 0 mục lấn ({checked} mục có toạ độ đã kiểm)")
        return 0

    print(f"✗ check_layout — {len(violations)} mục lấn")
    for line in violations:
        print(f"  {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

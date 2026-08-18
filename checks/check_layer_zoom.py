"""Biến đổi zoom chỉ xuất hiện trong khai báo lớp 1.

`zoom_level` là trường ĐÁNH DẤU zoom (lib.zoom) — không được rò rỉ vào
caption_plan.json / overlay_plan.json / cutaway_plan.json (lớp 4/3/2).

Đạt khi: 0 lớp 2/3/4 bị zoom
Phục vụ: §6.1 · TDD §12.1 · Lộ trình: Tuần 3
"""

from __future__ import annotations

import sys

from lib import paths, plan_io

MARKER_KEY = "zoom_level"
OTHER_LAYERS = (("caption", paths.CAPTION_PLAN), ("overlay", paths.OVERLAY_PLAN), ("cutaway", paths.CUTAWAY_PLAN))


def _load(path):
    if not path.exists():
        return None
    data, _ = plan_io.load_plan(path)
    return data


def main() -> int:
    hits: list[str] = []
    for kind, path in OTHER_LAYERS:
        plan = _load(path)
        if plan is None:
            continue
        for item in plan.get("items", []):
            if MARKER_KEY in item:
                hits.append(f"{kind}:{item.get('id')} — có trường '{MARKER_KEY}', chỉ lớp 1 được phép")

    if not hits:
        print("✓ check_layer_zoom — 0 lớp 2/3/4 bị zoom")
        return 0

    print(f"✗ check_layer_zoom — {len(hits)} vi phạm")
    for hit in hits:
        print(f"  {hit}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

"""Mỗi điểm cắt đã áp có đúng 1 mục che trong ±100ms.

"Điểm cắt" (v1.1) = 1 chỗ nối trên timeline SAU cắt giữa 2 đoạn giữ liền kề —
không phải 1 mục trong cut_plan.json (TDD §5.4). Zoom đổi mức đúng tại mọi
ranh giới đoạn theo thiết kế (lib.zoom), nên tự che 100% điểm cắt; cutaway
chỉ cần khớp trong cửa sổ dung sai khi có.

Đạt khi: 100%, in '42/42 · 0 điểm trần'
Phục vụ: [JMP] · TDD §12.1 · Lộ trình: Tuần 3
"""

from __future__ import annotations

import sys

from lib import config, paths, plan_io, timeline

TOLERANCE_SEC = 0.100


def _load(path):
    if not path.exists():
        return None
    data, _ = plan_io.load_plan(path)
    return data


def main() -> int:
    transcript = _load(paths.TRANSCRIPT)
    cut_plan = _load(paths.CUT_PLAN)
    if transcript is None or cut_plan is None or cut_plan.get("approved_at") is None:
        print("✓ check_cut_coverage — chưa có cut_plan.json đã duyệt, không có gì để kiểm")
        return 0

    cfg = config.cut_config()
    padding_sec = cfg.silence.padding_each_side_ms / 1000.0
    words = transcript["words"]
    duration = transcript["duration_sec"]

    removals = timeline.removal_intervals(words, cut_plan["items"], duration, padding_sec=padding_sec)
    kept_segments = timeline.kept_segments(removals, duration)
    joints = _joint_times(kept_segments)

    if not joints:
        print("✓ check_cut_coverage — 0/0 điểm cắt đã che · 0 điểm trần (không có điểm cắt nào)")
        return 0

    zoom_plan = _load(paths.ZOOM_PLAN)
    if zoom_plan is None:
        print("✗ check_cut_coverage — chưa có work/zoom_plan.json")
        print("  → Chạy: python -m steps.06_build_cutaway")
        return 1

    cutaway_plan = _load(paths.CUTAWAY_PLAN)
    cutaway_windows = (
        _cutaway_windows(cutaway_plan, words, cut_plan, duration, padding_sec) if cutaway_plan else []
    )
    zoom_levels = [item["zoom_level"] for item in zoom_plan.get("items", [])]

    uncovered = [
        t
        for index, t in enumerate(joints)
        if not (_zoom_covers(zoom_levels, index) or _cutaway_covers(cutaway_windows, t))
    ]

    total = len(joints)
    covered = total - len(uncovered)
    if not uncovered:
        print(f"✓ check_cut_coverage — {covered}/{total} điểm cắt đã che · 0 điểm trần")
        return 0

    print(f"✗ check_cut_coverage — {covered}/{total} điểm cắt đã che · {len(uncovered)} điểm trần")
    for t in uncovered:
        print(f"  {t:.3f}s — không có zoom hoặc cutaway che")
    return 1


def _joint_times(kept_segments: list[tuple[float, float]]) -> list[float]:
    """Mốc thời gian trên timeline SAU CẮT của từng ranh giới đoạn — bỏ mốc cuối (hết video)."""
    times: list[float] = []
    cursor = 0.0
    for lo, hi in kept_segments:
        cursor += hi - lo
        times.append(round(cursor, 3))
    return times[:-1]


def _zoom_covers(levels: list[float], joint_index: int) -> bool:
    """Ranh giới `joint_index` nằm giữa đoạn `joint_index` và `joint_index+1`."""
    if joint_index + 1 >= len(levels):
        return False
    return levels[joint_index] != levels[joint_index + 1]


def _cutaway_covers(windows: list[tuple[float, float]], t: float) -> bool:
    return any(lo - TOLERANCE_SEC <= t <= hi + TOLERANCE_SEC for lo, hi in windows)


def _cutaway_windows(cutaway_plan, words, cut_plan, duration, padding_sec) -> list[tuple[float, float]]:
    timeline_map = timeline.build_timeline_map(words, cut_plan["items"], duration, padding_sec=padding_sec)
    windows = []
    for item in cutaway_plan.get("items", []):
        start_id, end_id = item.get("anchor_start"), item.get("anchor_end")
        if start_id in timeline_map and end_id in timeline_map:
            windows.append((timeline_map[start_id][0], timeline_map[end_id][1]))
    return windows


if __name__ == "__main__":
    sys.exit(main())

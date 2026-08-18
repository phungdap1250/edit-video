"""Gán mức zoom luân phiên cho các đoạn giữ lại — TDD §5.4, §6.1.

Zoom là lớp 1 DUY NHẤT (video người nói) — trường `zoom_level` không được xuất
hiện ở bất kỳ plan nào khác (`checks/check_layer_zoom.py` thi hành điều này).
"""

from __future__ import annotations


def build_schedule(
    kept_segments: list[tuple[float, float]], max_safe_zoom: float, cfg
) -> list[dict]:
    """Một mục / đoạn giữ lại, mức zoom trong [min, effective_max], không lặp liền kề.

    `kept_segments` là các đoạn TRÊN TIMELINE SAU CẮT (đã nối liên tục — mỗi
    ranh giới giữa 2 đoạn liên tiếp chính là 1 "điểm cắt", TDD §5.4).
    """
    low = float(cfg.zoom.min)
    effective_max = round(min(float(cfg.zoom.max), max_safe_zoom), 3)
    peak_levels = _peak_levels(low, effective_max)

    items: list[dict] = []
    cursor = 0.0
    peak_cursor = 0
    for index, (_orig_lo, orig_hi) in enumerate(kept_segments):
        duration = round(orig_hi - _orig_lo, 3)
        t_start, t_end = round(cursor, 3), round(cursor + duration, 3)
        if index % 2 == 0 or not peak_levels:
            level = low
        else:
            level = peak_levels[peak_cursor % len(peak_levels)]
            peak_cursor += 1
        items.append(
            {
                "id": f"zoom_{index:03d}",
                "segment_index": index,
                "t_start": t_start,
                "t_end": t_end,
                "zoom_level": level,
                "layer": 1,
            }
        )
        cursor = t_end

    return items


def _peak_levels(low: float, effective_max: float, steps: int = 3) -> list[float]:
    """Vài mức đỉnh cách đều trong (low, effective_max] — vd 106%, 108%, 110%.

    `steps` mức khác nhau đủ để không cần lặp 2 đỉnh liên tiếp giống nhau khi
    luân phiên với `low` ở giữa (đoạn `low` luôn chen giữa 2 đoạn đỉnh).
    """
    if effective_max <= low:
        return []
    span = effective_max - low
    return [round(low + span * (i + 1) / steps, 3) for i in range(steps)]

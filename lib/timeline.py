"""Dịch cut_plan thành khoảng bị xoá và bảng tra neo → giây. TDD §5.2 bước 3.

Đây là điểm DUY NHẤT trong hệ thống tính timeline sau cắt. Caption, overlay,
cutaway, render đều đi qua đây — một hàm, một nơi để sửa, một nơi để kiểm.
"""

from __future__ import annotations

from bisect import bisect_right

from lib.errors import AIEditorError

BOF_ID = "w0000"  # neo biên đầu video — không text, không hiện caption
EOF_ID = "wEOF"  # neo biên cuối video


def is_active(item: dict) -> bool:
    """Cut được tính vào timeline: đã duyệt và không bị cut cha nuốt."""
    return item.get("status") == "accepted" and not item.get("absorbed_by")


def _bounds(words: list[dict], duration_sec: float) -> dict[str, tuple[float, float]]:
    """Bảng tra id → (start, end), có cả 2 neo biên."""
    table = {w["id"]: (float(w["start"]), float(w["end"])) for w in words}
    table[BOF_ID] = (0.0, 0.0)
    table[EOF_ID] = (duration_sec, duration_sec)
    return table


def removal_intervals(
    words: list[dict], cut_items: list[dict], duration_sec: float, *, padding_sec: float = 0.1
) -> list[tuple[float, float]]:
    """Khoảng thời gian bị xoá khỏi footage gốc, đã gộp và sắp xếp.

    · `silence` — thu gọn khoảng lặng còn `keep_ms`, xoá phần giữa
    · `filler` / `retake` — xoá trọn các từ, nhưng chừa `padding_sec` mỗi đầu
      để không cụt chữ đầu/cuối câu của đoạn giữ lại
    """
    table = _bounds(words, duration_sec)
    order = {w["id"]: i for i, w in enumerate(words)}
    raw: list[tuple[float, float]] = []

    for item in cut_items:
        if not is_active(item):
            continue
        start_id, end_id = item.get("anchor_start"), item.get("anchor_end")
        if start_id not in table or end_id not in table:
            raise AIEditorError(
                f"Cut {item.get('id')} neo vào từ không tồn tại: {start_id} → {end_id}",
                suggestion="Chạy: python -m tools.reanchor",
            )

        if item.get("kind") == "silence":
            gap_start, gap_end = table[start_id][1], table[end_id][0]
            keep = item.get("keep_ms", 0) / 1000.0
            if gap_end - gap_start <= keep:
                continue
            margin = keep / 2
            raw.append((gap_start + margin, gap_end - margin))
            continue

        lo, hi = table[start_id][0], table[end_id][1]
        # Chừa padding so với từ được giữ liền kề — chỉ ràng buộc khi khe quá hẹp
        previous = words[order[start_id] - 1] if order.get(start_id, 0) > 0 else None
        following = (
            words[order[end_id] + 1] if order.get(end_id, len(words) - 1) < len(words) - 1 else None
        )
        if previous is not None:
            lo = max(lo, float(previous["end"]) + padding_sec)
        if following is not None:
            hi = min(hi, float(following["start"]) - padding_sec)
        if hi > lo:
            raw.append((lo, hi))

    return merge(raw)


def merge(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Gộp các khoảng chồng lấn hoặc liền nhau."""
    merged: list[tuple[float, float]] = []
    for lo, hi in sorted(intervals):
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


def kept_segments(
    removals: list[tuple[float, float]], duration_sec: float
) -> list[tuple[float, float]]:
    """Phần bù của removals — chính là danh sách đoạn ffmpeg phải giữ."""
    segments: list[tuple[float, float]] = []
    cursor = 0.0
    for lo, hi in removals:
        if lo > cursor:
            segments.append((round(cursor, 3), round(lo, 3)))
        cursor = max(cursor, hi)
    if cursor < duration_sec:
        segments.append((round(cursor, 3), round(duration_sec, 3)))
    return segments


class Shifter:
    """Đổi giây trên timeline gốc sang giây trên timeline sau cắt."""

    def __init__(self, removals: list[tuple[float, float]]):
        self._starts = [lo for lo, _ in removals]
        self._removals = removals
        self._cumulative: list[float] = []
        total = 0.0
        for lo, hi in removals:
            total += hi - lo
            self._cumulative.append(total)

    def removed_before(self, t: float) -> float:
        index = bisect_right(self._starts, t) - 1
        if index < 0:
            return 0.0
        lo, hi = self._removals[index]
        before = self._cumulative[index - 1] if index else 0.0
        return before + (min(t, hi) - lo)

    def shift(self, t: float) -> float:
        return round(t - self.removed_before(t), 3)

    def is_removed(self, start: float, end: float) -> bool:
        """Từ bị xoá khi phần lớn thời lượng của nó nằm trong vùng xoá."""
        covered = sum(
            max(0.0, min(end, hi) - max(start, lo)) for lo, hi in self._removals
        )
        return covered >= (end - start) * 0.5


def build_timeline_map(
    words: list[dict], cut_items: list[dict], duration_sec: float, *, padding_sec: float = 0.1
) -> dict[str, tuple[float, float]]:
    """word_id → (start_mới, end_mới) sau cắt. Từ bị cắt không có trong bảng."""
    removals = removal_intervals(
        words, cut_items, duration_sec, padding_sec=padding_sec
    )
    shifter = Shifter(removals)
    timeline: dict[str, tuple[float, float]] = {}

    for word in words:
        start, end = float(word["start"]), float(word["end"])
        if shifter.is_removed(start, end):
            continue
        timeline[word["id"]] = (shifter.shift(start), shifter.shift(end))

    total_kept = duration_sec - sum(hi - lo for lo, hi in removals)
    timeline[BOF_ID] = (0.0, 0.0)
    timeline[EOF_ID] = (round(total_kept, 3), round(total_kept, 3))
    return timeline

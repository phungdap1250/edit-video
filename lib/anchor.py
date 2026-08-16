"""Neo ID từ — trái tim của quyết định 4. TDD §3.2, §5.2, §5.6.

Luật vàng: thứ tự từ xác định bằng VỊ TRÍ trong mảng words, không bằng giá trị ID.
ID cấp một chiều, không bao giờ tái sử dụng.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from lib.errors import AIEditorError

ID_PREFIX = "w"
ID_WIDTH = 4
REANCHOR_GUARD_SEC = 2.0  # chốt an toàn ±2s khi kế thừa ID — TDD QĐ 4


def format_id(n: int) -> str:
    return f"{ID_PREFIX}{n:0{ID_WIDTH}d}"


def assign_ids(words: list[dict], next_id: int = 1) -> tuple[list[dict], int]:
    """Cấp ID cho từ chưa có ID. Bộ đếm CHỈ TĂNG."""
    for word in words:
        if not word.get("id"):
            word["id"] = format_id(next_id)
            next_id += 1
    return words, next_id


def _key(word: dict) -> tuple[str, float]:
    """Khoá diff: (text, start) — không dùng text đơn lẻ vì cụm lặp sẽ căn lệch."""
    return (word["text"], round(float(word["start"]), 3))


def inherit_ids(
    old_words: list[dict], new_words: list[dict], next_id: int
) -> tuple[list[dict], int, list[str]]:
    """Diff dãy để từ cũ giữ nguyên ID sau khi sửa transcript.

    Trả (new_words đã gắn ID, next_id mới, danh sách ID đã biến mất).
    Từ khớp nhưng lệch thời điểm quá REANCHOR_GUARD_SEC thì KHÔNG kế thừa —
    thà cấp ID mới (hỏng ồn ào) còn hơn neo nhầm từ (hỏng im lặng).
    """
    matcher = SequenceMatcher(
        a=[_key(w) for w in old_words], b=[_key(w) for w in new_words], autojunk=False
    )
    inherited: set[str] = set()
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            continue
        for offset in range(i2 - i1):
            old, new = old_words[i1 + offset], new_words[j1 + offset]
            if abs(float(old["start"]) - float(new["start"])) > REANCHOR_GUARD_SEC:
                continue
            new["id"] = old["id"]
            inherited.add(old["id"])

    new_words, next_id = assign_ids(new_words, next_id)
    lost = [w["id"] for w in old_words if w["id"] not in inherited]
    return new_words, next_id, lost


def build_timeline_map(
    words: list[dict], cut_items: list[dict], *, padding_ms: int = 100
) -> dict[str, tuple[float, float]]:
    """Ánh xạ word.id → (start, end) trên timeline SAU KHI CẮT.

    Từ nằm trong một cut `accepted` bị loại khỏi map — mọi neo trỏ vào nó là
    neo mồ côi và bị `check_anchor_integrity.py` bắt.
    """
    removed = _removed_word_ids(words, cut_items)
    pad = padding_ms / 1000.0

    timeline: dict[str, tuple[float, float]] = {}
    cursor = 0.0
    previous_end: float | None = None

    for word in words:
        if word["id"] in removed:
            previous_end = None
            continue
        start, end = float(word["start"]), float(word["end"])
        if previous_end is None:
            cursor += pad if timeline else 0.0
        else:
            cursor += max(0.0, start - previous_end)
        timeline[word["id"]] = (round(cursor, 3), round(cursor + (end - start), 3))
        cursor += end - start
        previous_end = end

    return timeline


def _removed_word_ids(words: list[dict], cut_items: list[dict]) -> set[str]:
    order = {w["id"]: i for i, w in enumerate(words)}
    removed: set[str] = set()
    for item in cut_items:
        if item.get("status") != "accepted" or item.get("kind") == "silence":
            continue
        start, end = item.get("anchor_start"), item.get("anchor_end")
        if start not in order or end not in order:
            raise AIEditorError(
                f"Cut {item.get('id')} neo vào từ không tồn tại: {start} → {end}",
                suggestion="Chạy: python -m tools.reanchor",
            )
        for word in words[order[start] : order[end] + 1]:
            removed.add(word["id"])
    return removed


def resolve(anchor: str, timeline: dict[str, tuple[float, float]]) -> tuple[float, float]:
    """Timestamp là thứ TÍNH RA ĐƯỢC từ neo, không phải thứ lưu cứng — §13.2."""
    if anchor not in timeline:
        raise AIEditorError(
            f"Neo {anchor} không còn tồn tại sau khi cắt",
            suggestion="Chạy: python -m tools.reanchor để xem mục cần duyệt lại",
        )
    return timeline[anchor]

"""Neo ID từ — trái tim của quyết định 4. TDD §3.2, §5.2, §5.6.

Luật vàng: thứ tự từ xác định bằng VỊ TRÍ trong mảng words, không bằng giá trị ID.
ID cấp một chiều, không bao giờ tái sử dụng.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from lib import timeline
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


# build_timeline_map sống ở lib/timeline.py cùng phép tính khoảng bị xoá — nơi
# này chỉ tái xuất để mọi chỗ gọi vẫn theo đúng chữ ký TDD §5.2 bước 3.
#
# Hai neo biên w0000 / wEOF là ẢO: chúng chỉ tồn tại trong bảng tra của
# timeline.py, KHÔNG nằm trong transcript.words[]. Nhét chúng vào words[] sẽ
# làm hỏng khoá diff (text, start) của inherit_ids và len vào lớp caption.
build_timeline_map = timeline.build_timeline_map


def resolve(anchor: str, timeline: dict[str, tuple[float, float]]) -> tuple[float, float]:
    """Timestamp là thứ TÍNH RA ĐƯỢC từ neo, không phải thứ lưu cứng — §13.2."""
    if anchor not in timeline:
        raise AIEditorError(
            f"Neo {anchor} không còn tồn tại sau khi cắt",
            suggestion="Chạy: python -m tools.reanchor để xem mục cần duyệt lại",
        )
    return timeline[anchor]

"""Ngữ cảnh dùng chung cho 3 cơ chế phát hiện cắt — TDD §5.2 bước 2."""

from __future__ import annotations

from dataclasses import dataclass

from lib.normalize import strip_diacritics

SENTENCE_END_CHARS = ".?!…"
SENTENCE_GAP_MS = 1000  # khoảng lặng > 1s cũng tính là ranh giới câu


@dataclass
class Context:
    """Bọc words[] kèm các phép tra cứu mà cả 3 cơ chế đều cần."""

    words: list[dict]
    duration_sec: float

    def gap_before_ms(self, i: int) -> float:
        """Khoảng lặng ngay trước từ thứ i. Từ đầu tiên tính từ mốc 0."""
        if i <= 0:
            return float(self.words[0]["start"]) * 1000 if self.words else 0.0
        return (float(self.words[i]["start"]) - float(self.words[i - 1]["end"])) * 1000

    def gap_after_ms(self, i: int) -> float:
        """Khoảng lặng ngay sau từ thứ i. Từ cuối tính tới hết video."""
        if i >= len(self.words) - 1:
            return (self.duration_sec - float(self.words[-1]["end"])) * 1000
        return (float(self.words[i + 1]["start"]) - float(self.words[i]["end"])) * 1000

    def is_sentence_end(self, i: int) -> bool:
        if i >= len(self.words) - 1:
            return True
        text = self.words[i]["text"].strip()
        return text[-1:] in SENTENCE_END_CHARS or self.gap_after_ms(i) > SENTENCE_GAP_MS

    def is_sentence_start(self, i: int) -> bool:
        return i == 0 or self.is_sentence_end(i - 1)

    def sentence_start_index(self, i: int) -> int:
        """Chỉ số từ đầu câu chứa từ thứ i — mốc lùi của tầng 1."""
        cursor = i
        while cursor > 0 and not self.is_sentence_start(cursor):
            cursor -= 1
        return cursor

    def key(self, i: int) -> str:
        """Chuỗi so khớp: chữ thường, bỏ dấu, bỏ dấu câu."""
        return strip_diacritics(self.words[i]["text"]).lower().strip(".,!?…:;\"'")

    def phrase(self, start: int, end: int) -> str:
        """Nguyên văn cụm từ start..end — dùng cho anchor_text và context."""
        return " ".join(w["text"] for w in self.words[start : end + 1])


def make_item(
    item_id: str,
    kind: str,
    ctx: Context,
    start: int,
    end: int,
    *,
    status: str,
    tier: int = 0,
    confidence: float = 1.0,
    group: str | None = None,
    decided_by: str = "auto",
) -> dict:
    """Dựng một mục cut_plan neo vào ID từ. Timestamp chỉ để đọc bằng mắt."""
    return {
        "id": item_id,
        "kind": kind,
        "group": group,
        "anchor_start": ctx.words[start]["id"],
        "anchor_end": ctx.words[end]["id"],
        "anchor_text": ctx.phrase(start, end),
        "t_start": round(float(ctx.words[start]["start"]), 3),
        "t_end": round(float(ctx.words[end]["end"]), 3),
        "tier": tier,
        "confidence": round(confidence, 2),
        "context": ctx.phrase(max(0, start - 6), min(len(ctx.words) - 1, end + 6)),
        "absorbed_by": None,
        "status": status,
        "decided_by": decided_by,
    }

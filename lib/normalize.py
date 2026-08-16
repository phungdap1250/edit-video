"""Chuẩn hoá transcript TRƯỚC khi gán ID — TDD §5.2 bước 1.

Bắt buộc chạy trước `anchor.assign_ids()`. Chạy sau thì mỗi lần làm tròn khác
nhau sẽ đẩy khoá diff `(text, start)` lệch đi và ID nhảy lung tung.
"""

from __future__ import annotations

import re
import unicodedata

MS = 3  # giây làm tròn 3 chữ số thập phân — TDD §13.5


def normalize_words(words: list[dict]) -> list[dict]:
    """Làm tròn timestamp, chuẩn hoá Unicode, vá mốc chồng lấn/ngược."""
    out: list[dict] = []
    previous_end = 0.0
    for word in words:
        text = unicodedata.normalize("NFC", str(word.get("text", "")).strip())
        if not text:
            continue
        start = round(max(float(word["start"]), previous_end), MS)
        end = round(max(float(word["end"]), start), MS)
        out.append({**word, "text": text, "start": start, "end": end})
        previous_end = end
    return out


def strip_diacritics(text: str) -> str:
    """Bỏ dấu để so khớp tầng 2 — TDD §5.2."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", stripped).replace("đ", "d").replace("Đ", "D")


def tokenize(text: str) -> list[str]:
    """Chuỗi token để so khớp — thường dùng kèm strip_diacritics()."""
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def silence_gaps(words: list[dict]) -> list[tuple[str, str, int]]:
    """Khoảng lặng giữa hai từ kẹp: (id trước, id sau, độ dài ms) — TDD §3.3."""
    gaps: list[tuple[str, str, int]] = []
    for previous, current in zip(words, words[1:]):
        gap_ms = int(round((float(current["start"]) - float(previous["end"])) * 1000))
        if gap_ms > 0:
            gaps.append((previous["id"], current["id"], gap_ms))
    return gaps

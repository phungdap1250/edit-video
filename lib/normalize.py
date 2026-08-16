"""Chuẩn hoá transcript TRƯỚC khi gán ID — TDD §5.2 bước 1.

Bắt buộc chạy trước `anchor.assign_ids()`. Chạy sau thì mỗi lần làm tròn khác
nhau sẽ đẩy khoá diff `(text, start)` lệch đi và ID nhảy lung tung.
"""

from __future__ import annotations

import re
import unicodedata

from lib import log

MS = 3  # giây làm tròn 3 chữ số thập phân — TDD §13.5
MIN_WORD_DUR_SEC = 0.030  # từ ngắn hơn 30ms được kéo dài, mượn từ khoảng lặng kề
OVERLAP_WARN_SEC = 0.100  # chồng lấn quá mức này thì ghi WARN


def normalize_words(words: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """Chuẩn hoá timestamp trước khi gán ID — TDD §5.2.

    Bốn luật: ép tăng đơn điệu · từ < 30ms kéo dài · chồng lấn > 100ms ghi WARN
    và kẹp về ranh giới · đếm số ca đã sửa.

    Trả (words đã chuẩn hoá, thống kê số ca sửa).
    """
    out: list[dict] = []
    fixes = {"monotonic": 0, "too_short": 0, "big_overlap": 0, "empty": 0}
    previous_end = 0.0

    for word in words:
        text = unicodedata.normalize("NFC", str(word.get("text", "")).strip())
        if not text:
            fixes["empty"] += 1
            continue

        start, end = float(word["start"]), float(word["end"])
        if start < previous_end:
            overlap = previous_end - start
            fixes["monotonic"] += 1
            if overlap > OVERLAP_WARN_SEC:
                fixes["big_overlap"] += 1
                log.warn(
                    f"chồng lấn {overlap * 1000:.0f}ms tại từ '{text}' "
                    f"({start:.3f}s) — kẹp về ranh giới"
                )
            start = previous_end

        if end - start < MIN_WORD_DUR_SEC:
            fixes["too_short"] += 1
            end = start + MIN_WORD_DUR_SEC

        start, end = round(start, MS), round(end, MS)
        out.append({**word, "text": text, "start": start, "end": end})
        previous_end = end

    total = sum(fixes.values())
    if total:
        log.info(
            f"chuẩn hoá transcript: {total} ca sửa "
            f"(đơn điệu {fixes['monotonic']}, quá ngắn {fixes['too_short']}, "
            f"chồng lấn lớn {fixes['big_overlap']}, rỗng {fixes['empty']})"
        )
    return out, fixes


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

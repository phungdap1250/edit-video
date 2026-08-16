"""Tầng 1 + Tầng 2 — nói vấp / thu lại. TDD §5.2 bảng "3 tầng, chạy tuần tự".

Tầng 1 (từ khoá "cắt cắt") chạy trước, cắt tự động. Tầng 2 (so khớp văn bản)
chỉ xét trên phần CÒN LẠI sau tầng 1 — nhận `consumed` để loại các từ đã dùng.
Tầng 3 (Claude đọc ngữ cảnh) không có code ở đây — đó là việc Claude làm qua
`tools.claude_write --kind cut`, xem TDD §7.1.
"""

from __future__ import annotations

from lib.cut_context import Context, make_item
from lib.normalize import strip_diacritics, tokenize


def detect_tier1(ctx: Context, cfg, start_index: int = 1) -> tuple[list[dict], set[int]]:
    """Từ khoá ra hiệu — nói sai thì nói "cắt cắt" rồi nói lại.

    Xoá từ mốc gần nhất trước đó (đầu câu hoặc khoảng lặng > 1s) đến hết từ khoá.
    Chỉ nhận khi khoá đứng liền sau khoảng lặng ≥300ms và trước khoảng lặng ≥300ms
    — ca nghi ngờ (khoá xuất hiện tự nhiên trong câu) đẩy xuống tầng 3, không tự cắt.
    """
    retake = cfg.retake
    keyword_tokens = tokenize(strip_diacritics(retake.tier1_keyword))
    n = len(keyword_tokens)
    items: list[dict] = []
    consumed: set[int] = set()
    counter = start_index

    i = 0
    while i <= len(ctx.words) - n:
        window = [ctx.key(i + offset) for offset in range(n)]
        if window != keyword_tokens:
            i += 1
            continue

        keyword_end = i + n - 1
        before_ok = ctx.gap_before_ms(i) >= retake.tier1_requires_silence_before_ms
        after_ok = ctx.gap_after_ms(keyword_end) >= retake.tier1_requires_silence_after_ms
        if not (before_ok and after_ok):
            i = keyword_end + 1  # nghi ngờ — để tầng 3 xét, không tiêu thụ vùng
            continue

        anchor_start = ctx.sentence_start_index(i)
        items.append(
            make_item(
                f"cut_{counter:03d}", "retake", ctx, anchor_start, keyword_end,
                status="accepted", tier=1, confidence=0.99, decided_by="auto",
            )
        )
        consumed.update(range(anchor_start, keyword_end + 1))
        counter += 1
        i = keyword_end + 1

    return items, consumed


def detect_tier2(
    ctx: Context, cfg, consumed: set[int], start_index: int = 1
) -> list[dict]:
    """So khớp văn bản — hai cụm liền kề trong window giây, giống nhau ≥ ngưỡng.

    So trên chuỗi token đã bỏ dấu, bỏ từ đệm (retake.tier2_strip_*). Đề xuất
    "giữ lần sau, bỏ lần trước" — cụm TRƯỚC bị đề xuất cắt.
    """
    retake = cfg.retake
    fillers = set(_filler_set())
    window_sec = retake.tier2_window_sec
    threshold = retake.tier2_similarity_threshold

    keys = [ctx.key(i) for i in range(len(ctx.words))]
    if retake.tier2_strip_fillers:
        keys = [k if k not in fillers else "" for k in keys]

    items: list[dict] = []
    counter = start_index
    n = len(ctx.words)

    i = 0
    while i < n:
        if i in consumed:
            i += 1
            continue
        max_len = min(12, n - i - 1)
        best: tuple[float, int, int, int] | None = None  # (score, i_end, j_start, j_end)
        # Cụm DÀI NHẤT thắng trước — đề xuất phải ôm trọn câu lặp lại, không vỡ
        # thành nhiều mảnh 1 từ chỉ vì chúng cũng "khớp" ở điểm dừng sớm hơn.
        for length in range(max_len, 0, -1):
            j = i + 1
            found = None
            while j + length <= n and float(ctx.words[j]["start"]) - float(ctx.words[i]["end"]) <= window_sec:
                i_span = keys[i : i + length]
                j_span = keys[j : j + length]
                if any(i_span) and any(j_span):
                    score = _similarity(i_span, j_span)
                    if score >= threshold and (found is None or score > found[0]):
                        found = (score, i + length - 1, j, j + length - 1)
                j += 1
            if found:
                best = found
                break

        if best is None:
            i += 1
            continue

        score, i_end, j_start, j_end = best
        if any(k in consumed for k in range(i, i_end + 1)):
            i += 1
            continue

        items.append(
            make_item(
                f"cut_{counter:03d}", "retake", ctx, i, i_end,
                status="pending", tier=2, confidence=round(score, 2), decided_by="auto",
            )
        )
        counter += 1
        i = i_end + 1  # nhảy qua cụm vừa gắn cờ, không xét chồng lấn trong tầng 2

    return items


def _similarity(a: list[str], b: list[str]) -> float:
    """Tỉ lệ token trùng nhau, vị trí-độc lập (đủ cho câu nói lặp lại)."""
    if len(a) != len(b):
        return 0.0
    matches = sum(1 for x, y in zip(a, b) if x and x == y)
    return matches / len(a)


def _filler_set() -> list[str]:
    from lib.config import filler_words

    return [strip_diacritics(w).lower() for w in filler_words()]

"""Từ đệm nhóm A/B — TDD §5.2 bảng "Thứ tự | Cơ chế".

Nhóm A: đứng MỘT MÌNH giữa hai khoảng lặng → cắt tự động.
Nhóm B: nằm giữa dòng chảy câu → chỉ đề xuất, mặc định KHÔNG cắt.

Luật cứng: không cắt từ đệm nếu nó là từ đầu tiên hoặc cuối cùng của một câu
có nghĩa — tránh cụt đầu/cuối câu.
"""

from __future__ import annotations

from lib.config import filler_words
from lib.cut_context import Context, make_item
from lib.normalize import strip_diacritics


def detect(ctx: Context, cfg, consumed: set[int], start_index: int = 1) -> list[dict]:
    fillers = {strip_diacritics(w).lower() for w in filler_words()}
    if not fillers:
        return []

    silence_ms = cfg.filler.group_a_requires_silence_ms
    guard_boundary = cfg.filler.never_cut_if_sentence_boundary

    items: list[dict] = []
    counter = start_index

    for i, word in enumerate(ctx.words):
        if i in consumed or ctx.key(i) not in fillers:
            continue
        if guard_boundary and (ctx.is_sentence_start(i) or ctx.is_sentence_end(i)):
            continue

        is_group_a = (
            ctx.gap_before_ms(i) >= silence_ms and ctx.gap_after_ms(i) >= silence_ms
        )
        group = "A" if is_group_a else "B"
        items.append(
            make_item(
                f"cut_{counter:03d}", "filler", ctx, i, i,
                status="accepted" if is_group_a else "pending",
                group=group,
                confidence=0.95 if is_group_a else 0.55,
                decided_by="auto",
            )
        )
        counter += 1

    return items

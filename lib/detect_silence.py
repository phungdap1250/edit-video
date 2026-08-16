"""Khoảng lặng theo bậc — TDD §5.2, PRD [CUT] bảng khoảng lặng.

Neo vào CẶP TỪ KẸP: anchor_start = từ cuối trước khoảng lặng, anchor_end = từ
đầu sau khoảng lặng. Giây không suy được từ neo (rút 2.4s xuống 400ms phụ thuộc
config), nên gap_original_ms và keep_ms được ghi lại để tái lập chính xác.
"""

from __future__ import annotations

from lib.cut_context import Context
from lib.timeline import BOF_ID, EOF_ID


def detect(ctx: Context, cfg, start_index: int = 1) -> list[dict]:
    """Trả danh sách mục `kind=silence`, đều ở trạng thái accepted."""
    silence = cfg.silence
    items: list[dict] = []
    counter = start_index

    for gap_ms, before_id, after_id, before_text, after_text in _gaps(ctx):
        keep_ms = _keep_ms(gap_ms, before_id, after_id, silence)
        if keep_ms is None or gap_ms <= keep_ms:
            continue
        items.append(
            {
                "id": f"cut_{counter:03d}",
                "kind": "silence",
                "group": None,
                "anchor_start": before_id,
                "anchor_end": after_id,
                "anchor_text": f"{before_text} → {after_text}",
                "gap_original_ms": int(round(gap_ms)),
                "keep_ms": int(keep_ms),
                "tier": 0,
                "confidence": 1.0,
                "absorbed_by": None,
                "status": "accepted",
                "decided_by": "auto",
            }
        )
        counter += 1
    return items


def _gaps(ctx: Context):
    """Mọi khoảng lặng, gồm cả hai biên đầu/cuối video."""
    if not ctx.words:
        return
    first, last = ctx.words[0], ctx.words[-1]

    yield (float(first["start"]) * 1000, BOF_ID, first["id"], "⟨đầu video⟩", first["text"])

    for i in range(len(ctx.words) - 1):
        current, following = ctx.words[i], ctx.words[i + 1]
        yield (
            ctx.gap_after_ms(i),
            current["id"],
            following["id"],
            current["text"],
            following["text"],
        )

    yield (
        (ctx.duration_sec - float(last["end"])) * 1000,
        last["id"],
        EOF_ID,
        last["text"],
        "⟨cuối video⟩",
    )


def _keep_ms(gap_ms: float, before_id: str, after_id: str, silence) -> int | None:
    """Bậc rút gọn. Trả None khi khoảng lặng ngắn, không cần đụng vào."""
    if before_id == BOF_ID or after_id == EOF_ID:
        return silence.trim_edges_to_ms
    if gap_ms < silence.keep_below_ms:
        return None
    if gap_ms <= silence.mid_threshold_ms:
        return silence.trim_mid_to_ms
    return silence.trim_long_to_ms

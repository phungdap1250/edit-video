"""Context — nền tảng dùng chung của cả 3 cơ chế phát hiện. TDD §5.2."""

from __future__ import annotations

from lib.cut_context import Context, make_item


def words(*specs) -> list[dict]:
    return [{"id": wid, "text": text, "start": s, "end": e} for wid, text, s, e in specs]


def test_gap_before_tu_dau_tien_tinh_tu_moc_0():
    ctx = Context(words=words(("w1", "a", 0.5, 1.0)), duration_sec=1.0)
    assert ctx.gap_before_ms(0) == 500


def test_gap_after_tu_cuoi_tinh_toi_het_video():
    ctx = Context(words=words(("w1", "a", 0.0, 1.0)), duration_sec=2.0)
    assert ctx.gap_after_ms(0) == 1000


def test_is_sentence_end_theo_dau_cham():
    ctx = Context(words=words(("w1", "xong.", 0.0, 0.5), ("w2", "rồi", 0.5, 1.0)), duration_sec=1.0)
    assert ctx.is_sentence_end(0) is True
    assert ctx.is_sentence_end(1) is True  # từ cuối video luôn là cuối câu


def test_is_sentence_end_theo_khoang_lang_dai():
    ctx = Context(
        words=words(("w1", "xong", 0.0, 0.5), ("w2", "rồi", 2.0, 2.5)), duration_sec=2.5
    )
    assert ctx.is_sentence_end(0) is True  # khoảng lặng 1.5s > 1000ms


def test_is_sentence_start_dau_video_va_sau_dau_cau():
    ctx = Context(
        words=words(("w1", "xong.", 0.0, 0.5), ("w2", "rồi", 0.5, 1.0)), duration_sec=1.0
    )
    assert ctx.is_sentence_start(0) is True
    assert ctx.is_sentence_start(1) is True


def test_sentence_start_index_lui_ve_dung_dau_cau():
    ctx = Context(
        words=words(
            ("w1", "chào.", 0.0, 0.5), ("w2", "cái", 0.5, 0.8),
            ("w3", "phễu", 0.8, 1.1), ("w4", "này", 1.1, 1.4),
        ),
        duration_sec=1.4,
    )
    assert ctx.sentence_start_index(3) == 1  # "này" lùi về "cái"


def test_key_bo_dau_ha_chu_va_bo_dau_cau():
    ctx = Context(words=words(("w1", "Phễu,", 0.0, 0.5)), duration_sec=0.5)
    assert ctx.key(0) == "pheu"


def test_phrase_noi_dung_van():
    ctx = Context(words=words(("w1", "cái", 0.0, 0.3), ("w2", "phễu", 0.3, 0.6)), duration_sec=0.6)
    assert ctx.phrase(0, 1) == "cái phễu"


def test_make_item_tinh_dung_anchor_va_khong_am_chi_so():
    src = words(("w1", "cái", 0.0, 0.3), ("w2", "phễu", 0.3, 0.6), ("w3", "này", 0.6, 0.9))
    ctx = Context(words=src, duration_sec=0.9)
    item = make_item("cut_001", "filler", ctx, 1, 1, status="pending")
    assert item["anchor_start"] == "w2" and item["anchor_end"] == "w2"
    assert item["anchor_text"] == "phễu"
    assert item["context"] == "cái phễu này"  # cửa sổ ±6 kẹp về biên mảng, không lỗi

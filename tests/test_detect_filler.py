"""Từ đệm nhóm A (tự cắt) / B (chỉ đề xuất). TDD §5.2."""

from __future__ import annotations

from lib import config
from lib.cut_context import Context
from lib.detect_filler import detect


def words(*specs) -> list[dict]:
    return [{"id": wid, "text": text, "start": s, "end": e} for wid, text, s, e in specs]


def cfg():
    return config.cut_config()


def test_nhom_a_dung_mot_minh_giua_hai_khoang_lang_tu_cat():
    src = words(("w0001", "a", 0.0, 0.5), ("w0002", "thì", 1.0, 1.2), ("w0003", "b", 1.7, 2.0))
    ctx = Context(words=src, duration_sec=2.0)
    items = detect(ctx, cfg(), consumed=set())
    assert len(items) == 1
    assert items[0]["group"] == "A" and items[0]["status"] == "accepted"


def test_nhom_b_giua_dong_chay_cau_chi_de_xuat():
    src = words(
        ("w0001", "cái", 0.0, 0.2), ("w0002", "thì", 0.2, 0.4), ("w0003", "phễu", 0.4, 0.6),
    )
    ctx = Context(words=src, duration_sec=0.6)
    items = detect(ctx, cfg(), consumed=set())
    assert len(items) == 1
    assert items[0]["group"] == "B" and items[0]["status"] == "pending"


def test_khong_cat_neu_la_tu_dau_cau():
    src = words(("w0001", "thì", 0.0, 0.3), ("w0002", "phễu", 0.3, 0.6))
    ctx = Context(words=src, duration_sec=0.6)
    assert detect(ctx, cfg(), consumed=set()) == []


def test_khong_cat_neu_la_tu_cuoi_cau():
    src = words(("w0001", "phễu", 0.0, 0.3), ("w0002", "thì", 0.3, 0.6))  # cuối video = cuối câu
    ctx = Context(words=src, duration_sec=0.6)
    assert detect(ctx, cfg(), consumed=set()) == []


def test_bo_qua_tu_da_bi_tieu_thu():
    src = words(("w0001", "a", 0.0, 0.5), ("w0002", "thì", 1.0, 1.2), ("w0003", "b", 1.7, 2.0))
    ctx = Context(words=src, duration_sec=2.0)
    assert detect(ctx, cfg(), consumed={1}) == []

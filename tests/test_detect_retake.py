"""Tầng 1 (từ khoá "cắt cắt") + Tầng 2 (so khớp văn bản). TDD §5.2."""

from __future__ import annotations

from lib import config
from lib.cut_context import Context
from lib.detect_retake import detect_tier1, detect_tier2


def words(*specs) -> list[dict]:
    return [{"id": wid, "text": text, "start": s, "end": e} for wid, text, s, e in specs]


def cfg():
    return config.cut_config()


def test_tang1_cat_tu_moc_gan_nhat_den_het_tu_khoa():
    src = words(
        ("w0001", "cái", 0.0, 0.3), ("w0002", "phễu", 0.3, 0.6),
        ("w0003", "cắt", 1.2, 1.4), ("w0004", "cắt", 1.4, 1.6),  # liền sau lặng 600ms
        ("w0005", "cái", 2.0, 2.3), ("w0006", "phễu", 2.3, 2.6), ("w0007", "này", 2.6, 3.0),
    )
    ctx = Context(words=src, duration_sec=3.0)
    items, consumed = detect_tier1(ctx, cfg())
    assert len(items) == 1
    item = items[0]
    assert item["tier"] == 1 and item["status"] == "accepted"
    assert item["anchor_start"] == "w0001"  # lùi về đầu câu
    assert item["anchor_end"] == "w0004"    # tới hết từ khoá
    assert consumed == {0, 1, 2, 3}


def test_tang1_tu_choi_khi_khong_du_khoang_lang():
    """"cắt cắt" dính liền câu nói (không có lặng trước) → nghi ngờ, không tự cắt."""
    src = words(
        ("w0001", "nên", 0.0, 0.2), ("w0002", "cắt", 0.2, 0.4), ("w0003", "cắt", 0.4, 0.6),
        ("w0004", "chỗ", 0.6, 0.8), ("w0005", "này", 0.8, 1.0),
    )
    ctx = Context(words=src, duration_sec=1.0)
    items, consumed = detect_tier1(ctx, cfg())
    assert items == []
    assert consumed == set()


def test_tang2_bat_cum_lap_trong_15s():
    src = words(
        ("w0001", "cái", 0.0, 0.3), ("w0002", "phễu", 0.3, 0.6), ("w0003", "này", 0.6, 0.9),
        ("w0004", "cái", 3.0, 3.3), ("w0005", "phễu", 3.3, 3.6), ("w0006", "này", 3.6, 3.9),
    )
    ctx = Context(words=src, duration_sec=4.0)
    items = detect_tier2(ctx, cfg(), consumed=set())
    assert len(items) == 1
    item = items[0]
    assert item["tier"] == 2 and item["status"] == "pending"
    assert item["anchor_start"] == "w0001"  # giữ lần sau, đề xuất bỏ lần trước
    assert item["anchor_end"] == "w0003"


def test_tang2_khong_xet_vung_da_tieu_thu_boi_tang1():
    src = words(
        ("w0001", "cái", 0.0, 0.3), ("w0002", "phễu", 0.3, 0.6), ("w0003", "này", 0.6, 0.9),
        ("w0004", "cái", 3.0, 3.3), ("w0005", "phễu", 3.3, 3.6), ("w0006", "này", 3.6, 3.9),
    )
    ctx = Context(words=src, duration_sec=4.0)
    items = detect_tier2(ctx, cfg(), consumed={0, 1, 2})
    assert items == []


def test_tang2_khong_giong_thi_khong_de_xuat():
    src = words(
        ("w0001", "hôm", 0.0, 0.3), ("w0002", "nay", 0.3, 0.6), ("w0003", "trời", 0.6, 0.9),
        ("w0004", "đẹp", 3.0, 3.3), ("w0005", "quá", 3.3, 3.6),
    )
    ctx = Context(words=src, duration_sec=4.0)
    assert detect_tier2(ctx, cfg(), consumed=set()) == []

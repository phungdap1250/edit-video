"""Chuẩn hoá timestamp TRƯỚC khi gán ID — TDD §5.2. Bốn luật, chạy thật với Scribe."""

from __future__ import annotations

from lib.normalize import normalize_words, silence_gaps, strip_diacritics, tokenize


def words(*specs) -> list[dict]:
    return [{"text": text, "start": s, "end": e} for text, s, e in specs]


def test_ep_tang_don_dieu_khi_tu_sau_bat_dau_truoc_khi_tu_truoc_ket_thuc():
    src = words(("a", 1.0, 1.3), ("b", 1.2, 1.5))  # chồng lấn 100ms
    out, fixes = normalize_words(src)
    assert out[1]["start"] >= out[0]["end"]
    assert fixes["monotonic"] == 1


def test_chong_lan_qua_100ms_duoc_ghi_nhan_rieng():
    src = words(("a", 1.0, 1.5), ("b", 1.1, 1.6))  # chồng lấn 400ms
    _, fixes = normalize_words(src)
    assert fixes["big_overlap"] == 1


def test_tu_qua_ngan_duoc_keo_dai_toi_30ms():
    src = words(("a", 1.000, 1.005))  # 5ms
    out, fixes = normalize_words(src)
    assert round(out[0]["end"] - out[0]["start"], 3) >= 0.030
    assert fixes["too_short"] == 1


def test_tu_rong_bi_loai():
    src = words(("", 1.0, 1.2), ("a", 1.2, 1.4))
    out, fixes = normalize_words(src)
    assert len(out) == 1
    assert fixes["empty"] == 1


def test_khong_co_loi_thi_khong_sua_gi():
    src = words(("a", 1.0, 1.2), ("b", 1.5, 1.8))
    out, fixes = normalize_words(src)
    assert out[0]["start"] == 1.0 and out[1]["end"] == 1.8
    assert sum(fixes.values()) == 0


def test_giu_nguyen_cac_truong_khac_cua_tu():
    src = [{"text": "a", "start": 1.0, "end": 1.2, "conf": 0.87}]
    out, _ = normalize_words(src)
    assert out[0]["conf"] == 0.87


def test_strip_diacritics_bo_dau_va_chuan_hoa_d():
    assert strip_diacritics("Phễu Đúng") == "Pheu Dung"


def test_tokenize_bo_dau_cau():
    assert tokenize("cắt cắt, chỗ này.") == ["cắt", "cắt", "chỗ", "này"]


def test_silence_gaps_tinh_dung_khoang_giua_hai_tu_ke():
    src = [
        {"id": "w1", "text": "a", "start": 0.0, "end": 1.0},
        {"id": "w2", "text": "b", "start": 1.8, "end": 2.0},
    ]
    gaps = silence_gaps(src)
    assert gaps == [("w1", "w2", 800)]


def test_silence_gaps_bo_qua_khi_khong_co_khoang():
    src = [
        {"id": "w1", "text": "a", "start": 0.0, "end": 1.0},
        {"id": "w2", "text": "b", "start": 1.0, "end": 2.0},
    ]
    assert silence_gaps(src) == []

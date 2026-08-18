"""lib.cutaway_assets — khớp ảnh có sẵn với đoạn cần cutaway — TDD §5.4."""

from __future__ import annotations

from lib import cutaway_assets


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n")
    return path


def test_khop_theo_id_muc(tmp_path):
    asset = _touch(tmp_path / "cta_001_phau_marketing.png")
    match = cutaway_assets.find_match({"id": "cta_001", "anchor_text": "gì đó"}, [asset])
    assert match == asset


def test_khop_theo_tu_khoa_chung(tmp_path):
    asset = _touch(tmp_path / "phau-marketing.png")
    item = {"id": "cta_002", "anchor_text": "cái phễu marketing ba tầng"}
    match = cutaway_assets.find_match(item, [asset])
    assert match == asset


def test_khong_khop_thi_tra_none(tmp_path):
    asset = _touch(tmp_path / "khong-lien-quan.png")
    item = {"id": "cta_003", "anchor_text": "quy trình bán hàng"}
    assert cutaway_assets.find_match(item, [asset]) is None


def test_danh_sach_rong_tra_none():
    assert cutaway_assets.find_match({"id": "cta_004", "anchor_text": "x"}, []) is None


def test_list_assets_chi_lay_dinh_dang_anh(tmp_path, monkeypatch):
    from lib import paths

    monkeypatch.setattr(paths, "ASSETS", tmp_path)
    _touch(tmp_path / "a.png")
    _touch(tmp_path / "b.jpg")
    _touch(tmp_path / "notes.txt")
    result = cutaway_assets.list_assets()
    assert {p.name for p in result} == {"a.png", "b.jpg"}

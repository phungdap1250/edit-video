"""lib.field_path — đọc/ghi theo đường dẫn kiểu content.items[0].text — TDD §3.4."""

from __future__ import annotations

from lib import field_path


def test_get_path_don_gian():
    assert field_path.get_path({"a": 1}, "a") == 1


def test_get_path_long():
    d = {"content": {"number": "3"}}
    assert field_path.get_path(d, "content.number") == "3"


def test_get_path_mang():
    d = {"content": {"items": [{"text": "a"}, {"text": "b"}]}}
    assert field_path.get_path(d, "content.items[0].text") == "a"
    assert field_path.get_path(d, "content.items[1].text") == "b"


def test_get_path_khong_ton_tai_tra_none():
    assert field_path.get_path({"a": 1}, "b") is None
    assert field_path.get_path({"a": {"b": 1}}, "a.c") is None


def test_set_path_ghi_dung_vi_tri():
    d = {"content": {"items": [{"text": "a"}]}}
    field_path.set_path(d, "content.items[0].text", "MỚI")
    assert d["content"]["items"][0]["text"] == "MỚI"


def test_set_path_khong_dung_index():
    d = {"a": 1}
    field_path.set_path(d, "a", 2)
    assert d["a"] == 2

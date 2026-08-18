"""lib.frame — đọc config/frame.md — TDD §5.5."""

from __future__ import annotations

from lib import frame, paths


def test_load_that_tu_repo():
    f = frame.load()
    assert f.colors["primary"]
    assert f.font_family
    assert f.radius_px > 0
    assert f.has_rules_section is True
    assert len(f.rules) > 0


def test_thieu_file_thi_dung_mac_dinh(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "FRAME_MD", tmp_path / "khong-ton-tai.md")
    f = frame.load()
    assert f.has_rules_section is False
    assert f.colors["primary"]


def test_thieu_muc_luat_thi_dung_luat_mac_dinh(tmp_path, monkeypatch):
    md = tmp_path / "frame.md"
    md.write_text(
        "---\ncolors:\n  primary: '#000'\n  ink: '#111'\n  paper: '#fff'\n"
        "font:\n  family: X\n  weights: [400]\nradius_px: 4\n---\n\n"
        "## Tinh thần thương hiệu\nabc\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "FRAME_MD", md)
    f = frame.load()
    assert f.has_rules_section is False
    assert len(f.rules) > 0  # bộ mặc định, không rỗng


def test_parse_dung_mau_font_radius(tmp_path, monkeypatch):
    md = tmp_path / "frame.md"
    md.write_text(
        "---\ncolors:\n  primary: '#ABCDEF'\n  ink: '#111111'\n  paper: '#FFFFFF'\n"
        "font:\n  family: Roboto\n  weights: [400, 900]\nradius_px: 8\n---\n\n"
        "## Luật kiểm được\n- Luật 1\n- Luật 2\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "FRAME_MD", md)
    f = frame.load()
    assert f.colors["primary"] == "#ABCDEF"
    assert f.font_family == "Roboto"
    assert f.font_weights == [400, 900]
    assert f.radius_px == 8
    assert f.rules == ["Luật 1", "Luật 2"]

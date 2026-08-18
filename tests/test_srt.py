"""lib.srt — xuất .srt khớp timeline sau cắt — TDD §5.3."""

from __future__ import annotations

from lib import srt


def test_format_timestamp_co_gio_phut_giay_ms():
    text = srt.build_srt([{"t_start": 3661.234, "t_end": 3662.5, "text": "x"}])
    assert "01:01:01,234 --> 01:01:02,500" in text


def test_build_srt_danh_so_tu_1():
    lines = [{"t_start": 0, "t_end": 1, "text": "a"}, {"t_start": 1, "t_end": 2, "text": "b"}]
    text = srt.build_srt(lines)
    assert text.startswith("1\n")
    assert "\n2\n" in text


def test_build_srt_rong_thi_chuoi_rong():
    assert srt.build_srt([]) == ""


def test_build_srt_dung_dinh_dang_khoi():
    text = srt.build_srt([{"t_start": 0.2, "t_end": 1.459, "text": "Xin chào"}])
    assert text == "1\n00:00:00,200 --> 00:00:01,459\nXin chào\n\n"

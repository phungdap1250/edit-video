"""lib/renderer.py — chỉ test phần logic thuần, không gọi npx thật. TDD §2.4.

Bug thật bắt được khi chạy render thật với video của người dùng (không unit
test nào bắt được, chỉ soi khung hình mới thấy — đúng cảnh báo của tài liệu
HyperFrames): #root thiếu CSS định vị khiến <video absolute> không có ngữ
cảnh, render ra toàn màu đen dù `npx hyperframes check` báo 0 lỗi.
"""

from __future__ import annotations

import pytest

from lib import renderer
from lib.config import Section
from lib.errors import AIEditorError

BLANK_TEMPLATE = """<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <style>
      * { margin: 0; }
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="10"
      data-width="1080"
      data-height="1920"
    >
      <!--
        Add your clips here. Example:
        <div id="title" class="clip" data-start="0" data-duration="5" data-track-index="1"
             style="font-size: 64px; color: #fff; padding: 40px">
          Hello World
        </div>
      -->
    </div>

    <script>
      window.__timelines = window.__timelines || {};
      const tl = gsap.timeline({ paused: true });
      // Example: tl.from("#title", { opacity: 0, y: -50, duration: 1 }, 0);
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


@pytest.fixture
def scaffold(tmp_path):
    (tmp_path / "hyperframes.json").write_text("{}")
    (tmp_path / "index.html").write_text(BLANK_TEMPLATE, encoding="utf-8")
    return tmp_path


@pytest.fixture
def scaffold_with_video(scaffold):
    """scaffold đã qua build_video_track — có CLIPS_MARKER + đủ điều kiện cho build_caption_track."""
    renderer.build_video_track(scaffold, "assets/source.mp4", [(0.0, 2.0)], 1080, 1920, 30)
    return scaffold


def test_resolution_preset_ngang_va_doc():
    assert renderer.resolution_preset(1920, 1080) == "landscape"
    assert renderer.resolution_preset(1080, 1920) == "portrait"


def test_build_video_track_tra_dung_tong_thoi_luong(scaffold):
    total = renderer.build_video_track(
        scaffold, "assets/source.mp4", [(0.0, 1.0), (3.0, 4.5)], 1080, 1920, 30
    )
    assert total == 2.5  # 1.0 + 1.5


def test_build_video_track_data_media_start_tro_dung_nguon(scaffold):
    renderer.build_video_track(scaffold, "assets/source.mp4", [(2.0, 3.5)], 1080, 1920, 30)
    html = (scaffold / "index.html").read_text(encoding="utf-8")
    assert 'data-media-start="2.0"' in html  # trỏ vào GIÂY TRÊN NGUỒN
    assert 'data-start="0.0"' in html  # clip đầu luôn bắt đầu ở mốc 0 timeline ra


def test_build_video_track_cac_doan_noi_tiep_khong_de_khe_ho(scaffold):
    renderer.build_video_track(
        scaffold, "assets/source.mp4", [(0.0, 1.0), (5.0, 5.5), (9.0, 9.2)], 1080, 1920, 30
    )
    html = (scaffold / "index.html").read_text(encoding="utf-8")
    # đoạn 2 phải bắt đầu ngay sau khi đoạn 1 kết thúc trên timeline RA (1.0), không phải nguồn (5.0)
    assert 'data-start="1.0"' in html
    assert 'data-start="1.5"' in html


def test_build_video_track_them_css_dinh_vi_cho_root(scaffold):
    """Bug thật: thiếu CSS này khiến render ra toàn màu đen — check không bắt được."""
    renderer.build_video_track(scaffold, "assets/source.mp4", [(0.0, 1.0)], 1080, 1920, 30)
    html = (scaffold / "index.html").read_text(encoding="utf-8")
    assert "#root {" in html
    assert "position: relative;" in html
    assert "width: 1080px;" in html
    assert "height: 1920px;" in html


def test_build_video_track_video_co_style_full_bleed(scaffold):
    renderer.build_video_track(scaffold, "assets/source.mp4", [(0.0, 1.0)], 1080, 1920, 30)
    html = (scaffold / "index.html").read_text(encoding="utf-8")
    assert "position:absolute" in html
    assert "object-fit:cover" in html


def test_build_video_track_khong_dau_luon_co_the_bo():
    with pytest.raises(AIEditorError):
        renderer.build_video_track(None, "x.mp4", [], 1080, 1920, 30)


def test_build_video_track_tu_choi_khi_template_da_bi_sua(tmp_path):
    (tmp_path / "hyperframes.json").write_text("{}")
    (tmp_path / "index.html").write_text("<html><body>không phải blank</body></html>")
    with pytest.raises(AIEditorError):
        renderer.build_video_track(tmp_path, "assets/source.mp4", [(0.0, 1.0)], 1080, 1920, 30)


def test_add_cutaway_layer_chua_lam_bao_dung_story():
    with pytest.raises(NotImplementedError, match="JMP-01"):
        renderer.add_cutaway_layer("s1", None, 0, 1)


CAPTION_STYLE = Section({
    "font": {"family": "Be Vietnam Pro", "fallbacks": ["Noto Sans", "Inter"],
             "weight_normal": 500, "weight_emphasis": 700},
    "size": {"landscape_px": 52, "portrait_px": 68},
    "color": {"dim": "#FFFFFF99", "active": "#FFFFFF", "emphasis": "#FF6B35"},
    "layout": {"max_chars_per_line_landscape": 42, "max_chars_per_line_portrait": 24,
               "max_lines": 2, "bottom_margin_percent": 8},
})

CAPTION_PLAN = {
    "mode": "karaoke_word",
    "lines": [{
        "id": "cap_000", "word_ids": ["w1", "w2"], "text": "Xin chào",
        "emphasis_word_ids": ["w2"], "t_start": 0.2, "t_end": 1.0,
        "word_starts": [0.2, 0.6], "line_break_after": None,
    }],
}


def test_resolve_embeddable_font_khong_co_thi_dung_du_phong():
    assert renderer.resolve_embeddable_font(CAPTION_STYLE) == "Inter"  # "Inter" nằm trong fallbacks


def test_resolve_embeddable_font_co_san_thi_dung_luon():
    style = Section({**CAPTION_STYLE, "font": {**CAPTION_STYLE["font"], "family": "Roboto"}})
    assert renderer.resolve_embeddable_font(style) == "Roboto"


def test_build_caption_track_ghi_dung_so_dong(scaffold_with_video):
    count = renderer.build_caption_track(scaffold_with_video, CAPTION_PLAN, CAPTION_STYLE, 1080, 1920)
    assert count == 1
    html = (scaffold_with_video / "index.html").read_text(encoding="utf-8")
    assert 'id="cap_000" class="clip cap-line"' in html
    assert 'data-start="0.2" data-duration="0.8"' in html


def test_build_caption_track_span_theo_tung_tu(scaffold_with_video):
    renderer.build_caption_track(scaffold_with_video, CAPTION_PLAN, CAPTION_STYLE, 1080, 1920)
    html = (scaffold_with_video / "index.html").read_text(encoding="utf-8")
    assert 'id="cap_000_w0"' in html
    assert 'id="cap_000_w1"' in html


def test_build_caption_track_tl_set_dung_moc_va_mau(scaffold_with_video):
    renderer.build_caption_track(scaffold_with_video, CAPTION_PLAN, CAPTION_STYLE, 1080, 1920)
    html = (scaffold_with_video / "index.html").read_text(encoding="utf-8")
    assert 'tl.set("#cap_000_w0", { color: "#FFFFFF" }, 0.2);' in html
    assert 'tl.set("#cap_000_w1", { color: "#FF6B35" }, 0.6);' in html  # w2 trong emphasis_word_ids


def test_build_caption_track_escape_html_trong_text():
    plan = {"mode": "karaoke_word", "lines": [{
        "id": "cap_x", "word_ids": ["w1"], "text": "<script>",
        "emphasis_word_ids": [], "t_start": 0, "t_end": 1, "word_starts": [0],
    }]}
    from lib.renderer import _caption_line_html

    assert "<script>" not in _caption_line_html(plan["lines"][0], CAPTION_STYLE)


def test_build_caption_track_khong_co_marker_thi_loi(scaffold):
    with pytest.raises(AIEditorError):
        renderer.build_caption_track(scaffold, CAPTION_PLAN, CAPTION_STYLE, 1080, 1920)

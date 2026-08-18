"""lib.overlay_content — 4 loại đồ hoạ motion — TDD §5.5.

pill_tu_khoa và card_khai_niem không có dữ liệu tự nhiên trong video mẫu
(13s, không có khái niệm/từ khoá phù hợp cách nhau đủ 500ms) nên chưa render
thật — test đơn vị này bù lại, đảm bảo đúng kỹ thuật (không nhúng </style>
sớm do lỗi nháy kép, có data-var-text, đúng cấu trúc).
"""

from __future__ import annotations

from lib import frame as frame_lib
from lib import overlay_content, paths


def _frame():
    return frame_lib.load()


def test_resolve_rect_mac_dinh():
    assert overlay_content.resolve_rect(None) == overlay_content.resolve_rect("right_third")


def test_resolve_rect_khong_ro_thi_ve_mac_dinh():
    assert overlay_content.resolve_rect("khong-ton-tai") == overlay_content.resolve_rect("right_third")


def test_pill_tu_khoa_co_data_var_text():
    item = {"id": "ov_p", "type": "pill_tu_khoa", "content": {"text": "phễu"}, "position": "right_third"}
    frag = overlay_content.build_fragment(item, _frame(), t_start=1.0)
    assert 'data-var-text="ov_p__text"' in frag["inner_html"]
    assert "phễu" in frag["inner_html"]
    assert frag["variables"] == [{"id": "ov_p__text", "type": "string", "label": "Từ khoá", "default": "phễu"}]


def test_card_khai_niem_co_2_bien():
    item = {"id": "ov_c", "type": "card_khai_niem",
            "content": {"title": "Phễu", "definition": "Mô hình bán hàng 3 tầng"}, "position": "right_third"}
    frag = overlay_content.build_fragment(item, _frame(), t_start=1.0)
    var_ids = {v["id"] for v in frag["variables"]}
    assert var_ids == {"ov_c__title", "ov_c__definition"}
    assert 'data-var-text="ov_c__title"' in frag["inner_html"]
    assert 'data-var-text="ov_c__definition"' in frag["inner_html"]


def test_khong_bi_loi_nhay_kep_trong_style_attribute():
    """Bug thật: font-family:"X" bên trong style="..." (nháy kép) đóng attribute
    sớm, phá vỡ toàn bộ CSS còn lại — mọi builder đều phải tránh."""
    frame = _frame()
    for item in (
        {"id": "ov_1", "type": "con_so_nhay", "content": {"number": "3", "label": "bước"}},
        {"id": "ov_2", "type": "pill_tu_khoa", "content": {"text": "x"}},
        {"id": "ov_3", "type": "card_khai_niem", "content": {"title": "a", "definition": "b"}},
        {"id": "ov_4", "type": "danh_sach_bung_dan", "content": {"items": [{"text": "a"}]}},
    ):
        frag = overlay_content.build_fragment(item, frame, t_start=0.5)
        # style="..." không được chứa " ngay sau font-family: (nháy kép lồng)
        assert 'font-family:"' not in frag["inner_html"]


def test_extract_variables_khop_build_fragment():
    item = {"id": "ov_x", "type": "con_so_nhay", "content": {"number": "5", "label": "phút"}}
    assert overlay_content.extract_variables(item) == {"ov_x__number": "5", "ov_x__label": "phút"}


def test_extract_variables_danh_sach():
    item = {"id": "ov_y", "type": "danh_sach_bung_dan",
            "content": {"items": [{"text": "a"}, {"text": "b"}]}}
    assert overlay_content.extract_variables(item) == {"ov_y__item0": "a", "ov_y__item1": "b"}


def test_list_reveal_tween_theo_dung_moc():
    item = {"id": "ov_l", "type": "danh_sach_bung_dan",
            "content": {"items": [{"text": "a", "_reveal_at_sec": 0.5}, {"text": "b", "_reveal_at_sec": 1.5}]}}
    frag = overlay_content.build_fragment(item, _frame(), t_start=0.3)
    assert "0.5" in frag["tween_lines"][0]
    assert "1.5" in frag["tween_lines"][1]

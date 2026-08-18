"""lib.zoom.build_schedule — TDD §5.4."""

from __future__ import annotations

from lib import zoom
from lib.config import Section

CFG = Section({"zoom": {"min": 1.00, "max": 1.10, "fallback_max_if_no_face": 1.04}})


def test_mot_doan_duy_nhat_muc_100():
    items = zoom.build_schedule([(0.0, 5.0)], 1.10, CFG)
    assert len(items) == 1
    assert items[0]["zoom_level"] == 1.00
    assert items[0]["layer"] == 1


def test_luan_phien_khong_lap_lien_ke():
    segments = [(0.0, 2.0)] * 5
    items = zoom.build_schedule(segments, 1.10, CFG)
    levels = [i["zoom_level"] for i in items]
    for a, b in zip(levels, levels[1:]):
        assert a != b


def test_khong_vuot_max_safe_zoom():
    items = zoom.build_schedule([(0.0, 1.0)] * 4, 1.05, CFG)
    for item in items:
        assert 1.00 <= item["zoom_level"] <= 1.05


def test_thoi_gian_tren_timeline_sau_cat_lien_tuc():
    segments = [(10.0, 12.0), (30.0, 33.5), (50.0, 51.0)]
    items = zoom.build_schedule(segments, 1.10, CFG)
    assert items[0]["t_start"] == 0.0
    assert items[0]["t_end"] == 2.0
    assert items[1]["t_start"] == 2.0
    assert items[1]["t_end"] == 5.5
    assert items[2]["t_start"] == 5.5
    assert items[2]["t_end"] == 6.5

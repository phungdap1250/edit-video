"""checks.check_layer_zoom — zoom_level chỉ được khai báo ở lớp 1 — TDD §6.1."""

from __future__ import annotations

import importlib
import json

from lib import paths


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "CAPTION_PLAN", tmp_path / "caption_plan.json")
    monkeypatch.setattr(paths, "OVERLAY_PLAN", tmp_path / "overlay_plan.json")
    monkeypatch.setattr(paths, "CUTAWAY_PLAN", tmp_path / "cutaway_plan.json")


def test_khong_co_file_nao_thi_dat(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    import checks.check_layer_zoom as mod

    importlib.reload(mod)
    assert mod.main() == 0


def test_zoom_level_lo_o_overlay_thi_bat(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _write(paths.OVERLAY_PLAN, {"version": 1, "items": [{"id": "ov_001", "zoom_level": 1.06}]})

    import checks.check_layer_zoom as mod

    importlib.reload(mod)
    assert mod.main() == 1


def test_cutaway_khong_co_zoom_level_thi_dat(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _write(paths.CUTAWAY_PLAN, {"version": 1, "items": [{"id": "cta_001", "image_source": "missing"}]})

    import checks.check_layer_zoom as mod

    importlib.reload(mod)
    assert mod.main() == 0

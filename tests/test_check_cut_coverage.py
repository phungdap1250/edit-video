"""checks.check_cut_coverage — mỗi điểm cắt có đúng 1 mục che trong ±100ms — TDD §5.4."""

from __future__ import annotations

import importlib
import json

from lib import paths


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "TRANSCRIPT", tmp_path / "transcript.json")
    monkeypatch.setattr(paths, "CUT_PLAN", tmp_path / "cut_plan.json")
    monkeypatch.setattr(paths, "ZOOM_PLAN", tmp_path / "zoom_plan.json")
    monkeypatch.setattr(paths, "CUTAWAY_PLAN", tmp_path / "cutaway_plan.json")


def _seed_one_cut(duration=1.5):
    """1 từ đệm bị cắt giữa 2 từ giữ lại → đúng 1 điểm cắt trên timeline sau cắt."""
    _write(paths.TRANSCRIPT, {
        "version": 1, "duration_sec": duration, "width": 1920, "height": 1080,
        "words": [
            {"id": "w0001", "text": "a", "start": 0.0, "end": 0.5},
            {"id": "w0002", "text": "ừm", "start": 0.5, "end": 1.0},
            {"id": "w0003", "text": "b", "start": 1.0, "end": duration},
        ],
    })
    _write(paths.CUT_PLAN, {
        "version": 1, "approved_at": "2026-08-16T00:00:00+07:00",
        "items": [{"id": "cut_001", "kind": "filler", "anchor_start": "w0002",
                   "anchor_end": "w0002", "anchor_text": "ừm", "status": "accepted"}],
    })


def _load():
    import checks.check_cut_coverage as mod

    importlib.reload(mod)
    return mod


def test_chua_co_cut_plan_thi_khong_co_gi_de_kiem(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert _load().main() == 0


def test_khong_co_diem_cat_nao_thi_dat(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _write(paths.TRANSCRIPT, {
        "version": 1, "duration_sec": 1.0, "width": 1920, "height": 1080,
        "words": [{"id": "w0001", "text": "a", "start": 0.0, "end": 1.0}],
    })
    _write(paths.CUT_PLAN, {"version": 1, "approved_at": "2026-08-16T00:00:00+07:00", "items": []})
    assert _load().main() == 0


def test_thieu_zoom_plan_thi_bat(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _seed_one_cut()
    assert _load().main() == 1


def test_zoom_doi_muc_dung_ranh_gioi_thi_dat(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _seed_one_cut()
    _write(paths.ZOOM_PLAN, {
        "version": 1,
        "items": [
            {"id": "zoom_000", "zoom_level": 1.00, "t_start": 0.0, "t_end": 0.6},
            {"id": "zoom_001", "zoom_level": 1.06, "t_start": 0.6, "t_end": 1.2},
        ],
    })
    assert _load().main() == 0


def test_zoom_khong_doi_muc_va_khong_co_cutaway_thi_bat(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _seed_one_cut()
    _write(paths.ZOOM_PLAN, {
        "version": 1,
        "items": [
            {"id": "zoom_000", "zoom_level": 1.00, "t_start": 0.0, "t_end": 0.6},
            {"id": "zoom_001", "zoom_level": 1.00, "t_start": 0.6, "t_end": 1.2},
        ],
    })
    assert _load().main() == 1


def test_cutaway_che_diem_cat_thi_du_du_khi_zoom_khong_doi_muc(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _seed_one_cut()
    _write(paths.ZOOM_PLAN, {
        "version": 1,
        "items": [
            {"id": "zoom_000", "zoom_level": 1.00, "t_start": 0.0, "t_end": 0.6},
            {"id": "zoom_001", "zoom_level": 1.00, "t_start": 0.6, "t_end": 1.2},
        ],
    })
    _write(paths.CUTAWAY_PLAN, {
        "version": 1,
        "items": [{"id": "cta_001", "anchor_start": "w0001", "anchor_end": "w0003"}],
    })
    assert _load().main() == 0

"""Kiểm mã nghiệm thu check_anchor_integrity qua fixture tạm — không phải test đơn vị
của lib/, mà là test tích hợp cho chính script kiểm."""

from __future__ import annotations

import importlib
import json

from lib import paths


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_khong_neo_mo_coi_thi_dat(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "TRANSCRIPT", tmp_path / "transcript.json")
    monkeypatch.setattr(paths, "CUT_PLAN", tmp_path / "cut_plan.json")
    monkeypatch.setattr(paths, "OVERLAY_PLAN", tmp_path / "overlay_plan.json")
    monkeypatch.setattr(paths, "CUTAWAY_PLAN", tmp_path / "cutaway_plan.json")

    _write(paths.TRANSCRIPT, {
        "version": 1,
        "words": [{"id": "w0001", "text": "phễu", "start": 0.0, "end": 0.3}],
    })
    _write(paths.CUT_PLAN, {
        "version": 1,
        "items": [{"id": "cut_001", "kind": "filler", "anchor_start": "w0001",
                   "anchor_end": "w0001", "anchor_text": "phễu", "status": "pending"}],
    })

    import checks.check_anchor_integrity as mod
    importlib.reload(mod)
    assert mod.main() == 0


def test_neo_mo_coi_bi_bat(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "TRANSCRIPT", tmp_path / "transcript.json")
    monkeypatch.setattr(paths, "CUT_PLAN", tmp_path / "cut_plan.json")
    monkeypatch.setattr(paths, "OVERLAY_PLAN", tmp_path / "overlay_plan.json")
    monkeypatch.setattr(paths, "CUTAWAY_PLAN", tmp_path / "cutaway_plan.json")

    _write(paths.TRANSCRIPT, {
        "version": 1,
        "words": [{"id": "w0001", "text": "phễu", "start": 0.0, "end": 0.3}],
    })
    _write(paths.CUT_PLAN, {
        "version": 1,
        "items": [{"id": "cut_001", "kind": "filler", "anchor_start": "w9999",
                   "anchor_end": "w9999", "anchor_text": "?", "status": "pending"}],
    })

    import checks.check_anchor_integrity as mod
    importlib.reload(mod)
    assert mod.main() == 1

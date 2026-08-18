"""Tích hợp steps/04_build_caption.py — gom dòng + xuất .srt. TDD §5.3."""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace

import pytest

from lib import paths

_REAL_ROOT = paths.ROOT  # chụp TRƯỚC khi fixture monkeypatch paths.ROOT sang tmp_path


def _load_step_04():
    spec = importlib.util.spec_from_file_location(
        "step_04_build_caption", str(_REAL_ROOT / "steps" / "04_build_caption.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def isolated_project(tmp_path, monkeypatch):
    (tmp_path / "plans").mkdir()
    (tmp_path / "out").mkdir()
    monkeypatch.setattr(paths, "PLANS", tmp_path / "plans")
    monkeypatch.setattr(paths, "TRANSCRIPT", tmp_path / "plans" / "transcript.json")
    monkeypatch.setattr(paths, "CUT_PLAN", tmp_path / "plans" / "cut_plan.json")
    monkeypatch.setattr(paths, "CAPTION_PLAN", tmp_path / "plans" / "caption_plan.json")
    monkeypatch.setattr(paths, "OUT", tmp_path / "out")
    monkeypatch.setattr(paths, "ROOT", tmp_path)

    words = [
        {"id": "w0001", "text": "Xin", "start": 0.0, "end": 0.3},
        {"id": "w0002", "text": "chào.", "start": 0.3, "end": 0.6},
        {"id": "w0003", "text": "ừm", "start": 0.65, "end": 0.9},  # sẽ bị cắt
        {"id": "w0004", "text": "Tạm", "start": 2.0, "end": 2.3},
        {"id": "w0005", "text": "biệt.", "start": 2.3, "end": 2.6},
    ]
    (tmp_path / "plans" / "transcript.json").write_text(
        json.dumps({"version": 1, "duration_sec": 2.6, "width": 1920, "height": 1080, "words": words}),
        encoding="utf-8",
    )
    cut_items = [{"id": "cut_001", "kind": "filler", "anchor_start": "w0003",
                  "anchor_end": "w0003", "anchor_text": "ừm", "status": "accepted"}]
    (tmp_path / "plans" / "cut_plan.json").write_text(
        json.dumps({"version": 1, "approved_at": "2026-08-16T00:00:00+07:00", "items": cut_items}),
        encoding="utf-8",
    )
    return tmp_path


def test_chua_duyet_cut_plan_thi_loi(isolated_project):
    from lib.errors import AIEditorError
    from lib import plan_io

    cut_plan, version = plan_io.load_plan(paths.CUT_PLAN)
    cut_plan["approved_at"] = None
    plan_io.save_plan(paths.CUT_PLAN, cut_plan, version, force=True)

    step = _load_step_04()
    with pytest.raises(AIEditorError):
        step.main(Namespace(dry_run=False, json=False, verbose=False))


def test_bo_tu_bi_cat_khoi_caption(isolated_project):
    step = _load_step_04()
    step.main(Namespace(dry_run=False, json=False, verbose=False))
    saved = json.loads(paths.CAPTION_PLAN.read_text(encoding="utf-8"))
    all_word_ids = {wid for line in saved["lines"] for wid in line["word_ids"]}
    assert "w0003" not in all_word_ids  # từ đệm đã bị cắt


def test_xuat_srt_khop_dong(isolated_project):
    step = _load_step_04()
    result = step.main(Namespace(dry_run=False, json=False, verbose=False))
    srt_text = (paths.OUT / "final.srt").read_text(encoding="utf-8")
    assert srt_text.count("-->") == result["lines"]


def test_landscape_ngan_van_karaoke_word(isolated_project):
    step = _load_step_04()
    result = step.main(Namespace(dry_run=False, json=False, verbose=False))
    assert result["mode"] == "karaoke_word"  # landscape luôn karaoke_word


def test_dry_run_khong_ghi_gi(isolated_project):
    step = _load_step_04()
    result = step.main(Namespace(dry_run=True, json=False, verbose=False))
    assert result["dry_run"] is True
    assert not paths.CAPTION_PLAN.exists()

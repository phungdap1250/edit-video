"""Tích hợp steps/06_build_cutaway.py — zoom (OpenCV thật) + cutaway.

Chạy đúng main() thật với ffmpeg/OpenCV thật (frame tổng hợp không có mặt →
nhánh fallback max_safe_zoom thật). Chỉ mock lib.gemini.generate_image (mạng
ngoài) — E2E thật riêng, không thuộc phạm vi test nhanh này.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from lib import paths

_REAL_ROOT = paths.ROOT


def _load_step_06():
    spec = importlib.util.spec_from_file_location(
        "step_06_build_cutaway", str(_REAL_ROOT / "steps" / "06_build_cutaway.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_tiny_source(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=64x64:rate=10",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-c:v", "libx264", "-c:a", "aac", "-shortest", str(path)],
        capture_output=True, check=True,
    )


@pytest.fixture
def isolated_project(tmp_path, monkeypatch):
    for name in ("plans", "work", "source"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(paths, "PLANS", tmp_path / "plans")
    monkeypatch.setattr(paths, "TRANSCRIPT", tmp_path / "plans" / "transcript.json")
    monkeypatch.setattr(paths, "CUT_PLAN", tmp_path / "plans" / "cut_plan.json")
    monkeypatch.setattr(paths, "CUTAWAY_PLAN", tmp_path / "plans" / "cutaway_plan.json")
    monkeypatch.setattr(paths, "SOURCE", tmp_path / "source")
    monkeypatch.setattr(paths, "WORK", tmp_path / "work")
    monkeypatch.setattr(paths, "ZOOM_PLAN", tmp_path / "work" / "zoom_plan.json")
    monkeypatch.setattr(paths, "GENERATED_IMAGES", tmp_path / "work" / "generated_images")
    monkeypatch.setattr(paths, "CUTAWAY_NORMALIZED", tmp_path / "work" / "cutaway_normalized")
    monkeypatch.setattr(paths, "ASSETS", tmp_path / "assets")
    monkeypatch.setattr(paths, "ROOT", tmp_path)

    source = tmp_path / "source" / "raw.mp4"
    _make_tiny_source(source)

    words = [
        {"id": "w0001", "text": "a", "start": 0.0, "end": 0.5},
        {"id": "w0002", "text": "ừm", "start": 0.5, "end": 1.0},
        {"id": "w0003", "text": "b", "start": 1.0, "end": 2.0},
    ]
    (tmp_path / "plans" / "transcript.json").write_text(
        json.dumps({"version": 1, "duration_sec": 2.0, "width": 64, "height": 64, "words": words}),
        encoding="utf-8",
    )
    cut_items = [{"id": "cut_001", "kind": "filler", "anchor_start": "w0002",
                  "anchor_end": "w0002", "anchor_text": "ừm", "status": "accepted"}]
    (tmp_path / "plans" / "cut_plan.json").write_text(
        json.dumps({"version": 1, "approved_at": "2026-08-16T00:00:00+07:00", "items": cut_items}),
        encoding="utf-8",
    )
    return tmp_path


def test_zoom_plan_sinh_ra_khong_co_mat_thi_dung_fallback(isolated_project):
    step = _load_step_06()
    result = step.main(Namespace(dry_run=False, json=False, verbose=False))

    assert result["face_detected"] is False  # testsrc tổng hợp không có mặt người
    assert result["max_safe_zoom"] == pytest.approx(1.04)  # cfg.zoom.fallback_max_if_no_face
    assert paths.ZOOM_PLAN.exists()


def test_khong_co_cutaway_plan_thi_bo_qua(isolated_project):
    step = _load_step_06()
    result = step.main(Namespace(dry_run=False, json=False, verbose=False))
    assert result["cutaway_items"] == 0


def test_cutaway_khop_asset_co_san(isolated_project, monkeypatch):
    import cv2
    import numpy as np

    paths.ASSETS.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(paths.ASSETS / "cta_001_anh_co_san.png"), np.zeros((100, 100, 3), dtype="uint8"))
    paths.CUTAWAY_PLAN.write_text(
        json.dumps({
            "version": 1,
            "items": [{"id": "cta_001", "anchor_start": "w0001", "anchor_end": "w0003",
                       "anchor_text": "a b", "prompt": "x", "status": "pending"}],
        }),
        encoding="utf-8",
    )

    step = _load_step_06()
    result = step.main(Namespace(dry_run=False, json=False, verbose=False))

    assert result["matched"] == 1
    assert result["generated"] == 0
    saved = json.loads(paths.CUTAWAY_PLAN.read_text(encoding="utf-8"))
    assert saved["items"][0]["image_source"] == "user_asset"


def test_cutaway_thieu_khoa_gemini_thi_missing_khong_crash(isolated_project):
    paths.CUTAWAY_PLAN.write_text(
        json.dumps({
            "version": 1,
            "items": [{"id": "cta_002", "anchor_start": "w0001", "anchor_end": "w0003",
                       "anchor_text": "a b", "prompt": "x", "status": "pending"}],
        }),
        encoding="utf-8",
    )

    step = _load_step_06()
    result = step.main(Namespace(dry_run=False, json=False, verbose=False))

    assert result["missing"] == 1
    saved = json.loads(paths.CUTAWAY_PLAN.read_text(encoding="utf-8"))
    assert saved["items"][0]["image_source"] == "missing"


def test_doan_qua_ngan_bi_bo_qua_chi_zoom(isolated_project):
    """PRD [JMP] edge case: đoạn giữ lại < 1.5s → không chèn cutaway."""
    paths.CUTAWAY_PLAN.write_text(
        json.dumps({
            "version": 1,
            # w0001 dài 0.5s < cfg.cutaway.min_segment_sec (1.5s)
            "items": [{"id": "cta_003", "anchor_start": "w0001", "anchor_end": "w0001",
                       "anchor_text": "a", "prompt": "x", "status": "pending"}],
        }),
        encoding="utf-8",
    )
    step = _load_step_06()
    result = step.main(Namespace(dry_run=False, json=False, verbose=False))

    assert result["skipped"] == 1
    assert result["matched"] == 0 and result["generated"] == 0
    saved = json.loads(paths.CUTAWAY_PLAN.read_text(encoding="utf-8"))
    assert saved["items"][0]["status"] == "rejected"


def test_dry_run_khong_ghi_gi(isolated_project):
    step = _load_step_06()
    result = step.main(Namespace(dry_run=True, json=False, verbose=False))
    assert result["dry_run"] is True
    assert not paths.ZOOM_PLAN.exists()

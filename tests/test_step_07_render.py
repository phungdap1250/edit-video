"""Tích hợp steps/07_render.py — segment/disk/manifest, KHÔNG gọi npx thật.

Test riêng lib/renderer.py (test_renderer.py) không bắt được lỗi ráp nối:
tính segment từ cut_plan sai, quên kiểm dung lượng ổ, ghi manifest sai
đường dẫn. File này chạy đúng main() thật, chỉ mock lớp HyperFrames (chậm,
đã có E2E thật riêng ở test_e2e_render.py) và đổi PLANS/SOURCE/HF sang tmp_path.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from lib import paths

_REAL_ROOT = paths.ROOT  # chụp TRƯỚC khi fixture monkeypatch paths.ROOT sang tmp_path


def _load_step_07():
    spec = importlib.util.spec_from_file_location(
        "step_07_render", str(_REAL_ROOT / "steps" / "07_render.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_tiny_source(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=64x64:rate=10",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
         "-c:v", "libx264", "-c:a", "aac", "-shortest", str(path)],
        capture_output=True, check=True,
    )


@pytest.fixture
def isolated_project(tmp_path, monkeypatch):
    for name in ("plans", "work", "source", "hf", "out"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(paths, "PLANS", tmp_path / "plans")
    monkeypatch.setattr(paths, "TRANSCRIPT", tmp_path / "plans" / "transcript.json")
    monkeypatch.setattr(paths, "CUT_PLAN", tmp_path / "plans" / "cut_plan.json")
    monkeypatch.setattr(paths, "CAPTION_PLAN", tmp_path / "plans" / "caption_plan.json")
    monkeypatch.setattr(paths, "RENDER_MANIFEST", tmp_path / "plans" / "render_manifest.json")
    monkeypatch.setattr(paths, "SOURCE", tmp_path / "source")
    monkeypatch.setattr(paths, "HF", tmp_path / "hf")
    monkeypatch.setattr(paths, "OUT", tmp_path / "out")
    monkeypatch.setattr(paths, "ROOT", tmp_path)

    source = tmp_path / "source" / "raw.mp4"
    _make_tiny_source(source)

    words = [
        {"id": "w0001", "text": "a", "start": 0.0, "end": 0.5, "conf": 1.0},
        {"id": "w0002", "text": "b", "start": 1.0, "end": 1.5, "conf": 1.0},
        {"id": "w0003", "text": "c", "start": 2.5, "end": 3.0, "conf": 1.0},
    ]
    (tmp_path / "plans" / "transcript.json").write_text(
        json.dumps({"schema_version": 1, "version": 1, "duration_sec": 3.0, "words": words})
    )
    cut_plan = {
        "schema_version": 1, "version": 1, "approved_at": "2026-08-16T23:00:00+07:00",
        "items": [
            {"id": "cut_001", "kind": "silence", "status": "accepted",
             "anchor_start": "w0001", "anchor_end": "w0002", "keep_ms": 100},
        ],
    }
    (tmp_path / "plans" / "cut_plan.json").write_text(json.dumps(cut_plan))
    return tmp_path


def test_chan_render_khi_cut_plan_chua_duyet(isolated_project):
    step = _load_step_07()
    cut_plan_path = isolated_project / "plans" / "cut_plan.json"
    data = json.loads(cut_plan_path.read_text())
    data["approved_at"] = None
    cut_plan_path.write_text(json.dumps(data))

    from lib.errors import AIEditorError

    with pytest.raises(AIEditorError, match="chưa được duyệt"):
        step.main(Namespace(dry_run=False, final=False, json=False, verbose=False))


def test_dry_run_tinh_dung_segment_khong_dung_hyperframes(isolated_project):
    step = _load_step_07()
    result = step.main(Namespace(dry_run=True, final=False, json=False, verbose=False))
    assert result["dry_run"] is True
    assert result["segments"] >= 1
    assert result["kept_sec"] < 3.0  # đã bớt phần bị cắt


def test_render_that_goi_hyperframes_qua_mock(isolated_project, monkeypatch):
    """Mock lớp renderer — kiểm ĐÚNG chuỗi gọi + manifest, không tốn thời gian npx."""
    step = _load_step_07()
    calls: list[str] = []

    monkeypatch.setattr(step.renderer, "hf_available", lambda: (True, "0.7.109"))
    monkeypatch.setattr(
        step.renderer, "create_project",
        lambda project_dir, w, h, fps: (calls.append("create_project"), (1080, 1920))[1],
    )
    monkeypatch.setattr(
        step.renderer, "build_video_track",
        lambda *a, **k: (calls.append("build_video_track"), 2.0)[1],
    )
    monkeypatch.setattr(step.renderer, "check", lambda project_dir: calls.append("check"))

    def fake_render(project_dir, out, *, quality):
        calls.append(f"render:{quality}")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"fake-mp4-bytes")
        return out

    monkeypatch.setattr(step.renderer, "render", fake_render)

    result = step.main(Namespace(dry_run=False, final=False, json=False, verbose=False))

    assert calls == ["create_project", "build_video_track", "check", "render:draft"]
    assert Path(result["out"]).exists()
    manifest = json.loads((isolated_project / "plans" / "render_manifest.json").read_text())
    assert manifest["quality"] == "draft"
    assert len(manifest["blocks"]) == 1
    assert manifest["blocks"][0]["id"] == "whole"


def test_final_flag_render_high_quality(isolated_project, monkeypatch):
    step = _load_step_07()
    monkeypatch.setattr(step.renderer, "hf_available", lambda: (True, "0.7.109"))
    monkeypatch.setattr(step.renderer, "create_project", lambda *a, **k: (1080, 1920))
    monkeypatch.setattr(step.renderer, "build_video_track", lambda *a, **k: 2.0)
    monkeypatch.setattr(step.renderer, "check", lambda project_dir: None)

    seen_quality = []

    def fake_render(project_dir, out, *, quality):
        seen_quality.append(quality)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"x")
        return out

    monkeypatch.setattr(step.renderer, "render", fake_render)
    step.main(Namespace(dry_run=False, final=True, json=False, verbose=False))
    assert seen_quality == ["high"]


def test_bao_loi_khi_hyperframes_chua_san_sang(isolated_project, monkeypatch):
    step = _load_step_07()
    monkeypatch.setattr(step.renderer, "hf_available", lambda: (False, "không tìm thấy npx"))

    from lib.errors import AIEditorError

    with pytest.raises(AIEditorError, match="HyperFrames chưa sẵn sàng"):
        step.main(Namespace(dry_run=False, final=False, json=False, verbose=False))


def test_disk_space_chan_khi_thieu_dung_luong(isolated_project, monkeypatch):
    step = _load_step_07()
    monkeypatch.setattr(step.renderer, "hf_available", lambda: (True, "0.7.109"))

    class FakeUsage:
        free = 1 * 1024**3  # 1GB — dưới ngưỡng disk_estimate_gb_per_5min (8GB mặc định)

    monkeypatch.setattr(step.shutil, "disk_usage", lambda path: FakeUsage())

    from lib.errors import AIEditorError

    with pytest.raises(AIEditorError, match="Ổ đĩa"):
        step.main(Namespace(dry_run=False, final=False, json=False, verbose=False))

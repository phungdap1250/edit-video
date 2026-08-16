"""E2E render — gọi npx hyperframes THẬT, không mock. TDD §12.3.

Chậm (~1–2 phút: init + check + render thật qua Chrome headless của
HyperFrames) vì đụng dependency ngoài thật, khác với test_step_07_render.py
(nhanh, mock lớp renderer để kiểm logic ráp nối). Cả hai cùng cần — mock test
không bắt được lỗi thật kiểu "video đen vì thiếu CSS #root" đã gặp lúc code
[RND-01]; test này thì có, vì nó thật sự render ra pixel.

Dùng video tổng hợp tự sinh bằng ffmpeg lavfi — không phụ thuộc footage cá
nhân của người dùng, chạy được trên máy CI không có `source/raw.mp4`.

Chạy: pytest tests/test_e2e_render.py -q --timeout=180 (bỏ qua nếu thiếu
ffmpeg hoặc HyperFrames chưa cài).
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess

import pytest

from lib import paths

_REAL_ROOT = paths.ROOT
FFMPEG_MISSING = shutil.which("ffmpeg") is None


def _hyperframes_missing() -> bool:
    try:
        result = subprocess.run(
            ["npx", "hyperframes", "doctor", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(result.stdout)
        checks = {c["name"]: c for c in data.get("checks", [])}
        return not (checks.get("Node.js", {}).get("ok") and checks.get("Version", {}).get("ok"))
    except Exception:
        return True


def _load_step_07():
    spec = importlib.util.spec_from_file_location(
        "step_07_render_e2e", str(_REAL_ROOT / "steps" / "07_render.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def isolated_project(tmp_path, monkeypatch):
    for name in ("plans", "work", "source", "hf", "out"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(paths, "PLANS", tmp_path / "plans")
    monkeypatch.setattr(paths, "TRANSCRIPT", tmp_path / "plans" / "transcript.json")
    monkeypatch.setattr(paths, "CUT_PLAN", tmp_path / "plans" / "cut_plan.json")
    monkeypatch.setattr(paths, "RENDER_MANIFEST", tmp_path / "plans" / "render_manifest.json")
    monkeypatch.setattr(paths, "SOURCE", tmp_path / "source")
    monkeypatch.setattr(paths, "HF", tmp_path / "hf")
    monkeypatch.setattr(paths, "OUT", tmp_path / "out")
    monkeypatch.setattr(paths, "ROOT", tmp_path)

    source = tmp_path / "source" / "raw.mp4"
    # 3 giây, dọc (480x854 ~ tỉ lệ 9:16) — thử đúng nhánh "portrait" từng có bug
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=3:size=480x854:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            "-c:v", "libx264", "-c:a", "aac", "-shortest", str(source),
        ],
        capture_output=True, check=True, timeout=30,
    )

    words = [
        {"id": "w0001", "text": "một", "start": 0.0, "end": 0.5, "conf": 1.0},
        {"id": "w0002", "text": "hai", "start": 1.5, "end": 2.0, "conf": 1.0},
        {"id": "w0003", "text": "ba", "start": 2.5, "end": 3.0, "conf": 1.0},
    ]
    (tmp_path / "plans" / "transcript.json").write_text(
        json.dumps({"schema_version": 1, "version": 1, "duration_sec": 3.0, "words": words})
    )
    cut_plan = {
        "schema_version": 1, "version": 1, "approved_at": "2026-08-16T23:00:00+07:00",
        "items": [],  # không cắt gì — giữ nguyên 3s để đơn giản hoá E2E
    }
    (tmp_path / "plans" / "cut_plan.json").write_text(json.dumps(cut_plan))
    return tmp_path


@pytest.mark.skipif(FFMPEG_MISSING, reason="cần ffmpeg cài trên máy")
@pytest.mark.skipif(_hyperframes_missing(), reason="cần HyperFrames CLI (npx hyperframes doctor)")
def test_render_that_dau_cuoi_qua_npx_hyperframes_that(isolated_project):
    from argparse import Namespace

    step = _load_step_07()
    result = step.main(Namespace(dry_run=False, final=False, json=False, verbose=False))

    out = isolated_project / "out" / "draft.mp4"
    assert out.exists() and out.stat().st_size > 1000  # không phải file rỗng/hỏng

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-show_entries", "format=duration",
         "-of", "json", str(out)],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(probe.stdout)
    width = info["streams"][0]["width"]
    height = info["streams"][0]["height"]

    assert height > width  # PHẢI ra dọc — đúng bug orientation từng gặp thật
    assert (width, height) == (1080, 1920)  # preset portrait chuẩn PRD [RND-01]

    duration = float(info["format"]["duration"])
    assert duration == pytest.approx(3.0, abs=0.3)

    # Bug thật từng gặp: check báo 0 lỗi nhưng khung hình toàn màu đen vì
    # #root thiếu CSS định vị. Trích khung giữa video, xác nhận KHÔNG đen tuyền.
    frame = isolated_project / "frame.png"
    subprocess.run(
        ["ffmpeg", "-y", "-ss", "1.5", "-i", str(out), "-frames:v", "1", "-update", "1", str(frame)],
        capture_output=True, check=True,
    )
    assert frame.stat().st_size > 5000  # PNG đen tuyền nén rất nhỏ (~vài trăm byte)

    manifest = json.loads((isolated_project / "plans" / "render_manifest.json").read_text())
    assert manifest["blocks"][0]["id"] == "whole"
    assert result["quality"] == "draft"

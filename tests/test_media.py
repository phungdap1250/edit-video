"""Bọc ffmpeg/ffprobe thật — TDD §8. Rotation là bug thật: kích thước lưu trữ
thô đoán sai khung ngang/dọc cho video iPhone quay dọc (lưu pixel ngang + cờ
xoay -90°). probe()/cut_segments() chạy ffmpeg/ffprobe THẬT trên video tổng
hợp tự sinh bằng ffmpeg lavfi — không phụ thuộc file cá nhân của người dùng."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from lib.media import _rotation_degrees, cut_segments, probe

FFMPEG_MISSING = shutil.which("ffmpeg") is None


@pytest.fixture
def tiny_video(tmp_path):
    """Video 2s thật, 320×240, 10fps, có tiếng — sinh bằng ffmpeg lavfi."""
    out = tmp_path / "tiny.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:v", "libx264", "-c:a", "aac", "-shortest", str(out),
        ],
        capture_output=True, check=True,
    )
    return out


def test_rotation_tu_side_data_chuan_moi():
    stream = {"side_data_list": [{"rotation": -90}]}
    assert _rotation_degrees(stream) == -90


def test_rotation_tu_tags_rotate_kieu_cu():
    stream = {"tags": {"rotate": "90"}}
    assert _rotation_degrees(stream) == 90


def test_khong_co_rotation_thi_tra_0():
    assert _rotation_degrees({}) == 0
    assert _rotation_degrees({"side_data_list": [{}]}) == 0


def test_side_data_uu_tien_hon_tags():
    stream = {"side_data_list": [{"rotation": -90}], "tags": {"rotate": "0"}}
    assert _rotation_degrees(stream) == -90


@pytest.mark.skipif(FFMPEG_MISSING, reason="cần ffmpeg cài trên máy")
def test_probe_doc_dung_kich_thuoc_khong_xoay(tiny_video):
    info = probe(tiny_video)
    assert info["width"] == 320 and info["height"] == 240
    assert info["duration_sec"] == pytest.approx(2.0, abs=0.1)
    assert info["fps"] == pytest.approx(10.0, abs=0.1)
    assert info["vcodec"] == "h264" and info["acodec"] == "aac"


@pytest.mark.skipif(FFMPEG_MISSING, reason="cần ffmpeg cài trên máy")
def test_probe_bao_loi_ro_khi_thieu_am_thanh(tmp_path):
    silent = tmp_path / "silent.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=5",
         "-c:v", "libx264", str(silent)],
        capture_output=True, check=True,
    )
    with pytest.raises(Exception, match="không có luồng tiếng"):
        probe(silent)


@pytest.mark.skipif(FFMPEG_MISSING, reason="cần ffmpeg cài trên máy")
def test_cut_segments_giu_dung_tong_thoi_luong(tiny_video, tmp_path):
    out = tmp_path / "out.mp4"
    cut_segments(tiny_video, [(0.0, 0.5), (1.0, 1.8)], out, fps=10)
    info = probe(out)
    assert info["duration_sec"] == pytest.approx(0.5 + 0.8, abs=0.15)


@pytest.mark.skipif(FFMPEG_MISSING, reason="cần ffmpeg cài trên máy")
def test_cut_segments_tu_choi_khi_rong(tiny_video, tmp_path):
    with pytest.raises(Exception, match="[Kk]hông còn đoạn"):
        cut_segments(tiny_video, [], tmp_path / "out.mp4", fps=10)

"""Bọc ffmpeg/ffprobe — TDD §8. Mọi lời gọi ffmpeg đi qua đây."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lib import log
from lib.errors import AIEditorError


def _rotation_degrees(video_stream: dict) -> int:
    """Đọc góc xoay từ side_data (chuẩn mới) hoặc tags.rotate (QuickTime cũ)."""
    for side_data in video_stream.get("side_data_list", []):
        if "rotation" in side_data:
            return int(side_data["rotation"])
    return int(video_stream.get("tags", {}).get("rotate", 0))


def _run(args: list[str], what: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, capture_output=True, text=True, check=True)
    except FileNotFoundError as exc:
        raise AIEditorError(
            f"Không tìm thấy {args[0]}",
            suggestion="Cài ffmpeg: brew install ffmpeg",
        ) from exc
    except subprocess.CalledProcessError as exc:
        tail = (exc.stderr or "").strip().splitlines()[-3:]
        raise AIEditorError(
            f"{what} thất bại — {' / '.join(tail)}",
            suggestion="Chạy lại với --verbose để xem lệnh đầy đủ",
        ) from exc


def probe(video: Path) -> dict:
    """Trả {duration_sec, width, height, fps, vcodec, acodec}.

    width/height là KÍCH THƯỚC HIỂN THỊ — đã đổi chiều theo metadata rotation
    khi có (±90/±270, kiểu iPhone quay dọc lưu pixel ngang + cờ xoay). Dùng
    kích thước lưu trữ thô sẽ đoán sai khung ngang/dọc cho mọi video có xoay.
    """
    out = _run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(video)],
        f"Đọc thông tin {video.name}",
    ).stdout
    data = json.loads(out)

    video_stream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    audio_stream = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    if video_stream is None:
        raise AIEditorError(
            f"{video.name} không có luồng hình",
            suggestion="Kiểm tra lại file nguồn",
        )
    if audio_stream is None:
        raise AIEditorError(
            f"{video.name} không có luồng tiếng — không tạo được transcript",
            suggestion="Kiểm tra lại thiết bị thu lúc quay",
        )

    numerator, _, denominator = video_stream.get("r_frame_rate", "30/1").partition("/")
    fps = float(numerator) / float(denominator or 1)
    width, height = int(video_stream["width"]), int(video_stream["height"])
    if abs(_rotation_degrees(video_stream)) % 180 == 90:
        width, height = height, width
    return {
        "duration_sec": round(float(data["format"]["duration"]), 3),
        "width": width,
        "height": height,
        "fps": round(fps, 3),
        "vcodec": video_stream["codec_name"],
        "acodec": audio_stream["codec_name"],
    }


def extract_frame(video: Path, out: Path, *, at_sec: float) -> Path:
    """Xuất đúng 1 khung hình tại `at_sec` ra PNG — dùng cho dò khung mặt (TDD §5.4)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(
        ["ffmpeg", "-y", "-ss", str(at_sec), "-i", str(video), "-frames:v", "1", str(out)],
        "Xuất khung hình",
    )
    return out


def extract_audio(video: Path, out: Path, *, bitrate: str = "64k") -> Path:
    """Tách audio để gửi ElevenLabs — file video gốc KHÔNG rời máy (§10.3)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(
        ["ffmpeg", "-y", "-i", str(video), "-vn", "-c:a", "aac", "-b:a", bitrate, str(out)],
        "Tách audio",
    )
    return out


def cut_segments(video: Path, segments: list[tuple[float, float]], out: Path, fps: int) -> Path:
    """Giữ lại các đoạn đã duyệt, nối thành một file, chuẩn hoá về `fps`.

    Dùng filter trim/concat trong MỘT lần chạy: mã hoá lại một lần duy nhất,
    không sinh file tạm cho từng đoạn.
    """
    if not segments:
        raise AIEditorError(
            "Không còn đoạn nào để giữ sau khi áp cắt",
            suggestion="Mở lại python review.py cut và bỏ bớt điểm cắt",
        )
    out.parent.mkdir(parents=True, exist_ok=True)

    parts, labels = [], []
    for index, (start, end) in enumerate(segments):
        parts.append(
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,fps={fps}[v{index}];"
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{index}]"
        )
        labels.append(f"[v{index}][a{index}]")
    graph = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(segments)}:v=1:a=1[v][a]"

    log.info(f"áp cắt: giữ {len(segments)} đoạn → {out.name}")
    _run(
        ["ffmpeg", "-y", "-i", str(video), "-filter_complex", graph,
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "18", "-c:a", "aac", "-b:a", "192k", str(out)],
        "Áp cắt",
    )
    return out


def ensure_browser_playable(video: Path, cache: Path) -> Path:
    """Trình duyệt (kể cả Chromium của Playwright) thường KHÔNG decode được
    HEVC/H.265 — video "phát" đúng thời gian nhưng khung hình đứng đen, chỉ lộ
    ra khi mở thật (không unit test nào bắt được). Bản thân HyperFrames CLI xử
    lý y hệt: tự cache 1 bản proxy H.264 cho preview khi phát hiện HEVC.

    Trả `video` nguyên trạng nếu đã là H.264 (không mã hoá lại vô ích); trả
    đường dẫn `cache` (mã hoá 1 lần, dùng lại các lần sau) nếu là HEVC.
    """
    if probe(video)["vcodec"] not in ("hevc", "h265"):
        return video
    if cache.exists() and cache.stat().st_mtime >= video.stat().st_mtime:
        return cache

    log.info(f"{video.name}: mã HEVC không phát được trong trình duyệt — dựng bản xem trước H.264")
    cache.parent.mkdir(parents=True, exist_ok=True)
    _run(
        ["ffmpeg", "-y", "-i", str(video), "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", "-c:a", "aac", "-b:a", "128k", str(cache)],
        "Dựng bản xem trước H.264",
    )
    return cache

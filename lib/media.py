"""Bọc ffmpeg/ffprobe — TDD §8. Mọi lời gọi ffmpeg đi qua đây."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lib import log
from lib.errors import AIEditorError


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
    """Trả {duration_sec, width, height, fps, vcodec, acodec}."""
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
    return {
        "duration_sec": round(float(data["format"]["duration"]), 3),
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "fps": round(fps, 3),
        "vcodec": video_stream["codec_name"],
        "acodec": audio_stream["codec_name"],
    }


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

"""Mã băm khối — trái tim của render tăng dần. TDD §6.3.

Hai luật sống còn:
  · JSON đem băm dùng sort_keys=True, separators cố định (§13.5). Trộn với kiểu
    ghi ra đĩa là nguyên nhân kinh điển khiến hash trồi sụt.
  · MỌI thời điểm trong hash là TƯƠNG ĐỐI so với đầu khối. Khối dịch chỗ mà nội
    dung không đổi thì hash KHÔNG được đổi.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

HASH_LEN = 8  # 8 ký tự hex đầu → tên file work/blocks/<hash>.mp4


def canonical_json(data: Any) -> str:
    """Chuỗi tất định để băm — KHÁC với kiểu ghi ra đĩa."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_str(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ffmpeg_version() -> str:
    """Đổi ffmpeg = pixel có thể lệch → phải nằm trong ngữ cảnh hash."""
    try:
        out = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, check=True
        ).stdout
        return out.splitlines()[0].strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def block_hash(block_content: dict, ctx: dict) -> str:
    """SHA-256 của (nội dung khối tương đối + ngữ cảnh toàn cục).

    block_content — mọi thời điểm TƯƠNG ĐỐI (t_rel_*):
      segments[]  (word_id_in, word_id_out, dur_sec)
      zoom[]      (seg_index, level)
      caption[]   (text, emphasis_ids, t_rel_start, t_rel_end)
      overlay[]   (id, type, content, t_rel_in, t_rel_out, sha256(html))
      cutaway[]   (id, sha256(image), t_rel_in, t_rel_out)

    ctx — ngữ cảnh toàn cục:
      source_sha256, frame_md_sha256, caption_style_sha256,
      render_params (width, height, fps, quality, codec, bitrate),
      renderer_version, ffmpeg_version

    KHÔNG vào hash (v1.1 đã gỡ): sha256(work/cut.mp4), t_in/t_out tuyệt đối.
    """
    forbidden = {"t_in", "t_out", "cut_mp4_sha256"}
    leaked = forbidden & set(block_content)
    if leaked:
        raise ValueError(
            f"Trường bị cấm trong block_hash: {sorted(leaked)} — xem docs/TDD.md §6.3"
        )
    payload = {"content": block_content, "ctx": ctx}
    return sha256_str(canonical_json(payload))[:HASH_LEN]

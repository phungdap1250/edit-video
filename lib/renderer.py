"""Hàng rào chống rủi ro HyperFrames — TDD §2.4.

TOÀN BỘ tiếp xúc với HyperFrames nằm trong file này. Không file nào khác được
import hyperframes hay chạy lệnh `hf ...` — `checks/check_renderer_isolation.py`
grep khẳng định điều đó.

Nếu HyperFrames hụt (không làm được caption karaoke, không ghi được Variables từ
ngoài) thì chỗ phải sửa là đúng một file này, không phải 2.000 dòng.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

# Tăng tay khi đổi logic dựng — vào block_hash, làm mọi khối render lại (§6.3).
RENDERER_VERSION = 1

HF_BIN = os.environ.get("HYPERFRAMES_BIN", "hf")


def hf_available() -> tuple[bool, str]:
    """Kiểm HyperFrames có cài và chạy được không. Trả (ok, phiên bản/lý do)."""
    binary = shutil.which(HF_BIN)
    if binary is None:
        return False, f"Không tìm thấy '{HF_BIN}' trong PATH"
    try:
        out = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, check=True, timeout=30
        )
        return True, out.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        return False, f"Chạy '{HF_BIN} --version' thất bại: {exc}"


def create_project(project_dir: Path, width: int, height: int, fps: int) -> None:
    raise NotImplementedError("Tuần 1 — TDD §16")


def add_video_clip(scene_id: str, src: Path, t_in: float, t_out: float, zoom: float) -> None:
    """Lớp 1 — video người nói. Lớp DUY NHẤT được áp zoom (§6.1)."""
    raise NotImplementedError("Tuần 1 — TDD §16")


def add_caption_layer(scene_id: str, caption_items: list[dict], style: dict) -> None:
    """Lớp 4 — caption karaoke. Phép thử HyperFrames khó nhất của tuần 1."""
    raise NotImplementedError("Tuần 1 — TDD §16")


def add_overlay_layer(scene_id: str, html_path: Path, t_in: float, t_out: float) -> None:
    """Lớp 3 — đồ hoạ motion."""
    raise NotImplementedError("Tuần 3 — TDD §16")


def add_cutaway_layer(scene_id: str, image: Path, t_in: float, t_out: float) -> None:
    """Lớp 2 — cutaway."""
    raise NotImplementedError("Tuần 3 — TDD §16")


def write_variables(vars_dict: dict) -> None:
    """Đồng bộ MỘT CHIỀU plan → Variables (§6.5). Cấm đọc ngược."""
    raise NotImplementedError("Tuần 3 — TDD §16")


def read_variables() -> dict:
    """CHỈ dùng cho checks/check_variables_sync.py — không dùng ở nơi khác."""
    raise NotImplementedError("Tuần 3 — TDD §16")


def render_block(block_id: str, t_in: float, t_out: float, out: Path, quality: str) -> None:
    """Render CHỈ-VIDEO. Audio mux một lần duy nhất lúc concat — tránh AAC
    priming delay tích luỹ ~256ms qua 12 khối (§15 v1.1)."""
    raise NotImplementedError("Tuần 1 — TDD §16")


def open_studio() -> None:
    raise NotImplementedError("Tuần 1 — TDD §16")

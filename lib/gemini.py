"""Gọi Gemini API sinh ảnh cutaway — TDD §8, §14.

CHỈ file này gọi Gemini trực tiếp. `steps/06_build_cutaway.py` là nơi DUY
NHẤT được phép import module này (§7.2: Claude không được gọi Gemini trực
tiếp, phải qua step, để bộ đếm hạn mức trong lib.budget chạy đúng).
"""

from __future__ import annotations

import base64
from pathlib import Path

import requests

from lib import config
from lib.errors import AIEditorError

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MODEL = "imagen-3.0-generate-002"


def aspect_ratio(width: int, height: int) -> str:
    """Tỉ lệ khung của video — PRD [JMP]: "sinh ảnh theo tỉ lệ khung của video"."""
    if width == height:
        return "1:1"
    return "9:16" if height > width else "16:9"


def generate_image(prompt: str, width: int, height: int, out_path: Path, *, timeout: int = 60) -> Path:
    """Sinh 1 ảnh, ghi ra `out_path`. Không tự kiểm hạn mức — gọi lib.budget trước."""
    keys = config.require_keys(["GEMINI_API_KEY"])
    body = {
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": 1, "aspectRatio": aspect_ratio(width, height)},
    }
    try:
        response = requests.post(
            f"{API_BASE}/{MODEL}:predict",
            params={"key": keys["GEMINI_API_KEY"]},
            json=body,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise AIEditorError(
            f"Gọi Gemini thất bại: {exc}", suggestion="Kiểm kết nối mạng rồi thử lại"
        ) from exc

    if response.status_code != 200:
        raise AIEditorError(
            f"Gemini trả lỗi {response.status_code}: {response.text[:300]}",
            suggestion="Kiểm khoá GEMINI_API_KEY và hạn mức tài khoản Google",
        )

    predictions = response.json().get("predictions") or []
    if not predictions or "bytesBase64Encoded" not in predictions[0]:
        raise AIEditorError(
            "Gemini không trả ảnh nào cho mô tả này",
            suggestion="Sửa mô tả ảnh rồi thử sinh lại",
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(predictions[0]["bytesBase64Encoded"]))
    return out_path

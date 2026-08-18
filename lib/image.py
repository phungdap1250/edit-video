"""Chuẩn hoá ảnh cutaway về đúng tỉ lệ khung — TDD §5.4 edge case.

Ảnh trong assets/ sai tỉ lệ → thêm nền mờ từ chính ảnh đó, KHÔNG kéo méo hình.
"""

from __future__ import annotations

from pathlib import Path

import cv2

from lib.errors import AIEditorError

_RATIO_TOLERANCE = 0.02


def normalize_aspect(src: Path, out: Path, width: int, height: int) -> Path:
    """Ghi `out` đúng kích thước width×height. Lệch tỉ lệ → nền mờ, ảnh gốc giữ nguyên tỉ lệ ở giữa."""
    image = cv2.imread(str(src))
    if image is None:
        raise AIEditorError(f"Không đọc được ảnh {src.name}")

    src_h, src_w = image.shape[:2]
    out.parent.mkdir(parents=True, exist_ok=True)

    if abs((src_w / src_h) - (width / height)) <= _RATIO_TOLERANCE:
        cv2.imwrite(str(out), cv2.resize(image, (width, height)))
        return out

    background = cv2.GaussianBlur(cv2.resize(image, (width, height)), (0, 0), sigmaX=25)
    scale = min(width / src_w, height / src_h)
    fit_w, fit_h = int(src_w * scale), int(src_h * scale)
    fitted = cv2.resize(image, (fit_w, fit_h))
    x, y = (width - fit_w) // 2, (height - fit_h) // 2
    background[y : y + fit_h, x : x + fit_w] = fitted

    cv2.imwrite(str(out), background)
    return out

"""Dò khung mặt 1 lần lúc khởi tạo project — TDD §5.4, §8.

Không phải tracking: xuất đúng 1 khung hình giữa video, chạy Haar cascade của
OpenCV, suy ra mức zoom tối đa mà khuôn mặt vẫn còn trọn vẹn trong khung sau
khi zoom-crop-giữa-tâm kiểu Ken Burns.
"""

from __future__ import annotations

from pathlib import Path

import cv2

from lib import log, media


def detect_max_safe_zoom(video: Path, work_dir: Path, cfg) -> dict:
    """Trả {face_detected, max_safe_zoom, reason}.

    Thất bại (không có mặt, ngược sáng, khuất) → hạ trần về
    `cfg.zoom.fallback_max_if_no_face`, KHÔNG chặn pipeline.
    """
    info = media.probe(video)
    frame_path = work_dir / "face_probe.png"
    try:
        media.extract_frame(video, frame_path, at_sec=info["duration_sec"] / 2)
    except Exception as exc:  # ffmpeg lỗi hiếm gặp — vẫn không chặn pipeline
        return _fallback(cfg, f"không xuất được khung hình: {exc}")

    image = cv2.imread(str(frame_path))
    if image is None:
        return _fallback(cfg, "không đọc được khung hình đã xuất")

    faces = _detect_faces(image)
    if len(faces) == 0:
        return _fallback(cfg, "không dò được khung mặt")

    height, width = image.shape[:2]
    # Mặt lớn nhất — camera cố định, 1 người nói (assumption §11)
    fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    safe_zoom = _max_zoom_keeping_face_inside(width, height, fx, fy, fw, fh)
    safe_zoom = round(min(safe_zoom, float(cfg.zoom.max)), 3)
    safe_zoom = max(safe_zoom, float(cfg.zoom.min))

    log.info(f"dò khung mặt: mặt tại ({fx},{fy},{fw}x{fh}) → max_safe_zoom={safe_zoom}")
    return {"face_detected": True, "max_safe_zoom": safe_zoom, "reason": None}


def _detect_faces(image) -> list[tuple[int, int, int, int]]:
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    return [tuple(int(v) for v in face) for face in faces]


def _max_zoom_keeping_face_inside(
    width: int, height: int, fx: int, fy: int, fw: int, fh: int
) -> float:
    """Zoom lớn nhất mà crop giữa-tâm (Ken Burns) vẫn chứa trọn khung mặt.

    Zoom z crop 1 vùng W/z × H/z ở chính giữa khung. Mặt còn trọn vẹn khi
    khoảng cách từ tâm mặt tới tâm khung + nửa bề rộng mặt <= nửa bề rộng
    vùng crop, tính riêng cho mỗi trục rồi lấy trục siết chặt hơn.
    """
    cx, cy = width / 2, height / 2
    face_cx, face_cy = fx + fw / 2, fy + fh / 2

    def axis_limit(face_center: float, face_size: float, frame_center: float, frame_size: float) -> float:
        half_needed = abs(face_center - frame_center) + face_size / 2
        if half_needed <= 0:
            return float("inf")
        return frame_size / (2 * half_needed)

    limit_x = axis_limit(face_cx, fw, cx, width)
    limit_y = axis_limit(face_cy, fh, cy, height)
    return min(limit_x, limit_y)


def _fallback(cfg, reason: str) -> dict:
    fallback = float(cfg.zoom.fallback_max_if_no_face)
    log.warn(f"{reason} — dùng trần zoom an toàn {fallback}")
    return {"face_detected": False, "max_safe_zoom": fallback, "reason": reason}

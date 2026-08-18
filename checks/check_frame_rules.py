"""Quét CSS/HTML đồ hoạ đã dựng theo mục "Luật kiểm được" của frame.md.

Quét `hf/scenes/ov_*.html` — file THẬT `steps/05_build_overlay.py` đã dựng,
không suy diễn từ overlay_plan.json (luật áp lên HTML render ra, không áp lên
dữ liệu kế hoạch).

Đạt khi: 100% luật đạt
Phục vụ: [MGX] · TDD §12.1 · Lộ trình: Tuần 3
"""

from __future__ import annotations

import re
import sys

from lib import frame as frame_lib
from lib import paths

_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\b")
_BORDER_RADIUS = re.compile(r"border-radius:\s*(\d+)px")
_FONT_FAMILY = re.compile(r"font-family:\s*'([^']+)'")
_FONT_WEIGHT = re.compile(r"font-weight:\s*(\d+)")
_CARD_TEXT = re.compile(r'id="[^"]*_box"[^>]*>(.*?)</div>\s*</div>', re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
)


def main() -> int:
    scene_files = sorted(paths.HF_SCENES.glob("ov_*.html")) if paths.HF_SCENES.exists() else []
    if not scene_files:
        print("✓ check_frame_rules — chưa có đồ hoạ nào dựng (hf/scenes/), không có gì để kiểm")
        return 0

    frame = frame_lib.load()
    violations: list[str] = []
    for path in scene_files:
        html = path.read_text(encoding="utf-8")
        violations += _check_colors(path.name, html, frame)
        violations += _check_radius(path.name, html, frame)
        violations += _check_gradient(path.name, html)
        violations += _check_font(path.name, html, frame)
        violations += _check_card_word_limit(path.name, html)
        violations += _check_emoji(path.name, html)

    total_rules = len(frame.rules) * len(scene_files)
    if not violations:
        print(f"✓ check_frame_rules — 100% luật đạt ({len(frame.rules)} luật × {len(scene_files)} file)")
        return 0

    print(f"✗ check_frame_rules — {len(violations)}/{total_rules} lượt vi phạm")
    for line in violations:
        print(f"  {line}")
    return 1


def _check_colors(name: str, html: str, frame) -> list[str]:
    # "Không tính trắng/đen" = không tính 2 màu NỀN/CHỮ trung tính của chính
    # frame.md (ink/paper) — đọc từ config, không hardcode #000000/#ffffff
    # cứng (frame.md có thể chọn "đen" là #111111 chứ không phải đen tuyệt đối).
    neutral = {frame.colors["ink"].lower(), frame.colors["paper"].lower()}
    non_neutral = {c.lower() for c in _HEX_COLOR.findall(html)} - neutral
    if len(non_neutral) > 1:
        return [f"{name}: {len(non_neutral)} màu không tính trắng/đen (tối đa 1) — {sorted(non_neutral)}"]
    return []


def _check_radius(name: str, html: str, frame) -> list[str]:
    return [
        f"{name}: border-radius {value}px, chỉ nhận {frame.radius_px}px"
        for value in _BORDER_RADIUS.findall(html)
        if int(value) != frame.radius_px
    ]


def _check_gradient(name: str, html: str) -> list[str]:
    return [f"{name}: dùng gradient — cấm theo frame.md"] if "gradient" in html.lower() else []


def _check_font(name: str, html: str, frame) -> list[str]:
    errors = []
    families = set(_FONT_FAMILY.findall(html))
    if len(families) > 1:
        errors.append(f"{name}: dùng nhiều font trong 1 file — {families}")
    for weight in _FONT_WEIGHT.findall(html):
        if int(weight) not in frame.font_weights:
            errors.append(f"{name}: độ đậm {weight} không nằm trong {frame.font_weights}")
    return errors


def _check_card_word_limit(name: str, html: str, limit: int = 12) -> list[str]:
    errors = []
    for block in _CARD_TEXT.findall(html):
        text = _TAG.sub(" ", block).strip()
        word_count = len(text.split())
        if word_count > limit:
            errors.append(f"{name}: {word_count} từ trong card, vượt trần {limit}")
    return errors


def _check_emoji(name: str, html: str) -> list[str]:
    return [f"{name}: có emoji trong đồ hoạ — cấm theo frame.md"] if _EMOJI.search(html) else []


if __name__ == "__main__":
    sys.exit(main())

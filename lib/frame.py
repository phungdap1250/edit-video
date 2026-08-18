"""Đọc `frame.md` — nhận diện thương hiệu cho đồ hoạ motion. TDD §5.5.

Frontmatter YAML máy đọc (màu/phông/bo góc) + mục "Luật kiểm được" (danh sách
luật `check_frame_rules.py` quét được) + phần văn xuôi (Claude đọc lấy ý định,
KHÔNG phải tiêu chí Done).
"""

from __future__ import annotations

import re

import yaml

from lib import log, paths

_DEFAULT = {
    "brand": "AI Editor",
    "colors": {"primary": "#0F62FE", "ink": "#111111", "paper": "#FFFFFF"},
    "font": {"family": "Inter", "weights": [500, 700]},
    "radius_px": 12,
}
_DEFAULT_RULES = [
    "Tối đa 2 màu trong 1 đồ hoạ (không tính trắng/đen)",
    "Không dùng gradient",
    "Không dùng emoji trong đồ hoạ",
]


class Frame:
    def __init__(self, meta: dict, rules: list[str], spirit: str, *, has_rules_section: bool):
        self.meta = meta
        self.rules = rules
        self.spirit = spirit
        self.has_rules_section = has_rules_section

    @property
    def colors(self) -> dict:
        return self.meta["colors"]

    @property
    def font_family(self) -> str:
        return self.meta["font"]["family"]

    @property
    def font_weights(self) -> list[int]:
        return self.meta["font"]["weights"]

    @property
    def radius_px(self) -> int:
        return self.meta["radius_px"]


def load() -> Frame:
    """Thiếu `frame.md` → bộ mặc định trung tính, báo rõ (PRD [MGX] edge case)."""
    if not paths.FRAME_MD.exists():
        log.warn("Không có config/frame.md — dùng bộ mặc định trung tính, không có nhận diện thương hiệu")
        return Frame(_DEFAULT, _DEFAULT_RULES, "", has_rules_section=False)

    text = paths.FRAME_MD.read_text(encoding="utf-8")
    meta = _parse_frontmatter(text)
    rules, has_rules = _parse_section(text, "Luật kiểm được")
    spirit, _ = _parse_section(text, "Tinh thần thương hiệu")

    if not has_rules:
        log.warn(
            "frame.md thiếu mục 'Luật kiểm được' — chạy với bộ luật mặc định, "
            "tiêu chí Done về luật coi như CHƯA nghiệm thu được"
        )
        rules = _DEFAULT_RULES

    return Frame(meta or _DEFAULT, rules, "\n".join(spirit), has_rules_section=has_rules)


def _parse_frontmatter(text: str) -> dict | None:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return None
    return yaml.safe_load(match.group(1))


def _parse_section(text: str, heading: str) -> tuple[list[str], bool]:
    """Trả (danh sách dòng không rỗng đã bỏ gạch đầu dòng, có tìm thấy mục hay không)."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=\n## |\Z)", text, re.DOTALL | re.MULTILINE)
    if not match:
        return [], False
    body = match.group(1).strip()
    lines = [ln.lstrip("- ").strip() for ln in body.splitlines() if ln.strip()]
    return lines, True

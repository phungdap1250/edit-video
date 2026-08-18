"""Khớp ảnh có sẵn trong assets/ với đoạn cần cutaway — TDD §5.4.

Khớp theo tên file (chứa ID mục) hoặc theo từ khoá chung với `anchor_text`.
Chưa cần thư viện stock ảnh bên ngoài — PRD [JMP] ❌.
"""

from __future__ import annotations

from pathlib import Path

from lib import paths
from lib.normalize import strip_diacritics, tokenize

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
MIN_KEYWORD_LEN = 3


def list_assets() -> list[Path]:
    if not paths.ASSETS.exists():
        return []
    return sorted(p for p in paths.ASSETS.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)


def find_match(item: dict, assets: list[Path]) -> Path | None:
    """Trả file khớp nhất, hoặc None nếu không có gì phù hợp."""
    if not assets:
        return None

    item_id = item.get("id", "")
    for asset in assets:
        if item_id and item_id in asset.stem:
            return asset

    keywords = _keywords(item.get("anchor_text", ""))
    if not keywords:
        return None
    best, best_score = None, 0
    for asset in assets:
        stem_words = _keywords(asset.stem.replace("-", " ").replace("_", " "))
        score = len(keywords & stem_words)
        if score > best_score:
            best, best_score = asset, score
    return best


def _keywords(text: str) -> set[str]:
    return {strip_diacritics(w) for w in tokenize(text) if len(w) >= MIN_KEYWORD_LEN}

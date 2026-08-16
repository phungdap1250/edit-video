"""Đọc cấu hình và khoá API — TDD §9, §14.

Luật cứng §13.2: không ngưỡng nào hardcode trong steps/. Mọi số đọc qua đây.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from lib import paths
from lib.errors import AIEditorError


class Section(dict):
    """dict truy cập được bằng dấu chấm: cfg.silence.keep_below_ms."""

    def __getattr__(self, name: str) -> Any:
        try:
            value = self[name]
        except KeyError as exc:
            raise AttributeError(
                f"Thiếu khoá '{name}' trong cấu hình"
            ) from exc
        return Section(value) if isinstance(value, dict) else value


def _load_json(path: Path) -> Section:
    if not path.exists():
        raise AIEditorError(
            f"Không tìm thấy file cấu hình {path.name}",
            suggestion=f"Tạo lại {path} theo mẫu trong docs/TDD.md §9",
        )
    with path.open(encoding="utf-8") as f:
        return Section(json.load(f))


@lru_cache(maxsize=1)
def cut_config() -> Section:
    return _load_json(paths.CUT_CONFIG)


@lru_cache(maxsize=1)
def caption_style() -> Section:
    return _load_json(paths.CAPTION_STYLE)


@lru_cache(maxsize=1)
def filler_words() -> list[str]:
    """Mỗi dòng 1 mục, bỏ dòng ghi chú bắt đầu bằng #."""
    if not paths.FILLER_WORDS.exists():
        return []
    lines = paths.FILLER_WORDS.read_text(encoding="utf-8").splitlines()
    return [w.strip() for w in lines if w.strip() and not w.lstrip().startswith("#")]


def load_env() -> None:
    """Nạp .env một lần. Không có python-dotenv thì đọc tay, không chết."""
    env_file = paths.ROOT / ".env"
    if not env_file.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file)
    except ImportError:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def require_keys(names: list[str]) -> dict[str, str]:
    """Kiểm khoá API TRƯỚC khi làm việc tốn thời gian — TDD §14."""
    load_env()
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise AIEditorError(
            f"Thiếu khoá {', '.join(missing)} trong .env",
            suggestion=f"Thêm dòng {missing[0]}=... vào file .env rồi chạy lại",
        )
    return {n: os.environ[n] for n in names}

"""Đọc/ghi giá trị theo đường dẫn trường kiểu `content.items[0].text` — TDD §3.4.

`edited_fields[]` khoá theo ĐƯỜNG DẪN TRƯỜNG, không phải cấp mục — sửa 1 chữ
trong `content.items[0].text` không được khoá luôn cả `content.items[1]`.
"""

from __future__ import annotations

import re

_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def _tokens(path: str) -> list[str | int]:
    return [name if name else int(index) for name, index in _TOKEN.findall(path)]


def get_path(obj, path: str):
    cur = obj
    for token in _tokens(path):
        if isinstance(token, int):
            if not isinstance(cur, list) or token >= len(cur):
                return None
            cur = cur[token]
        else:
            if not isinstance(cur, dict) or token not in cur:
                return None
            cur = cur[token]
    return cur


def set_path(obj: dict, path: str, value) -> None:
    tokens = _tokens(path)
    cur = obj
    for token in tokens[:-1]:
        cur = cur[token]
    cur[tokens[-1]] = value

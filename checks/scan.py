"""Tiện ích quét mã nguồn dùng chung cho các script kiểm kiến trúc — TDD §12.2."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from lib import paths

CODE_DIRS = ("lib", "steps", "checks", "tools", "web")


def source_files(dirs: tuple[str, ...] = CODE_DIRS, suffix: str = ".py") -> list[Path]:
    files: list[Path] = []
    for name in dirs:
        root = paths.ROOT / name
        if root.exists():
            files.extend(p for p in root.rglob(f"*{suffix}") if "__pycache__" not in p.parts)
    return sorted(files)


def find(pattern: str, files: list[Path], *, exclude: set[Path] | None = None) -> list[str]:
    """Trả danh sách 'đường_dẫn:dòng: nội dung' khớp pattern."""
    exclude = exclude or set()
    regex = re.compile(pattern)
    hits: list[str] = []
    for path in files:
        if path in exclude:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if regex.search(line):
                rel = path.relative_to(paths.ROOT)
                hits.append(f"{rel}:{number}: {line.strip()}")
    return hits


def report(name: str, hits: list[str], ok_message: str) -> None:
    """In kết quả và thoát: 0 nếu sạch, 1 nếu có vi phạm."""
    if not hits:
        print(f"✓ {name} — {ok_message}")
        sys.exit(0)
    print(f"✗ {name} — {len(hits)} vi phạm")
    for hit in hits:
        print(f"  {hit}")
    sys.exit(1)

"""§13.3 — không có `except: pass` trong toàn bộ codebase."""

from __future__ import annotations

from checks import scan
from lib import paths

if __name__ == "__main__":
    me = {paths.ROOT / "checks" / "check_no_silent_except.py"}
    hits = scan.find(r"except[^:]*:\s*pass\s*$", scan.source_files(), exclude=me)
    scan.report("check_no_silent_except", hits, "không nuốt lỗi im lặng")

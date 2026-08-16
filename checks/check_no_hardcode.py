"""PRD [CUT] — không ngưỡng nào hardcode trong steps/. TDD §9.

Bắt "số ma": số nguyên >= 100 hoặc số thực, đứng trong biểu thức so sánh.
Ngưỡng phải đọc từ config/cut_config.json qua lib.config.
"""

from __future__ import annotations

from checks import scan
from lib import paths

MAGIC = r"[<>]=?\s*\d*\.?\d{2,}|\*\s*1000\b"

if __name__ == "__main__":
    me = {paths.ROOT / "checks" / "check_no_hardcode.py"}
    hits = scan.find(MAGIC, scan.source_files(("steps",)), exclude=me)
    scan.report("check_no_hardcode", hits, "mọi ngưỡng đọc từ config")

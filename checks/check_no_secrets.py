"""§10.1 — không khoá API nào lọt vào file được commit."""

from __future__ import annotations

from checks import scan
from lib import paths

# Mẫu khoá thật của 2 nhà cung cấp đang dùng — TDD §14
PATTERNS = r"sk_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_\-]{30,}"

if __name__ == "__main__":
    me = {paths.ROOT / "checks" / "check_no_secrets.py"}
    files = scan.source_files() + scan.source_files(("config",), ".json") + [paths.ROOT / "review.py"]
    hits = scan.find(PATTERNS, files, exclude=me)
    scan.report("check_no_secrets", hits, "không khoá API nào trong mã nguồn")

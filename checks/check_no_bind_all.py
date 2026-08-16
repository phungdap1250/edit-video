"""§10.2 — server duyệt chỉ nghe 127.0.0.1, không bao giờ 0.0.0.0."""

from __future__ import annotations

from checks import scan
from lib import paths

if __name__ == "__main__":
    me = {paths.ROOT / "checks" / "check_no_bind_all.py"}
    files = scan.source_files() + [paths.ROOT / "review.py"]
    # Chỉ bắt địa chỉ bind THẬT (nằm trong dấu nháy) — nhắc tới 0.0.0.0 trong
    # ghi chú là hợp lệ, và bắt cả nó thì check này thành tiếng ồn.
    hits = scan.find(r"[\"']0\.0\.0\.0[\"']|host\s*=\s*[\"']\s*[\"']", files, exclude=me)
    scan.report("check_no_bind_all", hits, "chỉ nghe 127.0.0.1")

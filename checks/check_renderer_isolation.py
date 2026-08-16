"""QĐ 1 — không file nào ngoài lib/renderer.py chạm HyperFrames. TDD §2.4."""

from __future__ import annotations

from checks import scan
from lib import paths

if __name__ == "__main__":
    allowed = {paths.ROOT / "lib" / "renderer.py", paths.ROOT / "checks" / "check_renderer_isolation.py"}
    hits = scan.find(r"hyperframes|\bhf\s|HYPERFRAMES_BIN|HF_BIN", scan.source_files(), exclude=allowed)
    scan.report("check_renderer_isolation", hits, "mọi tiếp xúc HyperFrames nằm trong lib/renderer.py")

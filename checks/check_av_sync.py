"""Tương quan chéo audio ra vs audio đã cắt tại 5 mốc 0/25/50/75/100%.

Đạt khi: cả 5 mốc ≤ 40ms VÀ drift(100%) − drift(0%) ≤ 40ms
Phục vụ: [RND] · TDD §12.1 · Lộ trình: Tuần 4
"""

from __future__ import annotations

import sys

if __name__ == "__main__":
    sys.stderr.write("✗ check_av_sync chưa implement — xem docs/TDD.md §12.1\n")
    sys.exit(1)

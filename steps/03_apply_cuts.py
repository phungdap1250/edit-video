"""Bước 3 — áp cắt bằng ffmpeg, tính lại timeline.

Đọc cut_plan.json (status=accepted) → ffmpeg cắt + nối → work/cut.mp4
→ build_timeline_map(): ánh xạ word.id sang giây trên timeline MỚI.
File gốc source/raw.mp4 KHÔNG BAO GIỜ bị ghi đè.

TDD: §5.2 · Lộ trình: Tuần 1
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("03_apply_cuts — xem docs/TDD.md §5.2")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("03_apply_cuts", main, parser.parse_args())

"""Bước 2 — phát hiện điểm cắt: khoảng lặng, từ đệm, nói vấp.

Bậc khoảng lặng 600/300/400ms · từ đệm nhóm A (tự cắt) / B (chỉ đề xuất)
· tầng 1 từ khoá 'cắt cắt' · tầng 2 so khớp 70%/15s · chỗ cắm tầng 3 của Claude
· bước 2.5 gộp chồng lấn (absorbed_by) → plans/cut_plan.json (pending)

TDD: §5.2 · Lộ trình: Tuần 1 sơ sài · Tuần 2 đủ 3 tầng
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("02_detect_cuts — xem docs/TDD.md §5.2")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("02_detect_cuts", main, parser.parse_args())

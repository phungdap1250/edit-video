"""Bước 6 — khớp assets/, sinh ảnh Gemini trong trần cứng.

Quét assets/ khớp từng đoạn → thiếu thì gọi Gemini.
Kiểm CẢ HAI trần trước mỗi lần gọi: 10 lượt/video và 120 lượt/tháng (§9.4).
Ảnh AI lưu riêng work/generated_images/, không lẫn assets/ người dùng.

TDD: §5.4 · Lộ trình: Tuần 3
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("06_build_cutaway — xem docs/TDD.md §5.4")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("06_build_cutaway", main, parser.parse_args())

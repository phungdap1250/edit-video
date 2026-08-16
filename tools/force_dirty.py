"""Ép một giai đoạn thành bẩn để render lại thủ công.

Dùng khi nghi máy đánh dấu bẩn sai.

TDD: §3.7 · Lộ trình: Tuần 4
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("tools.force_dirty — xem docs/TDD.md §3.7")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    parser.add_argument("stage", help="tên giai đoạn cần ép bẩn")
    cli.run("tools.force_dirty", main, parser.parse_args())

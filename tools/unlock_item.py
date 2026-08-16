"""Gỡ khoá edited_fields để Claude cập nhật lại được.

Không có lệnh này, sửa nhầm một chữ là mục đó đóng băng vĩnh viễn.

TDD: §3.4 · Lộ trình: Tuần 3
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("tools.unlock_item — xem docs/TDD.md §3.4")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    parser.add_argument("item_id")
    parser.add_argument("--field", help="chỉ gỡ khoá một đường dẫn trường")
    cli.run("tools.unlock_item", main, parser.parse_args())

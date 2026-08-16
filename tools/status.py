"""In bảng trạng thái bẩn/sạch của project.

Tính LẠI input_hash từng giai đoạn rồi ghi đè plans/project.json — file này là
bản chụp, không phải nguồn sự thật. Còn giai đoạn dirty/needs_review → in bảng
chặn render.

TDD: §3.7 · Lộ trình: Tuần 1
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("tools.status — xem docs/TDD.md §3.7")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("tools.status", main, parser.parse_args())

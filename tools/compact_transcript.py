"""Transcript rút gọn cho Claude — giảm 80% token.

Bỏ timestamp, conf, dấu ngoặc JSON. Giữ ID, chữ, [nghỉ Ns] khi > 600ms,
dấu câu. Cả 4 việc phán đoán chạy trong MỘT lượt đọc.

TDD: §7.3 · Lộ trình: Tuần 1
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("tools.compact_transcript — xem docs/TDD.md §7.3")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("tools.compact_transcript", main, parser.parse_args())

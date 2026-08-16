"""Sau khi sửa transcript: diff + kế thừa ID + liệt kê mục cần duyệt lại.

difflib khoá (text, start), chốt an toàn ±2s. Ba mức sửa: mức 1 chỉ dựng lại
caption · mức 2 chỉ duyệt lại mục mất neo (--only + partial/scope) · mức 3 hỏi
xác nhận rõ ràng trước khi mất toàn bộ duyệt.

TDD: §5.6 · Lộ trình: Tuần 2
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("tools.reanchor — xem docs/TDD.md §5.6")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    parser.add_argument("--only", action="store_true", help="chỉ duyệt lại mục mất neo")
    cli.run("tools.reanchor", main, parser.parse_args())

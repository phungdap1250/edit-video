"""Cửa DUY NHẤT để Claude ghi vào plans/*_plan.json.

Đi qua lib.validate_plan trước khi chạm đĩa. Sai schema → từ chối toàn bộ,
file cũ nguyên vẹn. Claude KHÔNG được sửa steps/, lib/, checks/, web/,
transcript.json, project.json, render_manifest.json (§7.2).

TDD: §7.4 · Lộ trình: Tuần 1
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("tools.claude_write — xem docs/TDD.md §7.4")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    parser.add_argument("--kind", required=True, choices=["cut", "overlay", "cutaway", "caption"])
    parser.add_argument("--items", required=True, help="đường dẫn file JSON chứa items[]")
    cli.run("tools.claude_write", main, parser.parse_args())

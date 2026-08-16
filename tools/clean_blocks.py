"""Xoá khối không thuộc bản dựng hiện tại.

Đối chiếu work/blocks/*.mp4 với render_manifest.json, xoá phần thừa.

TDD: §6.3 · Lộ trình: Tuần 4
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("tools.clean_blocks — xem docs/TDD.md §6.3")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("tools.clean_blocks", main, parser.parse_args())

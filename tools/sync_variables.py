"""Sinh lại hf/variables.json từ overlay_plan.

Đồng bộ MỘT CHIỀU plan → Variables. Cấm đọc ngược (§6.5).

TDD: §6.5 · Lộ trình: Tuần 3
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("tools.sync_variables — xem docs/TDD.md §6.5")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("tools.sync_variables", main, parser.parse_args())

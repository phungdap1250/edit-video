"""In bộ đếm Gemini + ước tính chi phí — CẢ HAI mức.

Lượt đã dùng trong video hiện tại (trần 10) và trong tháng (trần 120,
~/.ai-editor/budget_YYYY-MM.json). Một bộ đếm api_calls duy nhất, sinh lại
cũng tính.

TDD: §9.4 · Lộ trình: Tuần 3
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("tools.budget — xem docs/TDD.md §9.4")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("tools.budget", main, parser.parse_args())

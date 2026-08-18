"""In bộ đếm Gemini + ước tính chi phí — CẢ HAI mức.

Lượt đã dùng trong video hiện tại (trần per-video) và trong tháng (trần
per-month, ~/.ai-editor/budget_YYYY-MM.json). Một bộ đếm api_calls_used duy
nhất, sinh lại cũng tính.

TDD: §9.4 · Lộ trình: Tuần 3
"""

from __future__ import annotations

from lib import budget as budget_lib
from lib import cli, config, paths, plan_io


def main(args) -> dict:
    cfg = config.cut_config()
    cutaway_plan = {}
    if paths.CUTAWAY_PLAN.exists():
        cutaway_plan, _ = plan_io.load_plan(paths.CUTAWAY_PLAN)

    result = budget_lib.snapshot(cutaway_plan, cfg)
    print(
        f"Video hiện tại: {result['api_calls_used']}/{result['api_calls_limit']} lượt gọi Gemini\n"
        f"Tháng này:      {result['month_used']}/{result['month_limit']} lượt gọi Gemini "
        f"· ước tính {result['est_cost_vnd']:,}đ".replace(",", ".")
    )
    return result


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("tools.budget", main, parser.parse_args())

"""Sinh lại hf/variables.json từ overlay_plan.

Đồng bộ MỘT CHIỀU plan → Variables (§6.5). Cấm đọc ngược — `renderer.read_variables()`
chỉ có đúng 1 người gọi: `checks/check_variables_sync.py`.

Chỉ đồng bộ mục ĐÃ DUYỆT (status=approved) — chỉ chúng có mặt trong render
cuối (`renderer.build_overlay_track` cũng lọc y hệt), pending chưa cần biến.

TDD: §6.5 · Lộ trình: Tuần 3
"""

from __future__ import annotations

from lib import cli, overlay_content, paths, plan_io, renderer
from lib.errors import AIEditorError


def main(args) -> dict:
    if not paths.OVERLAY_PLAN.exists():
        raise AIEditorError(
            "Chưa có overlay_plan.json", suggestion="Chạy: python -m steps.05_build_overlay"
        )
    overlay_plan, _ = plan_io.load_plan(paths.OVERLAY_PLAN)
    approved = [i for i in overlay_plan.get("items", []) if i.get("status") == "approved"]

    variables: dict[str, str] = {}
    for item in approved:
        variables.update(overlay_content.extract_variables(item))

    if args.dry_run:
        return {"variables": len(variables), "items": len(approved), "dry_run": True}

    path = renderer.write_variables(variables)
    return {"variables": len(variables), "items": len(approved), "path": str(path)}


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("tools.sync_variables", main, parser.parse_args())

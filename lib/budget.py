"""Ngân sách Gemini — một bộ đếm, hai trần — TDD §9.4.

`api_calls_used` là bộ đếm DUY NHẤT: mọi lần gọi Gemini đều tính, kể cả sinh
lại. Trần per-video sống trong `cutaway_plan.json` (§3.5), trần per-month
sống ngoài project ở `~/.ai-editor/budget_YYYY-MM.json` (xuyên project).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from lib import log, paths
from lib.errors import AIEditorError


def month_key() -> str:
    return log.now_iso()[:7]  # "2026-08"


def _month_path(key: str) -> Path:
    return paths.MONTHLY_BUDGET_DIR / f"budget_{key}.json"


def month_used(key: str | None = None) -> int:
    path = _month_path(key or month_key())
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        return int(json.load(f).get("api_calls_used", 0))


def record_month_call(key: str | None = None) -> int:
    """Cộng 1 lượt vào bộ đếm tháng, trả tổng mới. Ghi nguyên tử — cùng luật §3.6."""
    key = key or month_key()
    path = _month_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    used = month_used(key) + 1
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump({"month": key, "api_calls_used": used}, f)
    os.replace(tmp, path)
    return used


def video_used(cutaway_plan: dict) -> int:
    return int(cutaway_plan.get("budget", {}).get("api_calls_used", 0))


def estimate_cost_vnd(calls: int, cfg) -> int:
    return int(calls) * int(cfg.budget.gemini_cost_vnd_per_call)


def check_regen_limit(item: dict, cfg) -> None:
    """Trần riêng của TỪNG mục — vượt chỉ chặn mục đó, không dừng cả video."""
    regen_limit = int(cfg.budget.gemini_regen_per_item)
    regen_count = int(item.get("regen_count", 0))
    if regen_count >= regen_limit:
        raise AIEditorError(
            f"{item.get('id')}: đã chạm trần {regen_limit} lần sinh lại/mục",
            suggestion="Bỏ ảnh phù hợp vào assets/ cho mục này thay vì sinh lại tiếp",
        )


def check_global_caps(cutaway_plan: dict, cfg) -> None:
    """Trần per-video và per-month — vượt một trong hai thì DỪNG gọi tiếp cho cả video.

    Kiểm CẢ HAI TRƯỚC KHI GỌI Gemini — không gọi rồi mới kiểm (§9.4).
    """
    video_limit = int(cfg.budget.gemini_api_calls_per_video)
    month_limit = int(cfg.budget.gemini_api_calls_per_month)
    used_video = video_used(cutaway_plan)
    used_month = month_used()

    if used_video >= video_limit:
        raise AIEditorError(
            f"Đã chạm trần lượt gọi Gemini cho video này: {used_video}/{video_limit}",
            suggestion="Bỏ ảnh có sẵn vào assets/ cho các mục còn thiếu",
        )
    if used_month >= month_limit:
        cost = estimate_cost_vnd(used_month, cfg)
        raise AIEditorError(
            f"Đã chạm trần tháng: {used_month}/{month_limit} lượt gọi Gemini "
            f"({cost:,}đ / {int(cfg.budget.monthly_budget_vnd):,}đ)".replace(",", "."),
            suggestion=(
                "Bỏ ảnh có sẵn vào assets/ cho các mục còn thiếu, hoặc sửa "
                "gemini_api_calls_per_month trong config nếu chấp nhận vượt ngân sách"
            ),
        )


def snapshot(cutaway_plan: dict, cfg) -> dict:
    """{ api_calls_used, api_calls_limit, month_used, month_limit, est_cost_vnd } — §4.2."""
    used_video = video_used(cutaway_plan)
    used_month = month_used()
    return {
        "api_calls_used": used_video,
        "api_calls_limit": int(cfg.budget.gemini_api_calls_per_video),
        "month_used": used_month,
        "month_limit": int(cfg.budget.gemini_api_calls_per_month),
        "est_cost_vnd": estimate_cost_vnd(used_month, cfg),
    }

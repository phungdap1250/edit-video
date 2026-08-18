"""Đường dẫn chuẩn của project — TDD §2.3. Mọi module lấy đường dẫn từ đây."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOURCE = ROOT / "source"
WORK = ROOT / "work"
BLOCKS = WORK / "blocks"
GENERATED_IMAGES = WORK / "generated_images"
CUTAWAY_NORMALIZED = WORK / "cutaway_normalized"
ASSETS = ROOT / "assets"
HF = ROOT / "hf"
HF_SCENES = HF / "scenes"
PLANS = ROOT / "plans"
DRAFT = ROOT / ".draft"
CONFIG = ROOT / "config"
LOGS = ROOT / "logs"
OUT = ROOT / "out"
WEB = ROOT / "web"

# Thư mục được phép phục vụ qua GET /media/<path> — allowlist, TDD §10.2
MEDIA_ALLOWLIST = (WORK, ASSETS, SOURCE, OUT, HF)

# Tầng dữ liệu
TRANSCRIPT = PLANS / "transcript.json"
CUT_PLAN = PLANS / "cut_plan.json"
CAPTION_PLAN = PLANS / "caption_plan.json"
OVERLAY_PLAN = PLANS / "overlay_plan.json"
CUTAWAY_PLAN = PLANS / "cutaway_plan.json"
PROJECT_STATE = PLANS / "project.json"
RENDER_MANIFEST = PLANS / "render_manifest.json"

# Cấu hình
CUT_CONFIG = CONFIG / "cut_config.json"
CAPTION_STYLE = CONFIG / "caption_style.json"
FILLER_WORDS = CONFIG / "filler_words.txt"
FRAME_MD = CONFIG / "frame.md"

# Log
RUN_LOG = LOGS / "run.log"
STATS = LOGS / "stats.jsonl"

# Zoom — tự động, không cần duyệt, tính lại được từ source + config (TDD §5.4)
ZOOM_PLAN = WORK / "zoom_plan.json"

# Ngân sách cấp tháng, xuyên project — TDD §9.4
MONTHLY_BUDGET_DIR = Path.home() / ".ai-editor"

PLAN_BY_KIND = {
    "cut": CUT_PLAN,
    "cutaway": CUTAWAY_PLAN,
    "overlay": OVERLAY_PLAN,
    "caption": CAPTION_PLAN,
}

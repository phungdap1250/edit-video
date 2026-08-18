"""Server duyệt cục bộ — TDD §4.2, §4.3, §10.2.

    python review.py cut | cutaway | storyboard

Lý do tồn tại: trình duyệt không ghi được file trên đĩa và chặn fetch() qua
file://. Server là cách duy nhất để trang duyệt vừa ghi được quyết định, vừa
phát được video/audio thật, vừa tải theo đoạn (HTTP Range).

Ràng buộc cứng: chỉ nghe 127.0.0.1 · chỉ phục vụ 4 thư mục trong allowlist ·
token phiên cho mọi /api/* · tự tắt sau khi lưu.
"""

from __future__ import annotations

import os
import secrets
import socket
import sys
import threading
import webbrowser
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file, send_from_directory

from lib import budget, config, paths, plan_io
from lib.errors import AIEditorError, PlanConflict
from lib.log import now_iso

app = Flask(__name__, static_folder=str(paths.WEB / "static"), static_url_path="/static")

SESSION_TOKEN = secrets.token_urlsafe(16)
PAGES = ("cut", "cutaway", "storyboard")
PLAN_KIND = {"cut": "cut", "cutaway": "cutaway", "storyboard": "overlay"}


# ── Bảo vệ /api/* ─────────────────────────────────────────────────
@app.before_request
def _guard_api():
    if not request.path.startswith("/api/"):
        return None
    if request.args.get("token") != SESSION_TOKEN and request.headers.get("X-Token") != SESSION_TOKEN:
        abort(403, "Token phiên không đúng")
    if request.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none"):
        abort(403, "Yêu cầu đến từ tab lạ")
    return None


# ── Trang ─────────────────────────────────────────────────────────
@app.get("/<page>")
def page(page: str):
    if page not in PAGES:
        abort(404)
    return send_from_directory(paths.WEB, f"{page}.html")


# ── Dữ liệu ───────────────────────────────────────────────────────
@app.get("/api/plan/<kind>")
def get_plan(kind: str):
    plan, version = plan_io.load_plan(_plan_path(kind))
    plan_io.snapshot_base(kind, plan)  # mốc so cho merge 3 chiều
    return jsonify({"ok": True, "version": version, "token": SESSION_TOKEN, **plan})


@app.post("/api/plan/<kind>")
def post_plan(kind: str):
    body = request.get_json(force=True)
    try:
        version, conflicts, summary = plan_io.promote_draft(
            kind,
            body.get("items", []),
            int(body.get("version", 0)),
            partial=bool(body.get("partial")),
            scope=body.get("scope"),
        )
    except PlanConflict as exc:
        return jsonify({"ok": False, "error": "PLAN_CONFLICT", "message": exc.message}), 409

    _append_stats(kind, summary)
    plan_io.clear_draft(kind)
    payload = {
        "ok": not conflicts,
        "version": version,
        "saved_at": now_iso(),
        "summary": summary,
        "conflicts": conflicts,
        "message": (
            f"Đã lưu · {summary['kept']} mục giữ · {summary['rejected']} mục bỏ "
            f"· {now_iso()[11:19]}"
        ),
    }
    if conflicts:
        payload["error"] = "PLAN_CONFLICT"
        payload["message"] = (
            f"Đã lưu {len(body.get('items', [])) - len(conflicts)} mục. "
            f"{len(conflicts)} mục cần anh quyết vì Claude cũng vừa sửa."
        )
        return jsonify(payload), 409
    return jsonify(payload)


@app.post("/api/draft/<kind>")
def post_draft(kind: str):
    plan_io.save_draft(kind, request.get_json(force=True))
    return jsonify({"ok": True, "saved_at": now_iso()})


@app.get("/api/draft/<kind>")
def get_draft(kind: str):
    return jsonify({"ok": True, "draft": plan_io.load_draft(kind)})


@app.get("/api/transcript")
def get_transcript():
    plan, version = plan_io.load_plan(paths.TRANSCRIPT)
    return jsonify({"ok": True, "version": version, **plan})


@app.get("/api/budget")
def get_budget():
    cutaway_plan = {}
    if paths.CUTAWAY_PLAN.exists():
        cutaway_plan, _ = plan_io.load_plan(paths.CUTAWAY_PLAN)
    return jsonify({"ok": True, **budget.snapshot(cutaway_plan, config.cut_config())})


# ── Media: allowlist thư mục + HTTP Range ─────────────────────────
@app.get("/media/<path:rel>")
def media(rel: str):
    target = (paths.ROOT / rel).resolve()
    if not any(_inside(target, allowed) for allowed in paths.MEDIA_ALLOWLIST):
        abort(403, "Đường dẫn nằm ngoài allowlist")
    if not target.is_file():
        abort(404)
    return send_file(target, conditional=True)  # conditional=True → HTTP Range


@app.post("/api/shutdown")
def shutdown():
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return jsonify({"ok": True})


# ── Tiện ích ──────────────────────────────────────────────────────
def _plan_path(kind: str) -> Path:
    if kind not in paths.PLAN_BY_KIND:
        abort(404, f"Loại plan không hợp lệ: {kind}")
    return paths.PLAN_BY_KIND[kind]


def _inside(target: Path, parent: Path) -> bool:
    return target == parent or parent.resolve() in target.parents


def _append_stats(kind: str, summary: dict) -> None:
    import json

    paths.LOGS.mkdir(parents=True, exist_ok=True)
    with paths.STATS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": now_iso(), "kind": kind, **summary}, ensure_ascii=False) + "\n")


def _free_port(start: int) -> int:
    for port in range(start, start + 12):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise AIEditorError(
        f"Không còn cổng trống trong dải {start}–{start + 11}",
        suggestion="Đóng bớt server đang chạy rồi thử lại",
    )


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in PAGES:
        sys.stderr.write(f"\n✗ Dùng: python review.py {' | '.join(PAGES)}\n")
        sys.exit(1)

    page_name = sys.argv[1]
    port = _free_port(int(os.environ.get("REVIEW_PORT", 7788)))
    url = f"http://127.0.0.1:{port}/{page_name}?token={SESSION_TOKEN}"
    print(f"\n  Trang duyệt: {url}\n  Ctrl+C để tắt\n")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port)  # KHÔNG BAO GIỜ 0.0.0.0 — §4.3


if __name__ == "__main__":
    main()

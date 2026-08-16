"""E2E luồng duyệt điểm cắt — Playwright giả lập người dùng thật. TDD §12.3.

Mở server review.py thật (subprocess), mở Chromium headless thật, click nút
Bỏ/Giữ thật, bấm Xuất quyết định thật — kiểm file cut_plan.json trên đĩa đổi
đúng như mong đợi. Không mock DOM, không mock fetch.

Chạy: pytest tests/test_e2e_review_cut.py -q  (cần: pip install playwright &&
playwright install chromium)
"""

from __future__ import annotations

import json
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def cut_project():
    """Ghi cut_plan/transcript tổng hợp vào plans/ THẬT của repo, có sao lưu/khôi phục.

    lib/paths.ROOT cố định theo vị trí file (`Path(__file__).resolve().parent.parent`),
    không đọc theo CWD của subprocess — review.py chạy ở bất kỳ thư mục nào vẫn luôn
    đọc đúng plans/ của repo (thiết kế 1-project-1-checkout, TDD §2.3). Vì vậy test E2E
    không thể "trỏ" server sang một thư mục giả; phải backup file thật, ghi đè tạm,
    rồi khôi phục — không dùng tmp_path làm project riêng.

    Xoá .draft/cut.*.json TRƯỚC khi ghi plan mới — nếu để tới finally mới xoá,
    một phiên review.py cũ còn sống (hoặc chưa thoát sạch) sẽ khiến client mới
    tải nhầm .draft/cut.draft.json cũ và ghi đè lên plan vừa nạp (review.js
    init(): draft có ưu tiên hơn plan, đúng thiết kế "mở lại nguyên trạng thái
    duyệt" — nhưng làm rò rỉ dữ liệu giữa 2 phiên test không liên quan).
    """
    from lib import paths

    backups: dict[Path, bytes | None] = {}
    for target in (paths.TRANSCRIPT, paths.CUT_PLAN):
        backups[target] = target.read_bytes() if target.exists() else None
        target.parent.mkdir(parents=True, exist_ok=True)
    for draft in (paths.DRAFT / "cut.draft.json", paths.DRAFT / "cut.base.json"):
        draft.unlink(missing_ok=True)

    words = [
        {"id": "w0001", "text": "chào", "start": 0.0, "end": 0.3, "conf": 1.0},
        {"id": "w0002", "text": "cả", "start": 0.3, "end": 0.6, "conf": 1.0},
        {"id": "w0003", "text": "nhà.", "start": 0.6, "end": 1.0, "conf": 1.0},
        {"id": "w0004", "text": "hôm", "start": 3.0, "end": 3.3, "conf": 1.0},
        {"id": "w0005", "text": "nay", "start": 3.3, "end": 3.6, "conf": 1.0},
    ]
    paths.TRANSCRIPT.write_text(
        json.dumps({"schema_version": 1, "version": 1, "duration_sec": 3.6, "words": words}),
        encoding="utf-8",
    )

    cut_plan = {
        "schema_version": 1, "version": 1, "input_hash": "test", "approved_at": None,
        "items": [
            {
                "id": "cut_001", "kind": "silence", "group": None,
                "anchor_start": "w0003", "anchor_end": "w0004",
                "anchor_text": "nhà. → hôm", "gap_original_ms": 2000, "keep_ms": 400,
                "tier": 0, "confidence": 1.0, "absorbed_by": None,
                "status": "accepted", "decided_by": "auto",
            },
            {
                "id": "cut_002", "kind": "filler", "group": "B",
                "anchor_start": "w0002", "anchor_end": "w0002", "anchor_text": "cả",
                "t_start": 0.3, "t_end": 0.6, "tier": 0, "confidence": 0.6,
                "context": "chào cả nhà", "absorbed_by": None,
                "status": "pending", "decided_by": "auto",
            },
        ],
    }
    paths.CUT_PLAN.write_text(json.dumps(cut_plan), encoding="utf-8")

    try:
        yield paths.ROOT
    finally:
        for target, original in backups.items():
            if original is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(original)
        for draft in (paths.DRAFT / "cut.draft.json", paths.DRAFT / "cut.base.json"):
            draft.unlink(missing_ok=True)


@pytest.fixture
def live_server(cut_project):
    """Chạy review.py thật dưới dạng subprocess — server thật, không mock."""
    port = _free_port()
    env = {"PATH": "/usr/bin:/bin:/opt/homebrew/bin", "REVIEW_PORT": str(port)}
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "review.py"), "cut"],
        cwd=str(cut_project), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        url = None
        deadline = time.time() + 10
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    raise RuntimeError("review.py thoát sớm:\n" + (proc.stdout.read() or ""))
                continue
            match = re.search(r"(http://127\.0\.0\.1:\d+/cut\?token=\S+)", line)
            if match:
                url = match.group(1)
                break
        if url is None:
            raise RuntimeError("Không thấy URL trong log khởi động review.py")
        yield url, cut_project
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


@pytest.mark.skipif(shutil.which("python3") is None, reason="cần python3 trong PATH")
def test_nguoi_dung_that_duyet_va_xuat_quyet_dinh(live_server):
    from lib import paths

    url, _ = live_server

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        page.goto(url)
        page.wait_for_selector("article.item")

        articles = page.locator("article.item")
        assert articles.count() == 2

        # Mục cut_002 (filler, pending) → bấm "Bỏ" (giữ chữ lại, không cắt)
        target = page.locator("article.item", has_text="cả")
        target.get_by_role("button", name="Bỏ").click()
        assert "rejected" in (target.get_attribute("class") or "")

        page.get_by_role("button", name="Xuất quyết định").click()
        page.wait_for_selector("text=Đã lưu", timeout=5000)

        browser.close()
        assert console_errors == [], f"Console có lỗi JS: {console_errors}"

    saved = json.loads(paths.CUT_PLAN.read_text())
    by_id = {it["id"]: it for it in saved["items"]}
    assert by_id["cut_002"]["status"] == "rejected"
    assert by_id["cut_002"]["decided_by"] == "user"
    assert by_id["cut_001"]["status"] == "accepted"  # không đụng tới, giữ nguyên
    assert saved["approved_at"] is not None
    assert saved["version"] == 2

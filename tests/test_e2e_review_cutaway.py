"""E2E luồng duyệt cutaway — Playwright giả lập người dùng thật. TDD §12.3.

Mở server review.py thật (subprocess), mở Chromium headless thật, click nút
Giữ/Bỏ/Sinh lại thật, bấm Xuất quyết định thật — kiểm file cutaway_plan.json
trên đĩa đổi đúng như mong đợi. Không mock DOM, không mock fetch, ảnh là file
PNG thật trên đĩa (phục vụ qua GET /media/<path>).

Chạy: pytest tests/test_e2e_review_cutaway.py -q  (cần: pip install playwright
&& playwright install chromium)
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
def cutaway_project():
    """Ghi cutaway_plan/transcript/ảnh tổng hợp vào plans/+work/ THẬT của repo,
    có sao lưu/khôi phục — cùng lý do với test_e2e_review_cut.py: review.py đọc
    lib.paths.ROOT cố định theo vị trí file, không theo CWD của subprocess."""
    from lib import paths

    backups: dict[Path, bytes | None] = {}
    for target in (paths.TRANSCRIPT, paths.CUTAWAY_PLAN):
        backups[target] = target.read_bytes() if target.exists() else None
        target.parent.mkdir(parents=True, exist_ok=True)
    for draft in (paths.DRAFT / "cutaway.draft.json", paths.DRAFT / "cutaway.base.json"):
        draft.unlink(missing_ok=True)

    words = [
        {"id": "w0001", "text": "chào", "start": 0.0, "end": 0.3},
        {"id": "w0002", "text": "cả", "start": 0.3, "end": 0.6},
        {"id": "w0003", "text": "nhà", "start": 0.6, "end": 2.5},
    ]
    paths.TRANSCRIPT.write_text(
        json.dumps({"schema_version": 1, "version": 1, "duration_sec": 2.5, "words": words}),
        encoding="utf-8",
    )

    image_dir = paths.WORK / "cutaway_normalized"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_path = image_dir / "cta_e2e_test.png"
    image_backed_up = image_path.exists()
    original_image = image_path.read_bytes() if image_backed_up else None
    # PNG 1x1 hợp lệ tối thiểu — đủ để <img> load được, không cần OpenCV ở đây.
    image_path.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
        "53de0000000c4944415478da6360606060000000050001a5f645400000000049454e44ae426082"
    ))

    cutaway_plan = {
        "schema_version": 1, "version": 1, "approved_at": None,
        "budget": {"api_calls_used": 0, "api_calls_limit": 10, "month_used": 0,
                   "month_limit": 120, "est_cost_vnd": 0},
        "items": [
            {"id": "cta_001", "anchor_start": "w0001", "anchor_end": "w0003",
             "anchor_text": "chào cả nhà", "prompt": None, "status": "pending",
             "image_source": "user_asset",
             "image_path": str(image_path.relative_to(paths.ROOT)),
             "t_dur": 2.5, "regen_count": 0, "regen_limit": 3},
        ],
    }
    paths.CUTAWAY_PLAN.write_text(json.dumps(cutaway_plan), encoding="utf-8")

    try:
        yield paths.ROOT
    finally:
        for target, original in backups.items():
            if original is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(original)
        for draft in (paths.DRAFT / "cutaway.draft.json", paths.DRAFT / "cutaway.base.json"):
            draft.unlink(missing_ok=True)
        if image_backed_up:
            image_path.write_bytes(original_image)
        else:
            image_path.unlink(missing_ok=True)


@pytest.fixture
def live_server(cutaway_project):
    """Chạy review.py thật dưới dạng subprocess — server thật, không mock."""
    port = _free_port()
    env = {"PATH": "/usr/bin:/bin:/opt/homebrew/bin", "REVIEW_PORT": str(port)}
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "review.py"), "cutaway"],
        cwd=str(cutaway_project), env=env,
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
            match = re.search(r"(http://127\.0\.0\.1:\d+/cutaway\?token=\S+)", line)
            if match:
                url = match.group(1)
                break
        if url is None:
            raise RuntimeError("Không thấy URL trong log khởi động review.py")
        yield url, cutaway_project
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


@pytest.mark.skipif(shutil.which("python3") is None, reason="cần python3 trong PATH")
def test_nguoi_dung_that_xem_anh_va_xuat_quyet_dinh(live_server):
    from lib import paths

    url, _ = live_server

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        page.goto(url)
        page.wait_for_selector("article.item")

        # Bộ đếm ngân sách hiện đúng trên đầu trang — PRD [JMP]
        assert "0/10" in page.locator(".budget").inner_text()

        # Ảnh THẬT load được (không phải icon vỡ) — server phục vụ qua /media
        img = page.locator("img.cutaway-thumb")
        assert img.count() == 1
        assert img.evaluate("el => el.naturalWidth > 0")

        page.get_by_role("button", name="Giữ").click()
        page.get_by_role("button", name="Xuất quyết định").click()
        page.wait_for_selector("text=Đã lưu", timeout=5000)

        browser.close()
        assert console_errors == [], f"Console có lỗi JS: {console_errors}"

    saved = json.loads(paths.CUTAWAY_PLAN.read_text())
    item = saved["items"][0]
    assert item["status"] == "accepted"
    assert item["decided_by"] == "user"
    assert saved["approved_at"] is not None


@pytest.mark.skipif(shutil.which("python3") is None, reason="cần python3 trong PATH")
def test_sinh_lai_xoa_anh_hien_tai_truoc_khi_luu(live_server):
    """"Sinh lại" chỉ được XOÁ image_path (trang không được ghi image_source,
    §4.2) — steps/06_build_cutaway mới thực sự gọi Gemini lại sau đó."""
    from lib import paths

    url, _ = live_server

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector("article.item")

        page.get_by_role("button", name="Sinh lại").click()
        page.wait_for_selector("text=chưa có ảnh")
        assert page.locator("img.cutaway-thumb").count() == 0

        page.get_by_role("button", name="Xuất quyết định").click()
        page.wait_for_selector("text=Đã lưu", timeout=5000)
        browser.close()

    saved = json.loads(paths.CUTAWAY_PLAN.read_text())
    item = saved["items"][0]
    assert item["image_path"] is None
    assert item["image_source"] == "user_asset"  # trang KHÔNG được ghi đè trường này

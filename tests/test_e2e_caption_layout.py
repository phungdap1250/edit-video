"""E2E layout caption — Playwright thật đo DOM. TDD §5.3 Done khi: tối đa 2 dòng.

Bug thật đã bắt được và sửa ở đây (không unit test thuần nào bắt được, chỉ đo
layout thật mới thấy): `position:absolute; left:50%; transform:translateX(-50%)`
khiến CSS tính "available width" chỉ bằng NỬA khung hình, kẹp `max-width` lại
bất kể giá trị đặt — câu đúng sát trần ký tự bị đẩy tràn 3-4 dòng thay vì 2.
Sửa bằng `left:0; right:0; margin:auto` để available width = trọn khung.

Chạy: pytest tests/test_e2e_caption_layout.py -q  (cần: pip install playwright
&& playwright install chromium)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib import caption_group, config, renderer

playwright_sync = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

BLANK_TEMPLATE = """<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <style>
      * { margin: 0; }
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="10"
      data-width="1080"
      data-height="1920"
    >
      <!--
        Add your clips here. Example:
        <div id="title" class="clip" data-start="0" data-duration="5" data-track-index="1"
             style="font-size: 64px; color: #fff; padding: 40px">
          Hello World
        </div>
      -->
    </div>

    <script>
      window.__timelines = window.__timelines || {};
      const tl = gsap.timeline({ paused: true });
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


@pytest.fixture
def project(tmp_path):
    (tmp_path / "hyperframes.json").write_text("{}")
    (tmp_path / "index.html").write_text(BLANK_TEMPLATE, encoding="utf-8")
    renderer.build_video_track(tmp_path, "assets/source.mp4", [(0.0, 6.0)], 1080, 1920, 30)
    return tmp_path


def _words_from(text: str, gap: float = 0.05) -> list[dict]:
    tokens = text.split()
    words, t = [], 0.0
    for i, token in enumerate(tokens):
        words.append({"id": f"w{i}", "text": token, "start": t, "end": t + 0.25})
        t += 0.25 + gap
    return words


def _line_rect(index_html: Path, line_id: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.goto(index_html.resolve().as_uri())
        info = page.evaluate(
            f"""() => {{
              const el = document.getElementById("{line_id}");
              const rect = el.getBoundingClientRect();
              const cs = getComputedStyle(el);
              return {{ width: rect.width, height: rect.height,
                        lines: Math.round(rect.height / parseFloat(cs.lineHeight)) }};
            }}"""
        )
        browser.close()
        return info


def test_dong_sat_tran_budget_khong_vuot_2_dong(project):
    """Nhóm từ do chính lib.caption_group tạo ra, đúng sát trần budget (không vượt) —
    kiểm layout thật phải ≤ 2 dòng theo Done khi (PRD [CAP])."""
    style = config.caption_style()
    max_chars = style.layout.max_chars_per_line_portrait
    budget = max_chars * style.layout.max_lines

    # Câu liên tục không dấu câu/khoảng lặng dài — ép group_lines gom sát trần budget.
    text = " ".join(["một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín", "mười"] * 3)
    words = _words_from(text)
    groups = caption_group.group_lines(words, budget)
    lines = caption_group.to_caption_lines(groups, style, max_chars)
    assert any(len(line["text"]) > max_chars for line in lines), "test vô nghĩa nếu không có dòng nào vượt 1 dòng"

    renderer.build_caption_track(project, {"mode": "karaoke_word", "lines": lines}, style, 1080, 1920)

    for line in lines:
        info = _line_rect(project / "index.html", line["id"])
        assert info["lines"] <= 2, f"{line['id']} ({len(line['text'])} ký tự) ra {info['lines']} dòng: {info}"


def test_container_canh_giua_khung(project):
    style = config.caption_style()
    line = {"id": "cap_center", "word_ids": ["w0"], "text": "Xin", "emphasis_word_ids": [],
            "t_start": 0.0, "t_end": 1.0, "word_starts": [0.0]}
    renderer.build_caption_track(
        project, {"mode": "karaoke_word", "lines": [line]}, style, 1080, 1920
    )
    info = _line_rect(project / "index.html", "cap_center")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.goto((project / "index.html").resolve().as_uri())
        center_x = page.evaluate(
            '() => { const r = document.getElementById("cap_center").getBoundingClientRect(); return r.x + r.width / 2; }'
        )
        browser.close()
    assert abs(center_x - 540) < 5  # canvas rộng 1080px, tâm phải ở 540px ± sai số render

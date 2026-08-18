"""Playwright: 20 từ ngẫu nhiên, tại t_từ + 80ms đọc DOM.

Mở THẲNG file composition đã render (không qua công cụ xem trước tương tác),
seek `window.__timelines[<id>]` — timeline chính chứa cả tween karaoke của
caption (lib.renderer.build_caption_track viết trực tiếp vào đó, không phải
sub-composition riêng).

Đạt khi: 20/20 đúng từ đang sáng
Phục vụ: [CAP] · TDD §12.1 · Lộ trình: Tuần 4
"""

from __future__ import annotations

import random
import re
import sys

from lib import config, paths, plan_io

T_OFFSET = 0.080  # TDD: "tại t_từ + 80ms"
SAMPLE_SIZE = 20


def _load(path):
    if not path.exists():
        return None
    data, _ = plan_io.load_plan(path)
    return data


def _all_words(caption_plan: dict, style) -> list[tuple[str, str, float]]:
    """Trả (span_id, màu mong đợi, t_start) cho mọi từ trong mọi dòng."""
    words = []
    for line in caption_plan.get("lines", []):
        emphasis = set(line.get("emphasis_word_ids", []))
        starts = line.get("word_starts") or []
        for i, word_id in enumerate(line.get("word_ids", [])):
            if i >= len(starts):
                continue
            color = style.color.emphasis if word_id in emphasis else style.color.active
            words.append((f"{line['id']}_w{i}", color, starts[i]))
    return words


def _extract_composition_id(index_html_path) -> str | None:
    match = re.search(r'data-composition-id="([^"]+)"', index_html_path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _colors_match(css_color: str, expected_hex: str) -> bool:
    numbers = re.findall(r"[\d.]+", css_color)
    if len(numbers) < 3:
        return False
    actual = tuple(round(float(n)) for n in numbers[:3])
    return actual == _hex_to_rgb(expected_hex)


def main() -> int:
    caption_plan = _load(paths.CAPTION_PLAN)
    index_html = paths.HF / "index.html"
    if caption_plan is None or not index_html.exists():
        print("✓ check_caption_timing — chưa có caption_plan.json hoặc hf/index.html đã render, không có gì để kiểm")
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("✗ check_caption_timing — thiếu playwright (pip install playwright && playwright install chromium)")
        return 1

    style = config.caption_style()
    words = _all_words(caption_plan, style)
    if not words:
        print("✓ check_caption_timing — caption_plan.json không có từ nào, không có gì để kiểm")
        return 0

    comp_id = _extract_composition_id(index_html)
    if comp_id is None:
        print("✗ check_caption_timing — không tìm thấy data-composition-id trong hf/index.html")
        return 1

    sample = random.sample(words, min(SAMPLE_SIZE, len(words)))
    failures: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(index_html.resolve().as_uri())
        for span_id, expected_color, t_start in sample:
            # Bọc trong arrow function KHÔNG return gì — `.seek()` trả về chính
            # timeline GSAP (tham chiếu vòng), Playwright cố serialize sẽ treo.
            page.evaluate(f'() => {{ window.__timelines["{comp_id}"].seek({t_start + T_OFFSET}); }}')
            actual = page.evaluate(f'getComputedStyle(document.getElementById("{span_id}")).color')
            if not _colors_match(actual, expected_color):
                failures.append(f"{span_id}: mong {expected_color} tại t+{T_OFFSET}s, thực {actual}")
        browser.close()

    total, passed = len(sample), len(sample) - len(failures)
    if not failures:
        print(f"✓ check_caption_timing — {passed}/{total} đúng từ đang sáng")
        return 0

    print(f"✗ check_caption_timing — {passed}/{total} đúng")
    for line in failures:
        print(f"  {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

"""Bộ chữ mẫu ề ữ ợ ẫ ỹ ặ ườ Đ — dấu tiếng Việt phải hiển thị đúng 100%.

KHÔNG dùng "ảnh chuẩn đã duyệt tay" như TDD §12.1 gợi ý (giống golden_transcript
của [CUT] — phụ thuộc con người, không tự động hoá được cho lần chạy đầu).
Thay bằng phép đo tự động: dựng mỗi ký tự mẫu lên <canvas> bằng ĐÚNG font caption
sẽ dùng khi render, so với ký tự GỐC không dấu — dấu bị vỡ/mất thì bounding-box
chiều cao và số pixel sáng gần như KHÔNG đổi so với bản không dấu.

Đạt khi: 8/8 ký tự khớp, không vỡ/chồng/mất dấu
Phục vụ: [CAP] · TDD §12.1 · Lộ trình: Tuần 4
"""

from __future__ import annotations

import sys

from lib import config, paths

SAMPLE_TO_BASE = {
    "ề": "e", "ữ": "u", "ợ": "o", "ẫ": "a", "ỹ": "y", "ặ": "a", "ườ": "uo", "Đ": "D",
}
MIN_HEIGHT_GROWTH_PX = 4  # dấu phụ (ề ữ ợ ẫ ỹ ặ ườ) phải cao hơn bản gốc ít nhất chừng này
MIN_PIXEL_DIFF_RATIO = 0.03  # Đ khác D chủ yếu ở gạch ngang — so bằng số pixel khác nhau


def _measure_js(font_family: str) -> str:
    """JS đo 1 ký tự trên canvas ẩn — trả {ascent, descent, litPixels} (list số nguyên)."""
    return f"""
(text) => {{
  const size = 120;
  const canvas = document.createElement('canvas');
  canvas.width = size; canvas.height = size;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, size, size);
  ctx.font = `700 72px "{font_family}"`;
  ctx.textBaseline = 'alphabetic';
  ctx.fillStyle = '#fff';
  ctx.fillText(text, 10, 90);
  const m = ctx.measureText(text);
  const data = ctx.getImageData(0, 0, size, size).data;
  let lit = 0;
  for (let i = 0; i < data.length; i += 4) if (data[i] > 128) lit++;
  return [Math.round((m.actualBoundingBoxAscent || 0) + (m.actualBoundingBoxDescent || 0)), lit];
}}
"""


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("✗ check_vietnamese_glyphs — thiếu playwright (pip install playwright && playwright install chromium)")
        return 1

    style = config.caption_style()
    from lib.renderer import resolve_embeddable_font

    font_family = resolve_embeddable_font(style)

    failures: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("about:blank")
        measure = page.evaluate(
            f"() => {{ window.__measure = {_measure_js(font_family)}; return true; }}"
        )
        for sample, base in SAMPLE_TO_BASE.items():
            sample_height, sample_lit = page.evaluate("(t) => window.__measure(t)", sample)
            base_height, base_lit = page.evaluate("(t) => window.__measure(t)", base)
            grew = sample_height - base_height >= MIN_HEIGHT_GROWTH_PX
            pixel_diff_ratio = abs(sample_lit - base_lit) / max(base_lit, 1)
            differs = pixel_diff_ratio >= MIN_PIXEL_DIFF_RATIO
            if not (grew or differs):
                failures.append(
                    f"'{sample}' (font {font_family}) — không thấy dấu/nét khác biệt so với "
                    f"'{base}' (cao {sample_height}px vs {base_height}px, pixel {sample_lit} vs {base_lit})"
                )
        browser.close()

    total = len(SAMPLE_TO_BASE)
    passed = total - len(failures)
    if not failures:
        print(f"✓ check_vietnamese_glyphs — {passed}/{total} ký tự khớp (font: {font_family})")
        return 0

    print(f"✗ check_vietnamese_glyphs — {passed}/{total} ký tự khớp")
    for line in failures:
        print(f"  {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

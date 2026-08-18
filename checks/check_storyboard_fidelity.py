"""So ảnh storyboard vs MP4 cuối tại 3 mốc có đồ hoạ.

So trong VÙNG `rect` của từng mục (không so toàn khung — codec video giải mã
lại giữa scene riêng và MP4 cuối có thể lệch vài pixel nền, không liên quan
tới việc đồ hoạ có khớp hay không, là điều tiêu chí này thực sự muốn biết).

Đạt khi: khác biệt < 2% điểm ảnh, cả 3 mốc
Phục vụ: [MGX] · TDD §12.1 · Lộ trình: Tuần 4
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from lib import paths, plan_io

DIFF_THRESHOLD = 0.02
SAMPLE_MOCS = 3


def main() -> int:
    out_mp4 = paths.OUT / "draft.mp4"
    if not paths.OVERLAY_PLAN.exists() or not out_mp4.exists():
        print("✓ check_storyboard_fidelity — chưa có overlay_plan.json hoặc video render, không có gì để kiểm")
        return 0

    try:
        import cv2
        import numpy as np
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        print(f"✗ check_storyboard_fidelity — thiếu thư viện: {exc}")
        return 1

    overlay_plan, _ = plan_io.load_plan(paths.OVERLAY_PLAN)
    approved = [i for i in overlay_plan.get("items", []) if i.get("status") == "approved" and i.get("rect")]
    if not approved:
        print("✓ check_storyboard_fidelity — không có mục đã duyệt có toạ độ, không có gì để kiểm")
        return 0

    index_html = paths.HF / "index.html"
    match_id = _extract_composition_id(index_html)
    samples = approved[:SAMPLE_MOCS]
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with sync_playwright() as p:
            browser = p.chromium.launch()

            for item in samples:
                t_start = _item_t_start(index_html, item["id"])
                if t_start is None:
                    failures.append(f"{item['id']}: không tìm thấy trong hf/index.html (chưa duyệt lúc render?)")
                    continue

                final_frame = tmp_path / f"{item['id']}_final.png"
                _extract_frame(out_mp4, t_start + 0.6, final_frame)

                scene_html = paths.HF_SCENES / f"{item['id']}.html"
                storyboard_frame = tmp_path / f"{item['id']}_storyboard.png"
                _screenshot_scene(browser, scene_html, storyboard_frame, t_start + 0.6)

                diff_ratio = _rect_diff_ratio(final_frame, storyboard_frame, item["rect"], cv2, np)
                if diff_ratio >= DIFF_THRESHOLD:
                    failures.append(f"{item['id']}: khác biệt {diff_ratio * 100:.1f}% (trần {DIFF_THRESHOLD * 100:.0f}%)")

            browser.close()

    if not failures:
        print(f"✓ check_storyboard_fidelity — {len(samples)}/{len(samples)} mốc khớp (< {DIFF_THRESHOLD*100:.0f}%)")
        return 0

    print(f"✗ check_storyboard_fidelity — {len(failures)}/{len(samples)} mốc lệch")
    for line in failures:
        print(f"  {line}")
    return 1


def _extract_composition_id(index_html: Path) -> str | None:
    import re

    m = re.search(r'data-composition-id="([^"]+)"', index_html.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def _item_t_start(index_html: Path, item_id: str) -> float | None:
    import re

    m = re.search(rf'id="{re.escape(item_id)}" data-start="([\d.]+)"', index_html.read_text(encoding="utf-8"))
    return float(m.group(1)) if m else None


def _extract_frame(video: Path, at_sec: float, out: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(at_sec), "-i", str(video), "-frames:v", "1", "-update", "1", str(out)],
        capture_output=True, check=True,
    )


def _scene_canvas_size(scene_html: Path) -> tuple[int, int]:
    import re

    text = scene_html.read_text(encoding="utf-8")
    w = re.search(r'data-width="(\d+)"', text)
    h = re.search(r'data-height="(\d+)"', text)
    return (int(w.group(1)) if w else 1080, int(h.group(1)) if h else 1920)


def _screenshot_scene(browser, scene_html: Path, out: Path, at_sec: float) -> None:
    # Viewport mặc định Playwright (1280×720) << canvas thật (vd 2160×3840) —
    # trang chỉ hiện được góc trên-trái composition, ảnh chụp SAI HOÀN TOÀN bố
    # cục dù không lỗi cú pháp gì (chỉ lộ ra khi so ảnh, không phải lint/log).
    width, height = _scene_canvas_size(scene_html)
    page = browser.new_page(viewport={"width": width, "height": height})
    page.goto(scene_html.resolve().as_uri(), timeout=15000)
    # 2 bug đã sửa (điều tra lúc lệch 39–99%, trần 2%):
    # (1) trước đây dùng `currentTime += 0.6` ngay sau goto(), nhưng scene tự
    #     seek video về mediaStart trên "loadedmetadata" (async) — evaluate()
    #     chạy trước khi seek đó xong thì += 0.6 cộng vào currentTime còn là 0,
    #     ra khung hình hoàn toàn sai. Sửa: set currentTime TUYỆT ĐỐI = at_sec.
    # (2) readyState >= 2 (HAVE_CURRENT_DATA) đạt được TRƯỚC KHI seek thật sự
    #     xong — set currentTime lần 2 lúc đó làm ngắt seek đang chạy dở, và
    #     sự kiện "seeked"/"timeupdate" của scene không kịp bắn nên GSAP
    #     timeline đứng ở progress=0 (đo trực tiếp: opacity đồ hoạ vẫn 0 dù
    #     currentTime đã đúng). Sửa: chờ readyState === 4 (HAVE_ENOUGH_DATA)
    #     cả trước lẫn sau khi set currentTime.
    page.wait_for_function(
        "document.getElementById('preview-video').readyState === 4", timeout=15000
    )
    page.evaluate(
        "(t) => { document.getElementById('preview-video').currentTime = t; }", at_sec
    )
    page.wait_for_function(
        "(t) => Math.abs(document.getElementById('preview-video').currentTime - t) < 0.05"
        " && document.getElementById('preview-video').readyState === 4",
        arg=at_sec, timeout=15000,
    )
    page.wait_for_timeout(400)
    page.screenshot(path=str(out))
    page.close()


def _rect_diff_ratio(img_a: Path, img_b: Path, rect: dict, cv2, np) -> float:
    a, b = cv2.imread(str(img_a)), cv2.imread(str(img_b))
    if a is None or b is None:
        return 1.0
    h, w = a.shape[:2]
    x0, y0 = int(rect["x"] * w), int(rect["y"] * h)
    x1, y1 = int((rect["x"] + rect["w"]) * w), int((rect["y"] + rect["h"]) * h)
    b_resized = cv2.resize(b, (w, h))
    crop_a = a[y0:y1, x0:x1]
    crop_b = b_resized[y0:y1, x0:x1]
    if crop_a.size == 0 or crop_b.size == 0:
        return 1.0
    diff = cv2.absdiff(crop_a, crop_b)
    changed = np.count_nonzero(np.any(diff > 30, axis=-1))
    return changed / (crop_a.shape[0] * crop_a.shape[1])


if __name__ == "__main__":
    sys.exit(main())

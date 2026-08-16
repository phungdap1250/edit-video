"""Bước 5 — dựng đồ hoạ HTML+GSAP từ overlay_plan.

4 loại: con_so_nhay · danh_sach_bung_dan · card_khai_niem · pill_tu_khoa.
Màu/phông lấy từ config/frame.md — KHÔNG hardcode. Tôn trọng edited_fields[].
→ hf/scenes/*.html (lớp 3)

TDD: §5.5 · Lộ trình: Tuần 1 sơ sài (1 loại) · Tuần 3 đủ 4 loại
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("05_build_overlay — xem docs/TDD.md §5.5")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("05_build_overlay", main, parser.parse_args())

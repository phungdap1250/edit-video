"""Bước 4 — gom dòng caption karaoke + xuất .srt.

Gom từ theo ngữ nghĩa (không ngắt giữa cụm) → Claude chọn emphasis (≤3/dòng)
→ plans/caption_plan.json + out/final.srt khớp timeline SAU cắt.
Caption ở lớp 4, đứng yên tuyệt đối, vùng caption là VÙNG CẤM.

TDD: §5.3 · Lộ trình: Tuần 1 — phép thử HyperFrames khó nhất
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("04_build_caption — xem docs/TDD.md §5.3")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("04_build_caption", main, parser.parse_args())

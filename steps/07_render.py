"""Bước 7 — chia khối, băm, render, concat, mux audio.

Chia khối 20–40s ranh giới trượt tới điểm an toàn → băm từng khối →
khối nào đã có file đúng băm thì BỎ QUA → render khối thiếu (1 tiến trình,
đóng/mở lại browser mỗi khối) → ffmpeg concat không mã hoá lại →
mux audio MỘT LẦN duy nhất → out/final.mp4

TDD: §6 · Lộ trình: Tuần 1 làm thật · Tuần 4 hoàn thiện
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("07_render — xem docs/TDD.md §6")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    parser.add_argument("--draft", action="store_true", help="bản nháp 480p")
    parser.add_argument("--final", action="store_true", help="bản cuối 1080p")
    cli.run("07_render", main, parser.parse_args())

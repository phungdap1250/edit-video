"""Bước 1 — tách audio, gọi ElevenLabs Scribe, gán ID từ.

ffmpeg tách audio → POST Scribe (language=vi, timestamps=word) → thử lại tối đa
3 lần (backoff 2s/8s/32s) rồi DỪNG → lib.normalize chuẩn hoá TRƯỚC khi gán ID
→ plans/transcript.json

TDD: §5.2 · Lộ trình: Tuần 1
"""

from __future__ import annotations

from lib import cli


def main(args) -> dict:
    raise NotImplementedError("01_transcript — xem docs/TDD.md §5.2")


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    parser.add_argument("source", help="đường dẫn video gốc")
    cli.run("01_transcript", main, parser.parse_args())

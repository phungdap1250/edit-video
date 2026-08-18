"""Xuất phụ đề .srt khớp timeline sau cắt — TDD §5.3."""

from __future__ import annotations


def _format_timestamp(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    hours, total_ms = divmod(total_ms, 3_600_000)
    minutes, total_ms = divmod(total_ms, 60_000)
    secs, ms = divmod(total_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def build_srt(lines: list[dict]) -> str:
    blocks = [
        f"{index}\n{_format_timestamp(line['t_start'])} --> {_format_timestamp(line['t_end'])}\n{line['text']}\n"
        for index, line in enumerate(lines, start=1)
    ]
    return "\n".join(blocks) + ("\n" if blocks else "")

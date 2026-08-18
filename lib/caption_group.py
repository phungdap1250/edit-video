"""Gom từ thành dòng caption karaoke — TDD §5.3.

Ngắt dòng CHỈ ở ranh giới từ (không bao giờ giữa 1 từ) — luôn ưu tiên điểm
ngắt tự nhiên (cuối câu / khoảng lặng); hạn ký tự chỉ là trần dự phòng khi
một câu quá dài không có điểm ngắt nào.
"""

from __future__ import annotations

SENTENCE_END_CHARS = ".?!…"
CLAUSE_GAP_MS = 300  # khoảng lặng giữa 2 từ cũng là ranh giới ngắt hợp lệ


def build_kept_words(transcript_words: list[dict], timeline_map: dict) -> list[dict]:
    """Từ còn giữ sau cắt, timestamp đã chuyển sang timeline MỚI — theo thứ tự gốc."""
    kept = []
    for w in transcript_words:
        pos = timeline_map.get(w["id"])
        if pos is None:
            continue
        kept.append({"id": w["id"], "text": w["text"], "start": pos[0], "end": pos[1]})
    return kept


def group_lines(words: list[dict], char_budget: int) -> list[list[dict]]:
    """karaoke_word: gom theo câu/cụm, trần `char_budget` (max_chars_per_line × max_lines)."""
    groups: list[list[dict]] = []
    current: list[dict] = []
    current_len = 0

    for i, w in enumerate(words):
        added_len = len(w["text"]) + (1 if current else 0)
        if current and current_len + added_len > char_budget:
            groups.append(current)
            current, current_len = [], 0
            added_len = len(w["text"])
        current.append(w)
        current_len += added_len

        is_last = i == len(words) - 1
        ends_sentence = w["text"].rstrip()[-1:] in SENTENCE_END_CHARS
        gap_after_ms = ((words[i + 1]["start"] - w["end"]) * 1000) if not is_last else None
        natural_boundary = ends_sentence or (gap_after_ms is not None and gap_after_ms >= CLAUSE_GAP_MS)
        if natural_boundary or is_last:
            groups.append(current)
            current, current_len = [], 0

    if current:
        groups.append(current)
    return groups


def group_words_pop(words: list[dict], max_words: int = 3) -> list[list[dict]]:
    """word_pop: cụm 1–3 từ, vẫn ưu tiên ngắt ở khoảng lặng khi có."""
    groups: list[list[dict]] = []
    current: list[dict] = []

    for i, w in enumerate(words):
        current.append(w)
        is_last = i == len(words) - 1
        gap_after_ms = ((words[i + 1]["start"] - w["end"]) * 1000) if not is_last else None
        boundary = len(current) >= max_words or is_last or (
            gap_after_ms is not None and gap_after_ms >= CLAUSE_GAP_MS
        )
        if boundary:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def choose_mode(style, orientation: str, total_duration_sec: float) -> str:
    threshold = style.mode_auto.word_pop_if_vertical_and_under_sec
    if orientation == "portrait" and total_duration_sec < threshold:
        return "word_pop"
    return "karaoke_word"


def to_caption_lines(groups: list[list[dict]], style, max_chars_per_line: int) -> list[dict]:
    """Chuyển nhóm từ → mục caption_plan.json (TDD §3.5). Không gán emphasis —
    đó là việc của Claude qua `tools.claude_write --kind caption` (TDD §7.1)."""
    min_display_sec = style.timing.min_display_ms / 1000.0
    max_linger_sec = style.timing.max_linger_after_speech_ms / 1000.0

    lines: list[dict] = []
    for index, group in enumerate(groups):
        t_start = group[0]["start"]
        natural_end = group[-1]["end"]
        t_end = max(natural_end, t_start + min_display_sec)
        t_end = min(t_end, natural_end + max_linger_sec)
        next_start = groups[index + 1][0]["start"] if index + 1 < len(groups) else None
        if next_start is not None:
            t_end = min(t_end, next_start)

        lines.append({
            "id": f"cap_{index:03d}",
            "word_ids": [w["id"] for w in group],
            "text": " ".join(w["text"] for w in group),
            "emphasis_word_ids": [],
            "t_start": round(t_start, 3),
            "t_end": round(max(t_end, t_start), 3),
            "line_break_after": _line_break_after(group, max_chars_per_line),
            # Mốc sáng từng từ THẬT (không chia đều) — TDD Done khi đòi sai lệch
            # < 150ms, chia đều thời lượng dòng theo số từ sẽ không đạt được mức đó.
            "word_starts": [round(w["start"], 3) for w in group],
        })
    return lines


def _line_break_after(group: list[dict], max_chars_per_line: int) -> int | None:
    """Chỉ số từ CUỐI CÙNG của dòng chữ thứ nhất — None nếu 1 dòng đã đủ chứa."""
    total = sum(len(w["text"]) for w in group) + max(0, len(group) - 1)
    if total <= max_chars_per_line:
        return None

    running, best = 0, None
    for i, w in enumerate(group):
        running += len(w["text"]) + (1 if i > 0 else 0)
        if running <= max_chars_per_line:
            best = i
        else:
            break
    return best

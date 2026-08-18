"""Bước 4 — gom dòng caption karaoke + xuất .srt.

Gom từ theo ngữ nghĩa (không ngắt giữa cụm) → plans/caption_plan.json (KHÔNG
có bước duyệt — PRD không yêu cầu, TDD §5.3) + out/final.srt khớp timeline
SAU cắt. Claude ghi thêm `emphasis_word_ids[]` sau, qua `tools.claude_write
--kind caption` (TDD §7.1). Caption ở lớp 4, đứng yên tuyệt đối.

TDD: §5.3 · Lộ trình: Tuần 1 — phép thử HyperFrames khó nhất
"""

from __future__ import annotations

from lib import caption_group, cli, config, hashing, log, paths, plan_io, srt, timeline
from lib.errors import AIEditorError
from lib.timeline import EOF_ID


def main(args) -> dict:
    transcript, _ = plan_io.load_plan(paths.TRANSCRIPT)
    cut_plan, _ = plan_io.load_plan(paths.CUT_PLAN)
    if cut_plan.get("approved_at") is None:
        raise AIEditorError(
            "cut_plan.json chưa được duyệt", suggestion="Chạy: python review.py cut"
        )

    cfg = config.cut_config()
    style = config.caption_style()
    words = transcript["words"]
    duration = transcript["duration_sec"]
    padding_sec = cfg.silence.padding_each_side_ms / 1000.0

    timeline_map = timeline.build_timeline_map(words, cut_plan["items"], duration, padding_sec=padding_sec)
    kept_words = caption_group.build_kept_words(words, timeline_map)
    if not kept_words:
        raise AIEditorError(
            "Không còn từ nào sau khi áp cắt", suggestion="Mở lại python review.py cut"
        )

    orientation = "portrait" if transcript["height"] > transcript["width"] else "landscape"
    total_duration = timeline_map[EOF_ID][0]
    mode = caption_group.choose_mode(style, orientation, total_duration)
    max_chars = (
        style.layout.max_chars_per_line_portrait
        if orientation == "portrait"
        else style.layout.max_chars_per_line_landscape
    )

    if mode == "word_pop":
        groups = caption_group.group_words_pop(kept_words)
    else:
        groups = caption_group.group_lines(kept_words, max_chars * style.layout.max_lines)
    lines = caption_group.to_caption_lines(groups, style, max_chars)

    if args.dry_run:
        return {"lines": len(lines), "mode": mode, "dry_run": True}

    document = {
        "schema_version": 1,
        "version": 0,
        "input_hash": hashing.sha256_file(paths.CUT_PLAN),
        "mode": mode,
        "lines": lines,
    }
    version = _save(document)

    srt_text = srt.build_srt(lines)
    paths.OUT.mkdir(parents=True, exist_ok=True)
    (paths.OUT / "final.srt").write_text(srt_text, encoding="utf-8")

    log.info(f"caption: {len(lines)} dòng, mode={mode} — đã xuất out/final.srt")
    return {"lines": len(lines), "mode": mode, "orientation": orientation, "version": version}


def _save(document: dict) -> int:
    if paths.CAPTION_PLAN.exists():
        _, current = plan_io.load_plan(paths.CAPTION_PLAN)
        return plan_io.save_plan(paths.CAPTION_PLAN, document, current, force=True)
    return plan_io.save_plan(paths.CAPTION_PLAN, document, 0)


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("04_build_caption", main, parser.parse_args())

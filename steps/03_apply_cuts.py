"""Bước 3 — áp cắt bằng ffmpeg, tính lại timeline.

Đọc cut_plan.json (status=accepted) → ffmpeg cắt + nối → work/cut.mp4
→ build_timeline_map(): ánh xạ word.id sang giây trên timeline MỚI.
File gốc source/raw.mp4 KHÔNG BAO GIỜ bị ghi đè.

TDD: §5.2 · Lộ trình: Tuần 1
"""

from __future__ import annotations

from lib import cli, config, log, media, paths, plan_io, timeline
from lib.errors import AIEditorError


def main(args) -> dict:
    transcript, _ = plan_io.load_plan(paths.TRANSCRIPT)
    cut_plan, _ = plan_io.load_plan(paths.CUT_PLAN)

    if cut_plan.get("approved_at") is None:
        raise AIEditorError(
            "cut_plan.json chưa được duyệt",
            suggestion="Chạy: python review.py cut",
        )

    words = transcript["words"]
    duration = transcript["duration_sec"]
    cfg = config.cut_config()
    padding_sec = cfg.silence.padding_each_side_ms / 1000.0

    removals = timeline.removal_intervals(words, cut_plan["items"], duration, padding_sec=padding_sec)
    segments = timeline.kept_segments(removals, duration)
    kept_sec = sum(hi - lo for lo, hi in segments)

    log.info(
        f"áp cắt: {len(removals)} khoảng bị xoá, giữ {len(segments)} đoạn "
        f"({kept_sec:.1f}s / {duration:.1f}s gốc)"
    )

    if args.dry_run:
        return {"segments": len(segments), "kept_sec": round(kept_sec, 1), "dry_run": True}

    source = paths.SOURCE / "raw.mp4"
    out = paths.WORK / "cut.mp4"
    media.cut_segments(source, segments, out, fps=cfg.render.fps)

    new_timeline = timeline.build_timeline_map(
        words, cut_plan["items"], duration, padding_sec=padding_sec
    )
    _save_timeline(new_timeline, kept_sec)

    log.info(f"work/cut.mp4: {kept_sec:.1f}s, {len(new_timeline) - 2} từ còn giữ")
    return {"kept_sec": round(kept_sec, 1), "words_kept": len(new_timeline) - 2}


def _save_timeline(mapping: dict[str, tuple[float, float]], duration_sec: float) -> None:
    """Lưu bảng tra để các step sau (caption/overlay/cutaway) không phải tính lại.

    Nằm trong work/, không phải plans/ — tính lại được từ transcript.json +
    cut_plan.json bất cứ lúc nào (TDD §2.3: plans/ là nguồn sự thật, work/ là
    thứ xoá đi lúc nào cũng được). Không thuộc 7 file plan cố định ở §3.1.
    """
    document = {
        "schema_version": 1,
        "version": 0,
        "duration_sec": round(duration_sec, 3),
        "words": {wid: {"start": s, "end": e} for wid, (s, e) in mapping.items()},
    }
    path = paths.WORK / "timeline_map.json"
    if path.exists():
        _, current = plan_io.load_plan(path)
        plan_io.save_plan(path, document, current, force=True)
    else:
        plan_io.save_plan(path, document, 0)


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("03_apply_cuts", main, parser.parse_args())

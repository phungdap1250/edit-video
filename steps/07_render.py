"""Bước 7 — sinh project HyperFrames, render, xuất MP4.

[RND-01] bản mỏng (TDD §16 tuần 1): render TOÀN BỘ composition một lần, chưa
chia khối tăng dần (§6.2/§6.3 cần timeline caption/overlay để tìm điểm an
toàn — các lớp đó thuộc [CAP-01]/[MGX-01], chưa tồn tại).

Render trỏ THẲNG vào source/raw.mp4 với mỗi đoạn giữ lại trỏ qua
`data-media-start` — HyperFrames tự trim, không cần work/cut.mp4 (tránh mã hoá
lại hai lần: ffmpeg cắt rồi HyperFrames render lại). work/cut.mp4 của bước 3
vẫn hữu ích cho debug/kiểm tay, không phải nguồn cho render.

TDD: §6 · Lộ trình: Tuần 1 làm thật (mỏng) · Tuần 4 hoàn thiện (chia khối)
"""

from __future__ import annotations

import shutil
from pathlib import Path

from lib import cli, config, frame as frame_lib, log, media, paths, plan_io, renderer, timeline
from lib.errors import AIEditorError


def main(args) -> dict:
    quality = "high" if args.final else "draft"

    transcript, _ = plan_io.load_plan(paths.TRANSCRIPT)
    cut_plan, _ = plan_io.load_plan(paths.CUT_PLAN)
    if cut_plan.get("approved_at") is None:
        raise AIEditorError(
            "cut_plan.json chưa được duyệt",
            suggestion="Chạy: python review.py cut",
        )

    source = paths.SOURCE / "raw.mp4"
    info = media.probe(source)
    cfg = config.cut_config()
    padding_sec = cfg.silence.padding_each_side_ms / 1000.0

    removals = timeline.removal_intervals(
        transcript["words"], cut_plan["items"], transcript["duration_sec"], padding_sec=padding_sec
    )
    segments = timeline.kept_segments(removals, transcript["duration_sec"])
    kept_sec = round(sum(hi - lo for lo, hi in segments), 3)

    if args.dry_run:
        return {"segments": len(segments), "kept_sec": kept_sec, "quality": quality, "dry_run": True}

    ok, detail = renderer.hf_available()
    if not ok:
        raise AIEditorError(
            f"HyperFrames chưa sẵn sàng: {detail}",
            suggestion="Kiểm môi trường dựng bằng lib.renderer.hf_available()",
        )

    _check_disk_space(cfg)

    canvas_width, canvas_height = renderer.create_project(
        paths.HF, info["width"], info["height"], cfg.render.fps
    )
    asset_rel = renderer.link_source_asset(paths.HF, source)
    renderer.build_video_track(
        paths.HF, asset_rel, segments, canvas_width, canvas_height, cfg.render.fps
    )
    _build_captions(canvas_width, canvas_height)
    _build_overlays(transcript, cut_plan, padding_sec, canvas_width, canvas_height)
    renderer.check(paths.HF)

    out = paths.OUT / ("final.mp4" if args.final else "draft.mp4")
    renderer.render(paths.HF, out, quality=quality)

    _save_manifest(segments, quality, out)

    log.info(f"render {quality} xong: {out.name}, {kept_sec}s, {len(segments)} đoạn")
    return {"out": str(out), "kept_sec": kept_sec, "segments": len(segments), "quality": quality}


def _check_disk_space(cfg) -> None:
    """Kiểm dung lượng trống TRƯỚC khi render — TDD §11.3, PRD [RND-01] Done khi."""
    free_gb = shutil.disk_usage(paths.ROOT).free / 1e9
    need_gb = cfg.render.disk_estimate_gb_per_5min
    if free_gb < need_gb:
        raise AIEditorError(
            f"Ổ đĩa chỉ còn {free_gb:.1f}GB trống, cần ít nhất {need_gb}GB để render an toàn",
            suggestion="Dọn bớt dung lượng rồi chạy lại — chưa có gì bị ghi ra khi lỗi này hiện",
        )


def _build_captions(canvas_width: int, canvas_height: int) -> None:
    """Lớp 4 — chưa có caption_plan.json (CAP-01 chưa chạy) thì bỏ qua, video vẫn dựng được."""
    if not paths.CAPTION_PLAN.exists():
        log.info("chưa có caption_plan.json — bỏ qua lớp caption")
        return
    caption_plan, _ = plan_io.load_plan(paths.CAPTION_PLAN)
    style = config.caption_style()
    renderer.build_caption_track(paths.HF, caption_plan, style, canvas_width, canvas_height)


def _build_overlays(transcript, cut_plan, padding_sec: float, canvas_width: int, canvas_height: int) -> None:
    """Lớp 3 — chưa có overlay_plan.json (MGX-01 chưa chạy) thì bỏ qua, video vẫn dựng được."""
    if not paths.OVERLAY_PLAN.exists():
        log.info("chưa có overlay_plan.json — bỏ qua lớp đồ hoạ")
        return
    overlay_plan, _ = plan_io.load_plan(paths.OVERLAY_PLAN)
    timeline_map = timeline.build_timeline_map(
        transcript["words"], cut_plan["items"], transcript["duration_sec"], padding_sec=padding_sec
    )
    frame = frame_lib.load()
    renderer.build_overlay_track(
        paths.HF, overlay_plan.get("items", []), frame, timeline_map, canvas_width, canvas_height
    )

def _save_manifest(segments: list[tuple[float, float]], quality: str, out: Path) -> None:
    """render_manifest.json — TDD §3.1. Khung 1 khối duy nhất, chưa chia nhỏ."""
    document = {
        "schema_version": 1,
        "version": 0,
        "renderer_version": renderer.RENDERER_VERSION,
        "quality": quality,
        "output": str(out.relative_to(paths.ROOT)),
        "blocks": [{"id": "whole", "segments": [[round(lo, 3), round(hi, 3)] for lo, hi in segments]}],
    }
    path = paths.RENDER_MANIFEST
    if path.exists():
        _, current = plan_io.load_plan(path)
        plan_io.save_plan(path, document, current, force=True)
    else:
        plan_io.save_plan(path, document, 0)


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    parser.add_argument("--draft", action="store_true", help="bản nháp 480p (mặc định)")
    parser.add_argument("--final", action="store_true", help="bản cuối 1080p")
    cli.run("07_render", main, parser.parse_args())

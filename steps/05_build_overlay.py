"""Bước 5 — dựng đồ hoạ HTML+GSAP từ overlay_plan.

4 loại: con_so_nhay · danh_sach_bung_dan · card_khai_niem · pill_tu_khoa.
Màu/phông lấy từ config/frame.md — KHÔNG hardcode. Tôn trọng edited_fields[]
(đã thi hành ở tools.claude_write, không đụng lại ở đây).

Dựng scene xem trước cho MỌI mục (kể cả pending) → hf/scenes/ov_*.html, phục
vụ trang /storyboard (bản động, có tiếng, tua được). Ghép vào lớp 3 của video
cuối là việc của steps/07_render (chỉ mục đã duyệt).

TDD: §5.5 · Lộ trình: Tuần 1 sơ sài (1 loại) · Tuần 3 đủ 4 loại
"""

from __future__ import annotations

from lib import cli, config, frame as frame_lib, log, media, overlay_content, paths, plan_io, renderer, timeline
from lib.errors import AIEditorError


def main(args) -> dict:
    transcript, _ = plan_io.load_plan(paths.TRANSCRIPT)
    cut_plan, _ = plan_io.load_plan(paths.CUT_PLAN)
    if cut_plan.get("approved_at") is None:
        raise AIEditorError(
            "cut_plan.json chưa được duyệt", suggestion="Chạy: python review.py cut"
        )

    if not paths.OVERLAY_PLAN.exists():
        log.info("chưa có overlay_plan.json — Claude chưa chọn đoạn cần đồ hoạ, bỏ qua")
        return {"scenes": 0, "skipped": 0}

    overlay_plan, _ = plan_io.load_plan(paths.OVERLAY_PLAN)
    items = overlay_plan.get("items", [])
    if not items:
        return {"scenes": 0, "skipped": 0}

    cfg = config.cut_config()
    padding_sec = cfg.silence.padding_each_side_ms / 1000.0
    timeline_map = timeline.build_timeline_map(
        transcript["words"], cut_plan["items"], transcript["duration_sec"], padding_sec=padding_sec
    )
    frame = frame_lib.load()
    canvas_width, canvas_height = transcript["width"], transcript["height"]

    if args.dry_run:
        return {"scenes": len(items), "dry_run": True}

    source = paths.SOURCE / "raw.mp4"
    video_rel_path = "../assets/source.mp4"
    if source.exists():
        renderer.link_source_asset(paths.HF, source)
        preview = media.ensure_browser_playable(source, paths.HF / "assets" / "source-preview.mp4")
        if preview != source:
            video_rel_path = "../assets/source-preview.mp4"

    built = skipped = 0
    for item in items:
        # rect do SCRIPT tính (giống t_dur ở cutaway [JMP-01]) — không phải trường
        # Claude ghi, nên ghi thẳng qua plan_io chứ không qua tools.claude_write.
        item["rect"] = overlay_content.resolve_rect(item.get("position"))
        scene = renderer.build_overlay_scene(
            paths.HF, item, frame, timeline_map, canvas_width, canvas_height, video_rel_path
        )
        if scene is None:
            skipped += 1
            log.warn(f"{item['id']}: neo đã mất (đoạn kích hoạt bị [CUT] cắt) — không dựng scene xem trước")
        else:
            built += 1

    overlay_plan["items"] = items
    _save(overlay_plan)

    log.info(f"đã dựng {built} scene đồ hoạ ({len(frame.rules)} luật frame.md), {skipped} mục bỏ qua")
    return {"scenes": built, "skipped": skipped, "frame_rules": len(frame.rules)}


def _save(document: dict) -> int:
    _, current = plan_io.load_plan(paths.OVERLAY_PLAN)
    return plan_io.save_plan(paths.OVERLAY_PLAN, document, current, force=True)


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("05_build_overlay", main, parser.parse_args())

"""Bước 6 — dò khung mặt tính zoom (lớp 1), khớp assets/, sinh ảnh Gemini (lớp 2).

Zoom: tự động, không cần duyệt → work/zoom_plan.json (§5.4, §6.1).
Cutaway: Claude đã chọn đoạn + soạn `prompt` qua `tools.claude_write --kind
cutaway` trước khi chạy bước này. Ở đây: quét assets/ khớp hình có sẵn, thiếu
thì kiểm CẢ HAI trần TRƯỚC KHI GỌI Gemini, ảnh AI sinh lưu work/generated_images/
— không lẫn assets/ người dùng. Chạm trần → dừng gọi tiếp, các mục còn lại
đánh dấu `missing`, video vẫn dựng được (chỉ thiếu mục đó).

TDD: §5.4 · Lộ trình: Tuần 3
"""

from __future__ import annotations

from lib import budget, cli, config, cutaway_assets, face, gemini, image, log, paths, plan_io, timeline
from lib import zoom as zoom_lib
from lib.errors import AIEditorError


def main(args) -> dict:
    transcript, _ = plan_io.load_plan(paths.TRANSCRIPT)
    cut_plan, _ = plan_io.load_plan(paths.CUT_PLAN)
    if cut_plan.get("approved_at") is None:
        raise AIEditorError(
            "cut_plan.json chưa được duyệt", suggestion="Chạy: python review.py cut"
        )

    cfg = config.cut_config()
    words = transcript["words"]
    duration = transcript["duration_sec"]
    padding_sec = cfg.silence.padding_each_side_ms / 1000.0

    removals = timeline.removal_intervals(words, cut_plan["items"], duration, padding_sec=padding_sec)
    kept_segments = timeline.kept_segments(removals, duration)

    if args.dry_run:
        return {"segments": len(kept_segments), "dry_run": True}

    zoom_summary = _build_zoom(kept_segments, cfg)
    cutaway_summary = _build_cutaway(transcript, words, cut_plan, duration, padding_sec, cfg)

    log.info(
        f"zoom: {zoom_summary['items']} đoạn (max_safe_zoom={zoom_summary['max_safe_zoom']}) · "
        f"cutaway: {cutaway_summary['matched']} khớp assets, {cutaway_summary['generated']} AI sinh, "
        f"{cutaway_summary['missing']} thiếu"
    )
    return {**zoom_summary, **cutaway_summary}


def _build_zoom(kept_segments: list[tuple[float, float]], cfg) -> dict:
    detection = face.detect_max_safe_zoom(paths.SOURCE / "raw.mp4", paths.WORK, cfg)
    schedule = zoom_lib.build_schedule(kept_segments, detection["max_safe_zoom"], cfg)
    document = {
        "schema_version": 1,
        "version": 0,
        "face_detected": detection["face_detected"],
        "max_safe_zoom": detection["max_safe_zoom"],
        "reason": detection["reason"],
        "items": schedule,
    }
    _save(paths.ZOOM_PLAN, document)
    return {
        "items": len(schedule),
        "max_safe_zoom": detection["max_safe_zoom"],
        "face_detected": detection["face_detected"],
    }


def _build_cutaway(transcript, words, cut_plan, duration, padding_sec, cfg) -> dict:
    if not paths.CUTAWAY_PLAN.exists():
        log.info("chưa có cutaway_plan.json — Claude chưa chọn đoạn cần minh hoạ, bỏ qua")
        return {"cutaway_items": 0, "matched": 0, "generated": 0, "missing": 0}

    plan, version = plan_io.load_plan(paths.CUTAWAY_PLAN)
    plan["items"] = plan.get("items", [])
    timeline_map = timeline.build_timeline_map(words, cut_plan["items"], duration, padding_sec=padding_sec)
    width, height = transcript["width"], transcript["height"]
    assets = cutaway_assets.list_assets()

    matched = generated = missing = skipped = 0
    global_stop_reason: str | None = None

    for item in plan["items"]:
        # image_path rỗng = cần (sinh) ảnh. Cờ đúng đắn để phát hiện "sinh lại":
        # trang /cutaway không được ghi image_source (§4.2 bảng quyền), bấm nút
        # sinh lại chỉ xoá image_path — image_source cũ vẫn còn để nhận biết.
        if item.get("image_path"):
            continue
        item["t_dur"] = _item_duration(item, timeline_map)
        item["regen_limit"] = int(cfg.budget.gemini_regen_per_item)

        skip_reason = _ineligible_reason(item["t_dur"], cfg)
        if skip_reason is not None:
            log.info(f"{item.get('id')}: {skip_reason} — bỏ qua, chỉ zoom")
            item["status"] = "rejected"
            item["image_source"] = "missing"
            skipped += 1
            continue

        asset = cutaway_assets.find_match(item, assets)
        if asset is not None:
            _assign_user_asset(item, asset, width, height)
            matched += 1
            continue

        missing_reason, is_global = _try_generate(item, plan, cfg, width, height, global_stop_reason)
        if missing_reason is None:
            generated += 1
        else:
            item["image_source"] = "missing"
            missing += 1
            if is_global:
                global_stop_reason = global_stop_reason or missing_reason

    plan["budget"] = budget.snapshot(plan, cfg)
    _save(paths.CUTAWAY_PLAN, plan, current_version=version)
    return {
        "cutaway_items": len(plan["items"]),
        "matched": matched,
        "generated": generated,
        "missing": missing,
        "skipped": skipped,
    }


def _ineligible_reason(t_dur: float, cfg) -> str | None:
    """PRD [JMP] edge case: đoạn quá ngắn không chèn cutaway; Done khi: không che mặt quá 8s."""
    if t_dur < float(cfg.cutaway.min_segment_sec):
        return f"đoạn giữ lại {t_dur}s ngắn hơn {cfg.cutaway.min_segment_sec}s"
    if t_dur > float(cfg.cutaway.max_face_cover_sec):
        return f"đoạn dài {t_dur}s sẽ che mặt quá {cfg.cutaway.max_face_cover_sec}s liên tục"
    return None


def _item_duration(item: dict, timeline_map: dict) -> float:
    start_id, end_id = item.get("anchor_start"), item.get("anchor_end")
    if start_id not in timeline_map or end_id not in timeline_map:
        raise AIEditorError(
            f"{item.get('id')} neo vào từ không tồn tại trên timeline sau cắt",
            suggestion="Chạy: python -m tools.reanchor",
        )
    return round(timeline_map[end_id][1] - timeline_map[start_id][0], 3)


def _assign_user_asset(item: dict, asset, width: int, height: int) -> None:
    out = paths.CUTAWAY_NORMALIZED / f"{item['id']}{asset.suffix.lower()}"
    image.normalize_aspect(asset, out, width, height)
    item["image_source"] = "user_asset"
    item["image_path"] = str(out.relative_to(paths.ROOT))
    item["prompt"] = None


def _try_generate(
    item: dict, plan: dict, cfg, width: int, height: int, global_stop_reason: str | None
) -> tuple[str | None, bool]:
    """Trả (lý do thất bại | None, có phải trần TOÀN VIDEO/THÁNG hay không).

    Trần regen chỉ chặn MỤC này; trần video/tháng chặn CẢ các mục sau —
    caller dùng cờ thứ hai để không gọi Gemini vô ích cho phần còn lại.
    """
    try:
        budget.check_regen_limit(item, cfg)
    except AIEditorError as exc:
        log.warn(exc.message)
        return exc.message, False

    if global_stop_reason is not None:
        return global_stop_reason, True

    try:
        budget.check_global_caps(plan, cfg)
    except AIEditorError as exc:
        log.warn(exc.render())
        return exc.message, True

    # image_path đã bị xoá (bấm "sinh lại") nhưng image_source cũ vẫn còn — dùng
    # nó để biết đây là lần sinh lại, không phải lần sinh đầu (script mới được
    # ghi image_source, trang /cutaway không được — §4.2).
    is_regen = item.get("image_source") == "ai_generated"
    out = paths.GENERATED_IMAGES / f"{item['id']}_v{int(item.get('regen_count', 0)) + 1}.png"
    try:
        gemini.generate_image(item.get("prompt") or item.get("anchor_text", ""), width, height, out)
    except AIEditorError as exc:
        log.warn(f"{item.get('id')}: {exc.message}")
        return exc.message, False

    budget.record_month_call()
    plan.setdefault("budget", {})
    plan["budget"]["api_calls_used"] = int(plan["budget"].get("api_calls_used", 0)) + 1
    item["regen_count"] = int(item.get("regen_count", 0)) + 1 if is_regen else int(item.get("regen_count", 0))
    item["image_source"] = "ai_generated"
    item["image_path"] = str(out.relative_to(paths.ROOT))
    return None, False


def _save(path, document: dict, current_version: int = 0) -> int:
    if path.exists():
        return plan_io.save_plan(path, document, current_version, force=True)
    return plan_io.save_plan(path, document, 0)


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    cli.run("06_build_cutaway", main, parser.parse_args())

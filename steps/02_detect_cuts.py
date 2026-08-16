"""Bước 2 — phát hiện điểm cắt: khoảng lặng, từ đệm, nói vấp.

Chạy tuần tự theo TDD §5.2: khoảng lặng theo bậc → tầng 1 ("cắt cắt") → tầng 2
(so khớp 70%/15s, chỉ xét phần tầng 1 chưa tiêu thụ) → từ đệm nhóm A/B (bỏ qua
từ đã tiêu thụ) → bước 2.5 gộp chồng lấn (absorbed_by).

Tầng 3 (Claude đọc ngữ cảnh) KHÔNG chạy ở đây — Claude ghi thêm mục `tier=3`
qua `tools.claude_write --kind cut` sau khi đọc transcript rút gọn (TDD §7.1).

TDD: §5.2 · Lộ trình: Tuần 1 sơ sài (chỉ khoảng lặng) · Tuần 2 đủ 3 tầng
"""

from __future__ import annotations

from lib import cli, config, detect_filler, detect_silence, hashing, log, paths, plan_io
from lib.cut_context import Context
from lib.cut_merge import merge_overlaps
from lib.detect_retake import detect_tier1, detect_tier2


def main(args) -> dict:
    transcript, _ = plan_io.load_plan(paths.TRANSCRIPT)
    words = transcript["words"]
    ctx = Context(words=words, duration_sec=transcript["duration_sec"])
    cfg = config.cut_config()
    order = {w["id"]: i for i, w in enumerate(words)}

    items: list[dict] = []
    counter = 1

    silence_items = detect_silence.detect(ctx, cfg, start_index=counter)
    items += silence_items
    counter += len(silence_items)

    if args.full:
        tier1_items, consumed = detect_tier1(ctx, cfg, start_index=counter)
        items += tier1_items
        counter += len(tier1_items)

        tier2_items = detect_tier2(ctx, cfg, consumed, start_index=counter)
        items += tier2_items
        counter += len(tier2_items)

        filler_items = detect_filler.detect(ctx, cfg, consumed, start_index=counter)
        items += filler_items
        counter += len(filler_items)
    else:
        log.info("chạy sơ sài (--full để bật tầng 1/2 và từ đệm) — TDD §16 Tuần 1")

    items = merge_overlaps(items, order)

    if args.dry_run:
        return {"items": len(items), "dry_run": True}

    document = {
        "schema_version": 1,
        "version": 0,
        "input_hash": hashing.sha256_file(paths.TRANSCRIPT),
        "approved_at": None,
        "items": items,
    }
    version = _save(document)

    auto = sum(1 for i in items if i["decided_by"] == "auto" and i["status"] == "accepted")
    pending = sum(1 for i in items if i["status"] == "pending")
    log.info(f"phát hiện {len(items)} điểm cắt: {auto} tự động, {pending} chờ duyệt")
    return {"items": len(items), "auto": auto, "pending": pending, "version": version}


def _save(document: dict) -> int:
    if paths.CUT_PLAN.exists():
        _, current = plan_io.load_plan(paths.CUT_PLAN)
        return plan_io.save_plan(paths.CUT_PLAN, document, current, force=True)
    return plan_io.save_plan(paths.CUT_PLAN, document, 0)


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    parser.add_argument(
        "--full", action="store_true",
        help="bật đủ tầng 1/2 và từ đệm (mặc định chỉ khoảng lặng — TDD §16 Tuần 1)",
    )
    cli.run("02_detect_cuts", main, parser.parse_args())

"""Bước 1 — tách audio, gọi ElevenLabs Scribe, gán ID từ.

ffmpeg tách audio → POST Scribe (language=vi, timestamps=word) → thử lại tối đa
3 lần (backoff 2s/8s/32s) rồi DỪNG → lib.normalize chuẩn hoá TRƯỚC khi gán ID
→ plans/transcript.json

TDD: §5.2 · Lộ trình: Tuần 1
"""

from __future__ import annotations

import shutil
from pathlib import Path

from lib import anchor, cli, config, hashing, log, media, normalize, paths, plan_io, transcribe
from lib.errors import AIEditorError


def main(args) -> dict:
    keys = config.require_keys(["ELEVENLABS_API_KEY"])
    cfg = config.cut_config()

    source = Path(args.source).resolve()
    if not source.is_file():
        raise AIEditorError(
            f"Không tìm thấy file {source}",
            suggestion="Bỏ video vào source/ rồi chạy lại",
        )

    info = media.probe(source)
    _guard_duration(info["duration_sec"], cfg, confirmed=args.yes)

    if args.dry_run:
        return {"source": str(source), **info, "dry_run": True}

    # File gốc luôn nguyên vẹn: nhận từ đâu cũng chép vào source/ rồi mới làm việc
    kept = paths.SOURCE / "raw.mp4"
    if source != kept.resolve():
        paths.SOURCE.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, kept)
        log.info(f"đã chép nguồn vào {kept.relative_to(paths.ROOT)}")

    audio = media.extract_audio(kept, paths.WORK / "audio.m4a")
    log.info(f"đã tách audio {audio.stat().st_size / 1e6:.1f}MB, gửi ElevenLabs Scribe")

    raw_words = transcribe.transcribe(audio, keys["ELEVENLABS_API_KEY"])
    words, fixes = normalize.normalize_words(raw_words)
    words, next_id = anchor.assign_ids(words, next_id=1)

    document = {
        "schema_version": 1,
        "version": 0,
        "source_file": str(kept.relative_to(paths.ROOT)),
        "source_sha256": hashing.sha256_file(kept),
        "duration_sec": info["duration_sec"],
        "width": info["width"],
        "height": info["height"],
        "fps": info["fps"],
        "language": "vi",
        "next_id": next_id,
        "words": words,
    }
    version = _save(document)

    log.info(f"transcript: {len(words)} từ, next_id={next_id}, version={version}")
    return {
        "words": len(words),
        "next_id": next_id,
        "duration_sec": info["duration_sec"],
        "normalize_fixes": sum(fixes.values()),
        "version": version,
    }


def _guard_duration(duration_sec: float, cfg, *, confirmed: bool) -> None:
    """Video vượt phạm vi MVP → cảnh báo và hỏi, không âm thầm chạy rồi treo máy."""
    limit = cfg.limits.warn_and_confirm_above_sec
    if duration_sec <= limit:
        return
    if confirmed:
        log.warn(f"video dài {duration_sec:.0f}s, vượt ngưỡng {limit}s — chạy theo --yes")
        return
    raise AIEditorError(
        f"Video dài {duration_sec / 60:.1f} phút, vượt phạm vi MVP ({limit / 60:.0f} phút). "
        "Máy M1/8GB có thể không đủ RAM.",
        suggestion="Thêm --yes nếu anh vẫn muốn chạy",
    )


def _save(document: dict) -> int:
    """Ghi transcript mới. Đã có file cũ thì tôn trọng version đang có."""
    if paths.TRANSCRIPT.exists():
        _, current = plan_io.load_plan(paths.TRANSCRIPT)
        log.warn(
            "transcript.json đã tồn tại — ghi đè bằng bản mới, mọi ID cũ mất hiệu lực "
            "(sửa transcript mức 3, TDD §5.6)"
        )
        return plan_io.save_plan(paths.TRANSCRIPT, document, current)
    return plan_io.save_plan(paths.TRANSCRIPT, document, 0)


if __name__ == "__main__":
    parser = cli.base_parser(__doc__.splitlines()[0])
    parser.add_argument("source", help="đường dẫn video gốc")
    parser.add_argument("--yes", action="store_true", help="xác nhận chạy video dài quá ngưỡng")
    cli.run("01_transcript", main, parser.parse_args())

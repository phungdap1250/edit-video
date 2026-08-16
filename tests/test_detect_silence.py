"""Bậc khoảng lặng 600/300/400ms — TDD §5.2, PRD [CUT] bảng khoảng lặng."""

from __future__ import annotations

from lib import config
from lib.cut_context import Context
from lib.detect_silence import detect
from lib.timeline import BOF_ID, EOF_ID


def words(*specs) -> list[dict]:
    return [{"id": wid, "text": text, "start": s, "end": e} for wid, text, s, e in specs]


def cfg():
    return config.cut_config()


def test_khoang_lang_duoi_600ms_khong_bi_dong():
    src = words(("w0001", "a", 0.2, 1.0), ("w0002", "b", 1.4, 2.0))  # gap 400ms
    ctx = Context(words=src, duration_sec=2.0)
    items = [i for i in detect(ctx, cfg()) if i["anchor_start"] != BOF_ID and i["anchor_end"] != EOF_ID]
    assert items == []


def test_khoang_lang_600ms_den_1_5s_rut_con_300ms():
    src = words(("w0001", "a", 0.2, 1.0), ("w0002", "b", 1.8, 2.5))  # gap 800ms
    ctx = Context(words=src, duration_sec=2.5)
    items = detect(ctx, cfg())
    mid = next(i for i in items if i["anchor_start"] == "w0001")
    assert mid["keep_ms"] == 300
    assert mid["gap_original_ms"] == 800
    assert mid["status"] == "accepted"


def test_khoang_lang_tren_1_5s_rut_con_400ms():
    src = words(("w0001", "a", 0.2, 1.0), ("w0002", "b", 3.0, 3.5))  # gap 2000ms
    ctx = Context(words=src, duration_sec=3.5)
    items = detect(ctx, cfg())
    mid = next(i for i in items if i["anchor_start"] == "w0001")
    assert mid["keep_ms"] == 400


def test_dau_va_cuoi_video_rut_ve_200ms():
    src = words(("w0001", "a", 3.0, 3.5))  # 3s im lặng đầu, video dài 5s
    ctx = Context(words=src, duration_sec=5.0)
    items = detect(ctx, cfg())
    head = next(i for i in items if i["anchor_start"] == BOF_ID)
    tail = next(i for i in items if i["anchor_end"] == EOF_ID)
    assert head["keep_ms"] == 200
    assert tail["keep_ms"] == 200


def test_neo_vao_cap_tu_kep_khong_phai_1_tu():
    src = words(("w0001", "a", 0.0, 1.0), ("w0002", "b", 1.8, 2.5))
    ctx = Context(words=src, duration_sec=2.5)
    mid = next(i for i in detect(ctx, cfg()) if i["kind"] == "silence" and i["anchor_start"] == "w0001")
    assert mid["anchor_start"] == "w0001" and mid["anchor_end"] == "w0002"
    assert "→" in mid["anchor_text"]

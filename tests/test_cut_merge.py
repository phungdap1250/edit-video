"""Bước 2.5 — gộp chồng lấn, absorbed_by. TDD §5.2."""

from __future__ import annotations

import pytest

from lib.cut_merge import merge_overlaps
from lib.errors import AIEditorError

ORDER = {f"w{n:04d}": n for n in range(20)}


def cut(item_id: str, kind: str, start: int, end: int) -> dict:
    return {
        "id": item_id, "kind": kind,
        "anchor_start": f"w{start:04d}", "anchor_end": f"w{end:04d}",
        "absorbed_by": None,
    }


def test_cut_nam_tron_trong_cut_khac_bi_nuot():
    parent = cut("cut_015", "retake", 2, 8)
    child = cut("cut_014", "filler", 4, 4)
    merge_overlaps([parent, child], ORDER)
    assert child["absorbed_by"] == "cut_015"
    assert parent["absorbed_by"] is None


def test_silence_khong_tham_gia_gop():
    parent = cut("cut_015", "retake", 2, 8)
    silence = cut("cut_016", "silence", 4, 5)
    merge_overlaps([parent, silence], ORDER)
    assert silence["absorbed_by"] is None


def test_khong_giao_nhau_thi_khong_bi_gan():
    a = cut("cut_001", "filler", 0, 1)
    b = cut("cut_002", "filler", 5, 5)
    merge_overlaps([a, b], ORDER)
    assert a["absorbed_by"] is None
    assert b["absorbed_by"] is None


def test_chong_lan_mot_phan_bi_tu_choi():
    a = cut("cut_001", "retake", 0, 5)
    b = cut("cut_002", "retake", 3, 8)
    with pytest.raises(AIEditorError):
        merge_overlaps([a, b], ORDER)


def test_span_trung_het_khong_nuot_nhau():
    a = cut("cut_001", "filler", 4, 4)
    b = cut("cut_002", "filler", 4, 4)
    merge_overlaps([a, b], ORDER)
    assert a["absorbed_by"] is None
    assert b["absorbed_by"] is None

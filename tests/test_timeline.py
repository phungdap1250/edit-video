"""removal_intervals, kept_segments, Shifter — TDD §5.2 bước 3."""

from __future__ import annotations

from lib import timeline as tl


def words(*specs) -> list[dict]:
    return [{"id": wid, "text": text, "start": s, "end": e} for wid, text, s, e in specs]


def test_removal_intervals_bo_qua_cut_chua_duyet():
    src = words(("w0001", "a", 0.0, 1.0), ("w0002", "thì", 1.0, 1.2), ("w0003", "b", 1.2, 2.0))
    cuts = [{"id": "cut_001", "kind": "filler", "status": "pending",
             "anchor_start": "w0002", "anchor_end": "w0002"}]
    assert tl.removal_intervals(src, cuts, 2.0, padding_sec=0) == []


def test_removal_intervals_bo_qua_cut_bi_nuot():
    src = words(("w0001", "a", 0.0, 1.0), ("w0002", "thì", 1.0, 1.2), ("w0003", "b", 1.2, 2.0))
    cuts = [{"id": "cut_001", "kind": "filler", "status": "accepted", "absorbed_by": "cut_002",
             "anchor_start": "w0002", "anchor_end": "w0002"}]
    assert tl.removal_intervals(src, cuts, 2.0, padding_sec=0) == []


def test_removal_intervals_chua_padding_hai_dau():
    """Từ "thì" dài 0.2s, đệm 0.1s mỗi đầu ăn hết khe → không còn gì để xoá."""
    src = words(("w0001", "a", 0.0, 1.0), ("w0002", "thì", 1.0, 1.2), ("w0003", "b", 1.2, 2.0))
    cuts = [{"id": "cut_001", "kind": "filler", "status": "accepted",
             "anchor_start": "w0002", "anchor_end": "w0002"}]
    assert tl.removal_intervals(src, cuts, 2.0, padding_sec=0.1) == []


def test_removal_intervals_du_dai_de_padding_khong_nuot_het():
    src = words(("w0001", "a", 0.0, 1.0), ("w0002", "thì đúng không", 1.0, 2.0),
                ("w0003", "b", 2.0, 3.0))
    cuts = [{"id": "cut_001", "kind": "filler", "status": "accepted",
             "anchor_start": "w0002", "anchor_end": "w0002"}]
    lo, hi = tl.removal_intervals(src, cuts, 3.0, padding_sec=0.1)[0]
    assert (lo, hi) == (1.1, 1.9)


def test_removal_intervals_silence_giu_keep_ms():
    src = words(("w0001", "a", 0.0, 1.0), ("w0002", "b", 3.0, 4.0))
    cuts = [{"id": "cut_001", "kind": "silence", "status": "accepted",
             "anchor_start": "w0001", "anchor_end": "w0002", "keep_ms": 400}]
    lo, hi = tl.removal_intervals(src, cuts, 4.0)[0]
    assert round(hi - lo, 3) == round(2.0 - 0.4, 3)  # xoá đúng phần vượt keep_ms


def test_merge_gop_khoang_chong_lan():
    assert tl.merge([(0, 2), (1, 3), (5, 6)]) == [(0, 3), (5, 6)]


def test_kept_segments_la_phan_bu():
    assert tl.kept_segments([(1.0, 2.0)], 5.0) == [(0.0, 1.0), (2.0, 5.0)]


def test_shifter_dich_dung_sau_mot_khoang_xoa():
    shifter = tl.Shifter([(1.0, 1.4)])
    assert shifter.shift(0.5) == 0.5
    assert shifter.shift(1.4) == 1.0
    assert shifter.shift(2.0) == 1.6


def test_shifter_is_removed_qua_nua_thoi_luong():
    shifter = tl.Shifter([(1.0, 1.4)])
    assert shifter.is_removed(1.0, 1.4) is True  # trọn trong vùng xoá
    assert shifter.is_removed(0.5, 1.1) is False  # phần lớn còn nằm ngoài


def test_build_timeline_map_co_neo_bien():
    src = words(("w0001", "a", 0.0, 1.0))
    result = tl.build_timeline_map(src, [], 1.0, padding_sec=0)
    assert result[tl.BOF_ID] == (0.0, 0.0)
    assert result[tl.EOF_ID][0] > 0

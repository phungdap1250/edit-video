"""Ca chính của QĐ 4 — cấp ID, kế thừa ID, build_timeline_map. TDD §12.3."""

from __future__ import annotations

from lib import anchor


def words(*specs) -> list[dict]:
    return [
        {"id": wid, "text": text, "start": start, "end": end}
        for wid, text, start, end in specs
    ]


def test_assign_ids_chi_tang_khong_tai_su_dung():
    result, next_id = anchor.assign_ids(
        [{"text": "a", "start": 0, "end": 1}, {"text": "b", "start": 1, "end": 2}], 5
    )
    assert [w["id"] for w in result] == ["w0005", "w0006"]
    assert next_id == 7


def test_inherit_ids_giu_id_cu_khi_sua_chinh_ta():
    old = words(("w0001", "quy", 1.0, 1.2), ("w0002", "phiếu", 1.2, 1.5), ("w0003", "này", 1.5, 1.7))
    new = [
        {"text": "quy", "start": 1.0, "end": 1.2},
        {"text": "phễu", "start": 1.2, "end": 1.5},
        {"text": "này", "start": 1.5, "end": 1.7},
    ]
    result, next_id, lost = anchor.inherit_ids(old, new, next_id=4)
    assert [w["id"] for w in result] == ["w0001", "w0004", "w0003"]
    assert lost == ["w0002"]
    assert next_id == 5


def test_inherit_ids_khong_ke_thua_khi_lech_qua_2s():
    """Thà cấp ID mới (hỏng ồn ào) còn hơn neo nhầm từ (hỏng im lặng)."""
    old = words(("w0001", "bước", 10.0, 10.3))
    new = [{"text": "bước", "start": 40.0, "end": 40.3}]
    result, _, lost = anchor.inherit_ids(old, new, next_id=2)
    assert result[0]["id"] == "w0002"
    assert lost == ["w0001"]


def test_build_timeline_map_dong_khoang_lang():
    src = words(("w0001", "a", 0.0, 1.0), ("w0002", "b", 3.0, 4.0))
    timeline = anchor.build_timeline_map(src, [], padding_ms=0)
    assert timeline["w0001"] == (0.0, 1.0)
    assert timeline["w0002"] == (3.0, 4.0)  # chưa cắt thì khoảng lặng giữ nguyên


def test_build_timeline_map_loai_tu_bi_cat():
    src = words(("w0001", "a", 0.0, 1.0), ("w0002", "ờ", 1.0, 1.4), ("w0003", "b", 1.4, 2.0))
    cuts = [{"id": "cut_001", "kind": "filler", "status": "accepted",
             "anchor_start": "w0002", "anchor_end": "w0002"}]
    timeline = anchor.build_timeline_map(src, cuts, padding_ms=0)
    assert "w0002" not in timeline
    assert timeline["w0003"][0] < 1.4  # timeline dồn lại sau khi cắt


def test_cut_bi_reject_khong_lam_mat_tu():
    src = words(("w0001", "a", 0.0, 1.0), ("w0002", "thì", 1.0, 1.2))
    cuts = [{"id": "cut_001", "kind": "filler", "status": "rejected",
             "anchor_start": "w0002", "anchor_end": "w0002"}]
    assert "w0002" in anchor.build_timeline_map(src, cuts)

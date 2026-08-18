"""Từ chối đúng, thông báo lỗi tiếng Việt — TDD §12.3, §7.4."""

from __future__ import annotations

import pytest

from lib import validate_plan
from lib.errors import AIEditorError

VALID = {
    "id": "ov_007", "type": "con_so_nhay", "anchor_start": "w0412", "anchor_end": "w0429",
    "anchor_text": "quy trình này có ba bước", "content": {"number": "3"}, "status": "pending",
}


def test_muc_hop_le_khong_bao_loi():
    assert validate_plan.validate("overlay", [VALID]) == []


def test_bat_thieu_truong_bat_buoc():
    errors = validate_plan.validate("overlay", [{**VALID, "anchor_text": None}])
    assert any("anchor_text" in e for e in errors)


def test_bat_enum_sai():
    errors = validate_plan.validate("overlay", [{**VALID, "type": "lower_third"}])
    assert any("lower_third" in e for e in errors)


def test_bat_id_trung():
    errors = validate_plan.validate("overlay", [VALID, VALID])
    assert any("trùng" in e for e in errors)


def test_bat_tier_ngoai_khoang():
    cut = {"id": "cut_014", "kind": "filler", "anchor_start": "w1", "anchor_end": "w1",
           "anchor_text": "thì", "status": "pending", "tier": 7}
    assert any("tier" in e for e in validate_plan.validate("cut", [cut]))


def test_bat_qua_3_tu_nhan_manh():
    line = {"id": "cap_031", "word_ids": ["w1"], "text": "x",
            "emphasis_word_ids": ["w1", "w2", "w3", "w4"]}
    assert any("3 từ nhấn mạnh" in e for e in validate_plan.validate("caption", [line]))


def test_raise_if_invalid_giu_file_cu_nguyen_ven():
    with pytest.raises(AIEditorError) as exc:
        validate_plan.raise_if_invalid("overlay", [{**VALID, "type": "sai"}])
    assert "File cũ nguyên vẹn" in exc.value.message


def test_cutaway_hop_le_khong_bao_loi():
    item = {"id": "cta_001", "anchor_start": "w1", "anchor_end": "w2", "status": "pending"}
    assert validate_plan.validate("cutaway", [item]) == []


def test_cutaway_khong_bat_buoc_image_source():
    """Claude chỉ chọn đoạn + soạn prompt (TDD §7.1 việc #4) — image_source do
    steps/06 gán sau, không thể có ở thời điểm Claude ghi."""
    item = {"id": "cta_001", "anchor_start": "w1", "anchor_end": "w2", "status": "pending"}
    assert not any("image_source" in e for e in validate_plan.validate("cutaway", [item]))


def _cfg(**overrides):
    from lib.config import Section

    base = {
        "budget": {
            "gemini_api_calls_per_video": 10,
            "gemini_api_calls_per_month": 120,
            "gemini_regen_per_item": 3,
        },
        "cutaway": {"max_face_cover_sec": 8.0},
    }
    base.update(overrides)
    return Section(base)


def test_cutaway_vuot_tran_regen_moi_muc():
    item = {"id": "cta_001", "anchor_start": "w1", "anchor_end": "w2", "status": "pending",
            "image_source": "ai_generated", "regen_count": 4, "t_dur": 2.0}
    errors = validate_plan.validate("cutaway", [item], {"cfg": _cfg()})
    assert any("sinh lại" in e for e in errors)


def test_cutaway_vuot_tran_video():
    items = [
        {"id": f"cta_{i:03d}", "anchor_start": "w1", "anchor_end": "w2", "status": "pending",
         "image_source": "ai_generated", "regen_count": 0, "t_dur": 1.0}
        for i in range(11)
    ]
    errors = validate_plan.validate("cutaway", items, {"cfg": _cfg()})
    assert any("lượt gọi Gemini/video" in e for e in errors)


def test_cutaway_vuot_tran_thang():
    item = {"id": "cta_001", "anchor_start": "w1", "anchor_end": "w2", "status": "pending",
            "image_source": "ai_generated", "regen_count": 0, "t_dur": 1.0}
    errors = validate_plan.validate("cutaway", [item], {"cfg": _cfg(), "month_used": 200})
    assert any("lượt gọi Gemini/tháng" in e for e in errors)


def test_cutaway_che_mat_qua_8s():
    item = {"id": "cta_001", "anchor_start": "w1", "anchor_end": "w2", "status": "pending",
            "image_source": "ai_generated", "regen_count": 0, "t_dur": 9.0}
    errors = validate_plan.validate("cutaway", [item], {"cfg": _cfg()})
    assert any("che mặt" in e for e in errors)


def test_cutaway_muc_pending_chua_sinh_khong_tinh_han_muc():
    """Mục Claude vừa soạn prompt (chưa image_source=ai_generated) không tiêu hạn mức."""
    item = {"id": "cta_001", "anchor_start": "w1", "anchor_end": "w2", "status": "pending", "t_dur": 20.0}
    assert validate_plan.validate("cutaway", [item], {"cfg": _cfg()}) == []

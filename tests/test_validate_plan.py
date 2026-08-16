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

"""lib.budget — trần per-video và per-month, một bộ đếm duy nhất — TDD §9.4."""

from __future__ import annotations

import pytest

from lib import budget, paths
from lib.config import Section
from lib.errors import AIEditorError

CFG = Section({
    "budget": {
        "gemini_api_calls_per_video": 2,
        "gemini_api_calls_per_month": 3,
        "gemini_regen_per_item": 1,
        "gemini_cost_vnd_per_call": 780,
        "monthly_budget_vnd": 100000,
    }
})


@pytest.fixture(autouse=True)
def isolated_month_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "MONTHLY_BUDGET_DIR", tmp_path / ".ai-editor")


def test_check_regen_limit_vuot_tran_thi_loi():
    with pytest.raises(AIEditorError):
        budget.check_regen_limit({"id": "cta_001", "regen_count": 1}, CFG)


def test_check_regen_limit_con_luot_thi_qua():
    budget.check_regen_limit({"id": "cta_001", "regen_count": 0}, CFG)


def test_check_global_caps_vuot_tran_video():
    plan = {"budget": {"api_calls_used": 2}}
    with pytest.raises(AIEditorError):
        budget.check_global_caps(plan, CFG)


def test_check_global_caps_vuot_tran_thang():
    budget.record_month_call()
    budget.record_month_call()
    budget.record_month_call()
    with pytest.raises(AIEditorError):
        budget.check_global_caps({"budget": {"api_calls_used": 0}}, CFG)


def test_record_month_call_cong_don():
    assert budget.record_month_call() == 1
    assert budget.record_month_call() == 2
    assert budget.month_used() == 2


def test_snapshot_tra_ca_hai_muc():
    plan = {"budget": {"api_calls_used": 1}}
    budget.record_month_call()
    result = budget.snapshot(plan, CFG)
    assert result == {
        "api_calls_used": 1,
        "api_calls_limit": 2,
        "month_used": 1,
        "month_limit": 3,
        "est_cost_vnd": 780,
    }

"""Ghi nguyên tử, xung đột version, draft → promote. TDD §12.3, §3.6, §4.2."""

from __future__ import annotations

import json

import pytest

from lib import paths, plan_io
from lib.errors import PlanConflict


@pytest.fixture
def overlay(tmp_path, monkeypatch):
    """Chuyển tầng dữ liệu sang tmp để không đụng plans/ thật."""
    path = tmp_path / "overlay_plan.json"
    monkeypatch.setattr(paths, "DRAFT", tmp_path / ".draft")
    monkeypatch.setattr(paths, "PLAN_BY_KIND", {**paths.PLAN_BY_KIND, "overlay": path})
    plan = {
        "schema_version": 1,
        "version": 5,
        "items": [
            {"id": "ov_007", "type": "con_so_nhay", "content": {"number": "3"}, "status": "pending"},
            {"id": "ov_012", "type": "pill_tu_khoa", "content": {"text": "phễu"}, "status": "pending"},
        ],
    }
    path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    return path


def read(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_save_plan_tang_version_va_ghi_nguyen_tu(overlay):
    data, version = plan_io.load_plan(overlay)
    new_version = plan_io.save_plan(overlay, data, version)
    assert new_version == 6
    assert read(overlay)["version"] == 6
    assert not list(overlay.parent.glob("*.tmp"))


def test_save_plan_lech_version_thi_raise(overlay):
    data, version = plan_io.load_plan(overlay)
    plan_io.save_plan(overlay, data, version)
    with pytest.raises(PlanConflict):
        plan_io.save_plan(overlay, data, version)


def test_promote_chi_ghi_truong_trong_whitelist(overlay):
    plan, _ = plan_io.load_plan(overlay)
    plan_io.snapshot_base("overlay", plan)
    # `type` không nằm trong whitelist của /storyboard → phải bị bỏ qua
    plan_io.promote_draft(
        "overlay",
        [{"id": "ov_007", "status": "approved", "type": "pill_tu_khoa"}],
        expected_version=5,
    )
    item = read(overlay)["items"][0]
    assert item["status"] == "approved"
    assert item["type"] == "con_so_nhay"


def test_promote_partial_khong_xoa_muc_ngoai_scope(overlay):
    """Ca bắt buộc của TDD §4.2."""
    plan, _ = plan_io.load_plan(overlay)
    plan_io.snapshot_base("overlay", plan)
    plan_io.promote_draft(
        "overlay",
        [{"id": "ov_007", "status": "approved"}],
        expected_version=5,
        partial=True,
        scope=["ov_007"],
    )
    items = {i["id"]: i for i in read(overlay)["items"]}
    assert set(items) == {"ov_007", "ov_012"}
    assert items["ov_012"]["status"] == "pending"


def test_xung_dot_o_cap_truong_van_luu_cac_muc_con_lai(overlay):
    """Anh duyệt `status`, Claude sửa `content` cùng lúc → cả hai cùng sống."""
    plan, _ = plan_io.load_plan(overlay)
    plan_io.snapshot_base("overlay", plan)

    plan["items"][1]["content"] = {"text": "phễu marketing"}  # Claude ghi ở giữa
    plan_io.save_plan(overlay, plan, 5)

    _, conflicts, _ = plan_io.promote_draft(
        "overlay",
        [
            {"id": "ov_007", "status": "approved"},
            {"id": "ov_012", "status": "approved"},
        ],
        expected_version=5,
    )
    items = {i["id"]: i for i in read(overlay)["items"]}
    assert conflicts == []
    assert items["ov_007"]["status"] == "approved"
    assert items["ov_012"]["content"] == {"text": "phễu marketing"}  # giữ bản Claude


def test_xung_dot_that_su_thi_bao_cao_dung_muc(overlay):
    plan, _ = plan_io.load_plan(overlay)
    plan_io.snapshot_base("overlay", plan)

    plan["items"][1]["content"] = {"text": "phễu marketing"}
    plan_io.save_plan(overlay, plan, 5)

    _, conflicts, _ = plan_io.promote_draft(
        "overlay", [{"id": "ov_012", "content": {"text": "phễu bán hàng"}}], expected_version=5
    )
    assert [c["id"] for c in conflicts] == ["ov_012"]
    assert read(overlay)["items"][1]["content"] == {"text": "phễu marketing"}


def test_draft_khong_dung_file_that(overlay):
    plan_io.save_draft("overlay", {"items": [{"id": "ov_007", "status": "rejected"}]})
    assert read(overlay)["version"] == 5
    assert plan_io.load_draft("overlay")["items"][0]["status"] == "rejected"

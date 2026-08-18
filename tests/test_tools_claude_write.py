"""Tích hợp tools/claude_write.py — cửa DUY NHẤT Claude ghi plans/*_plan.json — TDD §7.4."""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import pytest

from lib import paths

_REAL_ROOT = paths.ROOT


def _load():
    spec = importlib.util.spec_from_file_location(
        "tools_claude_write", str(_REAL_ROOT / "tools" / "claude_write.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    (tmp_path / "plans").mkdir()
    monkeypatch.setattr(paths, "PLANS", tmp_path / "plans")
    monkeypatch.setattr(paths, "TRANSCRIPT", tmp_path / "plans" / "transcript.json")
    monkeypatch.setattr(paths, "CUTAWAY_PLAN", tmp_path / "plans" / "cutaway_plan.json")
    monkeypatch.setattr(paths, "CAPTION_PLAN", tmp_path / "plans" / "caption_plan.json")
    monkeypatch.setattr(paths, "PLAN_BY_KIND", {
        "cut": tmp_path / "plans" / "cut_plan.json",
        "cutaway": tmp_path / "plans" / "cutaway_plan.json",
        "overlay": tmp_path / "plans" / "overlay_plan.json",
        "caption": tmp_path / "plans" / "caption_plan.json",
    })
    words = [{"id": "w0001", "text": "a", "start": 0.0, "end": 0.5},
             {"id": "w0002", "text": "b", "start": 0.5, "end": 1.0}]
    (tmp_path / "plans" / "transcript.json").write_text(
        json.dumps({"version": 1, "duration_sec": 1.0, "words": words}), encoding="utf-8"
    )
    return tmp_path


def _items_file(tmp_path: Path, items: list[dict]) -> str:
    path = tmp_path / "items.json"
    path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return str(path)


def test_tao_moi_cutaway_plan_chua_ton_tai(isolated):
    module = _load()
    items = [{"id": "cta_001", "anchor_start": "w0001", "anchor_end": "w0002", "status": "pending"}]
    result = module.main(Namespace(
        kind="cutaway", items=_items_file(isolated, items), dry_run=False, json=False, verbose=False
    ))
    assert result["written"] == 1
    saved = json.loads(paths.CUTAWAY_PLAN.read_text(encoding="utf-8"))
    assert saved["items"][0]["id"] == "cta_001"


def test_upsert_giu_nguyen_muc_khac_id(isolated):
    module = _load()
    paths.CUTAWAY_PLAN.write_text(json.dumps({
        "version": 1,
        "items": [{"id": "cta_old", "anchor_start": "w0001", "anchor_end": "w0002",
                   "status": "accepted", "image_source": "user_asset"}],
    }), encoding="utf-8")

    items = [{"id": "cta_new", "anchor_start": "w0001", "anchor_end": "w0002", "status": "pending"}]
    result = module.main(Namespace(
        kind="cutaway", items=_items_file(isolated, items), dry_run=False, json=False, verbose=False
    ))

    assert result["total"] == 2
    saved_ids = {i["id"] for i in json.loads(paths.CUTAWAY_PLAN.read_text(encoding="utf-8"))["items"]}
    assert saved_ids == {"cta_old", "cta_new"}


def test_anchor_khong_ton_tai_thi_tu_choi_ghi(isolated):
    from lib.errors import AIEditorError

    module = _load()
    items = [{"id": "cta_001", "anchor_start": "w9999", "anchor_end": "w9999", "status": "pending"}]
    with pytest.raises(AIEditorError):
        module.main(Namespace(
            kind="cutaway", items=_items_file(isolated, items), dry_run=False, json=False, verbose=False
        ))
    assert not paths.CUTAWAY_PLAN.exists()


def test_dry_run_khong_ghi_gi(isolated):
    module = _load()
    items = [{"id": "cta_001", "anchor_start": "w0001", "anchor_end": "w0002", "status": "pending"}]
    result = module.main(Namespace(
        kind="cutaway", items=_items_file(isolated, items), dry_run=True, json=False, verbose=False
    ))
    assert result["dry_run"] is True
    assert not paths.CUTAWAY_PLAN.exists()


def test_caption_upsert_gan_emphasis_giu_nguyen_truong_khac(isolated):
    """TDD §7.1 việc #2: Claude chỉ thêm emphasis_word_ids[] vào dòng steps/04 đã gom sẵn."""
    module = _load()
    paths.CAPTION_PLAN.write_text(json.dumps({
        "version": 1, "mode": "karaoke_word",
        "lines": [{"id": "cap_000", "word_ids": ["w0001", "w0002"], "text": "a b",
                   "emphasis_word_ids": [], "t_start": 0.0, "t_end": 1.0}],
    }), encoding="utf-8")
    module_items = [{"id": "cap_000", "word_ids": ["w0001", "w0002"], "text": "a b",
                      "emphasis_word_ids": ["w0002"], "t_start": 0.0, "t_end": 1.0}]

    result = module.main(Namespace(
        kind="caption", items=_items_file(isolated, module_items), dry_run=False, json=False, verbose=False
    ))
    assert result["written"] == 1
    saved = json.loads(paths.CAPTION_PLAN.read_text(encoding="utf-8"))
    assert saved["lines"][0]["emphasis_word_ids"] == ["w0002"]
    assert "approved_at" not in saved  # caption_plan.json không có bước duyệt


def test_caption_qua_3_tu_nhan_manh_thi_tu_choi(isolated):
    from lib.errors import AIEditorError

    module = _load()
    items = [{"id": "cap_000", "word_ids": ["w1"], "text": "x",
              "emphasis_word_ids": ["w1", "w2", "w3", "w4"]}]
    with pytest.raises(AIEditorError):
        module.main(Namespace(
            kind="caption", items=_items_file(isolated, items), dry_run=False, json=False, verbose=False
        ))

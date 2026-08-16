"""Tích hợp steps/02_detect_cuts.py — ráp 4 cơ chế + bước 2.5. TDD §5.2.

Test riêng từng detector (test_detect_*.py) không bắt được lỗi ráp nối: ID
trùng giữa các cơ chế, `consumed` không truyền đúng, `order` sai khi gọi
merge_overlaps. File này chạy đúng đường main() thật, chỉ đổi PLANS/TRANSCRIPT
sang tmp_path.
"""

from __future__ import annotations

import argparse
import json

import pytest

from lib import paths


def make_transcript(tmp_path, words: list[dict], duration_sec: float) -> None:
    plans_dir = tmp_path / "plans"
    plans_dir.mkdir()
    payload = {
        "schema_version": 1, "version": 1, "duration_sec": duration_sec,
        "words": words,
    }
    (plans_dir / "transcript.json").write_text(json.dumps(payload, ensure_ascii=False))


@pytest.fixture
def isolated_plans(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "PLANS", tmp_path / "plans")
    monkeypatch.setattr(paths, "TRANSCRIPT", tmp_path / "plans" / "transcript.json")
    monkeypatch.setattr(paths, "CUT_PLAN", tmp_path / "plans" / "cut_plan.json")
    return tmp_path


def w(wid, text, start, end):
    return {"id": wid, "text": text, "start": start, "end": end}


def _load_step_02():
    """steps/02_detect_cuts.py tên bắt đầu bằng số — không import được qua
    `import steps.02_detect_cuts`, phải nạp trực tiếp bằng đường dẫn file."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "step_02_detect_cuts", str(paths.ROOT / "steps" / "02_detect_cuts.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ca_4_co_che_cung_chay_khong_trung_id(isolated_plans):
    """Transcript tổng hợp có đủ: khoảng lặng dài, "cắt cắt", từ đệm nhóm A."""
    step = _load_step_02()

    make_transcript(
        isolated_plans,
        [
            w("w0001", "chào", 0.0, 0.3), w("w0002", "cả", 0.3, 0.6), w("w0003", "nhà.", 0.6, 1.0),
            w("w0004", "hôm", 3.0, 3.3), w("w0005", "nay", 3.3, 3.6),  # khoảng lặng 2.4s trước
            # "thì" không phải từ đầu/cuối video — nếu là từ cuối, luật §5.2
            # "không cắt từ đệm ở đầu/cuối câu" sẽ chặn nó, đúng thiết kế
            w("w0006", "thì", 4.0, 4.2),  # lặng 400ms trước, 300ms sau — đủ ngưỡng nhóm A
            w("w0007", "làm", 4.5, 4.8),
        ],
        duration_sec=4.8,
    )

    args = argparse.Namespace(full=True, dry_run=False, json=False, verbose=False)
    result = step.main(args)

    assert result["items"] >= 1
    saved = json.loads((isolated_plans / "plans" / "cut_plan.json").read_text())
    ids = [it["id"] for it in saved["items"]]
    assert len(ids) == len(set(ids))  # không ID nào trùng giữa các cơ chế
    kinds = {it["kind"] for it in saved["items"]}
    assert "silence" in kinds and "filler" in kinds


def test_khong_co_gi_de_cat_van_ghi_file_rong(isolated_plans):
    step = _load_step_02()

    make_transcript(
        isolated_plans, [w("w0001", "a", 0.0, 0.3), w("w0002", "b", 0.3, 0.6)], duration_sec=0.6
    )
    args = argparse.Namespace(full=True, dry_run=False, json=False, verbose=False)
    result = step.main(args)
    assert result["items"] == 0


def test_dry_run_khong_ghi_file(isolated_plans):
    step = _load_step_02()

    make_transcript(
        isolated_plans, [w("w0001", "a", 0.0, 0.3), w("w0002", "b", 3.0, 3.3)], duration_sec=3.3
    )
    args = argparse.Namespace(full=True, dry_run=True, json=False, verbose=False)
    step.main(args)
    assert not (isolated_plans / "plans" / "cut_plan.json").exists()

"""Tính ổn định của băm — TDD §12.3, §6.3."""

from __future__ import annotations

import pytest

from lib import hashing

CTX = {"source_sha256": "a3f9", "renderer_version": 1, "ffmpeg_version": "6.0"}


def test_thu_tu_key_khong_anh_huong_hash():
    a = {"segments": [["w0001", "w0010", 3.5]], "zoom": [[0, 1.06]]}
    b = {"zoom": [[0, 1.06]], "segments": [["w0001", "w0010", 3.5]]}
    assert hashing.block_hash(a, CTX) == hashing.block_hash(b, CTX)


def test_cung_dau_vao_cung_hash():
    block = {"segments": [["w0001", "w0010", 3.5]]}
    assert hashing.block_hash(block, CTX) == hashing.block_hash(block, CTX)


def test_doi_noi_dung_thi_doi_hash():
    base = {"segments": [["w0001", "w0010", 3.5]]}
    other = {"segments": [["w0001", "w0010", 3.6]]}
    assert hashing.block_hash(base, CTX) != hashing.block_hash(other, CTX)


def test_doi_renderer_version_thi_doi_hash():
    block = {"segments": [["w0001", "w0010", 3.5]]}
    assert hashing.block_hash(block, CTX) != hashing.block_hash(block, {**CTX, "renderer_version": 2})


def test_tu_choi_thoi_diem_tuyet_doi_trong_hash():
    """t_in/t_out tuyệt đối và sha256(cut.mp4) đã bị gỡ khỏi hash ở v1.1."""
    with pytest.raises(ValueError):
        hashing.block_hash({"segments": [], "t_in": 42.0}, CTX)
    with pytest.raises(ValueError):
        hashing.block_hash({"segments": [], "cut_mp4_sha256": "deadbeef"}, CTX)


def test_do_dai_hash_dung_8_ky_tu():
    assert len(hashing.block_hash({"segments": []}, CTX)) == hashing.HASH_LEN


def test_canonical_json_giu_dau_tieng_viet():
    assert "phễu" in hashing.canonical_json({"text": "phễu"})

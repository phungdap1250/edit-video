"""Hợp đồng thi hành được giữa Claude và pipeline — TDD §7.4.

Claude có thể sai, nhưng nó KHÔNG THỂ ghi một file sai vào đĩa. Sai schema →
từ chối ghi toàn bộ, file cũ nguyên vẹn, in lỗi tiếng Việt đủ cụ thể để tự sửa.
"""

from __future__ import annotations

from typing import Any

from lib.errors import AIEditorError

SCHEMAS: dict[str, dict[str, Any]] = {
    "cut": {
        "required": ["id", "kind", "anchor_start", "anchor_end", "anchor_text", "status"],
        "enums": {
            "kind": ["silence", "filler", "retake"],
            "status": ["pending", "accepted", "rejected"],
            "group": ["A", "B", None],
        },
        "ranges": {"tier": (0, 3), "confidence": (0.0, 1.0)},
        "custom": ["moi_anchor_phai_ton_tai_trong_transcript"],
    },
    "overlay": {
        "required": [
            "id", "type", "anchor_start", "anchor_end", "anchor_text", "content", "status"
        ],
        "enums": {
            "type": ["con_so_nhay", "danh_sach_bung_dan", "card_khai_niem", "pill_tu_khoa"],
            "status": ["pending", "approved", "rejected"],
        },
        "custom": [
            "moi_anchor_phai_ton_tai_trong_transcript",
            "khong_ghi_de_duong_dan_trong_edited_fields",
            "khong_qua_1_do_hoa_cung_luc",
            "cach_nhau_toi_thieu_500ms",
        ],
    },
    "cutaway": {
        "required": ["id", "anchor_start", "anchor_end", "image_source", "status"],
        "enums": {"image_source": ["user_asset", "ai_generated", "missing"]},
        "custom": [
            "khong_vuot_tran_api_calls_video",
            "khong_vuot_tran_api_calls_thang",
            "khong_vuot_3_lan_sinh_lai",
            "khong_che_mat_qua_8_giay",
        ],
    },
    "caption": {
        "required": ["id", "word_ids", "text"],
        "enums": {},
        "custom": ["toi_da_3_emphasis_moi_dong", "toi_da_42_ky_tu_moi_dong_ngang"],
    },
}


def validate(kind: str, items: list[dict], ctx: dict | None = None) -> list[str]:
    """Trả danh sách lỗi tiếng Việt. Rỗng = hợp lệ.

    ctx chứa transcript/timeline/budget để chạy các luật `custom` — các luật đó
    triển khai ở tuần 2–3 (TDD §16), phần schema tĩnh dưới đây chạy được ngay.
    """
    if kind not in SCHEMAS:
        raise AIEditorError(f"Loại plan không hợp lệ: {kind}")

    schema = SCHEMAS[kind]
    errors: list[str] = []
    seen: set[str] = set()

    for index, item in enumerate(items):
        label = item.get("id") or f"mục #{index}"

        for name in schema["required"]:
            if item.get(name) in (None, ""):
                errors.append(f"{label}: thiếu trường bắt buộc '{name}'")

        if label in seen:
            errors.append(f"{label}: ID trùng với mục trước")
        seen.add(label)

        for name, allowed in schema["enums"].items():
            if name in item and item[name] not in allowed:
                errors.append(
                    f"{label}: '{name}' = {item[name]!r} không hợp lệ "
                    f"(chỉ nhận {allowed})"
                )

        for name, (low, high) in schema.get("ranges", {}).items():
            if name in item and item[name] is not None and not low <= item[name] <= high:
                errors.append(f"{label}: '{name}' = {item[name]} ngoài khoảng [{low}, {high}]")

    if kind == "caption":
        for item in items:
            if len(item.get("emphasis_word_ids", [])) > 3:
                errors.append(f"{item.get('id')}: quá 3 từ nhấn mạnh trong 1 dòng")

    return errors


def raise_if_invalid(kind: str, items: list[dict], ctx: dict | None = None) -> None:
    errors = validate(kind, items, ctx)
    if not errors:
        return
    body = "\n  ".join(errors)
    raise AIEditorError(
        f"Từ chối ghi {kind}_plan.json — {len(errors)} lỗi\n\n  {body}\n\n"
        "  Không có gì được ghi. File cũ nguyên vẹn.",
        suggestion="Sửa các mục trên rồi chạy lại tools.claude_write",
    )

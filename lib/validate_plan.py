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
        # image_source KHÔNG bắt buộc lúc Claude ghi: Claude chỉ chọn đoạn + soạn
        # prompt (TDD §7.1 việc #4) — image_source do steps/06 gán sau khi khớp
        # assets/ hoặc gọi Gemini, Claude không biết trước giá trị này.
        "required": ["id", "anchor_start", "anchor_end", "status"],
        "enums": {"image_source": ["user_asset", "ai_generated", "missing", None]},
        "custom": [
            "moi_anchor_phai_ton_tai_trong_transcript",
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

    ctx = ctx or {}
    if "moi_anchor_phai_ton_tai_trong_transcript" in schema.get("custom", []):
        errors += _check_anchors_exist(items, ctx)
    if kind == "cutaway":
        errors += _check_cutaway_budget(items, ctx)

    return errors


def _check_anchors_exist(items: list[dict], ctx: dict) -> list[str]:
    valid_ids = ctx.get("valid_word_ids")
    if valid_ids is None:
        return []
    errors: list[str] = []
    for item in items:
        label = item.get("id")
        for field in ("anchor_start", "anchor_end"):
            anchor = item.get(field)
            if anchor is not None and anchor not in valid_ids:
                errors.append(f"{label}: {field} '{anchor}' không tồn tại trong transcript.json")
    return errors


def _check_cutaway_budget(items: list[dict], ctx: dict) -> list[str]:
    """khong_vuot_tran_api_calls_video · _thang · _3_lan_sinh_lai · _che_mat_qua_8_giay.

    Chỉ xét mục đã sinh bằng AI (`image_source=ai_generated`) — mục Claude mới
    soạn prompt (chưa gọi Gemini) không tiêu tốn hạn mức.
    """
    errors: list[str] = []
    cfg = ctx.get("cfg")
    ai_items = [i for i in items if i.get("image_source") == "ai_generated"]

    if cfg is not None:
        regen_limit = int(cfg.budget.gemini_regen_per_item)
        for item in ai_items:
            if int(item.get("regen_count", 0)) > regen_limit:
                errors.append(f"{item.get('id')}: vượt trần {regen_limit} lần sinh lại/mục")

        video_limit = int(cfg.budget.gemini_api_calls_per_video)
        video_calls = sum(int(i.get("regen_count", 0)) + 1 for i in ai_items)
        if video_calls > video_limit:
            errors.append(f"vượt trần {video_limit} lượt gọi Gemini/video (đang {video_calls})")

        month_used = ctx.get("month_used")
        month_limit = int(cfg.budget.gemini_api_calls_per_month)
        if month_used is not None and month_used > month_limit:
            errors.append(f"vượt trần {month_limit} lượt gọi Gemini/tháng (đang {month_used})")

        max_cover = float(cfg.cutaway.max_face_cover_sec)
        for item in ai_items:
            if float(item.get("t_dur", 0)) > max_cover:
                errors.append(f"{item.get('id')}: che mặt {item.get('t_dur')}s, vượt trần {max_cover}s")

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

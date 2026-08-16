"""Bước 2.5 — gộp chồng lấn, chạy SAU khi cả 6 cơ chế của bước 2 xong. TDD §5.2.

  · cut nằm TRỌN trong một cut khác  → gán absorbed_by, GIỮ trong file, LOẠI khỏi tính toán
  · bác bỏ cut cha ở /cut            → mọi cut con trỏ về nó TỰ ĐỘNG SỐNG LẠI (không cần code:
                                        absorbed_by chỉ có ý nghĩa khi cut cha status=accepted,
                                        xem lib.timeline.is_active)
  · cut chồng lấn MỘT PHẦN           → CẤM, việc của validate_plan.py

silence không tham gia gộp — nó neo cặp từ kẹp, không chiếm token nào.
"""

from __future__ import annotations

from lib.errors import AIEditorError


def merge_overlaps(items: list[dict], order: dict[str, int]) -> list[dict]:
    """Đánh dấu absorbed_by cho cut nằm trọn trong cut khác. Trả items đã sửa.

    Mỗi cặp chỉ xét MỘT lần (containment đối xứng: A chứa B ⇔ B nằm trong A) —
    so cả hai chiều sẽ báo nhầm "chồng lấn một phần" cho chính ca bao trọn.
    """
    spans = [
        (order[item["anchor_start"]], order[item["anchor_end"]], item)
        for item in items
        if item["kind"] != "silence"
    ]

    for a_index in range(len(spans)):
        a_lo, a_hi, a_item = spans[a_index]
        for b_index in range(a_index + 1, len(spans)):
            b_lo, b_hi, b_item = spans[b_index]
            if not _overlaps(a_lo, a_hi, b_lo, b_hi):
                continue

            a_in_b = b_lo <= a_lo and a_hi <= b_hi
            b_in_a = a_lo <= b_lo and b_hi <= a_hi
            if a_in_b and b_in_a:
                continue  # span trùng hệt — coi là hai đề xuất độc lập, không nuốt nhau
            if a_in_b:
                a_item["absorbed_by"] = b_item["id"]
            elif b_in_a:
                b_item["absorbed_by"] = a_item["id"]
            else:
                raise AIEditorError(
                    f"{a_item['id']} và {b_item['id']} chồng lấn MỘT PHẦN — không hợp lệ",
                    suggestion="Xem lại thuật toán phát hiện, hai cut không được cắt nhau nửa vời",
                )

    return items


def _overlaps(a_lo: int, a_hi: int, b_lo: int, b_hi: int) -> bool:
    return a_lo <= b_hi and b_lo <= a_hi

"""Chia khối render — ranh giới neo word ID và DÍNH. TDD §6.2.

Luật nền: khối được định danh bằng word ID, không bằng giây. Ranh giới cũ nào
vẫn thoả is_safe_point() thì giữ nguyên TUYỆT ĐỐI — thiếu luật dính này thì sửa
1 overlay ở khối 3 sẽ chia lại từ đó tới cuối và render tăng dần chết.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Block:
    word_start: str  # "w0410" — từ ĐƯỢC GIỮ đầu tiên của khối
    word_end: str  # "w0688" — từ ĐƯỢC GIỮ cuối cùng của khối
    segments: list = field(default_factory=list)  # [(word_in, word_out, dur_sec), ...]
    forced: bool = False  # True = cắt ép khi chạm hard_max, phải render dư 500ms/đầu
    # KHÔNG lưu t_in/t_out tuyệt đối ở đây — đó là việc của render_manifest.json.


# Bù bắt buộc khi cắt ép, mỗi đầu — TDD §6.2
FORCED_CUT_PAD_MS = 500


def find_blocks(timeline_map: dict, transcript: dict, prev_boundaries: list[str], cfg) -> list[Block]:
    """Chia timeline thành khối 20–40s, ranh giới trượt tới điểm an toàn.

    1. Đọc prev_boundaries từ render_manifest.json làm điểm khởi đầu.
       Lần đầu chạy: đặt điểm cắt ứng viên mỗi ~30 giây.
    2. RANH GIỚI DÍNH — ranh giới cũ còn thoả is_safe_point() thì GIỮ NGUYÊN;
       chỉ ranh giới vi phạm mới được dời, và chỉ trong phạm vi 2 khối kề.
    3. Trượt điểm vi phạm tới điểm an toàn gần nhất trong [target_min, target_max].
    4. Không có điểm an toàn → nới tới hard_max = 50s, ghi rõ vào log.
    5. Chạm hard_max mà vẫn chưa có → CẮT ÉP theo thang ưu tiên (§6.2).
       hard_max là trần THẬT, không phải gợi ý — vượt là swap rồi treo trên M1/8GB.
    6. Quy mọi ranh giới về word ID gần nhất rồi vứt giá trị giây đi.
    7. Hậu kiểm: khối ngắn hơn target_min/2 → hợp nhất vào khối kề;
       khối rỗng (bị retake cắt sạch) → biến mất khỏi manifest.
    """
    raise NotImplementedError("Tuần 1 — TDD §16. Đọc docs/TDD.md §6.2 trước khi viết.")


def is_safe_point(t: float, timeline: dict) -> bool:
    """Điểm an toàn = tại thời điểm t KHÔNG có:

    · đồ hoạ motion nào đang hiển thị hoặc đang vào/ra
    · cutaway nào đang hiển thị
    · zoom nào đang chuyển (đang trong Ken Burns transition)
    · dòng caption nào đang sáng — phải ở khoảng nghỉ giữa 2 dòng
    """
    raise NotImplementedError("Tuần 1 — TDD §16. Đọc docs/TDD.md §6.2 trước khi viết.")

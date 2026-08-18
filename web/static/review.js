/* State dùng chung cho 3 trang duyệt — TDD §4.2, §4.3.
   Alpine.js gọi: x-data="reviewPage('cut')"

   LAYOUT: file này CHỈ lo state và gọi API. Bố cục và style lấy từ ui-demo/ —
   xem CLAUDE.md. Không tự sáng tạo layout mới ở đây. */

const DRAFT_INTERVAL_MS = 10_000; // tự lưu nháp 10 giây — §4.3

function reviewPage(kind) {
  return {
    kind,
    items: [],
    version: 0,
    token: new URLSearchParams(location.search).get("token") || "",
    conflicts: [],
    message: "",
    loading: true,
    budget: null, // { api_calls_used, api_calls_limit, month_used, month_limit, est_cost_vnd } — chỉ /cutaway dùng

    async init() {
      const plan = await this.api("GET", `/api/plan/${this.kind}`);
      this.items = plan.items || [];
      this.version = plan.version;

      const draft = await this.api("GET", `/api/draft/${this.kind}`);
      if (draft.draft?.items) this.items = draft.draft.items; // khôi phục trạng thái duyệt

      if (this.kind === "cutaway") this.budget = await this.api("GET", "/api/budget");

      this.loading = false;
      setInterval(() => this.saveDraft(), DRAFT_INTERVAL_MS);
    },

    async api(method, path, body) {
      const res = await fetch(path + (path.includes("?") ? "&" : "?") + "token=" + this.token, {
        method,
        headers: { "Content-Type": "application/json", "X-Token": this.token },
        body: body ? JSON.stringify(body) : undefined,
      });
      return res.json();
    },

    setStatus(item, status) {
      item.status = status;
      item.decided_by = "user";
      item.decided_at = new Date().toISOString();
    },

    async saveDraft() {
      if (this.loading) return;
      await this.api("POST", `/api/draft/${this.kind}`, { items: this.items });
    },

    /* "Xuất quyết định" → server MERGE theo whitelist trường.
       409 chỉ khi xung đột cấp TRƯỜNG — phần còn lại VẪN LƯU, không tải lại trang. */
    async publish(scope = null) {
      const res = await this.api("POST", `/api/plan/${this.kind}`, {
        version: this.version,
        partial: Boolean(scope),
        scope,
        items: this.items,
      });
      this.version = res.version ?? this.version;
      this.conflicts = res.conflicts || [];
      this.message = res.message || "";
      if (!this.conflicts.length) await this.api("POST", "/api/shutdown");
    },

    resolveConflict(conflict, keepMine) {
      const item = this.items.find((i) => i.id === conflict.id);
      if (item) item[conflict.field] = keepMine ? conflict.yours : conflict.theirs;
      this.conflicts = this.conflicts.filter((c) => c !== conflict);
    },

    media(path) {
      return `/media/${path}?token=${this.token}`;
    },

    /* "Đã dùng n/10 · ước tính …đ" — PRD [JMP] bộ đếm ngân sách trên đầu trang /cutaway. */
    budgetLabel() {
      if (!this.budget) return "";
      const b = this.budget;
      return `Đã dùng ${b.api_calls_used}/${b.api_calls_limit} · tháng ${b.month_used}/${b.month_limit} · ước tính ${b.est_cost_vnd.toLocaleString("vi-VN")}đ`;
    },

    /* "sinh lại ảnh khác" (PRD [JMP]) — Claude không được gọi Gemini trực
       tiếp (§7.2), nên nút này chỉ ĐÁNH DẤU mục cần sinh lại: xoá ảnh hiện
       tại, publish(), rồi chạy lại `python -m steps.06_build_cutaway` để
       thật sự gọi Gemini trong trần đã kiểm. */
    regenerate(item) {
      if (item.regen_count >= item.regen_limit) return;
      item.image_path = null;
      item.decided_by = "user";
      item.decided_at = new Date().toISOString();
    },

    /* Nhãn lý do cho trang /cut — PRD [CUT]: "nhãn lý do, tầng phát hiện và độ tin cậy". */
    reasonLabel(item) {
      if (item.kind === "silence") return "khoảng lặng";
      if (item.kind === "filler") return item.group === "A" ? "từ đệm (tự động)" : "từ đệm (đề xuất)";
      if (item.kind === "retake") {
        return { 1: "nói lại (từ khoá)", 2: "nói lại (so khớp)", 3: "đổi hướng giữa câu" }[item.tier] || "nói lại";
      }
      return item.kind || "";
    },
  };
}

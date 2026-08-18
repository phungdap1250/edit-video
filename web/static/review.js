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
    playingAll: false, // "phát toàn bộ liên tục" — chỉ /storyboard dùng
    playAllIndex: -1,
    _expectedClipId: null,
    _onClipEndedBound: null,

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

    /* Canvas thật của scene (`#root` data-width/height, vd 2160×3840) lớn hơn
       nhiều khung xem 240×320 — scale bằng transform để đồ hoạ (thường nằm
       lệch phải khung) không bị crop mất, bug phát hiện lúc test thủ công
       [MGX-01]. Same-origin nên đọc thẳng contentWindow, không cần postMessage. */
    fitOverlayFrame(event) {
      const iframe = event.target;
      const root = iframe.contentWindow?.document?.getElementById("root");
      if (!root) return;
      const boxWidth = iframe.parentElement.clientWidth;
      const rootWidth = Number(root.dataset.width) || boxWidth;
      const rootHeight = Number(root.dataset.height) || iframe.parentElement.clientHeight;
      const scale = boxWidth / rootWidth;
      iframe.style.width = `${rootWidth}px`;
      iframe.style.height = `${rootHeight}px`;
      iframe.style.transform = `scale(${scale})`;
      iframe.parentElement.style.height = `${rootHeight * scale}px`;
    },

    /* "Phát toàn bộ liên tục" (PRD [MGX] Done khi, TDD §5.5) — mỗi thẻ là 1
       composition độc lập tự phát (xem build_overlay_scene), nên phát nối
       tiếp bằng cách gọi window.__aiEditorPlayClip() của từng iframe rồi chờ
       nó tự báo hết clip qua postMessage — không dựng lại 1 timeline chung. */
    playAll() {
      if (this.playingAll) {
        this.stopAll();
        return;
      }
      this.playingAll = true;
      this._onClipEndedBound = (e) => this._onClipEnded(e);
      window.addEventListener("message", this._onClipEndedBound);
      this._playAt(0);
    },

    stopAll() {
      this.playingAll = false;
      this.playAllIndex = -1;
      if (this._onClipEndedBound) window.removeEventListener("message", this._onClipEndedBound);
      document.querySelectorAll(".overlay-frame").forEach((frame) => {
        frame.contentWindow?.document?.getElementById("preview-video")?.pause();
      });
    },

    _playAt(index) {
      if (!this.playingAll) return;
      if (index >= this.items.length) {
        this.stopAll();
        return;
      }
      this.playAllIndex = index;
      const frame = document.querySelectorAll(".overlay-frame")[index];
      const playClip = frame?.contentWindow?.__aiEditorPlayClip;
      if (typeof playClip !== "function") {
        this._playAt(index + 1); // scene chưa nạp xong hoặc neo đã mất — bỏ qua, không kẹt luồng
        return;
      }
      this._expectedClipId = this.items[index].id;
      playClip();
    },

    _onClipEnded(event) {
      if (event.data?.type !== "ai-editor-clip-ended") return;
      if (!this.playingAll || event.data.id !== this._expectedClipId) return;
      this._playAt(this.playAllIndex + 1);
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

    /* Sửa chữ trên /storyboard (PRD [MGX]) — content là JSON tự do (4 loại đồ
       hoạ có cấu trúc khác nhau), nên ô sửa là 1 textarea JSON thay vì form
       riêng cho từng loại. Khoá CẢ "content" qua edited_fields[] — thô hơn
       khoá theo đường dẫn con (content.number) mà TDD §3.4 mô tả, nhưng an
       toàn: pipeline sinh lại sẽ không đụng bất kỳ phần nào của content này. */
    editContent(item, rawJson) {
      let parsed;
      try {
        parsed = JSON.parse(rawJson);
      } catch (e) {
        this.message = `content không phải JSON hợp lệ: ${e.message}`;
        return;
      }
      item.content = parsed;
      item.edited_fields = Array.from(new Set([...(item.edited_fields || []), "content"]));
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

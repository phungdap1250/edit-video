# Tài liệu dự án
Các tài liệu nằm trong repo — đọc khi cần, không phải mỗi lần:
- PRD (yêu cầu sản phẩm): docs/PRD.md
- TDD (thiết kế kỹ thuật): docs/TDD.md
- UI Demo (prototype thiết kế sẵn): ui-demo/

# Quy trình mỗi buổi build
Status quản thủ công trong PRD.md, ngay dưới tên feature. Bộ ký hiệu:
📝 Draft | ⏳ Todo | 🔄 In Progress | ⚠️ Partial | ✅ Done

1. Mở PRD.md, chọn story ⏳ Todo tiếp theo theo thứ tự ưu tiên (MUST trước, trong MUST theo lộ trình TDD §16)
2. Đổi status story đó sang 🔄 In Progress trước khi viết dòng code đầu tiên
3. Implement theo "Done khi" của story + phần kỹ thuật tương ứng trong TDD
4. Test: `make test` và các script nghiệm thu của story đó (cột "Phục vụ" ở PRD ⑨ / TDD §12.1)
5. Đổi status: ✅ Done chỉ khi **mọi** dòng "Done khi" đã đạt — còn thiếu dòng nào thì ⚠️ Partial, và ghi rõ thiếu gì
6. Mỗi buổi chỉ 1 story ở trạng thái 🔄 In Progress

Mã story: `[CUT]` cắt footage · `[RND]` timeline & render · `[JMP]` zoom & cutaway
· `[CAP]` caption karaoke · `[MGX]` motion graphics · `[INF]` hạ tầng.

# Nguyên tắc khi implement
- Trước khi code một User Story: đọc story đó trong PRD và phần kỹ thuật liên quan trong TDD
- Implement đầy đủ theo từng tiêu chí "Done khi" trong story
- Tham chiếu TDD cho mọi quyết định kỹ thuật: tech stack, DB schema, API design
- Đọc UI trong ui-demo/ trước khi viết layout — không tự sáng tạo layout mới
- Hỏi trước khi làm nếu có gì chưa rõ trong PRD hoặc TDD

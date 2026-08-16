# PRD — AI Editor

> Bộ công cụ dựng video tự động chạy trong Claude Code: người dùng đưa footage thô vào, ra lệnh bằng tiếng Việt, Claude đóng vai đạo diễn điều khiển HyperFrames để cắt, dựng motion-graphics và render ra MP4 hoàn chỉnh.

---

## ① Overview

- **App name:** AI Editor
- **Tagline:** Quay xong, nói tiếng Việt — máy dựng phần còn lại.
- **Problem:** Dựng 1 video hoàn chỉnh hiện tốn **cả ngày làm việc**, phải xoay giữa CapCut, editor thuê ngoài và script tự viết. Đau ở toàn bộ chuỗi: cắt khoảng lặng và từ đệm thủ công, làm motion graphic phải mở tool riêng, gắn caption từng dòng, sửa theo feedback phải làm lại tay, và chỉ đổi **1 câu thoại** cũng phải dựng + render lại từ đầu.
- **Solution:** Người dùng đưa vào **file video thô đã quay**, rồi **chat với Claude bằng tiếng Việt** để ra lệnh dựng. Claude đóng vai đạo diễn: phân tích transcript, đề xuất điểm cắt, lên kế hoạch overlay, dựng scene motion-graphics bằng HTML + GSAP trên **HyperFrames**, lắp timeline và render. Mọi bước có tính phán đoán đều đi qua **trang duyệt HTML** trước khi áp dụng. Trả ra **cả file MP4 hoàn chỉnh lẫn project HyperFrames** để sửa tiếp — đổi 1 câu chỉ render lại đoạn đó.
- **Platform:** Chạy trong **Claude Code / Cowork** — không có UI riêng. Người dùng mở Claude Code tại folder chứa video, ra lệnh bằng tiếng Việt. Sản phẩm là **bộ skill + toolkit**, xử lý local trên máy.
- **Giai đoạn:** Bản test nội bộ. Chưa đóng gói thành sản phẩm bán ra ngoài.

---

## ② Target User

**Persona chính: Phùng — chuyên gia đào tạo kinh doanh online, tự dựng video**

- **Độ tuổi / nghề nghiệp:** 32, chuyên gia đào tạo và tư vấn kinh doanh online, marketing automation, ứng dụng AI. Làm việc tự do, tự sản xuất toàn bộ nội dung.
- **Trình độ kỹ thuật:** Biết đọc code, chạy terminal thành thạo. Không ngại sửa file cấu hình.
- **Hàng ngày làm gì:** Quay talking-head chia sẻ kiến thức và bài giảng khoá học, **độ dài 5–15 phút/video**, rồi tự dựng.
- **Nỗi đau cụ thể:**
  - Dựng 1 video tốn cả ngày → không tăng được sản lượng
  - Sửa 1 câu phải dựng và render lại từ đầu
  - Motion graphic phải mở công cụ khác, mất mạch làm việc
  - Thuê editor ngoài thì chậm, tốn chi phí, và phải mô tả lại ý mỗi lần
- **Tool đang dùng:** CapCut, editor thuê ngoài, script tự code.
- **Mục tiêu:** Ra được **nhiều video** mà vẫn **cầu kỳ, chỉn chu** — không đánh đổi chất lượng lấy tốc độ.

---

## ③ Features & User Stories

> Mỗi feature gồm: Tên · Status · Story · Steps · Done khi · Edge cases
>
> **Status:** 📝 Draft · ⏳ Todo · 🔄 In Progress · ⚠️ Partial · ✅ Done — sửa tay tại chỗ.
> Mỗi feature ở đây có đúng 1 story nên status của feature cũng là status của story.
> ✅ Done chỉ được đặt khi **mọi dòng "Done khi"** của story đó đã đạt; đạt một phần là ⚠️ Partial.

---

### 🟢 MUST (bắt buộc có trong MVP)

---

#### [CUT] Feature 1: Cắt sạch footage thô (có duyệt trước)

**Status:** ⚠️ Partial — thiếu 2/8 dòng "Done khi", xem ghi chú dưới bảng Done khi.

**Story:** [CUT-01] Là người tự dựng video, tôi muốn Claude tự phát hiện và đề xuất các đoạn cần cắt trong footage thô, để tôi chỉ việc duyệt thay vì ngồi rà từng giây trên timeline.

**Steps to Complete:**
1. Người dùng đưa file video thô vào folder, ra lệnh bằng tiếng Việt
2. Hệ thống tách audio → gửi lên ElevenLabs Scribe → nhận transcript có timestamp cấp từ
3. Gán **ID bất biến cho từng từ** (`w0001`, `w0002`…) — xem mục ⑥. Mọi kế hoạch phía sau neo vào ID này, không neo vào giây
4. Hệ thống phát hiện 3 loại đoạn cần cắt theo tiêu chí ở bảng dưới
5. Xuất **`cut_plan.json`** (nguồn sự thật cho máy) + phục vụ trang duyệt `/cut` qua server duyệt cục bộ
6. Người dùng chạy `python review.py cut` → trình duyệt tự mở: transcript đầy đủ, đoạn bị đề xuất cắt hiện gạch ngang kèm **nhãn lý do, tầng phát hiện và độ tin cậy**. Bấm vào dòng nào để bỏ cắt / thêm cắt dòng đó
7. Bấm **"Xuất quyết định"** → server ghi đè `cut_plan.json` trên đĩa + ghi 1 dòng thống kê vào `stats.jsonl`
8. Hệ thống áp dụng cắt theo bản đã duyệt, tạo footage sạch

**Tiêu chí phát hiện — khoảng lặng** *(cấu hình trong `cut_config.json`, không hardcode)*

| Khoảng lặng gốc | Sau khi cắt | Lý do |
|---|---|---|
| < 600ms | Giữ nguyên | Nhịp nói tự nhiên |
| 600ms – 1,5s | Rút còn **300ms** | Vẫn có nhịp, bỏ phần thừa |
| > 1,5s | Rút còn **400ms** | Chỗ chuyển ý — giữ nhịp dài hơn cho người xem kịp tiêu hoá |
| Đầu và cuối video | Cắt sạch về **200ms** | Không cần bậc |

**Tiêu chí phát hiện — từ đệm** *(danh sách trong `filler_words.txt`, mỗi dòng 1 mục, người dùng sửa được)*

Bộ khởi tạo: `ờ`, `à`, `ừ`, `ừm`, `ơ`, `thì`, `là`, `kiểu như`, `nói chung là`, `cái mà`, `đúng không`, `các bạn thấy không`, `okay`.

| Nhóm | Định nghĩa | Xử lý |
|---|---|---|
| **A** | Từ đệm đứng **một mình giữa hai khoảng lặng** | **Cắt tự động**, không cần duyệt |
| **B** | Từ đệm nằm **giữa dòng chảy câu** | **Chỉ đề xuất, mặc định KHÔNG cắt**, hiện màu vàng trên trang duyệt |

Luật cứng: **không cắt từ đệm nếu nó là từ đầu tiên hoặc cuối cùng của một câu có nghĩa** — tránh cụt đầu/cuối câu.

**Tiêu chí phát hiện — đoạn nói vấp / thu lại** *(3 tầng, chạy tuần tự, tầng sau chỉ chạy trên phần còn lại của tầng trước)*

| Tầng | Cơ chế | Xử lý | Tỉ lệ bác bỏ mục tiêu |
|---|---|---|---|
| **1** | **Từ khoá ra hiệu** — người nói sai thì nói **"cắt cắt"** rồi nói lại. Hệ thống xoá từ mốc gần nhất trước đó (đầu câu hoặc khoảng lặng > 1s) đến hết từ khoá | **Cắt tự động** | < 2% |
| **2** | **So khớp văn bản** — hai cụm liền kề trong vòng **15 giây**, giống nhau **≥ 70%** trên chuỗi token (bỏ dấu, bỏ từ đệm trước khi so) → đề xuất **giữ lần sau, bỏ lần trước** | Đề xuất, có duyệt | < 15% |
| **3** | **Claude đọc ngữ cảnh** — bắt ca nói nửa câu rồi đổi hướng ("Cái phễu này có ba— thật ra là bốn bước") | **Luôn hiện màu vàng, mặc định không cắt** | < 40% |

**Done khi:**
- ⚠️ Transcript có timestamp cấp từ; **WER ≤ 10%** đo bằng `check_wer.py` trên bộ mẫu chuẩn `tests/golden_transcript.txt` (đoạn 3 phút gõ tay 1 lần, dùng lại mãi) — `lib/transcribe.py` (ElevenLabs Scribe) đã viết nhưng CHƯA gọi thật; `check_wer.py` còn là stub; `tests/golden_transcript.txt` chưa tồn tại — theo TDD §12.4 đây là thứ **duy nhất trong hệ thống không tự động hoá được**, cần anh gõ tay 1 lần
- ✅ Mỗi từ trong transcript có **ID bất biến**, `cut_plan.json` neo vào ID chứ không neo vào giây
- ✅ `cut_plan.json` ghi mỗi mục gồm: ID từ vào–ra, timestamp vào–ra (tính ra được), loại lỗi, **tầng phát hiện**, **độ tin cậy**, nội dung thoại tại đó
- ✅ Trang duyệt `/cut` chạy qua **server duyệt cục bộ**, hiển thị transcript có đánh dấu điểm cắt kèm tầng và độ tin cậy — chức năng đủ (đã smoke-test qua Flask test client), **bố cục còn là khung tối thiểu chờ `ui-demo/`** (hiện rỗng)
- ✅ Người dùng bỏ cắt / thêm cắt trên trang duyệt → bấm "Xuất quyết định" → **server ghi đè đúng file `cut_plan.json` trên đĩa**, hiện xác nhận kèm số mục giữ/bỏ và thời điểm lưu
- ✅ Ba tiêu chí phát hiện đọc từ `cut_config.json` và `filler_words.txt` — **không có ngưỡng nào hardcode trong code**
- ✅ Bản cắt xong không mất chữ đầu/cuối câu — giữ khoảng đệm tối thiểu **100ms** mỗi đầu
- ⚠️ Video 5 phút: xử lý xong bước đề xuất trong **dưới 2 phút** — chưa đo được, chưa có video mẫu 5 phút thật; đã xác nhận đúng trên video tổng hợp 4.6 giây (transcript giả lập → phát hiện → áp cắt bằng ffmpeg thật)
- ✅ File gốc luôn nguyên vẹn, mọi thao tác ghi ra file mới
- ❌ Chưa cần giao diện timeline trực quan dạng waveform kéo thả
- ❌ Chưa cần tự động phát hiện lỗi hình ảnh (mất nét, sai khung)

**Ghi chú Partial (16/08/2026):** 6/8 dòng đạt, có test (59 test pytest xanh). Đã chạy thử đầu-cuối **2 lần**: (1) video tổng hợp + ffmpeg thật, (2) **video thật của anh** (`IMG_4588.MOV`, 13.3s, 4K dọc iPhone) — gọi ElevenLabs Scribe thật, phát hiện 9 điểm cắt, duyệt qua trang `/cut` thật, áp cắt bằng ffmpeg thật (13.3s → 10.0s, 0 chữ mất, `check_anchor_integrity` sạch). Trong lần thử này bắt và sửa 1 lỗi thật: Alpine.js không khởi động do thứ tự nạp script sai ở cả 3 trang duyệt.

2 dòng còn thiếu vẫn phụ thuộc thứ ngoài tầm code, video 13s không đủ để chốt: (1) `tests/golden_transcript.txt` do anh gõ tay 3 phút để đo WER, (2) một video mẫu **5 phút** thật để đo hiệu năng (đã test 13s, chưa đại diện cho ngưỡng "dưới 2 phút" của video 5 phút). Không có 2 thứ này, `[CUT-01]` không thể lên ✅ Done dù pipeline đã chạy đúng trên dữ liệu thật.

**Edge cases:**
| Tình huống | Xử lý |
|---|---|
| Transcript sai từ tiếng Việt | Người dùng sửa trong file transcript, chạy lại — xử lý theo **3 mức sửa transcript** ở mục ⑥, không mất công đã duyệt ở bước khác |
| File video hỏng / codec lạ | Báo lỗi rõ tên codec, không treo tiến trình |
| Cắt quá tay làm mất nghĩa câu | File gốc giữ nguyên, mọi thao tác ghi ra file mới |
| Video dài trên 5 phút | Cảnh báo trước, hỏi xác nhận, không âm thầm chạy |
| Người dùng đóng tab giữa lúc duyệt | Bản nháp tự lưu mỗi 10 giây; mở lại thấy nguyên trạng thái duyệt |
| Từ khoá "cắt cắt" xuất hiện trong nội dung thật | Chỉ nhận khi đứng liền sau khoảng lặng ≥ 300ms và trước khoảng lặng ≥ 300ms; ca nghi ngờ đẩy xuống tầng 3, không tự cắt |

---

#### [RND] Feature 2: Lắp ráp timeline & render (HyperFrames)

**Status:** ⚠️ Partial — render 1-khối thật đã chạy đúng trên video thật; chia khối tăng dần + Variables cần [CAP-01]/[MGX-01]/[JMP-01] trước. Xem ghi chú dưới bảng Done khi.

**Story:** [RND-01] Là người tự dựng video, tôi muốn hệ thống ghép footage đã cắt cùng mọi lớp phủ vào một timeline HyperFrames và xuất ra MP4, để tôi có file hoàn chỉnh mà khi sửa chỉ phải render lại đúng đoạn đã đổi.

**Steps to Complete:**
1. Hệ thống đọc `cut_plan.json` đã duyệt từ Feature 1
2. Tự nhận diện khung hình gốc từ file nguồn (16:9 hoặc 9:16), đặt cấu hình composition tương ứng
3. Sinh project HyperFrames: mỗi đoạn giữ lại thành một clip trên timeline qua thuộc tính `data-*`, đúng thứ tự thời gian
4. Người dùng mở HyperFrames Studio để tua xem, hoặc render bản nháp 480p để coi tổng thể nhịp
5. Người dùng ra lệnh sửa → hệ thống phân loại: sửa chữ/màu/media đã duyệt thì đổi qua **Variables** (không render lại, **và ghi ngược về plan JSON ngay lúc sửa** — xem mục ⑥); sửa cấu trúc thì đánh dấu "bẩn" đúng các đoạn bị ảnh hưởng
6. Chia khối render: khối dài **20–40 giây**, ranh giới **trượt tới điểm an toàn** — thời điểm không có chuyển động nào đang chạy dở (không đồ hoạ trên màn hình, không cutaway, không zoom đang chuyển, đang ở khoảng nghỉ giữa hai dòng caption)
7. Render lại riêng các đoạn bẩn, nối với đoạn cũ bằng `ffmpeg concat` (không mã hoá lại)
8. Xuất MP4 cuối + giữ nguyên project HyperFrames để sửa tiếp

**Done khi:**
- ✅ Tự nhận đúng khung gốc: video ngang ra 1920×1080, video dọc ra 1080×1920 — không méo hình, không viền đen
- ✅ Xuất MP4 H.264, 30fps, audio đồng bộ — **lệch tiếng–hình ≤ 40ms tại cả 5 mốc 0/25/50/75/100%**, đo bằng `check_av_sync.py` (tương quan chéo audio đầu ra với audio footage đã cắt)
- ✅ **Mọi ranh giới khối render rơi vào điểm không có chuyển động đang chạy** — `check_block_boundary.py` đối chiếu danh sách ranh giới với timeline caption/đồ hoạ/cutaway/zoom, đạt = **0 va chạm**
- ✅ Không tìm được điểm an toàn trong 40 giây → cho phép kéo dài tới **50 giây** và báo rõ (ví dụ *"khối 7 dài 47s vì không có điểm cắt an toàn"*)
- ✅ Bản nháp 480p toàn video 5 phút: render xong **dưới 5 phút**
- ✅ Bản cuối 1080p toàn video 5 phút: render xong **dưới 35 phút**
- ✅ **Sửa 1 câu → render lại chỉ đoạn chứa câu đó, xong dưới 3 phút**
- ✅ **Sửa chữ / màu / media qua Variables: thấy đổi trong dưới 15 giây, không render lại**
- ✅ **Sửa chữ qua Variables → chạy lại toàn bộ pipeline → chữ vẫn là bản đã sửa, không quay về bản cũ** (bài test bắt buộc)
- ✅ Nối các đoạn thành file cuối: **dưới 30 giây**, không tụt chất lượng ở điểm nối
- ✅ Render đứt giữa chừng → chạy lại chỉ làm tiếp phần còn thiếu, đoạn đã xong không mất
- ✅ Mở được HyperFrames Studio để tua/xem trước khi render
- ✅ Trả ra cả MP4 lẫn project HyperFrames còn nguyên, sửa tay được
- ✅ File tạm của đoạn nào bị xoá ngay sau khi đoạn đó nối xong
- ✅ Kiểm tra dung lượng ổ trống trước khi bắt đầu render, báo trước nếu không đủ
- ❌ Chưa cần đổi khung chéo ngang↔dọc (để NICE TO HAVE)
- ❌ Chưa cần render trên cloud / nhiều máy
- ❌ Chưa cần xuất ProRes hay codec dựng chuyên nghiệp khác
- ❌ Chưa hỗ trợ video dài trên 5 phút

**Ghi chú Partial (16/08/2026):** Render THẬT qua HyperFrames CLI thật (`npx hyperframes`, không phải giả lập) đã chạy đúng đầu-cuối trên video của người dùng — xem ảnh khung hình đã soi bằng mắt, đúng chiều dọc 1080×1920, không méo, không viền đen, có tiếng.

✅ Đạt thật: nhận đúng khung ngang/dọc (đã sửa 1 bug thật — `ffprobe` báo kích thước lưu trữ thô, không tính metadata xoay của iPhone, khiến video dọc bị nhận nhầm thành ngang) · MP4 H.264/30fps xuất ra đúng · Studio preview mở được (`npx hyperframes preview`) · giữ cả MP4 lẫn project `hf/` nguyên vẹn, sửa tay được · kiểm dung lượng ổ trống trước khi render.

Trong lúc test bắt thêm 1 bug thật thứ hai: `<video>` sinh ra thiếu CSS định vị (`position:absolute` cần `#root` là ngữ cảnh định vị) → render ra **toàn màn hình đen** dù `npx hyperframes check` báo **0 lỗi** — đúng cảnh báo tài liệu HyperFrames: "không dựa vào automated gate, phải soi khung hình". Đã sửa, xác nhận lại bằng ảnh thật.

❌ Chưa đạt — cần hạ tầng chưa tồn tại, không phải thiếu công code đơn thuần:
- Chia khối render theo điểm an toàn (§6.2) — `is_safe_point()` cần đọc timeline caption/đồ hoạ/cutaway để biết chỗ nào "không có chuyển động đang chạy dở", nhưng 3 lớp đó thuộc `[CAP-01]`/`[MGX-01]`/`[JMP-01]`, chưa story nào trong số đó được code. Hiện tại render là **1 khối duy nhất** cho toàn video.
- Do chỉ 1 khối: "sửa 1 câu → render lại 1 đoạn", "render đứt → chạy tiếp phần thiếu", "nối đoạn dưới 30s", "xoá file tạm sau khi nối" đều **không áp dụng được** — không có khối nào để chia/nối/tiếp tục.
- Sửa qua Variables (không render lại) — thuộc `[MGX-01]` (Variables là bản chiếu của `overlay_plan.json`, chưa tồn tại).
- AV sync đo bằng `check_av_sync.py` — script còn là stub, chưa đo thật số lệch tiếng-hình.
- "Bản nháp 480p" — `--quality draft` của HyperFrames chỉ chỉnh **chất lượng mã hoá** (CRF/bitrate), không hạ **độ phân giải**; `--resolution` chỉ supersample lên theo bội số nguyên, không hạ xuống được. Bản nháp hiện render đúng độ phân giải nguồn (1080×1920), không phải 480p theo đúng nghĩa đen của tiêu chí.
- Cả 2 mốc thời gian (nháp dưới 5 phút, bản cuối dưới 35 phút) đo trên video 5 phút thật — chưa có video 5 phút để đo, chỉ mới test với 10 giây.

**Edge cases:**
| Tình huống | Xử lý |
|---|---|
| Render đứt giữa chừng (hết pin, tắt máy) | Giữ nguyên đoạn đã render, chạy lại làm tiếp phần thiếu |
| Video nguồn có fps lạ (25 / 29.97 / biến thiên) | Chuẩn hoá về 30fps trước khi dựng, báo rõ đã chuyển đổi |
| Audio lệch pha ngay từ file gốc | Phát hiện và báo trước khi dựng, không âm thầm dựng ra bản lệch |
| Hết dung lượng ổ giữa lúc render | Dừng sạch, báo còn thiếu bao nhiêu GB, không để lại file hỏng |
| Đánh dấu đoạn bẩn sai | Có lệnh ép render lại toàn bộ |
| RAM trống tụt dưới 800MB | Tạm dừng render, báo người dùng đóng bớt ứng dụng, giữ tiến độ |
| Variables và plan JSON lệch nhau | Trước mọi lần render: dừng, hiện 2 bản, hỏi giữ bản nào — không tự đoán |
| Đoạn dài liên tục không có điểm an toàn (nói liền mạch 50s+) | Chấp nhận khối dài hơn ngưỡng, báo rõ; không cắt bừa vào giữa chuyển động |

---

#### [JMP] Feature 3: Che jump cut — zoom tự động & cutaway có duyệt

**Status:** ⏳ Todo

**Story:** [JMP-01] Là người tự dựng video, tôi muốn hệ thống che các điểm cắt bằng zoom luân phiên và chèn hình minh hoạ đúng chỗ, để video không bị giật hình sau khi cắt và người xem có hình theo nội dung đang nói.

**Steps to Complete:**
1. Hệ thống đọc danh sách điểm cắt đã duyệt từ Feature 1
2. **Dò khung mặt 1 lần duy nhất** trên 1 khung hình lúc khởi tạo project (camera cố định, 1 người nói — theo assumption mục ⑪), tính ra **mức zoom tối đa an toàn**, ghi vào config
3. **Zoom — chạy tự động, không cần duyệt:** gán mức phóng luân phiên cho các đoạn liền kề (100% → 106% → 100%…), chuyển mượt kiểu Ken Burns. Zoom **chỉ tác động lên lớp video người nói** (xem bảng lớp bên dưới)
4. **Cutaway — Claude phân tích transcript**, xác định các đoạn đang giải thích khái niệm cần hình minh hoạ
5. Quét folder `assets/` của người dùng, khớp hình có sẵn với từng đoạn cần minh hoạ
6. Đoạn nào không có hình phù hợp → sinh ảnh bằng **Gemini API** theo nội dung đang nói, lưu vào folder riêng — **trong hạn mức ở bảng ngân sách bên dưới**
7. Xuất **`cutaway_plan.json`**, phục vụ trang duyệt `/cutaway` qua server duyệt cục bộ (bản động, phát được)
8. Người dùng duyệt trên storyboard: Giữ / Bỏ / thay hình / sinh lại ảnh khác
9. Bấm "Xuất quyết định" → server ghi đè `cutaway_plan.json` → hệ thống áp dụng vào timeline

**Thứ tự lớp hình ảnh — chốt cho toàn hệ thống**

| Lớp | Nội dung | Có bị zoom không |
|---|---|---|
| 4 (trên cùng) | Caption | **Không** |
| 3 | Đồ hoạ motion (card, pill, list, số) | **Không** |
| 2 | Cutaway (ảnh minh hoạ) | **Không** |
| 1 (đáy) | Video người nói | **Có** |

**Bảng ưu tiên khi trùng thời điểm**

1. Cutaway và đồ hoạ motion **không bao giờ chồng nhau**. Trùng → **giữ đồ hoạ motion, dời cutaway** (đồ hoạ bám chặt câu nói hơn; cutaway dời vài giây vẫn hợp lý)
2. Hai đồ hoạ motion trùng nhau → **Con số nhảy > Danh sách bung dần > Card khái niệm > Pill từ khoá**
3. Đồ hoạ mới chỉ vào sau khi đồ hoạ cũ ra hết + cách nhau tối thiểu **500ms**

**Hạn mức sinh ảnh** *(cấu hình trong `cut_config.json`)*

- Tối đa **25 ảnh/video**
- Tối đa **3 lần sinh lại cho mỗi mục**
- Chạm trần → dừng, báo *"đã dùng 25/25 lượt sinh ảnh cho video này"*, gợi ý bỏ ảnh vào `assets/`
- Trang duyệt hiện bộ đếm ngay trên đầu: `Đã dùng 12/25 · ước tính 9.400đ`

**Done khi:**
- ✅ **Mọi điểm cắt đều được che** — `check_cut_coverage.py` đối chiếu từng mục `status: applied` trong `cut_plan.json` với đúng 1 mục che (zoom hoặc cutaway) trong cửa sổ ±100ms, in ra `42/42 điểm cắt đã che · 0 điểm trần`. Đạt = **100%**
- ✅ Zoom luân phiên không lặp cùng mức ở 2 đoạn liền nhau; mức phóng trong khoảng **100–110%** **và không vượt mức zoom tối đa an toàn** tính từ khung mặt. Vượt → tự hạ xuống mức an toàn và báo
- ✅ Zoom chỉ áp lên lớp 1 — caption và đồ hoạ **không đổi cỡ, không bị đẩy khỏi khung** khi zoom
- ✅ `cutaway_plan.json` neo vào **ID từ**, ghi rõ **nguồn hình: có sẵn hay AI sinh** cho từng mục
- ✅ Ảnh AI sinh lưu vào folder riêng, không lẫn với `assets/` của người dùng
- ✅ **Không ảnh AI nào vào video khi chưa được duyệt** — mặc định là chưa duyệt
- ✅ Cutaway không che mặt người nói quá **8 giây liên tục**
- ✅ Không vượt **25 ảnh/video** và **3 lần sinh lại/mục** — chạm trần thì dừng, không âm thầm gọi tiếp API
- ✅ Từ chối toàn bộ kế hoạch cutaway → video vẫn dựng bình thường, chỉ còn zoom
- ❌ Chưa cần sinh video b-roll bằng AI (chỉ ảnh tĩnh)
- ❌ Chưa cần **bám mặt liên tục** khi zoom — chỉ dò 1 lần lúc khởi tạo để lấy vùng an toàn, sau đó dùng khung cố định
- ❌ Chưa cần thư viện stock ảnh bên ngoài

**Edge cases:**
| Tình huống | Xử lý |
|---|---|
| Người nói lệch tâm, zoom làm mất mặt | Mức zoom tối đa an toàn tính từ khung mặt lúc khởi tạo; lệch tâm nhiều → ưu tiên giữ nguyên khung |
| Dò mặt thất bại (ngược sáng, đeo khẩu trang, khuất) | Hạ trần zoom về **104%** cho toàn video, báo rõ *"không dò được khung mặt, dùng trần zoom an toàn"* |
| Ảnh AI sai ngữ cảnh | Người dùng ghi mô tả mới vào mục đó, sinh lại đúng mục đó (tối đa 3 lần), không chạy lại toàn bộ |
| Ảnh trong `assets/` sai tỉ lệ | Tự thêm nền mờ (blur) từ chính ảnh đó, không kéo méo hình |
| Gemini API lỗi hoặc hết quota | Đánh dấu mục đó "thiếu hình", vẫn dựng được phần còn lại |
| Folder `assets/` trống | Bỏ qua bước khớp hình, chuyển thẳng sang sinh ảnh, báo rõ cho người dùng |
| Đoạn giữ lại ngắn dưới 1,5 giây | Không chèn cutaway vào đó, chỉ zoom |

---

#### [CAP] Feature 4: Caption karaoke tiếng Việt

**Status:** ⏳ Todo

**Story:** [CAP-01] Là người tự dựng video, tôi muốn hệ thống tự sinh caption tiếng Việt bám theo lời nói và làm nổi bật từ khoá quan trọng, để người xem trên điện thoại hoặc xem không bật tiếng vẫn theo được nội dung.

**Steps to Complete:**
1. Đọc transcript word-level đã duyệt từ Feature 1 (đã trừ đoạn bị cắt, **neo theo ID từ**, timestamp tính lại về timeline mới)
2. Gom từ thành dòng caption theo ngữ nghĩa — ngắt ở dấu câu và cụm từ, không ngắt giữa cụm
3. Claude đánh dấu từ khoá cần nhấn mạnh: thuật ngữ chuyên môn, con số, tên công cụ
4. Chọn kiểu hiển thị: **karaoke highlight từng từ** là mặc định cho mọi video; **1–3 từ nhảy** chỉ áp dụng cho video dọc dưới 2 phút — hệ thống tự nhận, không cần khai báo
5. Dựng lớp caption bằng HyperFrames (HTML + GSAP), đặt ở **lớp 4 — trên cùng, không bị zoom**
6. Xuất song song file `.srt` khớp đúng timeline sau khi cắt
7. Người dùng chỉnh style (font, cỡ, màu, vị trí, màu nhấn) qua file cấu hình

**Vùng caption là vùng cấm**

Caption **đứng yên tuyệt đối** ở một vị trí cố định suốt video. Vùng caption khai báo trong config trở thành **vùng cấm** — đồ hoạ motion và cutaway là bên phải né, không được lấn vào. *(Đảo ngược so với bản v1: caption không tự dịch lên khi bị che, vì caption nhảy vị trí giữa video là lỗi hình người xem nhận ra ngay.)*

**Done khi:**
- ✅ Caption khớp lời nói, sai lệch **dưới 150ms**, kiểm bằng headless browser: lấy **20 từ ngẫu nhiên**, tại `t_từ + 80ms` đọc trạng thái DOM lớp caption, xác nhận đúng từ đó đang sáng. Đạt = **20/20**
- ✅ **Dấu tiếng Việt hiển thị đúng 100%** — kiểm bằng bộ chữ mẫu: ề, ữ, ợ, ẫ, ỹ, ặ, ườ, Đ — không vỡ dấu, không chồng dấu, không mất dấu
- ✅ **Video ngang và dọc: karaoke highlight từng từ** — cả câu hiện mờ, từ đang nói sáng lên
- ✅ **Kiểu 1–3 từ nhảy: chỉ cho video dọc dưới 2 phút**, hệ thống tự chọn theo độ dài
- ✅ Mỗi dòng caption tối đa 2 dòng chữ, không quá **42 ký tự/dòng** ở video ngang
- ✅ Không ngắt dòng giữa một cụm từ có nghĩa
- ✅ Từ khoá nhấn mạnh bằng màu/đậm, **tối đa 3 từ khoá trong 1 dòng**
- ✅ **Caption đứng yên suốt video** — không dịch chuyển vì bất kỳ lớp nào khác; cách mép đáy tối thiểu **8% chiều cao khung**
- ✅ **0 mục đồ hoạ hoặc cutaway lấn vào vùng caption** — kiểm bằng script đối chiếu toạ độ
- ✅ Xuất kèm `.srt` khớp timeline sau cắt, mở bằng trình phát ngoài vẫn đúng giờ
- ✅ Sửa file cấu hình style → chạy lại thấy đổi, không phải dựng lại từ đầu
- ❌ Chưa cần dịch caption sang ngôn ngữ khác
- ❌ Chưa cần nhiều style caption khác nhau trong cùng một video
- ❌ Chưa cần hiệu ứng chữ nâng cao (chữ 3D, chữ bay, chữ gõ máy)

**Edge cases:**
| Tình huống | Xử lý |
|---|---|
| Transcript sai chữ | Sửa trong file transcript → **mức 1** ở mục ⑥: chỉ dựng lại lớp caption, giữ nguyên mọi duyệt khác |
| Nói quá nhanh, dòng caption dồn cục | Tự tách thành dòng ngắn hơn thay vì hiện chớp dưới 0,5 giây |
| Đoạn im lặng dài giữa hai câu | Caption cũ không đứng quá 1 giây sau khi hết tiếng |
| Font cấu hình không có trên máy | Báo rõ tên font thiếu, dùng font dự phòng đã kiểm chứng dấu tiếng Việt — không âm thầm dựng bản vỡ dấu |
| Đồ hoạ / cutaway rơi vào vùng caption | **Đồ hoạ né, caption đứng yên** — dời hoặc thu nhỏ đồ hoạ, không đụng caption |
| Tiếng Anh xen tiếng Việt ("automation", "funnel") | Giữ nguyên, không tự dịch, không tự sửa chính tả |

---

#### [MGX] Feature 5: Motion graphics theo lời nói (HyperFrames)

**Status:** ⏳ Todo

**Story:** [MGX-01] Là người tự dựng video, tôi muốn hệ thống tự dựng đồ hoạ động bám đúng nội dung tôi đang nói, để người xem nhìn thấy được thứ tôi đang giải thích chứ không chỉ nghe.

**4 loại đồ hoạ trong MVP — tất cả đều kích hoạt bởi lời nói:**

| Loại | Kích hoạt bởi | Ưu tiên khi trùng |
|---|---|---|
| Con số nhảy | Con số / tỉ lệ được nói ra | 1 (cao nhất) |
| Danh sách bung dần | Câu liệt kê ("có 3 bước…") | 2 |
| Card khái niệm | Câu định nghĩa một thuật ngữ | 3 |
| Pill từ khoá | Từ khoá được nhấn mạnh | 4 |

**Steps to Complete:**
1. Claude đọc transcript đã duyệt, quét tìm 4 tình huống kích hoạt ở trên
2. Đọc **`frame.md`** của project — lấy mã màu hex, họ phông, quan hệ độ đậm nhạt từ frontmatter; đọc mục **"Luật kiểm được"** để lấy các luật máy kiểm; đọc phần văn bản bên dưới để nắm ý định thương hiệu
3. Sinh `overlay_plan.json`: mỗi mục gồm **ID từ vào–ra** (timestamp tính ra được), câu thoại kích hoạt, loại đồ hoạ, nội dung chữ/số
4. Dựng bản xem trước của từng đồ hoạ, ghép lên khung hình thật tại giây đó
5. Người dùng chạy `python review.py storyboard` → **phát từng thẻ có tiếng và chuyển động**, duyệt: Giữ / Bỏ / sửa chữ trực tiếp
6. Bấm "Xuất quyết định" → server ghi đè `overlay_plan.json`
7. Hệ thống dựng đồ hoạ thật và đặt lên **lớp 3** của timeline HyperFrames theo kế hoạch đã duyệt

**`overlay_plan.json` là chủ duy nhất của nội dung đồ hoạ.** Variables của HyperFrames chỉ là bản chiếu ra từ nó. Mọi sửa qua Variables được **ghi ngược về `overlay_plan.json` ngay lúc sửa**. Chi tiết ở mục ⑥.

**Done khi:**
- ✅ Dựng được đủ 4 loại: Card khái niệm, Pill từ khoá, Danh sách bung dần, Con số nhảy
- ✅ Mọi đồ hoạ lấy màu và phông từ `frame.md` — **không có màu/phông nào cứng trong code**
- ✅ **Đạt 100% mục "Luật kiểm được" của `frame.md`** — `check_frame_rules.py` quét CSS/HTML đồ hoạ đã dựng, in bảng đạt/không đạt từng luật
- ✅ Đồ hoạ xuất hiện trong khoảng **±300ms** so với câu thoại kích hoạt
- ✅ **Không đồ hoạ nào vào video khi chưa duyệt qua storyboard** — mặc định là chưa duyệt
- ✅ **Storyboard là bản động, phát được** — mỗi thẻ bấm Play chạy đúng đồ hoạ đã dựng: chuyển động, hiệu ứng vào/ra, chuyển cảnh, SFX
- ✅ **Có tiếng** — mỗi thẻ phát kèm audio gốc tại giây đó, nghe khớp với đồ hoạ đang chạy
- ✅ Có nút **phát toàn bộ storyboard liên tục** để xem nhịp video chảy thế nào
- ✅ Tua được trong từng thẻ, phát lại không giới hạn
- ✅ **Storyboard phát ra đúng thứ sẽ có trong video cuối** — `check_storyboard_fidelity.py` so ảnh tại **3 mốc** có đồ hoạ đang hiển thị: chụp khung từ storyboard và trích đúng khung đó từ MP4 cuối, **khác biệt dưới 2% số điểm ảnh**. Đạt = cả 3 mốc, ghi kết quả vào log sau mỗi lần render
- ✅ Chạy qua server duyệt cục bộ (`python review.py storyboard`), tải theo HTTP range — **chỉ tải đoạn đang xem**
- ✅ Sửa chữ trên storyboard → đồ hoạ dựng ra đúng chữ đã sửa, **và chữ đó không bị mất khi chạy lại pipeline**
- ✅ **Không quá 1 đồ hoạ hiển thị cùng lúc**; đồ hoạ và cutaway không bao giờ chồng nhau; đồ hoạ mới cách đồ hoạ cũ ≥ **500ms**
- ✅ Đồ hoạ không che mặt người nói và **không lấn vào vùng caption**
- ✅ Danh sách bung dần: từng mục chỉ hiện khi câu nói tới mục đó
- ❌ Chưa cần Lower-third (chuyển sang NICE TO HAVE)
- ❌ Chưa cần Trích dẫn, Intro/Outro, Thanh chương mục
- ❌ Chưa cần người dùng tự tạo loại đồ hoạ mới bằng giao diện

**Edge cases:**
| Tình huống | Xử lý |
|---|---|
| Project không có `frame.md` | Dùng bộ mặc định trung tính, báo rõ đang chạy không có nhận diện thương hiệu |
| `frame.md` có nhưng thiếu mục "Luật kiểm được" | Cảnh báo rõ, chạy tiếp với bộ luật mặc định; **tiêu chí Done về luật coi như chưa nghiệm thu được** |
| Quá nhiều điểm đề xuất (trên 20 mục cho video 5 phút) | Tự lọc giữ mục quan trọng nhất theo bảng ưu tiên, báo số mục đã lược bỏ |
| Hai đồ hoạ trùng thời điểm | Giữ mục ưu tiên cao hơn theo bảng, dời hoặc bỏ mục còn lại |
| Đồ hoạ trùng thời điểm với cutaway | Giữ đồ hoạ, dời cutaway |
| Chữ trong card quá dài, tràn khung | Tự thu cỡ chữ trong giới hạn; quá giới hạn thì cắt bớt và báo |
| Người dùng bỏ hết mọi mục | Video vẫn dựng bình thường, chỉ không có đồ hoạ |
| Đoạn thoại kích hoạt bị cắt ở Feature 1 | Mục đồ hoạ đó tự bị loại khỏi kế hoạch (neo ID biến mất), báo rõ trong danh sách "mục cần duyệt lại" |

---

### 🟠 NICE TO HAVE (sau này thêm)

- [ ] 📝 Draft · **[MGX-02] Lower-third** — thanh tên + chức danh trượt vào góc dưới, dùng khi video có khách mời
- [ ] 📝 Draft · **[RND-02] Đổi khung chéo ngang↔dọc** — xuất bản dọc từ nguồn quay ngang, có bám mặt người nói tự động và phóng to chữ cho khung dọc
- [ ] 📝 Draft · **[INF-01] Mở lên video 15 phút** — khi nâng cấp máy khỏi M1/8GB

---

## ④ Tech Stack

| Layer | Tech | Lý do chọn |
|---|---|---|
| Đạo diễn / điều phối | **Claude Code (Cowork)** | Ra lệnh bằng tiếng Việt, không cần dựng UI riêng cho bản test |
| Dựng & render | **HyperFrames** (HTML + GSAP) | Một hệ lo trọn: timeline qua `data-*`, nhập/trim video, caption nhấn theo từng từ, Variables đổi nội dung không cần render lại, render tất định, xuất nhiều tỉ lệ khung từ một project |
| Trang duyệt | **`review.py` — server duyệt cục bộ** (Flask hoặc `http.server`, ~120 dòng) | Trình duyệt **không ghi đè được file trên đĩa** và **chặn `fetch()` file cục bộ qua `file://`**. Server là cách duy nhất để trang duyệt vừa ghi được quyết định, vừa phát được video/audio thật, vừa tải theo đoạn |
| Transcript | **ElevenLabs Scribe API** | Mạnh nhất ở tiếng Việt, có timestamp cấp từ — điều kiện bắt buộc cho karaoke caption. ~$0.006/phút |
| Sinh ảnh cutaway | **Gemini API** | Sinh ảnh minh hoạ khi `assets/` không có hình phù hợp. Có trần cứng 25 ảnh/video |
| Dò khung mặt (1 lần) | **OpenCV** | Tính vùng zoom an toàn lúc khởi tạo project. Không phải tracking — chỉ 1 khung hình, ~15 dòng |
| Xử lý video cấp thấp | **ffmpeg** | Tách audio, chuẩn hoá fps, nối đoạn không mã hoá lại, tương quan chéo kiểm đồng bộ |
| Cấu hình thương hiệu | **`frame.md`** (cơ chế sẵn có của HyperFrames) | Frontmatter máy đọc (hex, phông, độ đậm) + mục **"Luật kiểm được"** + phần văn bản mô tả ý định |
| Cấu hình cắt | **`cut_config.json`** + **`filler_words.txt`** | Mọi ngưỡng cắt và danh sách từ đệm nằm ngoài code, sửa được sau mỗi video |
| Máy chạy | **MacBook Pro M1 / 8GB RAM / macOS** | Máy hiện có của người dùng — là ràng buộc thiết kế, không phải lựa chọn |

> **Ghi chú kiến trúc:** Remotion đã bị loại khỏi thiết kế. HyperFrames đã bao trọn timeline, trim, caption và render — giữ cả hai đồng nghĩa với duy trì hai hệ timeline, hai bộ render và một cầu nối giữa chúng.

---

## ⑤ Integration Points

### Server duyệt cục bộ (`review.py`)

```
python review.py cut         → http://127.0.0.1:7788/cut
python review.py cutaway     → http://127.0.0.1:7788/cutaway
python review.py storyboard  → http://127.0.0.1:7788/storyboard
```

1. Lệnh chạy → server bật, tự mở trình duyệt tới đúng trang
2. Trang nạp JSON qua `GET /api/plan` — không vướng CORS vì đã là `http://`
3. Người dùng duyệt, bấm **"Xuất quyết định"** → `POST /api/plan` → **server ghi đè file thật trên đĩa**
4. Trang hiện xác nhận: *"Đã lưu · 14 mục giữ · 6 mục bỏ · 14:32:07"*, đồng thời ghi 1 dòng vào `stats.jsonl`
5. Server tự tắt sau khi lưu, hoặc `Ctrl+C`

Ràng buộc bắt buộc:
- Chỉ nghe **`127.0.0.1`**, không nghe ra mạng ngoài
- Chỉ phục vụ file **trong thư mục project**, không đi ngược lên thư mục cha
- Cổng 7788 bị chiếm → tự nhảy cổng khác, in ra URL mới
- **Tự lưu nháp mỗi 10 giây** — đóng nhầm tab hoặc server chết thì mở lại vẫn nguyên trạng thái duyệt
- Phục vụ video/audio qua **HTTP range request** — chỉ tải đoạn đang xem

❌ **Không xử lý:** truy cập từ máy khác; xác thực người dùng (chạy local 1 người)

### ElevenLabs Scribe (transcript)
1. Tách audio từ video nguồn bằng ffmpeg → file audio nén
2. Gửi audio lên ElevenLabs Scribe API, yêu cầu timestamp cấp từ, ngôn ngữ tiếng Việt
3. Nhận về JSON transcript có timestamp từng từ
4. **Gán ID bất biến cho từng từ** (`w0001`, `w0002`…) trước khi lưu
5. Lưu vào project dưới dạng file sửa tay được — người dùng chữa chữ sai rồi chạy tiếp

❌ **Không xử lý:** phân tách nhiều người nói (diarization); tự thử lại vô hạn khi API lỗi (dừng và báo sau 3 lần thử)

### Gemini API (sinh ảnh cutaway)
1. Claude soạn mô tả ảnh từ câu thoại tại đoạn cần minh hoạ
2. **Kiểm hạn mức trước khi gọi**: còn lượt trong 25 ảnh/video và 3 lần/mục không? Hết → dừng, báo, không gọi
3. Gọi Gemini API sinh ảnh theo tỉ lệ khung của video
4. Lưu ảnh vào folder riêng (tách khỏi `assets/` người dùng), ghi nguồn "AI sinh" vào `cutaway_plan.json`
5. Cộng bộ đếm, cập nhật hiển thị `Đã dùng n/25 · ước tính … đ` trên trang duyệt
6. Ảnh chỉ vào video sau khi được duyệt trên storyboard

❌ **Không xử lý:** sinh video b-roll; tự sinh lại hàng loạt khi người dùng không ưng (chỉ sinh lại theo từng mục được yêu cầu, tối đa 3 lần/mục)

### HyperFrames CLI
1. Tạo và kiểm tra tính hợp lệ của project
2. Xem trước tại chỗ qua HyperFrames Studio
3. Render theo khối **20–40 giây, ranh giới trượt tới điểm an toàn**, xuất MP4
4. Đọc `frame.md` để áp nhận diện thương hiệu
5. Variables: đổi nội dung không render lại — **mọi thay đổi ghi ngược về plan JSON ngay lúc sửa**

❌ **Không xử lý:** render trên cloud ở giai đoạn MVP

### Quản lý khoá API
1. Khoá ElevenLabs và Gemini lưu trong file `.env` tại thư mục project
2. `.env` nằm trong `.gitignore`, không bao giờ commit
3. Thiếu khoá → báo rõ thiếu khoá nào, không chạy tiếp

---

## ⑥ Kiến trúc dữ liệu & Trạng thái

> Mục này là nền tảng của cả hệ thống. Đọc trước khi implement bất kỳ feature nào.

### 6.1 Luồng phụ thuộc

```
video gốc
   └→ transcript (có ID từ)
        └→ cut_plan.json
             └→ timeline đã cắt
                  ├→ caption
                  ├→ overlay_plan.json
                  └→ cutaway_plan.json
                       └→ render
```

Một chiều. Giai đoạn nào đổi thì **mọi giai đoạn phía sau bị đánh dấu bẩn**.

### 6.2 Neo vào ID của từ, không neo vào timestamp

Mọi kế hoạch trỏ vào **ID từ**, không trỏ vào giây:

```json
{ "id": "ov_007",
  "anchor_start": "w0412",
  "anchor_end": "w0429",
  "loai": "con_so_nhay",
  "noi_dung": "3 bước",
  "cau_kich_hoat": "quy trình này có ba bước" }
```

Timestamp là thứ **tính ra được** từ ID, không phải thứ lưu cứng. Nhờ đó: sửa transcript, cắt lại, timeline dịch bao nhiêu cũng được — mục `ov_007` vẫn bám đúng câu nói đó, **toàn bộ công duyệt được giữ nguyên, tự động**.

*Không có cơ chế này thì lời hứa "sửa transcript không mất công đã duyệt ở bước khác" là lời hứa suông.*

### 6.3 `project.json` — bảng trạng thái

Mỗi lần chạy, hệ thống **băm đầu vào của từng giai đoạn** và so với lần trước. Khác → đánh dấu bẩn, lan xuống toàn bộ phía sau.

| Giai đoạn | Đầu vào | Mã băm đầu vào | Trạng thái | Duyệt lúc |
|---|---|---|---|---|
| transcript | video gốc | `a3f9…` | sạch | — |
| cut_plan | transcript | `7c21…` | **đã duyệt** | 14:32 16/08 |
| overlay_plan | cut_plan | `9b04…` | **BẨN** ⚠ | 15:10 16/08 |
| render | tất cả | — | chặn | — |

Ra lệnh render khi còn giai đoạn bẩn → **chặn lại, in đúng bảng này ra**.

### 6.4 Ba mức sửa transcript

| Mức | Anh sửa gì | Ảnh hưởng | Việc phải làm lại |
|---|---|---|---|
| **1** | Sửa chính tả, **không đổi số từ** ("phiếu"→"phễu") | Chỉ chữ hiển thị đổi | Dựng lại lớp caption. **Cut / overlay / cutaway giữ nguyên duyệt.** Dưới 1 phút |
| **2** | Thêm / bớt / tách từ | ID dịch, một số neo mất | Tính lại `cut_plan`. Mục còn đủ neo → **giữ nguyên duyệt**. Mục mất neo → hiện **danh sách ngắn "3 mục cần duyệt lại"**, chỉ duyệt 3 mục đó |
| **3** | Chạy lại transcript từ đầu | Toàn bộ ID mới | Bẩn hết. **Hỏi xác nhận rõ ràng:** *"Sẽ mất 18 mục đã duyệt. Tiếp tục?"* |

Luật cốt lõi của mức 2: **phải chỉ ra đích danh mục nào cần duyệt lại**. Bắt duyệt lại cả 18 mục vì 3 mục lệch là cách nhanh nhất giết mục tiêu "thời gian ngồi làm dưới 20 phút/video".

### 6.5 Một chủ duy nhất cho mỗi loại dữ liệu

| Dữ liệu | Chủ duy nhất | Bản chiếu |
|---|---|---|
| Điểm cắt | `cut_plan.json` | — |
| Nội dung đồ hoạ | `overlay_plan.json` | Variables của HyperFrames |
| Cutaway | `cutaway_plan.json` | — |
| Style caption | file cấu hình style | — |

Quy tắc: **mọi sửa qua Variables được ghi ngược về `overlay_plan.json` ngay lúc sửa.** Trước mọi lần render, chạy bước kiểm lệch: Variables ≠ plan → dừng, hiện 2 bản, hỏi giữ bản nào.

*Không có quy tắc này, kịch bản mất dữ liệu gần như chắc chắn xảy ra: sửa nhanh qua Variables hôm nay → sửa transcript hôm sau → hệ thống dựng lại từ plan → chữ âm thầm quay về bản cũ.*

### 6.6 Thống kê quyết định — `stats.jsonl`

Mỗi lần bấm "Xuất quyết định", server ghi 1 dòng: tổng số đề xuất, số bị bác, **tách theo 3 tầng phát hiện**. Đây là nguồn dữ liệu cho chỉ số "tỉ lệ bác bỏ" ở mục ⑩ — không có nó thì chỉ số đó không đo được.

---

## ⑦ Non-Functional Requirements

**Hiệu năng** *(chuẩn theo M1 / 8GB RAM, video ≤ 5 phút, 1080p)*

| Chỉ tiêu | Ngưỡng |
|---|---|
| Transcript (ElevenLabs Scribe) | < 90 giây |
| Đề xuất cắt + trang duyệt | < 2 phút |
| Dựng storyboard động | < 3 phút |
| **Render lại 1 đoạn sau khi sửa** | **< 3 phút** |
| **Sửa chữ / màu qua Variables** | **< 15 giây, không render lại** |
| **Sửa transcript mức 1 → caption cập nhật** | **< 1 phút** |
| Bản nháp 480p toàn video | < 5 phút |
| Render bản cuối 1080p toàn video | < 35 phút |
| Nối các đoạn (ffmpeg concat) | < 30 giây |

**Ràng buộc bộ nhớ** *(điều kiện sống còn trên máy hiện tại)*

- RAM đỉnh khi render: **< 3GB**
- Ngưỡng cảnh báo RAM thấp: **< 800MB** trống
- Số tiến trình render song song: **1** — cố định, không tự tăng
- Kích thước 1 khối render: **20–40 giây**, ranh giới trượt tới điểm an toàn; tối đa **50 giây** khi không có điểm an toàn
- **Render theo khối, giải phóng bộ nhớ sau mỗi khối** — không giữ frame trong RAM, ghi thẳng ra đĩa; đóng và mở lại tiến trình trình duyệt sau mỗi khối để cắt rò rỉ bộ nhớ
- **Dừng và chạy tiếp được** — render đứt thì khối đã xong vẫn nguyên, chạy lại chỉ làm phần thiếu
- **Storyboard phải nhẹ** — server phục vụ theo HTTP range, chỉ tải đoạn đang xem

**Dung lượng ổ đĩa**

- Kiểm tra dung lượng trống **trước khi** bắt đầu render, báo trước nếu không đủ
- Xoá file tạm của mỗi khối **ngay sau khi** khối đó nối xong
- Ước tính file trung gian: 3–8GB cho video 5 phút 1080p

**Bảo mật & dữ liệu**

- Khoá API lưu trong `.env`, không commit lên git
- **File video gốc không rời máy** — chỉ audio đã tách được gửi lên ElevenLabs
- Server duyệt chỉ nghe `127.0.0.1`, chỉ phục vụ file trong thư mục project
- Toàn bộ file trung gian nằm trong folder project; xoá project là sạch

**Xử lý đồng thời**

- 1 video/lần. Không chạy song song nhiều video trên máy 8GB

**Chặn quá tải**

- Video trên 5 phút → cảnh báo trước, hỏi xác nhận, không âm thầm chạy rồi treo máy
- RAM trống tụt dưới 800MB → tạm dừng render, báo người dùng đóng bớt ứng dụng, giữ nguyên tiến độ
- Chạm trần 25 ảnh Gemini/video → dừng gọi API, báo rõ

---

## ⑧ Edge Cases & Error States

> Bảng tổng hợp các tình huống xuyên suốt hệ thống. Edge case riêng của từng tính năng nằm trong mục ③.

| Tình huống | Hành vi mong muốn |
|---|---|
| File video hỏng / codec lạ | Báo rõ tên codec không đọc được, dừng sạch, không treo |
| Video dài hơn 5 phút | Cảnh báo vượt phạm vi MVP, hỏi xác nhận trước khi chạy |
| Video có fps lạ (25 / 29.97 / biến thiên) | Chuẩn hoá về 30fps, báo rõ đã chuyển đổi |
| Audio lệch pha từ file gốc | Phát hiện và báo trước khi dựng |
| Transcript sai chữ tiếng Việt | Xử lý theo **3 mức** ở mục 6.4 — chỉ làm lại phần thật sự bị ảnh hưởng |
| Ra lệnh render khi còn giai đoạn bẩn | **Chặn, in bảng `project.json`**, chỉ rõ giai đoạn nào cần duyệt lại |
| Variables và plan JSON lệch nhau | Dừng trước render, hiện 2 bản, hỏi giữ bản nào |
| API ElevenLabs lỗi / hết quota | Thử lại tối đa 3 lần, sau đó dừng và báo rõ, không chạy tiếp với transcript rỗng |
| API Gemini lỗi / hết quota | Đánh dấu mục "thiếu hình", vẫn dựng được phần còn lại |
| Chạm trần 25 ảnh / 3 lần sinh lại | Dừng gọi API, báo số lượt đã dùng, gợi ý bỏ ảnh vào `assets/` |
| Thiếu khoá API trong `.env` | Báo rõ thiếu khoá nào, dừng trước khi tốn công xử lý |
| Cổng server duyệt bị chiếm | Tự nhảy cổng khác, in URL mới |
| Đóng tab / server chết giữa lúc duyệt | Bản nháp tự lưu mỗi 10 giây, mở lại nguyên trạng thái |
| Mất mạng giữa chừng | Bước cần mạng thì dừng và giữ tiến độ; bước xử lý local vẫn chạy tiếp bình thường |
| RAM trống dưới 800MB | Tạm dừng render, báo đóng bớt ứng dụng, giữ nguyên tiến độ |
| Hết dung lượng ổ giữa lúc render | Dừng sạch, báo còn thiếu bao nhiêu GB, không để lại file hỏng |
| Render đứt (hết pin / tắt máy) | Chạy lại chỉ làm tiếp phần còn thiếu |
| Không tìm được điểm cắt khối an toàn | Kéo dài khối tới 50 giây, báo rõ; không cắt vào giữa chuyển động |
| Không có `frame.md` | Dùng bộ mặc định trung tính, báo rõ đang chạy không có nhận diện thương hiệu |
| `frame.md` thiếu mục "Luật kiểm được" | Cảnh báo, chạy với bộ luật mặc định, đánh dấu tiêu chí đó chưa nghiệm thu được |
| Dò khung mặt thất bại | Hạ trần zoom về 104% toàn video, báo rõ |
| Font thiếu trên máy | Dùng font dự phòng đã kiểm chứng dấu tiếng Việt, báo rõ — không âm thầm dựng bản vỡ dấu |
| Người dùng bỏ hết mọi đề xuất | Video vẫn dựng được, chỉ thiếu lớp tương ứng |

---

## ⑨ Bộ kiểm nghiệm thu

> Chạy bằng **1 lệnh: `make check`**. Tổng khoảng 400 dòng Python. Đây là thứ biến PRD từ bản mô tả mong muốn thành hợp đồng nghiệm thu được.

| Script | Kiểm gì | Đạt khi | Phục vụ tiêu chí |
|---|---|---|---|
| `check_wer.py` | Độ chính xác transcript so với `tests/golden_transcript.txt` (3 phút gõ tay 1 lần) | **WER ≤ 10%** | [CUT] |
| `check_cut_coverage.py` | Mỗi điểm cắt đã áp dụng có đúng 1 mục che trong ±100ms | **100%**, in `42/42 · 0 điểm trần` | [JMP] |
| `check_av_sync.py` | Tương quan chéo audio đầu ra vs audio footage đã cắt tại 5 mốc 0/25/50/75/100% | **cả 5 mốc ≤ 40ms** | [RND] |
| `check_caption_timing.py` | Headless browser: 20 từ ngẫu nhiên, tại `t+80ms` đọc DOM xác nhận đúng từ đang sáng | **20/20** | [CAP] |
| `check_frame_rules.py` | Quét CSS/HTML đồ hoạ đã dựng theo mục "Luật kiểm được" của `frame.md` | **100% luật đạt** | [MGX] |
| `check_storyboard_fidelity.py` | So ảnh storyboard vs MP4 cuối tại 3 mốc có đồ hoạ | **khác biệt < 2% điểm ảnh**, cả 3 mốc | [MGX] |
| `check_block_boundary.py` | Ranh giới khối render vs timeline chuyển động | **0 va chạm** | [RND] |
| `check_layout.py` | Toạ độ đồ hoạ/cutaway vs vùng cấm caption | **0 mục lấn** | [CAP] |
| `check_variables_sync.py` | Variables vs `overlay_plan.json` | **không lệch** | [RND], [MGX] |

**Mẫu "Luật kiểm được" bắt buộc có trong `frame.md`** *(5–8 dòng, mỗi dòng là một luật máy kiểm được)*

```
- Tối đa 2 màu trong 1 đồ hoạ (không tính trắng/đen)
- Bo góc: 12px, không dùng giá trị khác
- Không dùng gradient
- Font chữ: chỉ Be Vietnam Pro, 2 độ đậm 500 và 700
- Chữ trong card: tối đa 12 từ
- Không dùng emoji trong đồ hoạ
```

Phần văn xuôi *"nên / không nên"* trong `frame.md` vẫn giữ để Claude đọc lấy tinh thần — **nhưng nó không còn là tiêu chí Done.** Tinh thần không nghiệm thu được; luật thì có.

---

## ⑩ Success Metrics

**Tuần 1**
- Dựng xong **1 video hoàn chỉnh** từ đầu đến cuối chỉ bằng chat tiếng Việt, không mở CapCut lần nào
- Tổng thời gian: từ **cả ngày** xuống **dưới 3 tiếng**
- `make check` chạy được, tất cả script đều ra kết quả (chưa cần đạt hết)

**Tháng 1**
- Dựng được **10 video**, quy trình chạy ổn định không phải sửa code giữa chừng
- Thời gian/video xuống **dưới 90 phút**, trong đó thời gian người dùng thật sự ngồi làm (duyệt storyboard) **dưới 30 phút** — phần còn lại máy tự chạy
- **Tỉ lệ đề xuất cắt bị bác bỏ, đo từ `stats.jsonl`, tách theo tầng:** tầng 1 **< 2%** · tầng 2 **< 15%** · tầng 3 **< 40%**
- `make check` đạt **9/9** trên ít nhất 3 video liên tiếp

**Tháng 3**
- Sản lượng **8–12 video/tháng** đều đặn
- Thời gian ngồi làm **dưới 20 phút/video**
- Không còn thuê editor ngoài cho dạng video này
- Chi phí API thực tế **dưới 100.000đ/tháng**, đo từ bộ đếm Gemini và log ElevenLabs

> Giai đoạn này **chỉ đo năng suất dựng**. Chưa đo chỉ số kết quả video (lượt xem, thời gian xem trung bình).

---

## ⑪ Constraints & Assumptions

**Giới hạn:**

- **Budget:** Dưới **100.000đ/tháng** cho API, tính theo 10 video × 5 phút — ElevenLabs Scribe ~8.000đ, Gemini sinh ảnh ~30.000–80.000đ. **Có trần cứng thi hành trong code**: 25 ảnh/video, 3 lần sinh lại/mục
- **Timeline:** Chưa chốt mốc cứng — ưu tiên có bản chạy được đầu-cuối trước, tối ưu sau
- **Team size:** 1 người + Claude Code
- **Tech constraints:**
  - MacBook Pro **M1 / 8GB RAM**, RAM trống thực tế thường dưới 2GB → mọi thiết kế phải chạy được trong điều kiện chật
  - MVP giới hạn video **dưới 5 phút**
  - Chạy hoàn toàn local, không có hạ tầng cloud
  - Không có UI riêng — mọi tương tác qua chat Claude Code và các trang duyệt phục vụ bởi server cục bộ
  - **Trình duyệt không ghi được file đĩa và chặn `fetch()` qua `file://`** — đây là ràng buộc kỹ thuật cứng, là lý do tồn tại của `review.py`

**Assumptions (giả định):**

- Video quay bằng **1 máy, 1 góc cố định, 1 người nói duy nhất** — giả định này là điều kiện để dò khung mặt 1 lần thay vì bám mặt liên tục
- **Chất lượng audio đầu vào tạm ổn** (có mic, không quá ồn) — PRD này **không có tính năng xử lý âm thanh**: không khử ồn, không chuẩn hoá âm lượng, không nhạc nền
- Mỗi video là **1 file quay liền mạch**, không phải ghép nhiều file rời
- Người dùng quay **tiếng Việt, có xen thuật ngữ tiếng Anh**
- **Người dùng chấp nhận đổi thói quen quay**: nói **"cắt cắt"** khi cần thu lại. Đây là giả định về hành vi — nếu không giữ được thói quen này thì tầng 1 mất tác dụng và tỉ lệ bác bỏ tăng
- **HyperFrames chạy ổn định trên macOS M1** — cần xác minh sớm, đây là **giả định rủi ro cao nhất của dự án**
- **HyperFrames cho phép đọc/ghi Variables từ ngoài** (qua CLI hoặc file) — điều kiện bắt buộc để thi hành quy tắc "một chủ duy nhất" ở mục 6.5. **Cần xác minh cùng lúc với giả định trên**
- Người dùng biết đọc code và chạy terminal, không cần giao diện thân thiện cho người không kỹ thuật

---

## Changelog

| Ngày | Thay đổi | Người cập nhật |
|---|---|---|
| 15/08/2026 | v1 — draft đầu tiên, dựng qua phỏng vấn | Phùng Đáp |
| 16/08/2026 | v2 — review theo góc nhìn senior PM. **(1)** Chốt tiêu chí phát hiện định lượng cho Feature 1: bậc khoảng lặng 600/300/400ms, từ đệm chia nhóm A/B, 3 tầng phát hiện nói vấp. **(2)** Thay cơ chế "ghi đè JSON từ trang HTML" bằng **server duyệt cục bộ `review.py`** — trình duyệt không ghi được file đĩa và chặn `fetch()` qua `file://`. **(3)** Thêm mục ⑥ Kiến trúc dữ liệu & Trạng thái: **neo ID từ** thay timestamp, `project.json` theo dõi bẩn/sạch, 3 mức sửa transcript, quy tắc một chủ duy nhất. **(4)** Thay 7 tiêu chí Done không kiểm được bằng script đo được; thêm mục ⑨ Bộ kiểm nghiệm thu (9 script, `make check`). **(5)** Gỡ 5 xung đột tính năng: ranh giới khối render trượt tới điểm an toàn, Variables ghi ngược về plan, bảng thứ tự lớp + zoom chỉ áp lớp video, bảng ưu tiên cutaway/đồ hoạ, trần cứng ngân sách Gemini. Vùng caption đổi thành vùng cấm (caption đứng yên, đồ hoạ né) | Phùng Đáp + Claude |

# MASTER PROMPT — tái hiện 1 Reel bằng code (low poly)

Khung chung cho mọi video. Agent `prompt` copy khung này vào `channels/<handle>/prompts/<id>.md`, điền đủ mọi mục cho video cụ thể, và tinh chỉnh chính file này khi rút ra bài học mới.

---

## 0. Tóm tắt
- Nguồn: <url> · kênh @<handle> · <view> view · <thời lượng>s
- Câu chuyện 1 câu: …
- Vì sao video này viral (hook / cảm xúc / thông tin): …

## 1. Ràng buộc kỹ thuật
- Khung 1080×1920, 30fps, thời lượng <t>s (khớp gốc ±0.2s).
- Safe zone: chữ và chi tiết quan trọng nằm trong y ∈ [250, 1500], x ∈ [60, 1020].
- Trang theo hợp đồng `window.REEL` (xem brief coder); mọi chuyển động là hàm của t.
- Audio: voiceover (giọng edge-tts: …, tốc độ …) + SFX theo cue. Nhịp beat chính: <các mốc giây>.
- Lời thoại (nguyên văn, theo beat): …
- SFX cue: <t>s whoosh · <t>s pop · …

## 2. Câu chuyện
- Hook (0–2s): …
- Diễn biến: …
- Payoff: …
- CTA / kết: …

## 3. Timeline từng beat
| # | t0–t1 (s) | Cảnh / vật thể (vị trí px) | Chuyển động (từ → đến, easing) | Chữ trên màn hình (nguyên văn · font · cỡ · màu · vị trí) | Âm thanh / nhịp |
|---|-----------|----------------------------|-------------------------------|-----------------------------------------------------------|-----------------|
| 1 | 0.00–1.20 | … | … | … | … |

Chuyển cảnh giữa các beat: <cut / whip / zoom / morph …>.

## 4. Hướng visual (cho styler)
- Bảng màu (hex): nền …, chính …, phụ …, nhấn …, chữ …
- Low poly: mức chi tiết …, flat shading, vật thể chính dựng từ …
- Ánh sáng: key … (hướng, màu), fill …, bóng …
- Camera: góc …, chuyển động …
- Mood / tham chiếu: …
- Giữ lại từ gốc: … · Được phép khác gốc: …
- **Điện ảnh (BẮT BUỘC, user: "dramatic và cinematic là key")**: shot list từng beat gồm cỡ cảnh (toàn/trung/cận/đặc tả), góc máy (thấp/cao/dutch/qua vai) và chuyển động camera, kèm lý do; bối cảnh từng cảnh (không gian, đạo cụ kể chuyện, nguồn sáng); biểu cảm và body language nhân vật theo beat; ánh sáng và màu theo cảm xúc; khoảnh khắc payoff.
- **Chi tiết vật liệu (BẮT BUỘC)**: mỗi vật chính ghi chất liệu, độ bóng (roughness/metalness), bóng đổ và phản xạ.

## 4b. Chuyển cảnh & effect (BẮT BUỘC — user yêu cầu mọi video có chuyển cảnh phù hợp, effect hợp lý)
| Mốc (s) | Cảnh A → B / khoảnh khắc | Gốc làm gì | Đề xuất chuyển cảnh / effect (có lý do) | SFX |
|---------|--------------------------|-----------|------------------------------------------|-----|
| … | … | cắt cứng / dissolve / zoom | vd match cut lịch → lịch tường; pop + vòng sóng khi biển cấm hiện | whoosh / thud |
Ghi đủ: mọi điểm chuyển cảnh + mọi khoảnh khắc nhấn (xuất hiện đạo cụ, va chạm, đổi số, payoff). Gốc chỉ cắt cứng vẫn phải đề xuất cách nâng nhịp cắt.

## 5. Tiêu chí giống gốc (manager dùng để QA)
1. Hook xuất hiện trước 0.5s và đọc được trên điện thoại.
2. …

## 6. Lỗi thường gặp (bổ sung dần)
- Chữ quá nhỏ: chữ chính ≥ 64px, phụ ≥ 40px.
- Beat cuối hụt: giữ khung kết ≥ 0.8s để người xem kịp đọc CTA.
- Vật thể đứng im > 1.5s trông như video bị đơ — luôn có chuyển động nhẹ.
- Thiếu chuyển cảnh/effect (user đã phản hồi): dissolve/cắt trơn giữa mọi cảnh và không có effect nhấn = bị trả về. Luôn điền mục 4b.
- Hình phẳng, thiếu điện ảnh (user đã phản hồi): camera 1 góc chính diện, nhân vật trên nền trống, mặt không biểu cảm, vật không bóng đổ hoặc không độ bóng đều bị trả về.
- Biến dạng cơ thể (bụng bầu, phình to…) là biến dạng của chính thân/áo liền khối, không phải vật thể dán vào; ghi rõ trạng thái sau sự kiện (vd sau sinh bụng phẳng) để không sót vật thể.

## 7. Kịch bản tiếng Việt (Bước 4 — viết ở `prompts/<id>.vi.md`)
- 1 giọng duy nhất `vi-VN-NamMinhNeural`, rate cố định cho cả kênh (+8%).
- Hook là câu hỏi TRỌN Ý ("… thì sao?"), khớp chữ hook trên màn hình bản VI.
- Tránh dấu "?" / dấu phẩy thừa giữa câu: NamMinh ngắt dài ở đó → dễ vượt khoảng lặng 1s.
- Khoảng lặng ≤ 1.0s, câu đầu ≤ 0.5s; video loop thì tính cả khoảng lặng từ câu cuối vòng về câu đầu, và câu cuối nên nối ý được về câu đầu.
- Nhạc tắt ở đoạn kết → lời đọc trên nền đó, không duck; đặt từ khoá ("im bặt"…) rơi đúng khoảnh khắc.
- Đơn vị kiểu quen thuộc: "4h 15p", "3 ngày 2h", số nghìn có dấu chấm "8.760", thập phân dấu phẩy "1,4 L"; số trong ô cố định (tabular-nums) để không nhảy chỗ.
- Chữ kết cảm thán dùng từ Việt tự nhiên ("Phù." thay "Ahh.").

---
## Nhật ký tinh chỉnh
- 2026-10-21 · khởi tạo khung.
- 2026-10-21 · thêm mục 4b chuyển cảnh & effect bắt buộc (feedback user video #1), quy tắc biến dạng cơ thể liền thân (feedback user video #2).
- 2026-10-21 · thêm chuẩn điện ảnh (góc quay, mật độ chi tiết, bối cảnh, biểu cảm, dramatic) và chi tiết vật liệu bắt buộc (feedback user cho styler).

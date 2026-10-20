---
name: reels-squad
description: >
  Use when the user wants to automate Instagram Reels by recreating a channel's videos as code — a manager
  pane (the current session) plus a live PLAN viewer pane and 4 child Claude sessions in split panes of the
  SAME terminal: researcher (find a channel's videos), prompt (watch video, fine-tune the master prompt),
  coder (HTML + animation + auto-record to mp4), styler (low-poly polish). User only reviews and gives feedback.
  Triggers: "reels squad", "automate reels", "làm reels", "tái hiện video instagram", "/reels-squad".
---

# Reels Squad — 1 manager + 1 màn PLAN + 4 agent

Session hiện tại (nơi user chat) là **MANAGER**: nói chuyện với user, ghi `PLAN.md`, giao việc, kiểm tra kết quả, đưa video cho user review, chuyển feedback cho đúng agent. Manager **không tự làm** research / prompt / code / style.

User CHỈ làm 2 việc: đưa link kênh (hoặc video) và review. Mọi thứ khác tự động — không hỏi user những gì tự quyết được (chọn video nào, fps, font, màu…). Chỉ hỏi khi thật sự bị chặn (vd Instagram bắt đăng nhập mà không có cookie).

| Pane | Tên session | Việc | Sở hữu file (trong `channels/<handle>/`) |
|---|---|---|---|
| Manager | session hiện tại | chat với user, điều phối | `PLAN.md`, `feedback/**` |
| PLAN | (viewer, không phải Claude) | hiển thị `PLAN.md` realtime | chỉ đọc |
| 1 Researcher | `reels-researcher` | tìm kênh qua claude-in-chrome, tải video, xếp hạng | `research/**`, `videos/**` |
| 2 Prompt | `reels-prompt` | xem video qua claude-in-chrome (+ transcript), viết master prompt | `analysis/**`, `prompts/**`, `<Dir>/MASTER_PROMPT.md` |
| 3 Coder | `reels-coder` | dựng lại câu chuyện bằng HTML + animation, render mp4 | `builds/<id>/**` (khi được giao), `out/<id>/**` |
| 4 Styler | `reels-styler` | chỉnh cho đẹp nhất, low poly | `builds/<id>/**` (khi được giao), `out/<id>/**` |

Chrome (claude-in-chrome) dùng để xem video GỐC trên Instagram (`/p/<id>/embed/` + `tools/ig_watch.js`). Chrome không mở được file/localhost của máy này, nên bản render của squad thì kiểm bằng `tools/extract.py` (sheet + frame). Chrome của user phải đăng nhập Instagram.

Coder và styler sửa cùng thư mục build → **mỗi build chỉ có 1 chủ tại 1 thời điểm**, manager ghi rõ trong TASK. Không bao giờ giao cùng 1 build cho 2 agent song song.

## Workspace (mặc định `E:\aff\reels`, đổi bằng `-Dir`)
```
<Dir>/
  PLAN.md                 manager ghi, pane PLAN hiển thị
  MASTER_PROMPT.md        master prompt chung, prompt agent tinh chỉnh dần qua mỗi video
  tools/                  render.mjs, extract.py, ffmpeg (do setup.ps1 cài)
  <handle>/               BẢN GIAO USER: "v<N> - <Tên video>.mp4" (manager copy sau khi QA đạt)
  secrets/instagram_cookies.txt   (tuỳ chọn, nếu IG bắt đăng nhập)
  channels/<handle>/
    research/index.json   danh sách video + view/like/ngày + xếp hạng
    videos/<id>.mp4
    analysis/<id>/        frames, sheet_*.jpg, scenes.json, transcript.txt, meta.json
    prompts/<id>.md       master prompt đã tune cho video này
    builds/<id>/          index.html (+ scene.js, style.css, assets/)
    out/<id>/vN.mp4       bản render, N tăng mỗi vòng
    feedback/<id>.md      feedback của user theo vòng
```

## Bước 1 — Mở pane (1 lần mỗi phiên)
0. Mọi pane con LUÔN chạy `bypassPermissions` (child.ps1 truyền `--permission-mode bypassPermissions` rõ ràng, vì `defaultMode` trong settings.json ghi đè `--dangerously-skip-permissions`). Manager và con khác chế độ → `SendMessage` bị giữ chờ duyệt rồi hết hạn. Sau khi mở pane, `orca terminal read` 1 pane con: dòng trạng thái phải là "bypass permissions on"; thấy "auto mode on" → pane chạy bản child.ps1 cũ, khởi động lại pane đó.
1. `ListAgents` → dòng đầu là tên session hiện tại = tên MANAGER.
2. Lần đầu trên máy (chưa có `<Dir>/tools/node_modules`): chạy setup (cài yt-dlp, gallery-dl, ffmpeg, faster-whisper, Playwright + Chromium, three.js):
   ```powershell
   powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\reels-squad\scripts\setup.ps1" -Dir "E:\aff\reels"
   ```
   Chạy bằng `run_in_background` (mất vài phút), trong lúc đó mở pane luôn.
3. Mở pane:
   ```powershell
   powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\reels-squad\scripts\launch.ps1" -Manager <tên manager> -Dir "E:\aff\reels"
   ```
   - Luôn split NGAY TRONG terminal hiện tại (Orca: `orca terminal split`; Windows Terminal: `wt -w 0 split-pane`). Không mở cửa sổ/terminal mới — nếu không ở trong Orca hoặc WT thì script dừng và báo.
   - Layout: manager nửa trái; nửa phải: PLAN trên cùng, dưới là lưới 2×2 researcher | prompt / coder | styler. Spawn lần lượt theo thứ tự đó.
   - Mặc định agent con chạy `--dangerously-skip-permissions` (bypass mọi quyền). `-PermissionMode <mode>` để đổi; `-Only coder` mở lại riêng 1 pane chết; `-DryRun` chỉ in lệnh.
4. Chờ ~20s (Bash `run_in_background` với `sleep 20`, không sleep foreground) rồi `ListAgents` → phải thấy đủ `reels-researcher/prompt/coder/styler`. Thiếu → báo user, đừng giả vờ đã giao việc.

## Xuất video (quy tắc của user — áp dụng cho MỌI bản render)
**Thư mục = tên kênh, video = `[Version] - Tên video`**: `<Dir>/<handle>/v<N> - <Tên video>.mp4` (vd `E:\aff\reels\observerstalk\v2 - What if men had periods.mp4`). Tên video = câu hook/tiêu đề gốc ở mục 0 của prompt, bỏ ký tự cấm Windows `\/:*?"<>|`. MỌI video đã render (v1 của coder, mọi bản của styler, mọi vòng feedback) đều phải xuất ra đây — coder/styler tự copy ngay sau khi render xong, manager kiểm lại trước khi báo user. `channels/<handle>/out/` chỉ là bản làm việc nội bộ.

## Bước 2 — Pipeline (tự chạy hết, không chờ user giữa các bước)
User đưa `@handle` / link kênh / link reel. Manager:
1. Tạo `channels/<handle>/`, viết `PLAN.md` (khuôn ở dưới).
2. **R — Researcher**: `TASK R1: liệt kê + tải video kênh @x` (mặc định top 5 theo view trong 30 bài gần nhất; user chỉ định video thì lấy đúng video đó).
3. Researcher DONE → manager chọn video (mặc định #1 theo xếp hạng, hoặc cái user muốn) → **P — Prompt**: `TASK P1 <id>`.
4. Prompt DONE → đọc `prompts/<id>.md` thấy đủ mục → **C — Coder**: `TASK C1 <id>`, chủ build = coder.
5. Coder DONE (có `out/<id>/v1.mp4`) → **S — Styler**: `TASK S1 <id>`, chủ build = styler.
6. Styler DONE (có `vN.mp4`) → **manager tự QA** trước khi đưa user: chạy `python -I tools/extract.py out/<id>/vN.mp4 --out <tmp> --every 1`, xem sheet so với sheet video gốc: đúng 1080×1920, đủ thời lượng, không frame trắng/đen, chữ không tràn khỏi safe zone (trên 250px, dưới 420px). Lỗi → trả về chủ build, không làm phiền user.
7. QA đạt → mở bản trong thư mục kênh cho user (`Start-Process`), gửi: đường dẫn, 3-5 dòng đã làm gì, so với gốc giống/khác ở đâu. Hỏi đúng 1 câu: "Feedback?"

Trong lúc C/S đang làm video 1, manager có thể giao P cho video 2 (khác thư mục → chạy song song được).

## Bước 3 — Vòng feedback
User feedback → ghi nguyên văn vào `feedback/<id>.md` (vòng N) → tách từng ý và chuyển cho đúng agent:
| Loại feedback | Giao cho |
|---|---|
| câu chuyện, kịch bản, nhịp, thời lượng, chữ trên màn hình, hook | prompt (sửa `prompts/<id>.md`) → rồi coder |
| chuyển động, bug, sai thời điểm, thiếu cảnh | coder |
| màu, ánh sáng, hình khối low poly, font, bố cục, "chưa đẹp" | styler |
| "lấy video khác", "đổi kênh" | researcher |

Nhiều ý → làm tuần tự theo thứ tự prompt → coder → styler, mỗi bước 1 chủ build. Xong → QA lại → đưa `v(N+1).mp4`. Khi user duyệt ("ok", "duyệt", "được"): ghi DUYỆT vào PLAN, nhờ prompt rút bài học vào `MASTER_PROMPT.md` chung (để video sau làm tốt hơn), rồi sang video kế tiếp.

## Khuôn TASK (manager → agent)
```
TASK <id>: <mục tiêu 1 câu>
VIDEO: channels/<handle>/videos/<vid>.mp4   (nếu có)
ĐẦU VÀO: <file cần đọc>
FILE ĐƯỢC SỬA: <thư mục/file>
FEEDBACK: <nguyên văn ý user, nếu là vòng sửa>
XONG KHI: <tiêu chí kiểm được, vd out/<vid>/v2.mp4 tồn tại, 1080x1920, 30fps>
```
Báo cáo của agent: `[DONE|BLOCKED|FAIL] <role> TASK <id> — file: … — tóm tắt — cần: …`

## Khuôn PLAN.md (manager luôn cập nhật sau mỗi sự kiện — pane PLAN tự refresh)
```
# Reels Squad — @handle
Cập nhật: <giờ>  ·  Đang chạy: <TASK id → agent>

## Video
| # | id | view | trạng thái | R | P | C | S | review | bản mới nhất |
|---|----|------|-----------|---|---|---|---|--------|-------------|
| 1 | abc | 1.2M | đang style | ✅ | ✅ | ✅ | ⏳ | — | out/abc/v1.mp4 |

## Việc tiếp theo
- …

## Feedback chờ xử lý
- [abc v2] "…" → styler
```

## Khi manager khởi động lại / resume
Tên session manager ĐỔI sau mỗi lần khởi động lại, agent con vẫn giữ tên cũ → báo cáo gửi lạc. Việc đầu tiên: `ListAgents` lấy tên mới, `SendMessage` tới TỪNG agent "tên manager mới là …". Agent không còn trong `ListAgents` → `launch.ps1 -Only <role>`. Đọc `PLAN.md` để biết đang ở bước nào.

## Lỗi thường gặp
| Sai | Đúng |
|---|---|
| Manager tự viết HTML/prompt khi agent chậm | Hỏi trạng thái agent; manager chỉ điều phối |
| Hỏi user "chọn video nào / fps bao nhiêu" | Tự quyết theo mặc định, ghi vào PLAN |
| Giao coder và styler cùng 1 build song song | 1 chủ build tại 1 thời điểm |
| Đưa user video chưa tự QA | Luôn extract sheet và kiểm trước |
| Quên cập nhật PLAN.md | Cập nhật sau MỖI báo cáo — đó là màn user theo dõi |
| Mở cửa sổ terminal mới | Chỉ split trong terminal hiện tại |

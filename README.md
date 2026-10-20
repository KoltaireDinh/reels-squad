# reels-squad

Claude Code skill that turns an Instagram channel's Reels into code-rendered, low-poly remakes — automatically.
You chat with one **manager** session; it runs a **live PLAN pane** and **4 agents** in split panes of the same terminal:

```
┌───────────────┬─────────────────────────┐
│               │  PLAN (live PLAN.md)    │
│   MANAGER     ├────────────┬────────────┤
│  (you chat)   │ researcher │  prompt    │
│               ├────────────┼────────────┤
│               │   coder    │  styler    │
└───────────────┴────────────┴────────────┘
```

| Agent | Job |
|---|---|
| researcher | Lists a channel's reels in your logged-in Chrome (claude-in-chrome), ranks them, downloads them (yt-dlp) |
| prompt | Watches the original in Chrome (frame-accurate seek + screenshots) plus transcript/scene cuts, writes a per-video master prompt, and keeps refining `MASTER_PROMPT.md` |
| coder | Rebuilds the story as an HTML page (three.js) driven by a pure `seek(t)` and renders it frame by frame to MP4 (Playwright + ffmpeg), with TTS/SFX audio |
| styler | Polishes the build in a low-poly style (lighting, palette, transitions, effects) and re-renders |

Your only job is to review the videos and give feedback; the manager routes each point to the right agent and re-renders.
Every render is exported to `<workspace>/<channel>/v<N> - <Video title>.mp4`.

## Requirements
- Windows, [Claude Code](https://claude.com/claude-code), running inside **Orca** or **Windows Terminal** (panes are split in place; no new window is opened)
- Chrome with the Claude in Chrome extension, logged in to Instagram
- Python 3.10+, Node 18+

## Install
```powershell
git clone <this repo> "$HOME\.claude\skills\reels-squad"
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\reels-squad\scripts\setup.ps1" -Dir "D:\reels"
```
`setup.ps1` installs yt-dlp, gallery-dl, faster-whisper, edge-tts, ffmpeg, Playwright + Chromium and three.js/gsap into `<Dir>\tools`.

## Use
In Claude Code: `/reels-squad https://www.instagram.com/<channel>/` (pass `-Dir` to `launch.ps1` / `setup.ps1` if your workspace is not the default `E:\aff\reels`).

Child agents always start with `--permission-mode bypassPermissions` (explicit, so a `defaultMode` in settings.json cannot override it). Run the manager in bypass mode too, otherwise cross-session messages are held for approval.

## Layout
```
SKILL.md                  manager playbook (pipeline, task format, feedback routing, PLAN.md format)
roles/*.md                briefs for researcher / prompt / coder / styler
scripts/launch.ps1        split panes (Orca or Windows Terminal) and start the agents
scripts/child.ps1         start one agent session with its brief
scripts/plan-view.ps1     live PLAN.md viewer pane
scripts/setup.ps1         one-time workspace setup
scripts/render.mjs        deterministic HTML -> MP4 renderer (window.REEL contract)
scripts/extract.py        frames, contact sheets, scene cuts, transcript
scripts/ig_collect.js     collect reel URLs + views from a profile page (run in Chrome)
scripts/ig_fetch.py       index / download reels
scripts/ig_watch.js       frame-accurate video watcher for Chrome screenshots
scripts/vo.py             Vietnamese (or any) voiceover + word-timed subtitles, checks gaps <= 1s
templates/MASTER_PROMPT.md  starting master prompt
```

Download and remake only content you have the right to use.

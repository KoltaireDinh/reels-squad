"""Voiceover + subtitle timing for the localized (e.g. Vietnamese) version of a reel.

Usage:
    python -I tools/vo.py <script.json> --out <build>/audio/vo [--voice vi-VN-NamMinhNeural] [--rate +8%]
        [--duration 24.82] [--max-gap 1.0]

script.json: {"voice": "...", "rate": "+8%", "lines": [{"id": "l1", "t": 0.20, "text": "..."}, ...]}
  t = when the line should start (seconds in the video). Lines are spoken in order; a line that would
  overlap the previous one is pushed later and reported.

Writes to --out:
  <id>.mp3 per line, vo.wav (all lines placed at their start times, 48 kHz mono),
  subs.json  [{id, start, end, text, words:[{start, end, text}]}]  -> the build renders subtitles from this,
  report.txt  durations, gaps, overlaps, and FAIL lines when a gap between lines exceeds --max-gap
              or speech runs past --duration.
Exit code 1 when the report has FAIL lines, so the caller rewrites/retimes the script.
"""
import argparse
import asyncio
import json
import subprocess
import sys
import wave
from pathlib import Path

import site
if site.getusersitepackages() not in sys.path:
    sys.path.append(site.getusersitepackages())
import edge_tts  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
FFMPEG = str(HERE / "bin" / "ffmpeg.exe") if (HERE / "bin" / "ffmpeg.exe").exists() else "ffmpeg"
SR = 48000


async def synth(text, voice, rate, mp3):
    words = []
    with open(mp3, "wb") as f:
        async for chunk in edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary").stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s = chunk["offset"] / 1e7
                words.append({"start": s, "end": s + chunk["duration"] / 1e7, "text": chunk["text"]})
    return words


def decode(mp3):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(mp3), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def trim(x, thresh=0.01):
    """Drop leading/trailing near-silence so placement and gaps reflect actual speech."""
    idx = np.flatnonzero(np.abs(x) > thresh)
    if not len(idx):
        return x, 0.0
    a, b = max(idx[0] - int(0.02 * SR), 0), min(idx[-1] + int(0.06 * SR), len(x))
    return x[a:b], a / SR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice")
    ap.add_argument("--rate")
    ap.add_argument("--duration", type=float)
    ap.add_argument("--max-gap", type=float, default=1.0)
    a = ap.parse_args()

    spec = json.loads(Path(a.script).read_text(encoding="utf-8"))
    voice = a.voice or spec.get("voice", "vi-VN-NamMinhNeural")
    rate = a.rate or spec.get("rate", "+0%")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    subs, report, fails, cursor = [], [f"voice={voice} rate={rate}"], [], 0.0
    clips = []
    for line in spec["lines"]:
        mp3 = out / f"{line['id']}.mp3"
        words = asyncio.run(synth(line["text"], voice, rate, mp3))
        audio, lead = trim(decode(mp3))
        dur = len(audio) / SR
        start = float(line["t"])
        if start < cursor:
            report.append(f"PUSH {line['id']}: wanted {start:.2f}s, previous line ends {cursor:.2f}s")
            start = cursor + 0.05
        gap = start - cursor if subs else start
        if subs and gap > a.max_gap:
            fails.append(f"FAIL gap {gap:.2f}s before {line['id']} (max {a.max_gap}s)")
        end = start + dur
        subs.append({"id": line["id"], "start": round(start, 3), "end": round(end, 3), "text": line["text"],
                     "words": [{"start": round(start + w["start"] - lead, 3), "end": round(start + w["end"] - lead, 3),
                                "text": w["text"]} for w in words]})
        clips.append((start, audio))
        report.append(f"{line['id']}: {start:6.2f}-{end:6.2f}s ({dur:.2f}s) gap {gap:.2f}s  {line['text']}")
        cursor = end

    total = a.duration or cursor + 0.2
    if cursor > total:
        fails.append(f"FAIL speech ends {cursor:.2f}s, video is {total:.2f}s")
    mix = np.zeros(int((max(total, cursor) + 0.1) * SR), dtype=np.float32)
    for start, audio in clips:
        i = int(start * SR)
        mix[i:i + len(audio)] += audio
    with wave.open(str(out / "vo.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())

    (out / "subs.json").write_text(json.dumps(subs, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "report.txt").write_text("\n".join(report + fails), encoding="utf-8")
    sys.stdout.buffer.write(("\n".join(report + fails) + "\n").encode("utf-8"))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()

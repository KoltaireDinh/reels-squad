"""Turn a video into things an agent can "watch": frames, contact sheets, scene cuts, transcript.

Usage:
    python -I tools/extract.py <video.mp4> --out <dir> [--every 0.5] [--no-whisper] [--model small]

Writes to <dir>:
    meta.json        duration, size, fps
    frames/          one JPG every --every seconds (f_0000.50.jpg = at 0.50s)
    sheet_XX.jpg     contact sheets (4x4 grid, in time order) for a fast overview
    scenes.json      timestamps of hard cuts
    transcript.txt   timestamped speech (faster-whisper, if installed)
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ffmpeg_exe():
    local = HERE / "bin" / "ffmpeg.exe"
    return str(local) if local.exists() else "ffmpeg"


def run(args):
    return subprocess.run([ffmpeg_exe(), "-hide_banner", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


def probe(video):
    err = run(["-i", str(video)]).stderr
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    size = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", err)
    fps = re.search(r"([\d.]+) fps", err)
    return {
        "duration": int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3]) if dur else None,
        "width": int(size[1]) if size else None,
        "height": int(size[2]) if size else None,
        "fps": float(fps[1]) if fps else None,
        "has_audio": "Audio:" in err,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--every", type=float, default=0.5)
    ap.add_argument("--no-whisper", action="store_true")
    ap.add_argument("--model", default="small")
    a = ap.parse_args()

    video, out = Path(a.video), Path(a.out)
    frames = out / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    meta = probe(video)
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("meta", meta)

    rate = 1 / a.every
    run(["-y", "-i", str(video), "-vf", f"fps={rate},scale=540:-2", "-q:v", "3", str(frames / "tmp_%05d.jpg")])
    for i, f in enumerate(sorted(frames.glob("tmp_*.jpg"))):
        f.replace(frames / f"f_{i * a.every:07.2f}.jpg")
    print("frames", len(list(frames.glob("f_*.jpg"))))

    run(["-y", "-i", str(video), "-vf", f"fps={rate},scale=270:-2,tile=4x4:padding=6:color=white", "-q:v", "3", str(out / "sheet_%02d.jpg")])
    print("sheets", len(list(out.glob("sheet_*.jpg"))), f"(16 frames each, {a.every}s apart)")

    log = run(["-i", str(video), "-vf", "select='gt(scene,0.3)',showinfo", "-f", "null", "-"]).stderr
    cuts = [round(float(t), 2) for t in re.findall(r"pts_time:([\d.]+)", log)]
    (out / "scenes.json").write_text(json.dumps(cuts), encoding="utf-8")
    print("cuts", cuts)

    if meta["has_audio"] and not a.no_whisper:
        wav = out / "audio.wav"
        run(["-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
        # `python -I` drops user site-packages, where some faster-whisper deps (yaml, av) live.
        import site
        if site.getusersitepackages() not in sys.path:
            sys.path.append(site.getusersitepackages())
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            print("faster-whisper not installed; skipping transcript", file=sys.stderr)
            return
        model = WhisperModel(a.model, device="cpu", compute_type="int8")
        # Feed samples directly: faster-whisper's own decoding goes through PyAV, whose API drifts between versions.
        import wave
        import numpy as np
        with wave.open(str(wav), "rb") as w:
            samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        segs, info = model.transcribe(samples, vad_filter=True)
        lines = [f"[{s.start:6.2f} - {s.end:6.2f}] {s.text.strip()}" for s in segs]
        (out / "transcript.txt").write_text(f"lang={info.language}\n" + "\n".join(lines), encoding="utf-8")
        print("transcript", len(lines), "lines, lang", info.language)


if __name__ == "__main__":
    main()

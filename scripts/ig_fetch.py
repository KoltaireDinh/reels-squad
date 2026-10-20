"""List and download an Instagram channel's reels.

Usage:
    python -I tools/ig_fetch.py list <handle> --out channels/<handle>/research [--limit 30]
        Needs login: <workspace>/secrets/instagram_cookies.txt (Netscape cookies.txt). Without it,
        collect reel URLs from the logged-in browser instead and use `index`.
    python -I tools/ig_fetch.py index <urls.txt> --out channels/<handle>/research
        urls.txt: one reel URL per line, optionally "<url><TAB><views>" (views as shown, e.g. 1.2M).
        Fetches likes/comments/date/caption per URL (works without login) -> index.json.
    python -I tools/ig_fetch.py get <post-or-reel-url> --out channels/<handle>/videos
        Downloads the mp4 (works without login for public posts).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COOKIES = HERE.parent / "secrets" / "instagram_cookies.txt"


def auth():
    return ["--cookies", str(COOKIES)] if COOKIES.exists() else []


def ytdlp(args):
    base = [sys.executable, "-m", "yt_dlp", "--no-warnings", "--ffmpeg-location", str(HERE / "bin")]
    r = subprocess.run(base + auth() + args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[-800:])
    return r.stdout


SUFFIX = {"": 1, "k": 1e3, "n": 1e3, "m": 1e6, "tr": 1e6, "b": 1e9, "tỷ": 1e9, "ty": 1e9}


def parse_views(s):
    """Views as Instagram shows them, in English or Vietnamese locale: 12.5K, 1.2M, 60,6 N, 1,2 Tr, 1.918."""
    if not s:
        return None
    m = re.fullmatch(r"([\d.,]+)\s*([^\d\s.,]*)", s.strip())
    if not m or m[2].lower() not in SUFFIX:
        return None
    num, suffix = m[1], m[2].lower()
    if "," in num and "." in num:
        num = num.replace(".", "").replace(",", ".") if num.rfind(",") > num.rfind(".") else num.replace(",", "")
    elif "," in num:
        # "60,6 N" -> decimal comma; "1,234" without suffix -> thousands separator.
        num = num.replace(",", ".") if suffix else num.replace(",", "")
    elif "." in num and not suffix and re.fullmatch(r"\d{1,3}(\.\d{3})+", num):
        num = num.replace(".", "")  # "1.918" -> 1918
    return int(float(num) * SUFFIX[suffix])


def row(info, url, views=None):
    return {
        "id": info.get("id"), "url": info.get("webpage_url") or url,
        "views": info.get("view_count") or views, "likes": info.get("like_count"), "comments": info.get("comment_count"),
        "date": info.get("upload_date"), "duration": info.get("duration"),
        "caption": (info.get("description") or "")[:500],
    }


def write_index(out, rows):
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(rows)} reels -> {out / 'index.json'}")


def cmd_list(a):
    if not COOKIES.exists():
        raise SystemExit(f"Profile listing needs login: no {COOKIES}. Collect reel URLs in the logged-in browser, then run `index`.")
    url = f"https://www.instagram.com/{a.handle.lstrip('@')}/reels/"
    r = subprocess.run([sys.executable, "-m", "gallery_dl", "--cookies", str(COOKIES), "--simulate", "--dump-json",
                        "--range", f"1-{a.limit}", url], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        items = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise SystemExit(f"gallery-dl failed:\n{r.stderr[-800:]}")
    rows, seen = [], set()
    for item in items:
        meta = item[-1] if isinstance(item, list) and item and isinstance(item[-1], dict) else {}
        if "error" in meta:
            raise SystemExit(f"gallery-dl: {meta.get('message')} (cookies expired?)")
        code = meta.get("post_shortcode") or meta.get("shortcode")
        if not code or code in seen:
            continue
        seen.add(code)
        rows.append({
            "id": code, "url": f"https://www.instagram.com/reel/{code}/",
            "views": meta.get("video_view_count") or meta.get("view_count"), "likes": meta.get("likes"),
            "comments": meta.get("comment_count"), "date": str(meta.get("post_date") or meta.get("date") or "")[:10],
            "duration": meta.get("video_duration"), "caption": (meta.get("description") or "")[:500],
        })
    write_index(Path(a.out), rows)


def cmd_index(a):
    rows = []
    for line in Path(a.urls).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        url, _, views = line.strip().partition("\t")
        try:
            rows.append(row(json.loads(ytdlp(["-J", "--skip-download", url])), url, parse_views(views)))
        except RuntimeError as e:
            print(f"skip {url}: {e}", file=sys.stderr)
            rows.append({"id": None, "url": url, "views": parse_views(views), "error": str(e)[-200:]})
    write_index(Path(a.out), rows)


def cmd_get(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        print(ytdlp(["-f", "bv*+ba/b", "--merge-output-format", "mp4", "-o", str(out / "%(id)s.%(ext)s"),
                     "--print", "after_move:filepath", "--write-info-json", a.url]).strip())
    except RuntimeError as e:
        raise SystemExit(f"download failed: {e}\nIf this is a login error, export cookies to {COOKIES}.")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("handle"); p.add_argument("--out", required=True); p.add_argument("--limit", type=int, default=30)
    i = sub.add_parser("index"); i.add_argument("urls"); i.add_argument("--out", required=True)
    g = sub.add_parser("get"); g.add_argument("url"); g.add_argument("--out", required=True)
    a = ap.parse_args()
    {"list": cmd_list, "index": cmd_index, "get": cmd_get}[a.cmd](a)


if __name__ == "__main__":
    main()

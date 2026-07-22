#!/usr/bin/env python3
"""
Download the MP4 from a Substack video post using authenticated cookies.

Reads `Input/{slug}_video_meta.json` for the `mp4_src` URL and writes
`Input/{slug}_video.mp4`. Streams to disk (avoids Playwright's 512MB
in-memory string limit).

Usage:
  python scripts/fetch_substack_video_mp4.py <slug>
"""
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import requests


def load_cookies(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {c["name"]: c["value"] for c in raw}


def main(slug: str):
    meta = json.load(open(f"Input/{slug}_video_meta.json", encoding="utf-8"))
    mp4_url = meta["mp4_src"]
    out_path = Path(f"Input/{slug}_video.mp4")

    cookies = load_cookies(Path("cookies_substack.json"))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": meta.get("page_url", "https://substack.com/"),
        "Accept": "*/*",
    }

    print(f"Downloading {mp4_url} ...", flush=True)
    with requests.get(mp4_url, cookies=cookies, headers=headers, stream=True, timeout=180, allow_redirects=True) as r:
        if not r.ok:
            print(f"ERROR: HTTP {r.status_code}", file=sys.stderr)
            sys.exit(2)
        total = 0
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    total += len(chunk)
                    if total % (50 * 1024 * 1024) < 1024 * 1024:
                        print(f"  {total/1024/1024:.0f} MB...", flush=True)

    print(f"WROTE_MP4={out_path} ({total/1024/1024:.1f} MB)", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: fetch_substack_video_mp4.py <slug>")
        sys.exit(2)
    main(sys.argv[1])

#!/usr/bin/env python3
"""
Fix Markdown Printer output: resolve relative image/link paths against the
page's own URL, and optionally download images locally.

Markdown Printer emits `![alt](src)` using the raw HTML src attribute, so
relative paths ("/assets/fig1.png", "../img/fig.png") survive as-is and break
downstream. This script rewrites them using the "**Source:** <url>" line the
extension writes into the header.

Usage:
  python md_absolutize.py file.md [more.md ...]              # rewrite in place
  python md_absolutize.py --download-dir assets file.md      # also fetch images
  python md_absolutize.py --base https://example.com/p file.md  # explicit base
"""

import argparse
import hashlib
import mimetypes
import os
import re
import sys
import urllib.parse
import urllib.request

SOURCE_RE = re.compile(r"^\*\*Source:\*\*\s*(\S+)", re.MULTILINE)
# ![alt](target) and [text](target); avoids reference-style and empty targets
MD_LINK_RE = re.compile(r"(!?)\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(\s+\"[^\"]*\")?\s*\)")

SKIP_PREFIXES = ("http://", "https://", "data:", "mailto:", "tel:", "#", "//")


def find_base(text, override=None):
    if override:
        return override
    m = SOURCE_RE.search(text)
    return m.group(1) if m else None


def download(url, outdir, session_cache):
    if url in session_cache:
        return session_cache[url]
    os.makedirs(outdir, exist_ok=True)
    path = urllib.parse.urlparse(url).path
    name = os.path.basename(path) or "image"
    stem, ext = os.path.splitext(name)
    digest = hashlib.sha1(url.encode()).hexdigest()[:8]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            if not ext:
                ext = mimetypes.guess_extension(
                    (r.headers.get_content_type() or "")
                ) or ".img"
    except Exception as e:  # noqa: BLE001
        print(f"  ! failed {url}: {e}", file=sys.stderr)
        session_cache[url] = None
        return None
    fname = f"{stem}-{digest}{ext}"
    with open(os.path.join(outdir, fname), "wb") as f:
        f.write(data)
    session_cache[url] = fname
    return fname


def process(path, base_override=None, download_dir=None):
    with open(path, encoding="utf-8") as f:
        text = f.read()

    base = find_base(text, base_override)
    if not base:
        print(f"{path}: no base URL found (pass --base)", file=sys.stderr)
        return

    cache = {}
    stats = {"abs": 0, "dl": 0}

    def repl(m):
        bang, alt, target, title = m.groups()
        title = title or ""
        if target.startswith(SKIP_PREFIXES):
            absolute = target
        else:
            absolute = urllib.parse.urljoin(base, target)
            stats["abs"] += 1
        if bang and download_dir:
            local = download(absolute, download_dir, cache)
            if local:
                stats["dl"] += 1
                rel = os.path.join(os.path.basename(download_dir.rstrip("/")), local)
                return f"{bang}[{alt}]({rel}{title})"
        return f"{bang}[{alt}]({absolute}{title})"

    new = MD_LINK_RE.sub(repl, text)
    if new != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
    print(f"{path}: base={base} absolutized={stats['abs']} downloaded={stats['dl']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--base", help="explicit base URL if no Source: line")
    ap.add_argument("--download-dir", help="fetch images into this directory")
    a = ap.parse_args()
    for p in a.files:
        process(p, a.base, a.download_dir)


if __name__ == "__main__":
    main()

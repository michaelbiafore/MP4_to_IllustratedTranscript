#!/usr/bin/env python3
"""
finalize_slides.py — make a reveal.js HTML deck fully email-portable:

  1. Replace reveal.js CDN refs with inlined CSS+JS from .cache/reveal-5.1.0/
  2. Base64-inline every <img src="..."> using scripts/embed_slide_images.py logic

Usage:
  python scripts/finalize_slides.py <path/to/SLIDES.html>
"""
import argparse
import subprocess
import sys
from pathlib import Path


def inline_reveal(html_path: Path) -> int:
    cache = Path(".cache/reveal-5.1.0")
    rcss = (cache / "reveal.css").read_text(encoding="utf-8")
    bcss = (cache / "black.css").read_text(encoding="utf-8")
    rjs  = (cache / "reveal.js").read_text(encoding="utf-8")

    h = html_path.read_text(encoding="utf-8")
    h = h.replace(
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">',
        '<style>\n/* reveal.js v5.1.0 */\n' + rcss + '\n</style>'
    )
    h = h.replace(
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/black.css">',
        '<style>\n/* reveal.js black theme v5.1.0 */\n' + bcss + '\n</style>'
    )
    h = h.replace(
        '<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>',
        '<script>\n/* reveal.js v5.1.0 */\n' + rjs + '\n</script>'
    )
    cdn_left = h.count("cdn.jsdelivr")
    html_path.write_text(h, encoding="utf-8")
    return cdn_left


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html_path")
    args = ap.parse_args()

    html = Path(args.html_path)
    if not html.exists():
        print(f"ERROR: not found: {html}", file=sys.stderr)
        sys.exit(2)

    cdn_left = inline_reveal(html)
    print(f"[reveal] inlined; cdn.jsdelivr refs remaining: {cdn_left}")
    if cdn_left:
        print("WARNING: not all CDN refs replaced — check spelling in template", file=sys.stderr)

    print("[images] running embed_slide_images.py …")
    r = subprocess.run([sys.executable, "scripts/embed_slide_images.py", str(html)],
                       capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(r.returncode)

    size_kb = html.stat().st_size // 1024
    print(f"[done] final HTML: {html} ({size_kb} KB)")


if __name__ == "__main__":
    main()

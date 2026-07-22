#!/usr/bin/env python3
"""Inline reveal.js CDN assets into a slide deck for email portability.

Reads .cache/reveal-5.1.0/{reveal.css, black.css, reveal.js} and substitutes
the CDN <link>/<script> references in the target HTML with inline <style>/<script>.
"""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "reveal-5.1.0"

if len(sys.argv) != 2:
    print("usage: inline_reveal_assets.py <html_file>", file=sys.stderr)
    sys.exit(1)

target = Path(sys.argv[1])
html = target.read_text(encoding="utf-8")

reveal_css = (CACHE / "reveal.css").read_text(encoding="utf-8")
black_css  = (CACHE / "black.css").read_text(encoding="utf-8")
reveal_js  = (CACHE / "reveal.js").read_text(encoding="utf-8")

# 1. Replace the two reveal.js stylesheets with one inline <style>
link_pat = re.compile(
    r'<link\s+rel="stylesheet"\s+href="https://cdn\.jsdelivr\.net/npm/reveal\.js@5\.1\.0/dist/reveal\.css">\s*'
    r'<link\s+rel="stylesheet"\s+href="https://cdn\.jsdelivr\.net/npm/reveal\.js@5\.1\.0/dist/theme/black\.css">'
)
inline_css_block = (
    "<style>\n/* reveal.js@5.1.0 reveal.css (inlined) */\n"
    + reveal_css
    + "\n/* reveal.js@5.1.0 theme/black.css (inlined) */\n"
    + black_css
    + "\n</style>"
)
html, n_css = link_pat.subn(lambda _m: inline_css_block, html, count=1)
if n_css != 1:
    print("ERROR: did not match the two CDN <link> tags", file=sys.stderr)
    sys.exit(2)

# 2. Replace the reveal.js <script src=...> with inline <script>
script_pat = re.compile(
    r'<script\s+src="https://cdn\.jsdelivr\.net/npm/reveal\.js@5\.1\.0/dist/reveal\.js"></script>'
)
inline_js_block = "<script>\n/* reveal.js@5.1.0 reveal.js (inlined) */\n" + reveal_js + "\n</script>"
html, n_js = script_pat.subn(lambda _m: inline_js_block, html, count=1)
if n_js != 1:
    print("ERROR: did not match the CDN <script src> tag", file=sys.stderr)
    sys.exit(3)

# 3. Sanity: no remaining cdn.jsdelivr refs to reveal.js
if "cdn.jsdelivr.net/npm/reveal.js" in html:
    print("ERROR: residual reveal.js CDN ref remains", file=sys.stderr)
    sys.exit(4)

target.write_text(html, encoding="utf-8")
size_kb = target.stat().st_size / 1024
print(f"OK — inlined reveal.css + black.css + reveal.js into {target}")
print(f"   final size: {size_kb:.1f} KB")

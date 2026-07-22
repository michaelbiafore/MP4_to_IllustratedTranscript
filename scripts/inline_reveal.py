"""Inline reveal.js v5.1.0 into a slide-deck source by replacing markers.

Usage:
    python inline_reveal.py <src_html> <out_html>

The source HTML must contain the literal markers  /*REVEAL_CSS*/  and
/*REVEAL_JS*/  (inside a <style> and a <script> block respectively). They are
replaced with the cached reveal.js CSS/JS so the deck has zero CDN dependencies.

Looks for the cached assets at, in order:
    .cache/reveal-5.1.0/{reveal.css,reveal.js}
    .cache/reveal/{reveal.min.css,reveal.min.js}
(relative to the project root = two levels up from this script).
"""
import os, sys

src_path, out_path = sys.argv[1], sys.argv[2]
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

candidates = [
    (os.path.join(root, ".cache", "reveal-5.1.0", "reveal.css"),
     os.path.join(root, ".cache", "reveal-5.1.0", "reveal.js")),
    (os.path.join(root, ".cache", "reveal", "reveal.min.css"),
     os.path.join(root, ".cache", "reveal", "reveal.min.js")),
]
css_path = js_path = None
for c, j in candidates:
    if os.path.exists(c) and os.path.exists(j):
        css_path, js_path = c, j
        break
if not css_path:
    sys.exit("ERROR: cached reveal.js assets not found under .cache/. "
             "Download reveal.min.css and reveal.min.js (v5.1.0) into .cache/reveal/.")

src = open(src_path, encoding="utf-8").read()
css = open(css_path, encoding="utf-8").read()
js = open(js_path, encoding="utf-8").read()

if "/*REVEAL_CSS*/" not in src or "/*REVEAL_JS*/" not in src:
    sys.exit("ERROR: source HTML is missing /*REVEAL_CSS*/ or /*REVEAL_JS*/ marker.")

src = src.replace("/*REVEAL_CSS*/", css, 1).replace("/*REVEAL_JS*/", js, 1)
open(out_path, "w", encoding="utf-8").write(src)

cdn = src.count("cdn.jsdelivr")
print(f"wrote {out_path}")
print(f"reveal source: {os.path.relpath(css_path, root)}")
print(f"remaining CSS/JS markers: {src.count('/*REVEAL_CSS*/')}/{src.count('/*REVEAL_JS*/')}  |  cdn refs: {cdn}")

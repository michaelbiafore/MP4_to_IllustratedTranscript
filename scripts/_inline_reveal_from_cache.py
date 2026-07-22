"""Replace reveal.js 5.1.0 CDN <link>/<script> refs with inline assets from .cache/reveal-5.1.0.

Usage: python _inline_reveal_from_cache.py <html-file>
"""
import re, sys
from pathlib import Path

ROOT = Path(r"A:/Packages/Transcript2MDSlides")
CACHE = ROOT / ".cache" / "reveal-5.1.0"

def main(target: Path) -> None:
    reveal_css = (CACHE / "reveal.css").read_text(encoding="utf-8")
    black_css = (CACHE / "black.css").read_text(encoding="utf-8")
    reveal_js = (CACHE / "reveal.js").read_text(encoding="utf-8")

    html = target.read_text(encoding="utf-8")

    css_pat = re.compile(r'<link\s+rel="stylesheet"\s+href="https://cdn\.jsdelivr\.net/npm/reveal\.js@5\.1\.0/dist/reveal\.css">')
    theme_pat = re.compile(r'<link\s+rel="stylesheet"\s+href="https://cdn\.jsdelivr\.net/npm/reveal\.js@5\.1\.0/dist/theme/black\.css">')
    js_pat = re.compile(r'<script\s+src="https://cdn\.jsdelivr\.net/npm/reveal\.js@5\.1\.0/dist/reveal\.js"></script>')

    html, n1 = css_pat.subn(lambda _m: f"<style>\n{reveal_css}\n</style>", html, count=1)
    html, n2 = theme_pat.subn(lambda _m: f"<style>\n{black_css}\n</style>", html, count=1)
    html, n3 = js_pat.subn(lambda _m: f"<script>\n{reveal_js}\n</script>", html, count=1)

    if (n1, n2, n3) != (1, 1, 1):
        print(f"ERROR: substitution counts (css, theme, js) = ({n1}, {n2}, {n3})", file=sys.stderr)
        sys.exit(1)
    if "cdn.jsdelivr" in html:
        print(f"ERROR: cdn.jsdelivr refs remain: {html.count('cdn.jsdelivr')}", file=sys.stderr)
        sys.exit(1)

    target.write_text(html, encoding="utf-8")
    print(f"Inlined reveal assets into {target.name}")

if __name__ == "__main__":
    main(Path(sys.argv[1]))

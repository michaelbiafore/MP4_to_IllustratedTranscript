"""Inline reveal.js CSS and JS into a slide deck HTML to make it fully portable
(no CDN requests). The decks are emailed to recipients whose corporate firewalls
often block cdn.jsdelivr.

Usage:
    python scripts/_inline_revealjs.py <html_file> [--cache-dir DIR]
"""
import argparse
import re
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("html_file")
    p.add_argument("--cache-dir", default=".cache/revealjs")
    args = p.parse_args()

    html_path = Path(args.html_file)
    cache = Path(args.cache_dir)

    reveal_css = (cache / "reveal.css").read_text(encoding="utf-8")
    theme_css = (cache / "black.css").read_text(encoding="utf-8")
    reveal_js = (cache / "reveal.js").read_text(encoding="utf-8")

    html = html_path.read_text(encoding="utf-8")

    # Replace the reveal.css link (use callable to avoid backreference parsing in CSS body)
    html = re.sub(
        r'<link rel="stylesheet"\s+href="https://cdn\.jsdelivr\.net/npm/reveal\.js@[^"]+/dist/reveal\.css"\s*/?>',
        lambda _m: f"<style>\n/* Inlined reveal.js core CSS */\n{reveal_css}\n</style>",
        html,
    )
    html = re.sub(
        r'<link rel="stylesheet"\s+href="https://cdn\.jsdelivr\.net/npm/reveal\.js@[^"]+/dist/theme/[^"]+\.css"\s*/?>',
        lambda _m: f"<style>\n/* Inlined reveal.js black theme */\n{theme_css}\n</style>",
        html,
    )
    html = re.sub(
        r'<script src="https://cdn\.jsdelivr\.net/npm/reveal\.js@[^"]+/dist/reveal\.js"></script>',
        lambda _m: f"<script>\n/* Inlined reveal.js core */\n{reveal_js}\n</script>",
        html,
    )

    # Strip fragment classes (visibility depends on JS — kill them so all
    # content shows in email preview panes)
    html = re.sub(r'\sclass="(?:[^"]*\s)?fragment(?:\s[^"]*)?"', '', html)

    html_path.write_text(html, encoding="utf-8")

    # Verify
    remaining_cdn = len(re.findall(r"cdn\.jsdelivr", html))
    remaining_fragments = len(re.findall(r'class="[^"]*\bfragment\b', html))
    size_mb = html_path.stat().st_size / 1024 / 1024
    print(f"Inlined reveal.js into {html_path.name}")
    print(f"  Final size: {size_mb:.2f} MB")
    print(f"  Remaining cdn.jsdelivr refs: {remaining_cdn}")
    print(f"  Remaining fragment classes: {remaining_fragments}")


if __name__ == "__main__":
    main()

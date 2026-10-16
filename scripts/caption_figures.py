# -*- coding: utf-8 -*-
"""Post-process a pandoc-built transcript: give every screenshot a visible caption.

pandoc -f markdown-implicit_figures emits a bare <img> whose caption survives only
as alt text. For a translated transcript the caption is where the English lives, so
each screenshot is rewrapped as <figure>/<figcaption> (matching the inline SVG
figures, which already carry one) and a small block of caption CSS is appended to
the emerald theme.
"""
import re
import sys

CSS = """
<style>
figure.svgfig, figure.shot { margin: 2em 0; }
figure.shot img { display:block; width:100%; height:auto; border:1px solid #e2e8f0;
                  border-radius:6px; }
figure.svgfig > svg { margin: 0 auto !important; }
figure.svgfig figcaption, figure.shot figcaption {
  margin-top: .7em; padding-left: .9em; border-left: 3px solid #059669;
  font-size: .86em; line-height: 1.55; color: #475569; }
figure.svgfig figcaption::first-line, figure.shot figcaption::first-line { font-weight: 600; }
</style>
"""

# pandoc writes the attributes in its own order (role / aria-label / src / alt), so
# match the whole tag and pull the two attributes out of it.
IMG = re.compile(r'<p><img ([^>]*?)/?>\s*</p>', re.S)


def main(path):
    html = open(path, encoding="utf-8").read()

    def repl(m):
        attrs = m.group(1)
        src = re.search(r'src="([^"]+)"', attrs)
        alt = re.search(r'alt="(Figure \d+): ([^"]*)"', attrs, re.S)
        if not src or not alt:
            return m.group(0)
        label, cap = alt.group(1), alt.group(2).replace("&quot;", '"')
        return (f'<figure class="shot"><img src="{src.group(1)}" alt="{label}" />'
                f'<figcaption>{label}: {cap}</figcaption></figure>')

    html, n = IMG.subn(repl, html)
    if "</head>" not in html:
        raise SystemExit("no </head> in output")
    html = html.replace("</head>", CSS + "</head>", 1)
    open(path, "w", encoding="utf-8").write(html)
    print(f"captioned {n} screenshots in {path}")


if __name__ == "__main__":
    main(sys.argv[1])

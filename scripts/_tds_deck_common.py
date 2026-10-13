"""
Shared builder for portable reveal.js decks (house 'midnight' style).

Guarantees identical styling and the correct DARK background across every deck,
so the white-page gotcha (reveal's built-in white viewport painting over body)
cannot recur. Import this from a per-deck build script:

    from _tds_deck_common import slide, b64img, build_html

    slides = []
    slides.append(slide('<div class="title">...</div>'))
    ...
    build_html(
        title="My Deck Title",
        slides_html=slides,
        footer="Short · Source citation",
        out_path=r"A:/.../Output/Slides/My_Deck_20_SLIDES.html",
    )

Conventions (per project mandate): reveal CSS+JS inlined, images base64, NO
fragments, dark background #1a1a2e, blue accent #64b5f6.
"""
from __future__ import annotations

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVEAL_DIR = ROOT / ".cache" / "reveal"

CUSTOM_CSS = """
:root{
  --bg:#1a1a2e; --bg2:#202044; --fg:#eaeaf2; --muted:#9aa0c4;
  --accent:#64b5f6; --accent2:#9ad0ff; --warn:#ef5350; --good:#66bb6a; --gold:#ffca28;
}
/* --- DARK BACKGROUND: force onto every reveal surface (see slidefy-pdf gotcha) --- */
html,body{background:#1a1a2e!important;}
.reveal-viewport{background:#1a1a2e!important;}
.reveal{background:#1a1a2e!important; color:var(--fg);}
.reveal .backgrounds,.reveal .slide-background{background-color:#1a1a2e!important;}

.reveal{ font-family:"Inter","Segoe UI","Helvetica Neue",Arial,sans-serif; font-size:30px; }
.reveal .slides{ text-align:left; }
.reveal section{ padding:0 2.5vw; }
.reveal h1,.reveal h2,.reveal h3{ color:var(--accent); font-weight:700; text-transform:none; letter-spacing:0; line-height:1.15; }
.reveal h1{ font-size:2.2em; }
.reveal h2{ font-size:1.5em; margin-bottom:.3em; overflow-wrap:anywhere; }
.reveal h3{ font-size:1.1em; color:var(--accent2); margin-top:0; }
.reveal p,.reveal li{ color:var(--fg); line-height:1.45; }
.reveal ul{ margin:.2em 0 0 1.2em; }
.reveal li{ margin:.35em 0; }
.reveal strong{ color:var(--accent2); }
.reveal em{ color:var(--muted); font-style:italic; }
.reveal small,.reveal .small{ color:var(--muted); font-size:.6em; }
.reveal a{ color:var(--accent2); }

.title{ text-align:center; }
.title h1{ font-size:2.5em; margin-bottom:.25em; }
.title .subtitle{ color:var(--accent2); font-size:1.05em; }
.title .authors{ color:var(--muted); font-size:.55em; margin-top:1.2em; line-height:1.4; }
.title .source{ color:var(--muted); font-size:.5em; margin-top:.8em; }

.bignum{ font-size:5.2em; font-weight:800; color:var(--accent); line-height:1; letter-spacing:-.02em; }
.bignum.warn{ color:var(--warn); } .bignum.good{ color:var(--good); } .bignum.gold{ color:var(--gold); }
.arrow{ color:var(--muted); font-size:1.5em; margin:.3em 0; }

.center{ text-align:center; }
.flex{ display:flex; gap:2em; align-items:flex-start; } .flex>div{ flex:1; }
.grid2{ display:grid; grid-template-columns:1fr 1fr; gap:1.4em 2.2em; }
.grid3{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:1.2em 1.6em; }
.grid4{ display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:1em 1.2em; }

.card{ background:var(--bg2); border-left:4px solid var(--accent); padding:.7em .9em; border-radius:6px; }
.card h3{ margin:0 0 .35em 0; font-size:.95em; color:var(--accent); }
.card p,.card li{ font-size:.58em; line-height:1.35; margin:.18em 0; }
.card.good{ border-left-color:var(--good); } .card.good h3{ color:var(--good); }
.card.warn{ border-left-color:var(--warn); } .card.warn h3{ color:var(--warn); }
.card.gold{ border-left-color:var(--gold); } .card.gold h3{ color:var(--gold); }

.figwrap{ text-align:center; height:78vh; display:flex; flex-direction:column; justify-content:center; }
.figwrap img{ max-height:72vh; max-width:96vw; margin:0 auto; border-radius:6px; background:#fff; }
.figwrap .cap{ color:var(--muted); font-size:.5em; margin-top:.6em; }

.kicker{ display:inline-block; background:var(--bg2); color:var(--accent2); padding:.15em .6em; border-radius:999px; font-size:.5em; letter-spacing:.1em; text-transform:uppercase; margin-bottom:.6em; }
.tag{ display:inline-block; background:rgba(100,181,246,.15); color:var(--accent2); padding:.12em .55em; border-radius:4px; font-size:.55em; margin-right:.35em; }
.quote{ font-size:1.15em; font-style:italic; color:var(--accent2); border-left:4px solid var(--accent); padding-left:.8em; margin:.4em 0; }
.footer{ position:fixed; bottom:8px; right:14px; color:var(--muted); font-size:.42em; z-index:20; }
"""


def b64img(path) -> str:
    """Base64 data URI for a PNG (or any image) file."""
    data = Path(path).read_bytes()
    return f"data:image/png;base64,{base64.b64encode(data).decode('ascii')}"


def slide(content: str, classes: str = "") -> str:
    cls = f' class="{classes}"' if classes else ""
    return f"      <section{cls}>\n{content}\n      </section>\n"


def figure_slide(headline: str, img_uri: str, caption: str, img_style: str = "") -> str:
    """Standard full-bleed figure slide."""
    style = f' style="{img_style}"' if img_style else ""
    return slide(
        f"""        <h2>{headline}</h2>
        <div class="figwrap">
          <img src="{img_uri}"{style} alt="figure"/>
          <div class="cap">{caption}</div>
        </div>"""
    )


def build_html(title: str, slides_html: list[str], footer: str, out_path) -> Path:
    reveal_css = (REVEAL_DIR / "reveal.min.css").read_text(encoding="utf-8")
    reveal_js = (REVEAL_DIR / "reveal.min.js").read_text(encoding="utf-8")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>
{reveal_css}
{CUSTOM_CSS}
</style>
</head>
<body>
<div class="reveal">
  <div class="slides">
{''.join(slides_html)}
  </div>
</div>
<div class="footer">{footer}</div>
<script>
{reveal_js}
</script>
<script>
Reveal.initialize({{
  hash: true, history: false, controls: true, progress: true,
  slideNumber: 'c/t', transition: 'slide',
  width: 1280, height: 720, margin: 0.04, minScale: 0.2, maxScale: 1.0
}});
</script>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote: {out_path}  ({out_path.stat().st_size:,} bytes, {len(slides_html)} slides)")
    return out_path

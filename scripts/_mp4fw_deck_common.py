"""Shared builder for portable reveal.js decks produced by /MP4+FasterWhisp.

Follows the MP4+WizWhisp Phase 7 contract exactly:
  - reveal.js v5.1.0 CSS+JS inlined (zero CDN refs)
  - every image base64-inlined
  - no `class="fragment"` anywhere
  - transition: 'fade', center: true, slideNumber: true, hash: true
  - click-to-zoom lightbox on `section img.shot`
  - dark navy #1a1a2e / blue #64b5f6 / red #ef5350 / green #66bb6a
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVEAL_DIR = ROOT / ".cache" / "reveal"

CUSTOM_CSS = """
:root{
  --bg:#1a1a2e; --bg2:#202044; --fg:#eaeaf2; --muted:#9aa0c4;
  --accent:#64b5f6; --accent2:#9ad0ff; --warn:#ef5350; --good:#66bb6a; --gold:#ffca28;
}
html,body{background:#1a1a2e!important;}
.reveal-viewport{background:#1a1a2e!important;}
.reveal{background:#1a1a2e!important; color:var(--fg);}
.reveal .backgrounds,.reveal .slide-background{background-color:#1a1a2e!important;}

.reveal{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif; font-size:30px; }
.reveal .slides{ text-align:left; }
.reveal section{ padding:0 34px; box-sizing:border-box; }
.reveal section *{ box-sizing:border-box; }
.reveal h1,.reveal h2,.reveal h3{ color:var(--accent); font-weight:700; text-transform:none; letter-spacing:0; line-height:1.15; }
.reveal h1{ font-size:2.2em; }
.reveal h2{ font-size:1.35em; margin-bottom:.3em; overflow-wrap:anywhere; }
.reveal h3{ font-size:1.05em; color:var(--accent2); margin-top:0; }
.reveal p,.reveal li{ color:var(--fg); line-height:1.45; }
.reveal ul{ margin:.2em 0 0 1.2em; }
.reveal li{ margin:.35em 0; }
.reveal strong{ color:var(--accent2); }
.reveal em{ color:var(--muted); font-style:italic; }
.reveal small,.reveal .small{ color:var(--muted); font-size:.6em; }
.reveal a{ color:var(--accent2); }

.title{ text-align:center; }
.title h1{ font-size:2.3em; margin-bottom:.25em; }
.title .subtitle{ color:var(--accent2); font-size:1.0em; }
.title .authors{ color:var(--muted); font-size:.55em; margin-top:1.2em; line-height:1.4; }
.title .source{ color:var(--muted); font-size:.5em; margin-top:.8em; }

.bignum{ font-size:4.6em; font-weight:800; color:var(--accent); line-height:1; letter-spacing:-.02em; }
.bignum.warn{ color:var(--warn); } .bignum.good{ color:var(--good); } .bignum.gold{ color:var(--gold); }
.arrow{ color:var(--muted); font-size:1.4em; margin:.3em 0; }

.center{ text-align:center; }
.flex{ display:flex; gap:2em; align-items:flex-start; } .flex>div{ flex:1; }
.grid2{ display:grid; grid-template-columns:1fr 1fr; gap:1.2em 2em; }
.grid3{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:1em 1.4em; }

.card{ background:var(--bg2); border-left:4px solid var(--accent); padding:.7em .9em; border-radius:6px; }
.card h3{ margin:0 0 .35em 0; font-size:.9em; color:var(--accent); }
.card p,.card li{ font-size:.56em; line-height:1.35; margin:.18em 0; }
.card.good{ border-left-color:var(--good); } .card.good h3{ color:var(--good); }
.card.warn{ border-left-color:var(--warn); } .card.warn h3{ color:var(--warn); }
.card.gold{ border-left-color:var(--gold); } .card.gold h3{ color:var(--gold); }

.figwrap{ text-align:center; }
.reveal section img.shot{ max-height:66vh; max-width:94vw; margin:0 auto; border-radius:6px;
  border:1px solid rgba(154,208,255,.25); cursor:zoom-in; display:block; }
.figwrap .cap{ color:var(--muted); font-size:.46em; margin-top:.55em; line-height:1.4; }

.kicker{ display:inline-block; background:var(--bg2); color:var(--accent2); padding:.15em .6em; border-radius:999px; font-size:.5em; letter-spacing:.1em; text-transform:uppercase; margin-bottom:.5em; }
.tag{ display:inline-block; background:rgba(100,181,246,.15); color:var(--accent2); padding:.12em .55em; border-radius:4px; font-size:.55em; margin-right:.35em; }
.quote{ font-size:1.1em; font-style:italic; color:var(--accent2); border-left:4px solid var(--accent); padding-left:.8em; margin:.4em 0; }
.attrib{ color:var(--muted); font-size:.55em; margin-top:.5em; }
.footer{ position:fixed; bottom:8px; right:14px; color:var(--muted); font-size:.42em; z-index:20; }

#lightbox{ position:fixed; inset:0; background:rgba(6,6,16,.94); display:none; z-index:9999;
  align-items:center; justify-content:center; cursor:zoom-out; }
#lightbox.on{ display:flex; }
#lightbox img{ max-width:96vw; max-height:94vh; border-radius:6px; }
"""


def b64img(path) -> str:
    """Base64 data URI for an image file (mime sniffed from the extension)."""
    p = Path(path)
    mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode('ascii')}"


def slide(content: str, classes: str = "") -> str:
    cls = f' class="{classes}"' if classes else ""
    return f"      <section{cls}>\n{content}\n      </section>\n"


def figure_slide(headline: str, img_uri: str, caption: str, alt: str, img_style: str = "") -> str:
    """Full-bleed screenshot slide with a click-to-zoom image."""
    style = f' style="{img_style}"' if img_style else ""
    head = f"        <h2>{headline}</h2>\n" if headline else ""
    return slide(
        f"""{head}        <div class="figwrap">
          <img class="shot" src="{img_uri}"{style} alt="{alt}"/>
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
<div id="lightbox"><img alt="zoomed figure"/></div>
<script>
{reveal_js}
</script>
<script>
Reveal.initialize({{
  hash: true, history: false, controls: true, progress: true,
  slideNumber: true, center: true, transition: 'fade',
  width: 1280, height: 720, margin: 0.04, minScale: 0.2, maxScale: 1.0
}});
(function(){{
  var lb = document.getElementById('lightbox');
  var lbImg = lb.querySelector('img');
  document.addEventListener('click', function(e){{
    var t = e.target;
    if (t && t.tagName === 'IMG' && t.classList.contains('shot')) {{
      lbImg.src = t.src; lb.classList.add('on');
    }} else if (lb.classList.contains('on')) {{
      lb.classList.remove('on'); lbImg.removeAttribute('src');
    }}
  }});
  document.addEventListener('keydown', function(e){{
    if (e.key === 'Escape' && lb.classList.contains('on')) {{
      lb.classList.remove('on'); lbImg.removeAttribute('src');
    }}
  }});
}})();
</script>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote: {out_path}  ({out_path.stat().st_size:,} bytes, {len(slides_html)} slides)")
    return out_path

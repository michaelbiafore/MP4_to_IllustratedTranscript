# CN Figures → English

Convert **a single figure that contains Chinese text** (a diagram, chart, table, flowchart,
pyramid, etc.) into a **similar figure with English text in place of the Chinese**, preserving
the meaning, layout, and colour semantics as closely as possible. The result is emitted as a
**PNG** (plus an editable SVG master and ready-to-paste embed snippets) so it drops straight
into Markdown and HTML.

**Input**: $ARGUMENTS

`$ARGUMENTS` is a path to the source figure — normally an image file (`.png`, `.jpg`,
`.jpeg`, `.webp`). Optional trailing flags:

- `--out DIR` — output directory (default: same directory as the input).
- `--width N` — target CSS width of the figure in px (default: sized to content, ~900–980).
- `--scale N` — PNG rasterization scale factor (default `2`; higher = crisper/larger PNG).
- `--transparent` — render the PNG on a transparent background instead of white.
- `--title "…"` — override the figure's title text (default: translate the source title).
- `--svg-only` / `--png-only` — emit just one format (default: emit both).

> This command is the **single-figure** distillation of the technique documented in
> [`Refs/Chinese_to_English_Figures.md`](../../Refs/Chinese_to_English_Figures.md). Read that
> note if anything below is unclear — it has the full rationale and the palette/glossary.

---

## Core principle: reconstruct, don't overpaint

Do **not** try to erase Chinese pixels and type English on top of the raster — it is fragile,
blurry, and doesn't scale. Instead: **read the figure → capture its structure and text as
data → re-emit it as a clean vector (SVG) → rasterize to PNG.** The reconstruction is what
lets the English text wrap correctly and stay crisp.

---

## Instructions

### 1. Resolve the input and prepare output paths

- If `$ARGUMENTS` has no directory separator, look for the file in `Input/`.
- If the input is a **PDF**, first extract the target image with PyMuPDF (dedupe by xref) and
  treat the extracted PNG as the figure:
  ```bash
  uv run python -c "import fitz; d=fitz.open('SRC.pdf'); [ (lambda px: (px if px.n<=4 else fitz.Pixmap(fitz.csRGB,px)).save(f'Input/fig_p{i+1}_{im[0]}.png')) (fitz.Pixmap(d,im[0])) for i,p in enumerate(d) for im in p.get_images(full=True) ]"
  ```
- Derive the output stem from the input filename: `<stem>_EN.svg`, `<stem>_EN.png`.

### 2. Read the Chinese figure carefully (this is the translation step)

**View the image** (Read tool renders it). If it is small or dense, that's fine — read it at
full resolution. Record four things:

1. **Figure archetype / layout.** Which shape is it? Common ones:
   card-row-with-arrows · parallel columns · table · pyramid (stacked trapezoids) ·
   trilemma triangle · flow tree (root → branches) · snaking numbered pipeline ·
   multi-box "panorama" · circular flywheel · 2-D quadrant/matrix · timeline.
2. **Every piece of Chinese text, in its position** — title, subtitle, box headers,
   sub-labels, bullets, axis labels, arrow/edge captions, footnotes, legend, severity chips.
3. **Colour semantics** — the source colours usually carry meaning; preserve the mapping.
   A good default palette (matches the repo house style):
   green = go/write/safe · amber = caution/store · blue = info/read · red = fatal/danger ·
   purple = human/control · gray = neutral. 
4. **Spatial relationships** — what points to what, nesting, ordering, groupings, brackets.

**Translation rules:**
- Translate for **meaning**, not word-for-word; keep it concise so it fits the box.
- Keep a **consistent glossary** if the figure repeats terms, and match any surrounding
  document's wording. Useful defaults seen in this repo:
  评测=Evaluation · 记忆=Memory · 落地=Deployment · 控制=Control · 信号=Signal ·
  飞轮=flywheel · 门控=gate/gating · 灰度=canary · 回流=backflow · 归因=attribution ·
  分层=layered · 三分法=three-way split · 避坑清单=pitfalls checklist ·
  严重度 高/中/低/低频致命 = Severity High/Medium/Low/Low-but-fatal.
- **Keep code-ish tokens verbatim**: file names, `MEMORY.md`, `.learnings/`, `node_id`,
  `temperature=0`, `Top-K`, `AST`, `Gate 1–5`, `10% × 7 days`, numbers, and math.
- Re-express circled numerals ①②③ as `1 2 3` badges; translate emoji-as-icon into a short word
  or drop it.

### 3. Reconstruct as inline SVG

You have two paths — prefer the first when the figure fits an archetype:

**(a) Reuse the renderer library.** `scripts/_flywheel_figs.py` provides tested,
portable renderers: `fig_flow`, `fig_table`, `fig_pyramid`, `fig_trilemma`, `fig_tree`,
`fig_snake`, `fig_panorama`, `fig_flywheel`, `fig_dataflow`. Import it and call the matching
one with your translated data. Example (a trilemma triangle):
```python
import sys; sys.path.insert(0, "scripts")
from _flywheel_figs import fig_trilemma
svg = fig_trilemma("The evaluation trilemma",
    "Precision × Cost × Coverage — no silver bullet",
    ["Precision","(evaluate accurately)"], ["Cost","(affordable)"],
    ["Coverage","(evaluate everything)"],
    ["high precision → high cost","wide coverage → precision hard","low cost → narrow coverage"],
    ["Solution: layered combination","Rules + LLM Judge + Human"])
open("out_EN.svg","w",encoding="utf-8").write(svg)
```

**(b) Hand-author the SVG** for a one-off layout. Follow these portability rules (they matter
because the figure must render offline with zero external deps):
- **System font stack only**: `font-family="system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"`. No web-font fetches.
- **Arrowheads as `<polygon>`**, computed from `atan2` — **never** `<marker>`/`<defs>` (their
  ids collide when several SVGs share one HTML page).
- **`viewBox="0 0 W H"`** plus `width:100%; max-width:Wpx; height:auto` so it scales crisply.
- Wrap long strings to the box width (estimate ~`0.53 × font-size` px per character).
- White rounded "card" frame + centered bold title + optional italic subtitle, so it reads as
  a finished figure.
- Preserve the source's colour mapping and relative positions.

Write the SVG to `<stem>_EN.svg`.

### 4. Rasterize SVG → PNG (the requested output format)

There is no `cairosvg`/`inkscape` here — use **Edge headless**. Wrap the SVG in a tight HTML
page, set the window to the figure's pixel size, and screenshot with a scale factor:

```powershell
# vars: $svgW,$svgH = the SVG viewBox W,H ; $scale = 2 ; $stem = output stem
$html = "<!doctype html><meta charset=utf-8><style>html,body{margin:0;padding:0}</style>" + (Get-Content "$stem`_EN.svg" -Raw)
Set-Content -Encoding utf8 "$stem`_EN.wrap.html" $html
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$bg = "--default-background-color=00000000"   # omit for white; keep for --transparent
& $edge --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=$scale `
  --window-size=$svgW,$svgH $bg `
  "--screenshot=$((Resolve-Path .))\$stem`_EN.png" "file:///$((Resolve-Path "$stem`_EN.wrap.html") -replace '\\','/')"
```

Notes / gotchas (from the Notes doc):
- **Use absolute paths** for both `--screenshot` and the `file:///` URL — a relative
  screenshot path silently writes nothing (exit 0, no file).
- The PNG is `(W×scale) × (H×scale)`; keep each side under ~2000px for easy embedding
  (`scale 2` on a 980-wide figure → 1960px, fine).
- `--window-size` clips taller content — set it to the true `viewBox` height (or larger).
- Delete the temp `*.wrap.html` afterward.

### 5. Verify against the original, then iterate

- **View the generated PNG** and compare to the source: is **every** Chinese string now
  English? Is the layout/ordering/colour faithful? Any clipped or overflowing text?
- If the image-read tool starts rejecting images (a cumulative per-turn cap that shows a
  misleading "exceeds 2000px" error), fall back to a **programmatic bounds check**: regex all
  `x/y/cx/cy`, `points`, and path coordinates out of the SVG and confirm they lie within
  `0..W` / `0..H` (nothing drawn off-canvas). Then fix text sizes/wrapping and re-rasterize.
- Iterate until it matches.

### 6. Emit the figure and copy-paste embed snippets

Report the output paths and print ready-to-use embeds. For maximum portability (self-contained,
survives being emailed as a lone file — the repo mandate), prefer the **base64 data-URI**:

```bash
# base64 data URI (portable; paste into Markdown or HTML)
uv run python -c "import base64,sys,pathlib; d=base64.b64encode(pathlib.Path(sys.argv[1]).read_bytes()).decode(); print('![English figure](data:image/png;base64,'+d+')')" "<stem>_EN.png"
```

Provide all of:
- **Markdown (file ref):** `![English figure](<stem>_EN.png)`
- **Markdown (portable):** the base64 data-URI line above.
- **HTML:** `<img src="<stem>_EN.png" alt="English figure" style="max-width:100%;height:auto">`
- Mention that **`<stem>_EN.svg` is the editable master** and is itself embeddable (inline
  `<svg>` in HTML, or `<img src>` in Markdown) if a vector is preferred over PNG.

---

## Quality Checklist

- [ ] **All** Chinese characters replaced with English (none left in the PNG).
- [ ] Meaning preserved; concise enough to fit; code tokens/numbers kept verbatim.
- [ ] Layout, ordering, groupings, arrows, and colour semantics match the original.
- [ ] No clipped or overflowing text; nothing drawn off-canvas.
- [ ] PNG is crisp (scale ≥ 2) and a reasonable size (each side ≲ 2000px).
- [ ] Fully portable: SVG uses only system fonts and inline shapes — zero external/network refs.
- [ ] Embed snippets provided (Markdown file-ref, portable base64, HTML), plus the SVG master.
- [ ] Temp wrapper HTML cleaned up.

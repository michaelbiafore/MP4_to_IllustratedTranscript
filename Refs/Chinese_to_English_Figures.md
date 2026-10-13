# Reading Chinese Figures and Reconstructing Them in English

A field guide to the technique used to turn a heavily-illustrated Chinese article (Tencent's
*"一篇讲透Agent自进化飞轮怎么搭：评测→记忆→落地→控制"* / "Building the Agent Self-Evolution
Flywheel") into a portable English **illustrated translation** — where every one of the
**38 figures** is rebuilt as an English-only diagram, not just the original Chinese raster
image.

The deliverable lives at
`Output/Formatted/Building_The_Agent_Self_Evolution_Flywheel_ILLUSTRATED_TRANSLATION.{md,html}`.
The reusable renderer library is `scripts/_flywheel_figs.py`; the per-figure data and
assembly for that particular article are archived in `examples/_flywheel_build.py`
(git-ignored, local only).

---

## 0. The core decision: reconstruct, don't edit

There are three ways to "translate" a figure. Only the third scales and stays portable:

| Approach | Problem |
|----------|---------|
| **Leave the Chinese image in place** | Reader can't read it; defeats the purpose. |
| **Overpaint English onto the raster** (inpaint + retype) | Per-image manual pixel work; fragile; blurry; 38× the effort; alignment nightmares. |
| **Rebuild the figure as vector (inline SVG)** ✅ | Crisp, scalable, fully portable, editable, and — crucially — *data-driven*, so ~10 reusable renderers cover all 38 figures. |

The whole method below flows from that decision: **read the Chinese → capture the figure's
*structure and text* as data → re-emit as English SVG through a shared renderer.**

---

## 1. Get a clean source that actually contains the figures

The first PDF the user exported had only **2 real raster images**; its diagrams were live
HTML/canvas that rendered as **blank gaps** in the PDF. Lesson: **before promising figures,
probe the file.**

The second export ("save webpage as PDF" done differently) embedded all the diagrams. Probe
with **PyMuPDF (`fitz`)**:

```python
import fitz
d = fitz.open(SRC)
total = sum(len(p.get_images(full=True)) for p in d)
print(d.page_count, "pages,", total, "images")
```

This reported **27 pages, 39 embedded images** (1 banner + 38 diagrams). Only now is it safe
to commit to "yes, I can extract ~20+ figures."

### Extract every image, de-duplicated by xref

The same image can be referenced from multiple pages; de-dupe by the PDF **xref** so you get
each bitmap once, and name files so the page and native size are visible at a glance:

```python
import fitz, os
d = fitz.open(SRC); seen = set()
os.makedirs("Input/EVALS2_figs", exist_ok=True)
for i, p in enumerate(d):
    for im in p.get_images(full=True):
        xref = im[0]
        if xref in seen:      # dedupe
            continue
        seen.add(xref)
        px = fitz.Pixmap(d, xref)
        if px.n > 4:          # CMYK / alpha -> RGB
            px = fitz.Pixmap(fitz.csRGB, px)
        px.save(f"Input/EVALS2_figs/p{i+1:02d}_x{xref}_{px.width}x{px.height}.png")
```

Result: `p02_x14_1080x778.png`, `p05_x28_1080x729.png`, … The filename tells you the source
page (`p05`), the xref (`x28`), and the resolution (`1080x729`) — all useful when cataloging.
The banner (`p01_x7_640x208`) is the only non-figure; everything ≥ ~300px wide was a genuine
info-graphic.

---

## 2. Read the Chinese figures

**Read the extracted PNGs directly** (the image-reading tool renders them visually). Chinese
text in the diagrams is legible at 1080px. Do it in **small batches (5 images per call)** so
each image stays large enough to read every label.

For each image, write down three things — this *is* the translation work:

1. **Figure type / layout** — is it a card-row-with-arrows, a pyramid, a trilemma triangle,
   a table, a flow tree, a snaking pipeline, a multi-box "panorama", a circular flywheel?
   The type determines which renderer rebuilds it.
2. **Every piece of Chinese text**, in place (titles, box headers, sub-labels, bullets, axis
   labels, footnotes, arrow captions).
3. **Colour semantics** — the source used a consistent palette that carries meaning:
   green = write/safe/go, amber = store/caution, blue = read/info, red = fatal/regression,
   purple = human/control, gray = neutral/Level-0. Preserve it.

### Reading / translating tips specific to these diagrams

- **Severity chips** (`高 / 中 / 低 / 低频致命`) → `High / Medium / Low / Low-but-fatal`.
- **Domain vocabulary must be translated consistently across all 38 figures**, because the
  same terms recur. Keep a running glossary, e.g.:
  评测=Evaluation, 记忆=Memory, 落地/落地工程化=Deployment/Engineering, 控制=Control,
  信号=Signal, 积累=Accumulation, 飞轮=flywheel, 齿=tooth, 门控=gating/gate,
  灰度=canary, 回流=backflow, 归因=attribution, 分层=layered, 三分法=three-way split,
  收束=conclusion, 避坑清单=pitfalls checklist, 元评测集=meta-eval set.
- **Keep code-ish tokens verbatim** (`.learnings/`, `MEMORY.md`, `skills/`, `node_id`,
  `temperature=0`, `Top-K`, `AST`, `Gate 1–5`, `10% × 7 days`).
- **Emoji / circled numerals** (①②③…) — re-express as `1 2 3` badges in the SVG.
- Watch for text that is *outside* boxes: axis labels on pyramids ("高频/中频/低频" =
  high/mid/low-freq), edge labels on triangles, and dashed "downgrade/backflow" captions on
  arrows. These are easy to miss and often carry the key relationship.

---

## 3. Turn the reading into data, then into English SVG

The heart of the method: a **data-driven SVG generator**. Instead of drawing 38 bespoke
diagrams, classify each into one of ~10 layout archetypes and write **one renderer per
archetype**. Each figure is then just a small Python data structure passed to a renderer.

### 3.1 The renderer library (`_flywheel_figs.py`)

Shared primitives first:

- `esc()` — XML-escape all text.
- `wrap_px(text, width, size)` — greedy word-wrap using an average glyph-width estimate
  (`0.53 × font-size`), so text fits inside a known box width without a font metrics library.
- `txt()`, `block()` — single line / multi-line text.
- `rrect()` — rounded rectangle (the universal box).
- `arrow(x1,y1,x2,y2)` — a line **plus a hand-built polygon arrowhead** computed from
  `atan2`. **Do not use SVG `<marker>`/`<defs>` for arrowheads**: when dozens of SVGs are
  inlined into one HTML page, their marker `id`s collide. Polygon heads are self-contained.
- `chip()` — a pill/badge (severity chips, tags).
- `svg_open()` / `header()` — every figure is a white rounded "card" with a bordered frame,
  a bold centered title, and an optional italic subtitle. This gives all 38 a consistent look.

The ~10 archetype renderers:

| Renderer | Rebuilds | Figures |
|----------|----------|---------|
| `fig_flow` | row/column of boxes, optional arrows between, optional numbered badges | p03, p08, p10, p12, p13a, p14b, p15c, p17, p18a, p19, p21a, p21b, p23, p26a, p26b, p27 |
| `fig_table` | titled table; auto-wrapped cells; coloured **severity chips**; zebra rows | p05b, p09b, p11a, p14a, p15a, p20a, p24a |
| `fig_pyramid` | stacked trapezoids with left axis + right annotations | p07b, p13b |
| `fig_trilemma` | triangle with vertex circles, edge labels, centre solution box | p05a |
| `fig_tree` | root → mid → N coloured branch rows (condition → action) | p09a |
| `fig_snake` | numbered pipeline that snakes L→R then R→L across rows | p16, p18b |
| `fig_panorama` | vertical stack of full-width bands and multi-column rows | p02, p04, p11b, p15b, p20b |
| `fig_flywheel` | centre node + 4 nodes at N/E/S/W + curved clockwise arrows | p24b |
| `fig_dataflow` | vertical graph with two branches that merge + a dashed loop-back | p25 |

Key implementation choices that make the output faithful **and** portable:

- **Measure, then draw.** For card rows, first compute each card's required height from its
  wrapped content, set all cards to the tallest, then render — so a row is visually even.
- **`viewBox` + `width:100%; max-width:<W>px`** on every `<svg>` → responsive but capped;
  scales crisply on any screen and in print.
- **System font stack only** (`system-ui, -apple-system, "Segoe UI", Roboto, …`) — no web
  font fetch, per the repo's portability mandate.
- **No external anything** — every shape and glyph is inline SVG; there are zero `http`
  `src`/`link` references in a finished figure.

### 3.2 Example: one figure as data

The trilemma triangle (`p05a`, originally 评测的三难困境) becomes:

```python
F['p05a'] = fig_trilemma(
    'The evaluation trilemma',
    'Precision × Cost × Coverage — no silver bullet, only layered combination',
    ['Precision', '(evaluate accurately)'],     # top vertex
    ['Cost', '(affordable)'],                    # bottom-left
    ['Coverage', '(evaluate everything)'],       # bottom-right
    ['high precision → high cost',               # three edge labels
     'wide coverage → precision hard',
     'low cost → narrow coverage'],
    ['Solution: layered combination',            # centre box
     'Rules (bottom) + LLM Judge (middle) + Human (top)'])
```

That's the entire figure. All the translated Chinese lives in that literal; the geometry is
the renderer's job. This is why 38 figures were tractable.

---

## 4. Place the figures back into the translated prose

The English **body text** already existed (the second PDF's body was machine-translated to
English, then edited). The build script (`_flywheel_build.py build`) reads that markdown and
inserts each figure at the right spot two ways:

- **Replace placeholders** — the first-draft translation had italic notes like
  *"[the source PDF has a diagram here that did not render…]"*. Each is replaced wholesale by
  its figure.
- **Insert-after anchors** — for figures with no placeholder, the script finds an **exact,
  unique sentence** already in the text and inserts the `<figure>…</figure>` immediately after
  it (e.g., the trilemma goes right after the sentence that introduces "precision × cost ×
  coverage").

Each figure is wrapped as raw HTML:

```
<figure>
<svg …>…</svg>
</figure>
```

**Make the script assert every anchor is found.** A single mismatch (below) silently drops a
figure otherwise:

> **Gotcha — curly vs straight quotes.** Anchor strings must match the source file's *exact*
> glyphs. `can't` (straight `'`) ≠ `can’t` (curly `’`); em-dashes and `→` arrows must match
> byte-for-byte. The build printed `!!! MISSING ANCHORS: ['INS:p21b']` until the apostrophe
> was fixed. Always fail loudly on a missing anchor.

---

## 5. Build portable HTML and verify

Build with pandoc (repo house style — emerald theme, resources embedded):

```
pandoc -f markdown-implicit_figures INPUT.md -s --embed-resources \
  -H ../../Refs/formatted_transcript_style.html \
  --metadata title="…" -o OUTPUT.html
```

pandoc passes raw `<svg>` through untouched, and `--embed-resources` base64-inlines the two
real PNGs (banner + account card). Both `.md` and `.html` end up self-contained.

**Automated verification (grep the built HTML):**

- `grep -oc '<svg'` → **38** (all figures present).
- `grep -oE '(src|href)="https?://'` → the only externals are intended **live `href` links**;
  **no `src` fetches**. (The user asked for live, checked links.)
- `grep -c 'did not render'` → **0** (no leftover placeholders).
- Cross-check every TOC `href="#…"` against the generated `<h2 id="…">` — all resolve.
  (pandoc strips leading digits from heading ids and collapses `—` to a single `-`, so the
  TOC hrefs must be written to match the *generated* ids, not the heading text.)

**Visual QA without a rasterizer.** `cairosvg` isn't installed here, so render SVG→PNG with
**Edge headless**:

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
  --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1.5 `
  --window-size=1040,7200 "--screenshot=<ABSOLUTE>.png" "file:///<ABSOLUTE>.html"
```

> **Gotcha — absolute paths.** Both `--screenshot` and the `file:///` URL must be absolute; a
> relative screenshot path silently writes nothing (exit 0, no file).
>
> **Gotcha — window height clips.** Headless captures the `--window-size` box; tall pages get
> cut. Screenshot individual figures, or set a generous height.
>
> **Gotcha — the image-read API has a cumulative per-turn cap.** After ~40–50 images in one
> session turn, the tool rejects *all* further images with a misleading "dimensions exceed
> 2000px" error, even for small (780px) ones. When that hits, fall back to a **programmatic
> bounds check**: regex every `x/y/cx/cy`, `points`, and path coordinate out of each SVG and
> compare against its `viewBox` W×H to catch clipping/overflow. It won't catch aesthetic
> overlap, but it proves nothing is drawn off-canvas.

---

## 6. Checklist for the next foreign-figure translation

1. **Probe first** (`fitz`): confirm the diagrams are real embedded images, not blank
   HTML/canvas gaps. If blank → get a better export before promising figures.
2. **Extract** de-duped by xref; name files `pNN_x<xref>_WxH.png`.
3. **Read in batches of ~5**; record layout + all text + colour semantics; keep a **consistent
   glossary** across figures.
4. **Classify** each figure into a layout archetype; write/reuse one renderer per archetype.
5. **Encode each figure as data**, English text only; let the renderer own the geometry.
6. **Assemble** by placeholder-replace + insert-after-anchor; **assert** every anchor matches
   (mind curly quotes / dashes / arrows).
7. **Build** portable HTML with pandoc `--embed-resources` + `-H` house style.
8. **Verify**: count `<svg>`, zero external `src`, zero placeholders, TOC ids resolve; visual
   QA via Edge headless with a programmatic bounds-check fallback.

See also: `Refs/formatted_transcript_style.html` (theme), the portability mandate in
`CLAUDE.md`, and the auto-memory note `translate-figures-as-english-svg`.

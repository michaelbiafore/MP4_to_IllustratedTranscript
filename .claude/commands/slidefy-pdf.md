# Slidefy PDF — Convert a Research Paper / Report PDF to a Slide Deck

Extract text + every captioned figure and table from a PDF, then assemble a self-contained reveal.js slide deck. Every figure and table in the source must appear in the deck.

**Arguments**: $ARGUMENTS

## Argument Parsing

Parse the arguments as: `<pdf_path> [num_slides] [--slug NAME] [--dpi N] [--out DIR]`

- **pdf_path** (required): Absolute or relative path to a PDF file (research paper, white paper, report, etc.)
- **num_slides** (optional): Target number of slides (default: **30**). Figures get dedicated slides, so a deck with many figures will be slightly larger than N.
- **--slug** (optional): Override the slug used for output filenames. Default: derived from the PDF stem with non-alphanumerics replaced by `_`, max 80 chars.
- **--dpi** (optional): Render DPI for figure crops (default: **220**). Lower (e.g. 150) for very long papers; higher (e.g. 300) when figures contain small text.
- **--out** (optional): Output directory for extracted text + figures (default: `Input/`). The final HTML lands in `Output/Slides/` regardless.

Examples:
```
/slidefy-pdf "A:/VR/2026/Spatial Computing_202401_35pp.pdf"
/slidefy-pdf "Refs/some_paper.pdf" 24
/slidefy-pdf paper.pdf 40 --dpi 260
```

## Agent Delegation Policy

When delegating to sub-agents:
- **Never use `run_in_background: true`** for agents whose job is writing output files. Background agents may execute in isolated worktrees whose writes do not persist.
- After any sub-agent writes a file, verify with `ls -la` in the main working directory. If missing, rewrite directly.
- Prefer doing the slide assembly **in the main agent** — the deck structure depends on the paper's content and is hard to spec exactly to a sub-agent.

## Pipeline

```
PDF  →  extract_pdf_content.py  →  RAW_PAPER.md + figs/*.png + manifest.json
                                            ↓
                                   read + plan outline
                                            ↓
                                   build_pdf_deck.py (or direct HTML write)
                                            ↓
                                  Output/Slides/{slug}_{N}_SLIDES.html
```

## Instructions

### Phase 0 — Resolve paths and prerequisites

1. **Resolve the PDF path**. If a bare filename was given, search `Input/`, `Refs/`, then the current directory.
2. **Verify Python deps**:
   ```bash
   .venv/Scripts/python.exe -c "import fitz; print('pymupdf', fitz.__version__)"
   ```
   If missing, install:
   ```bash
   .venv/Scripts/pip3.exe install pymupdf
   ```
   `pymupdf` is declared in `pyproject.toml`. This repo is self-sufficient — do NOT invoke any Python interpreter from other packages.
3. **Derive the slug** from the PDF stem (lowercase optional, non-alphanumerics → `_`, max 80 chars). Honor `--slug` if passed.

### Phase 1 — Extract text + figures

4. **Run the extractor**:
   ```bash
   .venv/Scripts/python.exe scripts/extract_pdf_content.py "<pdf_path>" --out Input --slug "<slug>" --dpi 220
   ```
   Produces:
   - `Input/{slug}_RAW_PAPER.md` — full per-page text with inline `![Figure N: …]({slug}_figs/figN_…png)` references
   - `Input/{slug}_figs/{fig|tab}NN_<slug>.png` — one PNG per captioned visual (Figures crop above the caption; Tables crop the table body)
   - `Input/{slug}_figs_manifest.json` — `[{page, kind, num, title, filename, relpath}, …]`

5. **Audit the extraction**:
   - Count figures vs tables: parse the manifest JSON.
   - **Visually review every PNG** with the Read tool (you are a multimodal model — actually look at each). Confirm each figure renders correctly and the table crops are tight (no body-text spillover). If any visual is clearly broken (e.g., empty white, or only a fragment), re-run extraction with `--dpi 300` or note it in the deck plan.
   - If the PDF has visuals **without captions** (e.g., a chart on page 1 with no "Figure 1:" line above/below), the extractor will not find them. Spot-check by skimming page text for lines like "as shown above" or visual references that don't have matching extracted images. Most academic PDFs caption everything; reports / slide decks often do not.

### Phase 2 — Plan the slide outline

6. **Read the extracted markdown**: `Input/{slug}_RAW_PAPER.md`. Identify:
   - Title, authors/source, arxiv ID or DOI, publication date.
   - Abstract / executive summary.
   - Major sections (H2 lines in the PDF — usually numbered `1. Introduction`, `2. Background`, etc.).
   - Key statistics — dollar amounts, percentages, year ranges, "N×" multipliers. These become **big-number slides**.
   - Memorable quotes or strong assertions (rare in papers — common in reports).
   - **Every figure and every table** — these MUST each get a dedicated slide.

7. **Compose a slide outline** targeting N slides:
   - **Slide 1**: Title — paper title, authors, source (arxiv ID + date), institution list.
   - **Slide 2**: "Why this matters" — the most striking number or claim in the paper. If the paper opens with a market size, growth rate, or scale-of-impact stat, lead with it.
   - **Slides 3 to N-1**: Content slides — sections, definitions, comparisons, deep-dives. Every figure and table from the source gets its own slide here, placed where it fits the narrative.
   - **Slide N**: Takeaway — the conclusion distilled to a single statement + the source citation.
   - **Figure/table slides count toward N.** If the paper has 9 figures+tables and N=30, you have ~21 text-driven slides for narrative.

8. **Apply Naked Presenter principles** (Garr Reynolds):
   - One idea per slide.
   - Minimal text; never bullet walls.
   - Big numbers as visual anchors — `<div class="bignum">$544B</div>`.
   - Storytelling flow between slides.
   - Card grids (`grid2`/`grid3`/`grid4`) for parallel comparisons.

### Phase 3 — Build the deck

9. **Generate the HTML** as a single self-contained file. Write a Python build script in `scripts/_build_{slug}_slides.py` (underscore-prefixed = one-off, project-specific) that:
   - Loads `.cache/reveal/reveal.min.css` and `.cache/reveal/reveal.min.js`.
   - Reads each figure PNG and base64-encodes it to a `data:image/png;base64,…` URI.
   - Emits a single HTML file with reveal.js inlined in `<style>…</style>` and `<script>…</script>` blocks.
   - Uses **no `class="fragment"`** — all content visible by default (email preview panes don't run reveal's fragment JS reliably).
   - Uses **no CDN refs** — recipients' corporate firewalls block them.
   - Outputs to `Output/Slides/{slug}_{N}_SLIDES.html`.

10. **Required HTML / CSS conventions** (see `scripts/_build_spatial_computing_slides.py` for a reference implementation):

    **Color scheme**:
    - Background: `#1a1a2e` (dark navy)
    - Card background: `#202044`
    - Primary text: `#eaeaf2`
    - Muted: `#9aa0c4`
    - Accent (blue): `#64b5f6`
    - Warning (red): `#ef5350`
    - Success (green): `#66bb6a`
    - Highlight (gold): `#ffca28`

    > **⚠️ Dark-background gotcha — set it on the right surfaces, then verify by rendering.**
    > Inlining reveal.js's core `reveal.css` *without* a dark theme (e.g. `black.css`) leaves reveal's built-in `.reveal-viewport{background-color:#fff}` and `.reveal{background:#fff}` in force. Setting only `body{background:#1a1a2e}` is **NOT enough** — the white viewport/`.reveal` paints on top of `body`, so the deck renders **white** (illegible light text). Force the dark color onto the actual surfaces with `!important`:
    > ```css
    > html,body{background:#1a1a2e!important}
    > .reveal-viewport{background:#1a1a2e!important}
    > .reveal{background:#1a1a2e!important}
    > .reveal .backgrounds,.reveal .slide-background{background-color:#1a1a2e!important}
    > ```
    > `grep` checks (no-CDN, base64, no-fragment) do **not** catch this — a white page passes them all. **Verify by headless-rendering the final file and sampling a corner pixel:**
    > ```
    > msedge --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=3500 \
    >   --window-size=900,600 --user-data-dir=<tmp> --screenshot=_chk.png "file:///<ABS path to .html>"
    > # then: corner pixel (6,6) must be dark (~26,26,46), not (255,255,255)
    > ```

    **Required CSS classes** (define these in a `<style>` block):
    - `.title` — centered title block
    - `.bignum` — 5em+ statistic display (with `.warn` / `.good` / `.gold` color variants)
    - `.kicker` — pill-shaped section label
    - `.card` — bordered content card (with `.good` / `.warn` / `.gold` border variants)
    - `.grid2`, `.grid3`, `.grid4` — CSS-grid layouts
    - `.figwrap` — figure container that constrains `max-height: 72vh`
    - `.quote` — italic blockquote
    - `.footer` — fixed bottom-right citation

    **Reveal.initialize options**:
    ```js
    Reveal.initialize({
      hash: true, history: false, controls: true, progress: true,
      slideNumber: 'c/t', transition: 'slide',
      width: 1280, height: 720, margin: 0.04,
      minScale: 0.2, maxScale: 1.6
    });
    ```

11. **Figure slide template**:
    ```html
    <section>
      <h2>[Context headline tying figure to narrative]</h2>
      <div class="figwrap">
        <img src="data:image/png;base64,...."/>
        <div class="cap">Figure N · [paper's caption text]</div>
      </div>
    </section>
    ```

12. **Run the build**:
    ```bash
    .venv/Scripts/python.exe scripts/_build_{slug}_slides.py
    ```

### Phase 4 — Verify

13. **Verify the output file exists and is well-formed**:
    ```bash
    ls -la "Output/Slides/{slug}_{N}_SLIDES.html"
    .venv/Scripts/python.exe -c "
    import re
    html = open(r'Output/Slides/{slug}_{N}_SLIDES.html', encoding='utf-8').read()
    print('sections     :', len(re.findall(r'<section[^>]*>', html)))
    print('cdn refs     :', len(re.findall(r'cdn\\.jsdelivr|cdn\\.', html)))
    print('fragment cls :', len(re.findall(r'class=\"[^\"]*fragment', html)))
    print('base64 imgs  :', len(re.findall(r'data:image/png;base64', html)))
    print('http scripts :', len(re.findall(r'<script[^>]*src=\"http', html)))
    print('http links   :', len(re.findall(r'<link[^>]*href=\"http', html)))
    "
    ```

    All checks must satisfy:
    - `sections` == target slide count
    - `cdn refs`, `fragment cls`, `http scripts`, `http links` == 0
    - `base64 imgs` >= count of unique figures referenced

14. **Report completion** to the user with:
    - Output filename and total slide count
    - Brief list of slide titles
    - File size
    - Reminder that the HTML is portable (inlined reveal + base64 figures)

## Quality Checklist

Before finalizing, verify:
- [ ] **Every figure and every table** from `{slug}_figs_manifest.json` appears as an `<img>` in the deck (count must match)
- [ ] Figure crops were visually reviewed (not just file-existence-checked)
- [ ] Title slide includes paper title, authors, source citation (arxiv ID + date), affiliations
- [ ] At least one big-number slide if the paper contains striking quantitative claims
- [ ] No bullet has more than ~12 words; no slide has more than 6 bullets
- [ ] Card grids used for parallel content (sectors, projects, comparisons)
- [ ] Color classes applied consistently (highlight=blue, warning=red, success=green, gold=accent)
- [ ] **No CDN refs** — `cdn.jsdelivr` count is 0
- [ ] **No fragment classes** — `class="fragment"` count is 0
- [ ] **All images base64-inlined** — no `<img src="../">` paths
- [ ] reveal.js CSS + JS inlined from `.cache/reveal/`
- [ ] Output landed in `Output/Slides/` and `ls -la` confirms non-zero size

## Notes

- **The Spatial Computing paper** (arxiv 2402.07912, Jan 2024) is the canonical reference case. See `scripts/_extract_spatial_computing_pdf.py` and `scripts/_build_spatial_computing_slides.py` — both are working examples of the pipeline.
- **Why a Python build script and not direct HTML writing?** A 30-slide deck with 9 base64-inlined figures is ~3 MB of text. Generating it via a Python script that reads the figures from disk is far cheaper (in tokens) than typing the base64 strings inline in HTML.
- **Why dedicated figure slides instead of inset images?** Research-paper figures are dense — they need full screen real estate to be legible. Inset images shrink them below readability.
- **What if the PDF has zero captioned figures?** The extractor will still produce the markdown. Build a text-only deck and tell the user the deck is figure-free.
- **What if a figure is in vector form and renders fuzzily at 220 DPI?** Re-run extraction with `--dpi 300`. The captured PNG embedded in the HTML will be larger but legibility improves.

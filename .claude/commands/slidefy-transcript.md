# Slidefy Transcript

Convert a formatted transcript into a summarized reveal.js slide deck.

**Arguments**: $ARGUMENTS

## Agent Delegation Policy

When delegating work to sub-agents:
- **Never use `run_in_background: true`** for agents whose primary job is writing output files. Background agents may execute in isolated worktrees whose writes do not persist to the main working directory.
- If a sub-agent is used for file writing, **always verify the output file exists** (via `ls -la`) in the main working directory after the agent returns — do not trust the agent's self-report.
- If verification fails, rewrite the file directly rather than re-launching another agent.

## Argument Parsing

Parse the arguments as: `<input_file> [num_slides]`

- **input_file** (required): Path to a formatted transcript (typically `*_FORMATTED_TRANSCRIPT.md`)
- **num_slides** (optional): Target number of slides to generate (default: 12)

Examples:
```
/slidefy-transcript Output/My_Video_FORMATTED_TRANSCRIPT.md 10
/slidefy-transcript My_Video_FORMATTED_TRANSCRIPT.md
```

## Instructions

1. **Resolve the input file path**:
   - If the path contains only a filename (no directory), look in `Output/Formatted/` directory
   - If the path contains a full path, use that path directly

2. **Read and analyze the formatted transcript**:
   - Identify the main title and speakers/source
   - **Extract the source URL** (look for a `**URL:**` line near the top of the formatted transcript)
   - Extract the Key Takeaways table (if present)
   - Identify all H2 (`##`) sections as major topics
   - Note any statistics, percentages, or quantitative claims (these become "big number" slides)
   - Extract memorable quotes marked with blockquotes (`>`)
   - **Inventory all figures**: Find all `![Figure N: Caption](path)` images in the source — these MUST all appear in the slides

3. **Detect if the source is a book summary**:
   - If the source contains multiple chapters (e.g., `## 1.`, `## 2.`, `## Chapter N`, or numbered H2 sections spanning many topics), treat it as a **book source**.
   - **Book-specific counting rules** (these slide types do NOT count toward the target N):
     - **Figure slides** — figures placed on their own dedicated slides
     - **Chapter title/divider slides** — slides that introduce a new chapter or major section
   - Only substantive content slides count toward N. The total slide count in the deck will be higher than N.
   - **Coverage check**: ensure ALL chapters from the source are represented in the slides — do not skip any chapter.

4. **Plan the slide structure** to fit approximately N slides:
   - **Slide 1**: Title slide with main title, speaker/source attribution, **source URL**, and **total slide count** including the breakdown (e.g., "124 slides (89 content + 35 figures)")
   - **Slides 2 to N-1**: Content slides covering key topics
   - **Slide N**: Closing slide with key question or call-to-action

5. **Select content for each slide** using these prioritization rules:
   - Prioritize content from the Key Takeaways table
   - Include slides with **big numbers** (statistics, percentages, dollar amounts)
   - Include at least one **memorable quote** slide
   - Combine related minor topics; expand critical topics
   - Omit sponsor breaks, asides, and tangential content

6. **Apply Naked Presenter principles** (Garr Reynolds):
   - **One idea per slide** — never more
   - **Minimal text** — 6 words or fewer per bullet when possible
   - **Big numbers as visual anchors** — statistics get their own prominent display
   - **Impact over information** — distill to the emotional/memorable core
   - **Storytelling over bullet walls** — use narrative flow between slides

7. **Generate the HTML slide deck** using reveal.js 5.1.0:

   **Required structure**:
   ```html
   <!DOCTYPE html>
   <html lang="en">
   <head>
       <meta charset="UTF-8">
       <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <title>[Slide Deck Title]</title>
       <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
       <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/black.css">
       <style>
           /* Custom styles */
       </style>
   </head>
   <body>
       <div class="reveal">
           <div class="slides">
               <section><!-- Slide 1 --></section>
               <section><!-- Slide 2 --></section>
               <!-- ... -->
           </div>
       </div>
       <script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
       <script>Reveal.initialize({ hash: true, slideNumber: true, transition: 'fade', center: true });</script>
   </body>
   </html>
   ```

   **Color scheme**:
   - Background: `#1a1a2e` (dark navy)
   - Primary text: `#eee` (light gray)
   - Accent/highlight: `#64b5f6` (blue)
   - Warning/negative: `#ef5350` (red)
   - Success/positive: `#66bb6a` (green)

   > **⚠️ Dark-background gotcha — set it on the right surfaces, then verify by rendering.**
   > The template above keeps `theme/black.css` (which supplies the dark bg). But if a portable build **inlines reveal's core `reveal.css` without `black.css`**, reveal's built-in `.reveal-viewport{background-color:#fff}` and `.reveal{background:#fff}` take over. Setting only `body{background:#1a1a2e}` is **NOT enough** — the white viewport/`.reveal` paints over `body`, so the deck renders **white** (illegible light text). Force the dark color onto the actual surfaces with `!important`:
   > ```css
   > html,body{background:#1a1a2e!important}
   > .reveal-viewport{background:#1a1a2e!important}
   > .reveal{background:#1a1a2e!important}
   > .reveal .backgrounds,.reveal .slide-background{background-color:#1a1a2e!important}
   > ```
   > `grep` checks (no-CDN, base64, no-fragment) do **not** catch this — a white page passes them all. **Verify by headless-rendering the final file and sampling a corner pixel** (`(6,6)` must be ~`(26,26,46)`, not `(255,255,255)`):
   > ```
   > msedge --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=3500 \
   >   --window-size=900,600 --user-data-dir=<tmp> --screenshot=_chk.png "file:///<ABS path to .html>"
   > ```

   **CSS classes to use**:
   - `.big-number` — for prominent statistics (font-size: 5em, color: blue)
   - `.highlight` — for emphasized phrases (color: blue)
   - `.warning` — for negative/caution items (color: red)
   - `.success` — for positive items (color: green)
   - `.three-col` with `.col` children — for 3-column layouts
   - `.attribution` — for source citations (smaller, gray)

8. **Slide type templates**:

   **Title Slide**:
   ```html
   <section>
       <h1>[Main Title]</h1>
       <h3>[Subtitle if applicable]</h3>
       <div class="attribution">
           <div class="speaker-box">[Speaker/Source info]</div>
           <p style="margin-top:0.5em;"><a href="[Source URL]" style="color:#888; font-size:0.9em;">[Source URL]</a></p>
           <p style="color:#666; font-size:0.8em;">[N] slides</p>
       </div>
   </section>
   ```

   **Big Number Slide**:
   ```html
   <section>
       <h2>[Context headline]</h2>
       <div class="big-number">40%</div>
       <p>[What the number means]</p>
   </section>
   ```

   **Quote Slide**:
   ```html
   <section>
       <h2>[Topic]</h2>
       <blockquote>"[Memorable quote from transcript]"</blockquote>
       <p class="attribution">— [Speaker]</p>
   </section>
   ```

   **Bullet Slide** (use sparingly):
   ```html
   <section>
       <h2>[Topic]</h2>
       <ul>
           <li>[Point 1 — 6 words max]</li>
           <li>[Point 2]</li>
           <li>[Point 3]</li>
       </ul>
   </section>
   ```

   **Comparison/Columns Slide**:
   ```html
   <section>
       <h2>[Comparison topic]</h2>
       <div class="three-col">
           <div class="col"><h4>[Option A]</h4><p>[Details]</p></div>
           <div class="col"><h4>[Option B]</h4><p>[Details]</p></div>
           <div class="col"><h4>[Option C]</h4><p>[Details]</p></div>
       </div>
   </section>
   ```

   **Figure Slide**:
   ```html
   <section>
       <h2>[Context or figure title]</h2>
       <img src="../../Input/{slug}_figs/fig_01.png" alt="Figure 1: Caption" style="max-height: 70vh;">
       <p class="attribution">[Caption or source]</p>
   </section>
   ```

9. **Handle figures — MANDATORY**:
   - **ALL figures from the source MUST appear in the slides** — do not omit any
   - Place figures on slides where they naturally fit the topic being discussed
   - If a figure doesn't fit naturally into the N main slides, add it as an **extra slide after slide N**
   - Use the Figure Slide template above
   - For Substack articles with charts/data visualizations, these often deserve their own dedicated slides

   **Figure path resolution — CRITICAL**:
   - The slide HTML lives in `Output/Slides/`. All `<img src="">` paths must be **relative from that directory** to the actual image file on disk.
   - **Always verify the actual directory structure** before generating paths. Run `ls` on the image directory to confirm what exists. Do NOT assume subdirectories (e.g., `assets/`, `media/`) exist — check first.
   - For images inside this repo (e.g., Substack `_figs/` folders): use `../../Input/{slug}_figs/fig_01.png`
   - For images in external directories (outside this repo): compute the correct relative path from `Output/Slides/` to the actual file. Example: if images are at `A:/Packages/OtherRepo/images/fig.png`, the path from `Output/Slides/` is `../../../OtherRepo/images/fig.png`.
   - **After generating all `<img>` tags**, grep the output for every unique image directory prefix used and verify each one resolves to an existing directory on disk. This catches stale or invented subdirectories before the user sees broken images.
   - Common pitfall: source markdown may reference paths like `images/assets/foo.png` but the actual files may all be flat in `images/foo.png` — always trust `ls`, not the source paths.
   - **Unicode smart quotes in paths**: Article titles fetched from the web may contain Unicode curly/smart quotes (`'` U+2018, `'` U+2019, `"` U+201C, `"` U+201D) in directory names. These look identical to ASCII quotes in terminal output but are different bytes. If an `<img src>` path uses ASCII `'` (U+0027) but the actual directory has `'` (U+2018) / `'` (U+2019), the image will silently fail to load. **Always check `ls | xxd`** on the figs directory name if it contains any quote-like characters, and URL-encode the Unicode bytes in the `src` attribute (e.g., `'` → `%E2%80%98`, `'` → `%E2%80%99`).
   - **Base64 image inlining for portability**: When the user requests a self-contained/portable HTML (e.g., "compile images into the HTML", "display on a remote system"), embed images as base64 data URIs (`data:image/jpeg;base64,...`). Convert large PNGs to JPEG (quality 85, max 1280px wide) first to keep file size reasonable — this typically achieves 90-95% size reduction. Use `scripts/convert_images_jpeg.py` as a reference implementation.
   - **CRITICAL — Image replacement ordering bug**: When replacing or converting base64 images in an existing HTML file, **NEVER match images by positional index** (e.g., "the Nth `data:image` URI in the HTML corresponds to the Nth file when sorted alphabetically"). The order of images in the HTML follows **presentation order** (e.g., cover, then foreword figure, then chapter 1 figures...), which almost certainly differs from alphabetical directory listing order (e.g., `9781394220403.jpg, c01f001.png, ... c08f001.png, flast01f001.png`). This mismatch silently swaps every image after the first divergence point. Instead, **match by content fingerprint**: base64-encode the first ~200 bytes of each source file and compare against the base64 data in each `<img>` tag's `src` attribute. This is order-independent and guarantees each image is replaced with its correct JPEG counterpart.

10. **Write the output file**:
   - **Generate the output filename from the slide deck title** (the H1 on your title slide), NOT from the input filename:
     1. Take the main title of your slide deck
     2. Lowercase it, replace spaces with hyphens, strip punctuation except hyphens
     3. Truncate to ~6 words (enough to be recognizable, e.g., `executive-briefing-valve-got-lord`)
     4. Append `_{N}_SLIDES.html` where `{N}` is the total number of slides in the deck
   - Output to `Output/Slides/` directory as: `Output/Slides/{title_slug}_{N}_SLIDES.html`

11. **Verify output file exists on disk**:
   - Run `ls -la` on the output `.html` file
   - If the file is missing or zero bytes, the write failed — rewrite directly (do not re-delegate to a sub-agent)
   - This catches silent failures from worktree isolation or agent sandboxing

12. **Inline all images as base64 data URIs — MANDATORY for portability**:
   Slide decks are meant to be shared by email and viewed on remote systems. Relative paths like `../../Input/...` will not resolve on a recipient's machine — every image would render as a broken icon. Run the inliner to make the HTML fully self-contained:

   ```bash
   .venv/Scripts/python.exe scripts/embed_slide_images.py "Output/Slides/{title_slug}_{N}_SLIDES.html"
   ```

   The script:
   - Replaces every local `<img src>` with a `data:image/jpeg;base64,...` URI
   - Downsamples images wider than 1600px (keeps slide text legible at email-safe size)
   - Re-encodes as JPEG quality 85 (~90% size reduction for 4K captures)
   - Leaves `data:` URIs and `http(s)://` URLs untouched (reveal.js CDN stays)
   - Overwrites the HTML in place by default

   Options when fine-grained control is needed:
   - `--no-resize` — preserve native resolution (may exceed email limits for large decks)
   - `--max-width 1920` — higher cap when small-text legibility is critical
   - `--jpeg-quality 92` — higher fidelity at larger size
   - `--output path.html` — write the portable copy to a new file instead of overwriting

   **CRITICAL ordering note**: this inliner resolves paths relative to the HTML's directory and then re-encodes each image. It is the correct tool for slide decks with many same-format images. The ordering pitfall warned about in step 9 only applies when *replacing existing base64 blobs* by positional index — this script matches by src attribute, so it is safe.

   After this step the HTML is fully portable — it will display correctly via email, on a colleague's laptop, or on any system that cannot access the original image paths.

13. **Report completion**:
   - Confirm the output filename and slide count
   - List the slide titles generated
   - Report the final HTML file size from the inliner summary (confirms portability success)

## Quality Checklist

Before finalizing, verify:
- [ ] Total content slides approximately equals N (within ±2) — figure slides and chapter dividers do NOT count toward N
- [ ] Title slide includes proper attribution, source URL, and total slide count (with breakdown if book source)
- [ ] At least one big-number slide if statistics exist in source
- [ ] **ALL figures from source are included** — none omitted
- [ ] Figure paths are **verified against disk** — every unique image directory prefix confirmed to exist via `ls`
- [ ] No invented subdirectories in paths (e.g., `assets/` that doesn't actually exist)
- [ ] No slide has more than 3-4 bullet points
- [ ] No bullet point exceeds ~10 words
- [ ] Quotes are actual quotes from the transcript (not paraphrased)
- [ ] Color classes applied consistently (highlight=blue, warning=red, success=green)
- [ ] reveal.js CDN links are version 5.1.0
- [ ] **Images inlined as base64** — `embed_slide_images.py` ran successfully; `grep -c 'data:image' HTML` equals the `<img>` tag count; zero missing images reported
- [ ] **Book sources only**: ALL chapters from the source are represented — none skipped
- [ ] **Book sources only**: Image count in slides matches unique image count in source (verify with diff/grep)

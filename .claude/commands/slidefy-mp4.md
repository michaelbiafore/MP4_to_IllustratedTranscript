# Slidefy MP4 — Convert Formatted MP4 Transcript to Slide Deck

Convert a formatted transcript (from `/format-mp4`) with embedded screenshots into a summarized reveal.js slide deck.

**Arguments**: $ARGUMENTS

## Argument Parsing

Parse the arguments as: `<input_file> [num_slides]`

- **input_file** (required): Path to a formatted transcript (typically `*_FORMATTED_TRANSCRIPT.md`)
- **num_slides** (optional): Target number of slides to generate (default: 20)

Examples:
```
/slidefy-mp4 Output/Formatted/20260409_204007_FORMATTED_TRANSCRIPT.md 30
/slidefy-mp4 20260409_204007_FORMATTED_TRANSCRIPT.md
```

## Agent Delegation Policy

When delegating work to sub-agents:
- **Never use `run_in_background: true`** for agents whose primary job is writing output files. Background agents may execute in isolated worktrees whose writes do not persist to the main working directory.
- If a sub-agent is used for file writing, **always verify the output file exists** (via `ls -la`) in the main working directory after the agent returns — do not trust the agent's self-report.

## Instructions

1. **Resolve the input file path**:
   - If the path contains only a filename (no directory), look in `Output/Formatted/` directory
   - If the path contains a full path, use that path directly

2. **Derive the slug** from the filename (everything before `_FORMATTED_TRANSCRIPT`).

3. **Read and analyze the formatted transcript**:
   - Identify the main title and speakers/source
   - Extract the Key Takeaways table (if present)
   - Identify all H2 (`##`) sections as major topics
   - Note any statistics, percentages, or quantitative claims (these become "big number" slides)
   - Extract memorable quotes marked with blockquotes (`>`)
   - **Inventory ALL figures**: Find every `![Figure N: Caption](path)` image in the formatted transcript. Count them. Every figure MUST appear as an `<img>` tag somewhere in the slide deck.

4. **Visually review the screenshots**: Read each unique screenshot referenced in the transcript using the Read tool. Classify each into:

   - **High-value visuals** — charts, graphs, architecture diagrams, dashboards with metrics, data tables, code with significant content, documentation pages, UI workflows. These get **standalone screenshot slides** with large display.
   - **Standard content** — VS Code with code/docs, terminal output, file trees. These get embedded as **smaller inset images alongside text**.
   - **Near-duplicates** — two frames showing nearly the same content. Place **side-by-side on a single slide**.

5. **Plan the slide structure** to fit approximately N slides:
   - **Slide 1**: Title slide with main title, speaker/source, and total slide count
   - **Slides 2 to N-1**: Content slides covering key topics
   - **Slide N**: Closing slide with key question or call-to-action
   - If there are more high-value screenshots than fit in N slides, **increase the total** to accommodate — never omit a screenshot to hit the target.

6. **Select content for each slide** using these prioritization rules:
   - Prioritize content from the Key Takeaways table
   - Include slides with **big numbers** (statistics, percentages, dollar amounts)
   - Include at least one **memorable quote** slide
   - **Integrate screenshots** into topic slides where they naturally fit
   - Combine related minor topics; expand critical topics
   - Omit tangential content, small talk, and administrative chatter

7. **Apply Naked Presenter principles** (Garr Reynolds):
   - **One idea per slide** — never more
   - **Minimal text** — 6 words or fewer per bullet when possible
   - **Big numbers as visual anchors** — statistics get their own prominent display
   - **Impact over information** — distill to the emotional/memorable core
   - **Storytelling over bullet walls** — use narrative flow between slides

8. **Generate the HTML slide deck** using reveal.js 5.1.0:

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

           /* Lightbox: click any image to view full-size */
           section img { cursor: pointer; }
           #lightbox-overlay {
               display: none; position: fixed;
               top: 0; left: 0; width: 100vw; height: 100vh;
               background: rgba(0,0,0,0.92); z-index: 9999;
               justify-content: center; align-items: center;
               cursor: zoom-out;
           }
           #lightbox-overlay.active { display: flex; }
           #lightbox-overlay img {
               max-width: 95vw; max-height: 92vh; border-radius: 8px;
               box-shadow: 0 0 40px rgba(100,181,246,0.3); object-fit: contain;
           }
           #lightbox-caption {
               position: fixed; bottom: 12px; left: 50%; transform: translateX(-50%);
               color: #aaa; font-size: 0.8em; background: rgba(0,0,0,0.7);
               padding: 4px 16px; border-radius: 4px; max-width: 80vw;
               text-align: center; pointer-events: none;
           }
       </style>
   </head>
   <body>
       <div class="reveal">
           <div class="slides">
               <section><!-- Slide 1 --></section>
               <!-- ... -->
           </div>
       </div>
       <!-- Lightbox overlay (click any image to expand, click again or Escape to close) -->
       <div id="lightbox-overlay">
           <img id="lightbox-img" src="" alt="">
           <div id="lightbox-caption"></div>
       </div>
       <script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
       <script>
           Reveal.initialize({ hash: true, slideNumber: true, transition: 'fade', center: true });
           // Lightbox
           const _ov = document.getElementById('lightbox-overlay');
           const _im = document.getElementById('lightbox-img');
           const _cp = document.getElementById('lightbox-caption');
           document.querySelectorAll('.reveal section img').forEach(img => {
               img.addEventListener('click', e => {
                   e.stopPropagation();
                   _im.src = img.src; _cp.textContent = img.alt || '';
                   _ov.classList.add('active');
               });
           });
           _ov.addEventListener('click', () => { _ov.classList.remove('active'); _im.src = ''; });
           document.addEventListener('keydown', e => {
               if (e.key === 'Escape' && _ov.classList.contains('active')) {
                   _ov.classList.remove('active'); _im.src = '';
               }
           });
       </script>
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

9. **Slide type templates**:

   **Title Slide**:
   ```html
   <section>
       <h1>[Main Title]</h1>
       <h3>[Subtitle if applicable]</h3>
       <div class="attribution">
           <div class="speaker-box">[Speaker/Source info]</div>
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
       <blockquote>"[Actual quote from transcript — never paraphrased]"</blockquote>
       <p class="attribution">— [Speaker]</p>
   </section>
   ```

   **High-Value Screenshot Slide** (charts, diagrams, dashboards):
   ```html
   <section>
       <h2>[Topic]</h2>
       <img src="../../Input/{slug}_figs_filtered/frame_XXXmYYs_screen_NNN.jpg"
            alt="Figure N: Caption"
            style="max-height: 55vh; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
       <p style="color:#aaa; font-size:0.7em; margin-top:0.3em;">[Caption]</p>
   </section>
   ```

   **Content + Inset Screenshot Slide** (code, docs, terminal):
   ```html
   <section>
       <h2>[Topic]</h2>
       <div style="display:flex; align-items:center; gap:1.5em;">
           <img src="../../Input/{slug}_figs_filtered/frame_XXXmYYs_screen_NNN.jpg"
                alt="Figure N: Caption"
                style="max-height:25vh; border-radius:8px; flex-shrink:0;">
           <div style="text-align:left;">
               <p>[Key point from this section]</p>
           </div>
       </div>
   </section>
   ```

   **Near-Duplicate Pair Slide** (side-by-side):
   ```html
   <section>
       <h2>[Topic]</h2>
       <div style="display:flex; gap:1em; justify-content:center;">
           <img src="..." style="max-height:50vh; border-radius:8px;" alt="...">
           <img src="..." style="max-height:50vh; border-radius:8px;" alt="...">
       </div>
       <p style="color:#aaa; font-size:0.7em;">[Caption]</p>
   </section>
   ```

   **Bullet Slide** (use sparingly):
   ```html
   <section>
       <h2>[Topic]</h2>
       <ul>
           <li>[Point — 6 words max]</li>
           <li>[Point]</li>
           <li>[Point]</li>
       </ul>
   </section>
   ```

10. **Figure path resolution — CRITICAL**:
    - The slide HTML lives in `Output/Slides/`. All `<img src="">` paths must be **relative from that directory**.
    - For screenshots: `../../Input/{slug}_figs_filtered/frame_*.jpg`
    - **Before writing the output file**: Run `ls Input/{slug}_figs_filtered/` and count the `.jpg` files. Then count the `<img` tags in your generated HTML. Log both counts. If they don't match, add the missing screenshots.

11. **Write the output file**:
    - **Generate the output filename from the slide deck title** (the H1 on your title slide), NOT from the input filename:
      1. Take the main title of your slide deck
      2. Lowercase it, replace spaces with hyphens, strip punctuation except hyphens
      3. Truncate to ~6 words (enough to be recognizable)
      4. Append `_{N}_SLIDES.html` where `{N}` is the total number of slides in the deck
    - Output to `Output/Slides/{title_slug}_{N}_SLIDES.html`
    - Create `Output/Slides/` directory if needed

12. **Verify output file exists**:
    - Run `ls -la` on the output `.html` file
    - If missing or zero bytes, rewrite directly

13. **Inline all images as base64 data URIs — MANDATORY for portability**:
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
    - `--no-resize` — preserve native resolution (may exceed email limits for 4K decks with many frames)
    - `--max-width 1920` — higher cap when small-text legibility is critical (useful for decks that include code/UI/spreadsheet screenshots)
    - `--jpeg-quality 92` — higher fidelity at larger size
    - `--output path.html` — write the portable copy to a new file instead of overwriting

    **Expected size**: for 100+ 4K screenshots at defaults, the output HTML typically lands around 10 MB — well within email attachment limits. Report this number.

    After this step the HTML is fully portable — it will display correctly via email, on a colleague's laptop, or on any system that cannot access the original image paths.

14. **Report completion**:
    - Confirm the output filename and slide count
    - List the slide titles generated
    - Note how many screenshot figures were included vs total available
    - Report the final HTML file size from the inliner summary (confirms portability success)

## Quality Checklist

Before finalizing, verify:
- [ ] Total slides approximately equals N (within ±3), plus extra if needed for screenshots
- [ ] Title slide includes proper attribution and total slide count
- [ ] At least one big-number slide if statistics exist in source
- [ ] Screenshots were visually reviewed and classified (high-value vs content vs near-duplicate)
- [ ] **ALL screenshot figures from source are included** — none omitted
- [ ] Figure paths use `../../Input/{slug}_figs_filtered/` and are verified against disk
- [ ] No slide has more than 3-4 bullet points
- [ ] No bullet point exceeds ~10 words
- [ ] Quotes are actual quotes from the transcript (not paraphrased)
- [ ] Color classes applied consistently (highlight=blue, warning=red, success=green)
- [ ] reveal.js CDN links are version 5.1.0
- [ ] **Images inlined as base64** — `embed_slide_images.py` ran successfully; `grep -c 'data:image' HTML` equals the `<img>` tag count; zero missing images reported; final HTML file size recorded

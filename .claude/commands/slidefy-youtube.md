# Slidefy YouTube Transcript with Screenshots

Convert a formatted YouTube transcript (with video screenshots) into a summarized reveal.js slide deck that includes the captured screenshots as figure slides.

**Arguments**: $ARGUMENTS

## Argument Parsing

Parse the arguments as: `<input_file> [num_slides]`

- **input_file** (required): Path to a formatted transcript (typically `*_FORMATTED_TRANSCRIPT.md`)
- **num_slides** (optional): Target number of slides to generate (default: 12)

Examples:
```
/slidefy-youtube Output/Formatted/My_Video_FORMATTED_TRANSCRIPT.md 10
/slidefy-youtube My_Video_FORMATTED_TRANSCRIPT.md
```

## Instructions

1. **Resolve the input file path**:
   - If the path contains only a filename (no directory), look in `Output/Formatted/` directory
   - If the path contains a full path, use that path directly

2. **Read and analyze the formatted transcript**:
   - Identify the main title and speakers/source
   - **Extract the source URL** (look for a `**URL:**` line near the top)
   - Extract the Key Takeaways table (if present)
   - Identify all H2 (`##`) sections as major topics
   - Note any statistics, percentages, or quantitative claims (these become "big number" slides)
   - Extract memorable quotes marked with blockquotes (`>`)
   - **Inventory ALL figures — CRITICAL**: Find every `![Figure N: Caption](path)` image in the formatted transcript. Also run `ls` on the corresponding `Input/{slug}_figs/` directory to confirm the actual files on disk. Every `.jpg` file in that directory MUST appear as an `<img>` tag somewhere in the slide deck. If the formatted transcript references 25 figures, the slides MUST contain 25 `<img>` tags (one per figure). These are video screenshots from `/fetch-youtube`.

3. **Plan the slide structure** to fit approximately N slides:
   - **Slide 1**: Title slide with main title, speaker/source attribution, **source URL**, and **total slide count**
   - **Slides 2 to N-1**: Content slides covering key topics
   - **Slide N**: Closing slide with key question or call-to-action

4. **Select content for each slide** using these prioritization rules:
   - Prioritize content from the Key Takeaways table
   - Include slides with **big numbers** (statistics, percentages, dollar amounts)
   - Include at least one **memorable quote** slide
   - **Integrate screenshot figures** into topic slides where they naturally fit
   - Combine related minor topics; expand critical topics
   - Omit sponsor breaks, asides, and tangential content

5. **Apply Naked Presenter principles** (Garr Reynolds):
   - **One idea per slide** — never more
   - **Minimal text** — 6 words or fewer per bullet when possible
   - **Big numbers as visual anchors** — statistics get their own prominent display
   - **Impact over information** — distill to the emotional/memorable core
   - **Storytelling over bullet walls** — use narrative flow between slides

6. **Generate the HTML slide deck** using reveal.js 5.1.0:

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
   > If the portable build inlines reveal's core `reveal.css` *without* a dark theme (`black.css`), reveal's built-in `.reveal-viewport{background-color:#fff}` and `.reveal{background:#fff}` stay in force. Setting only `body{background:#1a1a2e}` is **NOT enough** — the white viewport/`.reveal` paints over `body` and the deck renders **white** (illegible light text). Force the dark color onto the actual surfaces with `!important`:
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

7. **Slide type templates**:

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

   **Screenshot Slide** (for video frame captures):
   ```html
   <section>
       <h2>[Topic from this section]</h2>
       <img src="../../Input/{slug}_figs/frame_XXXmYYs_Topic.jpg" alt="Figure N: Caption" style="max-height: 55vh; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
       <p style="color:#aaa; font-size:0.7em; margin-top:0.3em;">[Brief caption or key point from this section]</p>
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

8. **Handle screenshot figures — MANDATORY, DO NOT SKIP ANY**:
   - **ALL figures from the formatted transcript MUST appear in the slides** — do not omit any. If there are 25 figures, there must be 25 `<img>` tags in the HTML output.
   - If the target slide count is N but there are more screenshots than would fit, **increase the total slide count** to accommodate all screenshots. It is NEVER acceptable to omit a screenshot to hit the target count.
   - Screenshots provide visual context from the actual video — they add significant value.

   **Classify screenshots by visual content before placing them:**

   Before laying out slides, review every screenshot (use the Read tool on each `.jpg` file) and classify each into one of two categories:

   - **High-value visuals** — charts, graphs, maps, data tables, bar charts, line plots, infographics, article headlines, editorial cartoons, photographs of places/things, any frame that is NOT the presenter's head and torso. These are the frames the user actually wants to see.
   - **Talking-head frames** — the presenter speaking to camera, which are visually identical across dozens of captures.

   **Presentation rules by category:**

   *High-value visuals* get **standalone screenshot slides** with large display:
   ```html
   <section>
       <h2>[Topic]</h2>
       <img src="..." alt="..." style="max-height: 60vh; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
       <p style="color:#aaa; font-size:0.7em;">[Caption describing what the chart/graphic shows]</p>
   </section>
   ```

   *Talking-head frames* are **embedded compactly within content slides** at smaller size, alongside text:
   ```html
   <section>
       <h2>[Topic]</h2>
       <div style="display:flex; align-items:center; gap:1.5em;">
           <img src="..." alt="..." style="max-height:25vh; border-radius:8px; flex-shrink:0;">
           <div style="text-align:left;">
               <p>[Key point from this section]</p>
           </div>
       </div>
   </section>
   ```

   *Near-duplicate pairs* (two frames ≤5 seconds apart showing the same content — common when a topic-boundary and extra-timestamp overlap) go **side-by-side on a single slide**:
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

   This classification-first approach ensures charts and data visuals are prominently displayed while talking-head frames don't bloat the deck with visually redundant full-screen slides.

   **Figure path resolution — CRITICAL**:
   - The slide HTML lives in `Output/Slides/`. All `<img src="">` paths must be **relative from that directory**.
   - For screenshots: use `../../Input/{slug}_figs/frame_*.jpg`
   - **Before writing the output file**: Run `ls Input/{slug}_figs/` and count the `.jpg` files. Then count the `<img` tags in your generated HTML. These two numbers MUST match. If they don't, you have omitted screenshots — go back and add the missing ones.

9. **Write the output file**:
   - **Generate the output filename from the slide deck title** (the H1 on your title slide), NOT from the input filename:
     1. Take the main title of your slide deck
     2. Lowercase it, replace spaces with hyphens, strip punctuation except hyphens
     3. Truncate to ~6 words (enough to be recognizable)
     4. Append `_{N}_SLIDES.html` where `{N}` is the total number of slides in the deck
   - Output to `Output/Slides/` directory as: `Output/Slides/{title_slug}_{N}_SLIDES.html`

10. **Inline all images as base64 data URIs — MANDATORY for portability**:
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
    - `--max-width 1920` — higher cap when small-text legibility is critical
    - `--jpeg-quality 92` — higher fidelity at larger size
    - `--output path.html` — write the portable copy to a new file instead of overwriting

    After this step the HTML is fully portable — it will display correctly via email, on a colleague's laptop, or on any system that cannot access the original image paths.

11. **Report completion**:
    - Confirm the output filename and slide count
    - List the slide titles generated
    - Note how many screenshot figures were included
    - Report the final HTML file size from the inliner summary (confirms portability success)

## Quality Checklist

Before finalizing, verify:
- [ ] Total slides approximately equals N (within ±2), plus any extra figure slides
- [ ] Title slide includes proper attribution, source URL, and total slide count
- [ ] At least one big-number slide if statistics exist in source
- [ ] **ALL screenshot figures from source are included** — none omitted
- [ ] Figure paths are **verified against disk** — `Input/{slug}_figs/` confirmed to exist
- [ ] No slide has more than 3-4 bullet points
- [ ] No bullet point exceeds ~10 words
- [ ] Quotes are actual quotes from the transcript (not paraphrased)
- [ ] Color classes applied consistently (highlight=blue, warning=red, success=green)
- [ ] reveal.js CDN links are version 5.1.0
- [ ] **Images inlined as base64** — `embed_slide_images.py` ran successfully; `grep -c 'data:image' HTML` equals the `<img>` tag count; zero missing images reported

# MP4+WizWhisp — Collate a Local MP4 and Its Transcript into a Formatted Transcript + Slide Deck

Turn a **local screen-recording MP4** (e.g. from EaseUS RecExperts) plus its **transcript** (e.g. from WizWhisp / WizScribe, or any `MM:SS text` timestamped file) into a polished, self-contained **formatted transcript** (Markdown + portable HTML) and a **portable HTML slide deck**, with the genuinely *interesting* screenshots inserted as figures at the right points.

This command bakes in the procedure and house style proven across the project's recent decks (Kieran Klaassen, Vibe Coders, Agent Teams, tmux). It is platform-specific to this Windows machine (uses the project `.venv` and a WinGet ffmpeg).

**Arguments**: $ARGUMENTS

## Argument Parsing

Parse as: `<mp4_path> <transcript_path> [--interval SEC] [--title "..."] [--slides N] [--no-html] [--no-cleanup]`

- **mp4_path** (required): Absolute or relative path to the MP4.
- **transcript_path** (optional but normally given): Path to a transcript file. Two accepted forms:
  - A **timestamped text file** — one segment per line, `MM:SS  text` or `HH:MM:SS text` (this is what WizWhisp/`*_timestamped.txt` exports look like). Preferred.
  - Omitted → pull from the **WizWhisp SQLite DB** (see "Transcript from the WizWhisp DB" below) by matching the MP4 basename.
- **--interval SEC** (optional): Seconds between frame captures. **Default 5.** Lower for fast screen changes, higher for slow slide talks.
- **--title "..."** (optional): Override the H1 title; otherwise derive it from the content.
- **--slides N** (optional): Target slide count. If omitted, use **as many slides as the content needs** (never drop a figure to hit a target).
- **--no-html** (optional): Skip the HTML transcript build (still writes the Markdown).
- **--no-cleanup** (optional): Keep raw frames and contact sheets; otherwise offer to delete them at the end (present sizes, let the user choose — never auto-delete).

Derive the **slug** from the MP4 filename without extension, replacing spaces with underscores (e.g. `tmux_ONDREJ_20260608_031152`). All intermediate paths use this slug.

---

## Core principle — what counts as an "interesting" screenshot

Sample the MP4 at the interval and keep a frame **only** if it is unique AND informative. A frame is **NOT** interesting (drop it) if it is:

1. **A human / body part** — talking heads, people standing, hands hovering over a keyboard or screen, or any frame whose content is a person rather than readable screen content. (A styled terminal/editor composited over a *faded* hands-on-keyboard background is fine — that is screen content, not a hands shot.)
2. **A duplicate** of a slide/screen already kept from an earlier timestamp.
3. **A partial reveal** of a slide/screen that appears more completely at a later timestamp — keep the most complete version.
4. **A logo or an advertisement** — brand cards, sponsor reads, course-promo b-roll, channel end-screens.

Use **all** the interesting frames you find — in *both* the formatted transcript and the slide deck. Do not trim to keep the document short, and do not pad. Place each figure in the transcript **as near as possible to the moment it appears** in the recording.

---

## Phase 0 — Prerequisites

1. **Python**: use the project venv `.venv/Scripts/python.exe` (NOT `python3` — not on PATH here). Verify deps:
   ```
   .venv/Scripts/python.exe -c "import PIL, imagehash, cv2; print('OK')"
   ```
   Install if missing: `.venv/Scripts/pip3.exe install opencv-python-headless imagehash Pillow`.
2. **ffmpeg / ffprobe**: usually at
   `C:/Users/<user>/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe` (and `ffprobe.exe` beside it). If absent, `winget install --id Gyan.FFmpeg -e` and locate the binary by searching the WinGet Packages folder. The binary may not be on PATH in the current shell — invoke it by full path.
3. **pandoc**: `pandoc --version` (3.x expected).
4. **Cached reveal.js** (for the portable deck): `.cache/reveal-5.1.0/reveal.css` and `reveal.js` (v5.1.0). If absent, `.cache/reveal/reveal.min.css` / `reveal.min.js` also work; otherwise download v5.1.0 into `.cache/reveal/`.
5. **Theme file**: `Refs/formatted_transcript_style.html` (the emerald HTML theme). Required for the HTML transcript.

---

## Phase 1 — Probe the video

```
"$FFPROBE" -v quiet -print_format json -show_format -show_streams "<mp4>"
```
Record duration, resolution, fps. Compute the expected frame count ≈ `duration / interval` so you know how many contact sheets to expect.

---

## Phase 2 — Extract frames (the long pole — run in the background)

Native resolution preserves text readability. Frame `N` ≈ `(N-1) * interval` seconds.
```
mkdir -p "Input/{slug}_figs"
"$FFMPEG" -i "<mp4>" -vf "fps=1/<interval>" -q:v 2 "Input/{slug}_figs/frame_%04d.jpg" -y -loglevel error
```
Run this **in the background** and do Phase 3 (transcript) while it runs.

### Transcript

- **If `transcript_path` is a timestamped text file**: read it directly. Format is `MM:SS  text` (or `HH:MM:SS text`) per line. This is the source of truth — do not re-run Whisper.
- **If no transcript was given (WizWhisp DB fallback)**: the DB is at
  `C:\Users\<user>\AppData\Local\Packages\49657NowSmartStudio.WizScribe_agnvvc9c4qtza\LocalCache\Local\WizWhisp\TaskHistory.db`.
  Table `TaskHistory` columns: `Id, Name, FilePath, ResultItemsJson`. Find the row whose `Name`/`FilePath` matches the MP4 basename; `ResultItemsJson` is a JSON list of `{"Start":"HH:MM:SS.fff","End":"...","Text":"..."}`. Export to `Input/{slug}_RAW_TRANSCRIPT.txt` as `[M:SS] text` per non-empty segment (convert Start → total seconds → `M:SS`). See `scripts/_export_wizwhisp.py` for a working template.

Read the **entire** transcript before curating frames — the spoken content tells you what each screen is and where section boundaries fall. Note the speaker(s): a single-narrator tutorial is written as flowing prose (no speaker labels); an interview/multi-speaker recording uses bold speaker labels (`**Name:**`).

---

## Phase 3 — Build contact sheets, then curate by eye

1. **Build labeled contact sheets** so you can review every frame fast:
   ```
   .venv/Scripts/python.exe scripts/mp4wizwhisp_montage.py "Input/{slug}_figs" "Input/_montage_{slug}" <interval>
   ```
   This writes `sheet_NN.jpg` (6×8 grid, each thumb labeled `#index  M:SS`).
2. **Read every contact sheet** with the Read tool. Note candidate frame numbers for anything that looks unique and informative.
3. **Confirm at full resolution**: open each candidate `Input/{slug}_figs/frame_NNNN.jpg` with the Read tool before keeping it. This is where you apply the four exclusion rules, resolve near-duplicates (keep the most complete), reject partial reveals (find the fully-revealed frame), and write a concrete caption describing exactly what is on screen.
4. Build the **picks list**: an ordered list of `[frame_index, caption]` in the order the figures should appear in the document (normally chronological; you may place a frame shown later but topically belonging earlier — e.g. an intro graphic — where it reads best, and note the real timestamp in the caption). Write it to `Input/{slug}_picks.json` as a JSON array, e.g.
   ```json
   [[33, "The chat-room interface ..."], [71, "The classifier result ..."]]
   ```

> Captions must be specific (what app, what command, what is shown), written from your full-res review — never "Screenshot at 12:00".

---

## Phase 4 — Materialize the curated figures + manifest

```
.venv/Scripts/python.exe scripts/mp4wizwhisp_curate.py "Input/{slug}_figs" "Input/{slug}_figs_filtered" "Input/{slug}_frames_manifest.json" <interval> "Input/{slug}_picks.json"
```
This copies each pick to `Input/{slug}_figs_filtered/frame_{MMM}m{SS}s_screen_{NNN}.jpg` and writes the manifest (figure_num, filename, timestamp, total_seconds, original_frame, caption_hint).

---

## Phase 5 — Write the formatted Markdown

Output to `Output/Formatted/{Title_Case_With_Underscores}_FORMATTED_TRANSCRIPT.md`. Derive the filename from the H1 title (lowercase→Title_Case, ~6 words), not from the slug.

### Header block
```
# {Title Derived from Content}

**Source:** {what kind of recording}
**Presenter:** {name(s)} {— role/affiliation if known}
**Runtime:** ~{Hh MMm}
**Figures:** {N} live-demo screenshots drawn from the recording

> This is a lightly cleaned, verbatim transcript ... Timestamps (`*[~MM:SS]*`) mark roughly five-minute intervals from the start. {List any transcription artifacts you corrected.}
```

### Table of Contents
- A bulleted TOC with anchor links, nested H2 → H3.
- **Anchor convention (pandoc 3.6.x):** lowercase, spaces → `-`, drop `&`, `,`, `'`, `:`, `—`, parentheses, `?`. **pandoc KEEPS the dot `.`** (so "Opus 4.6" → `#opus-4.6-...`). Never double a hyphen. Prefer anchor-safe headings (alphanumerics, spaces, and `vs` without a period) to avoid surprises — the Phase 6 link check is the backstop.

### Body
- **Detect topic changes** from BOTH the transcript text and the screenshots; use `##`/`###` sections.
- **Lightly cleaned verbatim**: keep the speaker's words and phrasing; remove only filler (`um`, `uh`), false starts, and dead repetition. Do not summarize away content. Condense chit-chat/asides into `>` blockquotes. For multi-speaker recordings, label speakers in bold; for a monologue, write flowing prose.
- **Correct obvious transcription artifacts** (mis-heard product names, etc.) and note the notable fixes in the intro blockquote. Lightly mask gratuitous profanity in these professional deliverables.
- **Timestamps** `*[~MM:SS]*` under each major section at ~5-minute intervals.
- **Figures** at the moment each screen appears:
  ```
  ![Figure N: Specific caption](../../Input/{slug}_figs_filtered/frame_MMMmSSs_screen_NNN.jpg)
  ```
  Use **every** figure from the manifest, numbered in document order.
- Use `>` blockquotes for memorable quotes, **bold** for tools/commands/key terms, bullet lists for enumerations, `---` between major sections.

### Footer
- A **Key Takeaways** table (`| Concept | Summary |`), one row per major theme.

---

## Phase 6 — Build the portable HTML transcript (house "emerald" theme)

Must be fully self-contained (works after emailing to a machine with no shared paths or CDN). Build **from `Output/Formatted/`** so the `../../Input/...` image paths resolve:
```
pandoc -f markdown-implicit_figures "{Title}_FORMATTED_TRANSCRIPT.md" \
  -s --embed-resources \
  -H "../../Refs/formatted_transcript_style.html" \
  --metadata title="{Title}" \
  -o "{Title}_FORMATTED_TRANSCRIPT.html"
```
- `-H` appends the emerald theme AFTER pandoc's default CSS (don't use `--css`). `--embed-resources` base64-inlines every image. `-f markdown-implicit_figures` keeps images inline.

**Verify (do not skip):**
- Figures embedded: `grep -c 'data:image'` == number of figures.
- Portable: `grep -c 'src="\.\.'` == **0** (no external image refs).
- Theme applied: file contains `#059669` and `apple-system`.
- **Every TOC link resolves** — compare generated heading ids against TOC hrefs; the diff must be empty:
  ```bash
  grep -oE '<h[123] id="[^"]+"' f.html | sed -E 's/.*id="([^"]+)"/\1/' | sort -u > ids
  grep -oE 'href="#[^"]+"'      f.html | sed -E 's/href="#([^"]+)"/\1/' | sort -u > hrefs
  comm -23 hrefs ids   # MUST be empty; if not, fix the TOC hrefs to match the generated ids
  ```

---

## Phase 7 — Build the portable HTML slide deck (reveal.js, fully inlined)

Naked-Presenter style; **must be email-portable** — reveal.js inlined (no CDN), all images base64, no fragment classes.

1. **Write the deck source** to `Output/Slides/_{slug}_deck_src.html` with:
   - Two `<style>` blocks: the first containing the literal marker `/*REVEAL_CSS*/`, the second your custom theme. A `<script>` block containing `/*REVEAL_JS*/`, then a second `<script>` with `Reveal.initialize`.
   - **Color scheme:** dark navy `#1a1a2e` bg, light `#eee` text, blue accent `#64b5f6`, red `#ef5350`, green `#66bb6a`. Sans-serif (`-apple-system, "Segoe UI", Roboto, …`).
   - One `<section>` per slide. Title slide; big-number slides for statistics; quote slides (verbatim quotes); high-value screenshot slides; the occasional 3-column or bullet slide. **One idea per slide, minimal text.**
   - Include **every** figure from the manifest as an `<img class="shot" src="../../Input/{slug}_figs_filtered/frame_*.jpg" alt="Figure N: ...">`.
   - `Reveal.initialize({ hash: true, slideNumber: true, transition: 'fade', center: true });` — **transition must be `fade`**, never slide/shuffle. **No `class="fragment"`** anywhere (content must be visible without JS toggling).
   - A click-to-zoom **lightbox** for `section img.shot` (overlay div + the small JS handler).
2. **Inline reveal.js** (marker replacement → final file):
   ```
   .venv/Scripts/python.exe scripts/inline_reveal.py "Output/Slides/_{slug}_deck_src.html" "Output/Slides/{Title}_{N}_SLIDES.html"
   ```
3. **Base64-inline every image** (MANDATORY for portability):
   ```
   .venv/Scripts/python.exe scripts/embed_slide_images.py "Output/Slides/{Title}_{N}_SLIDES.html"
   ```
4. **Verify:** section count == N; `grep -c 'data:image'` == img count; `grep -c 'src="\.\.'` == 0; `grep -c 'cdn.jsdelivr'` == 0; `grep -c 'class="fragment'` == 0; `grep -c "transition: 'fade'"` >= 1. Report the final file size.
5. **Delete the temp source** `Output/Slides/_{slug}_deck_src.html`.

---

## Phase 8 — Report & cleanup

- Report: runtime/resolution, transcript segment/word counts, raw → kept frame counts (with what was excluded by which rule), output file paths and sizes, and all verification results.
- **Keep**: `Output/Formatted/*.{md,html}`, `Output/Slides/*_SLIDES.html`, and `Input/{slug}_figs_filtered/` (the `.md` references the filtered figs; the `.html` files have them embedded).
- **Offer to delete** (unless `--no-cleanup`; present sizes, let the user choose — never auto-delete): raw frames `Input/{slug}_figs/` (large), contact sheets `Input/_montage_{slug}/`, and the temporary `Input/{slug}_picks.json`.

---

## Quality Checklist

- [ ] Frames sampled at the interval; every contact sheet reviewed; every kept frame confirmed at full resolution.
- [ ] Kept frames are all unique + informative; humans/body-parts, duplicates, partial reveals, and logos/ads excluded.
- [ ] **All** interesting frames used in BOTH the transcript and the deck; figures placed at the right moments; captions are specific.
- [ ] Header block + intro blockquote + Key Takeaways table present; speakers handled (labels vs prose); artifacts corrected and noted.
- [ ] Timestamps at ~5-min intervals.
- [ ] HTML transcript: emerald theme applied, every image base64-embedded, zero external refs, **every TOC link resolves** (`comm` check empty).
- [ ] Slide deck: reveal.js inlined (zero CDN), all images base64, no fragment classes, `transition: 'fade'`, lightbox present, section count reported.
- [ ] Files named `{Title_Case}_FORMATTED_TRANSCRIPT.{md,html}` in `Output/Formatted/` and `{Title_Case}_{N}_SLIDES.html` in `Output/Slides/`.

## Reusable scripts this command uses
- `scripts/mp4wizwhisp_montage.py` — raw frames → labeled contact sheets
- `scripts/mp4wizwhisp_curate.py` — picks.json → `*_figs_filtered/` + manifest
- `scripts/inline_reveal.py` — inline cached reveal.js v5.1.0 into the deck source
- `scripts/embed_slide_images.py` — base64-inline all slide images
- `scripts/_export_wizwhisp.py` — WizWhisp DB → RAW_TRANSCRIPT.txt (fallback when no transcript file is given)
- `Refs/formatted_transcript_style.html` — the emerald HTML transcript theme

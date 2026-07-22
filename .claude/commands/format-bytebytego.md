# Format ByteByteGo Session — Local MP4 + WizWhisp Transcript → Portable Formatted Transcript

Turn a **local screen-recording of a ByteByteGo "Build with Claude Code" session** (or any similar lecture/office-hours/Zoom recording) plus its **WizWhisp (WizScribe) transcript** into a polished, self-contained markdown + HTML transcript with screenshots inserted at the right points.

This command bakes in all the design decisions used to produce the reference files in `Output/Formatted/`:

- `Build_with_Claude_Code_Session_1_Onboarding_Context_Skills_FORMATTED_TRANSCRIPT.{md,html}`
- `Build_with_Claude_Code_Session_2_Agentic_Engineering_FORMATTED_TRANSCRIPT.{md,html}`
- `Build_with_Claude_Code_Office_Hours_QA_FORMATTED_TRANSCRIPT.{md,html}`

**Arguments**: $ARGUMENTS

## Argument Parsing

Parse as: `<mp4_path> [--interval SEC] [--official-slides DIR] [--title "..."] [--no-html]`

- **mp4_path** (required): Absolute or relative path to the MP4 (e.g. a file under `C:/Users/biafo/Videos/EaseUS RecExperts/`).
- **--interval** (optional): Seconds between frame captures. Default **10** for these sessions (lots of fast screen changes). Use 15 for slower talks.
- **--official-slides DIR** (optional): A folder of pre-extracted official slide PNGs (e.g. `Input/BBG_ClaudeCode_02_hires_official_slides/`). When the presenter shows a real slide deck, insert these slides AND the live-demo screenshots. Office-hours / pure-Q&A recordings have no slides — omit this and use only live-demo screenshots.
- **--title** (optional): Override the H1 title. Otherwise derive it from the content.
- **--no-html** (optional): Skip the HTML build.

Derive the **slug** from the MP4 filename without extension (spaces → underscores), e.g. `BBG_ClaudeCode_03_hires_20260604_195833`.

---

## Phase 0 — Prerequisites

1. **Python**: use the project venv `.venv/Scripts/python.exe` (NOT `python3` — not on PATH on this Windows machine). Verify deps:
   ```
   .venv/Scripts/python.exe -c "import imagehash, PIL, cv2; print('OK')"
   ```
   Install if missing: `.venv/Scripts/pip3.exe install opencv-python-headless imagehash Pillow`.
2. **ffmpeg / ffprobe**: usually at
   `C:/Users/<user>/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe`
   (and `ffprobe.exe` beside it). If absent, `winget install --id Gyan.FFmpeg -e` and locate the binary.
3. **pandoc**: `pandoc --version` (3.x expected).

Run frame extraction (Phase 2, the long pole) **in the background** while you do Phase 1 in parallel.

---

## Phase 1 — Get the WizWhisp transcript (do NOT re-run Whisper)

WizWhisp/WizScribe stores transcripts in a **SQLite DB**, not a file. The MP4 folder will *not* contain a transcript — pull it from the DB.

1. **DB location**:
   `C:\Users\<user>\AppData\Local\Packages\49657NowSmartStudio.WizScribe_agnvvc9c4qtza\LocalCache\Local\WizWhisp\TaskHistory.db`
2. **Table `TaskHistory`** columns: `Id, Name, Category, FilePath, TaskAddedTime, AudioFileLength, ResultItemsJson`.
   Find the row whose `Name`/`FilePath` matches the MP4 (match on basename). `ResultItemsJson` is a JSON **list** of segments: `{"Start": "HH:MM:SS.fff", "End": "...", "Text": "..."}`.
3. **Export** to `Input/{slug}_RAW_TRANSCRIPT.txt` (one line per segment, `[M:SS] text`) and keep `Input/{slug}_transcript.json`. Convert `HH:MM:SS.fff` → total seconds → `[M:SS]`. Drop empty-text segments.

Write a small throwaway script (see `scripts/_export_wizwhisp.py` for a working template) rather than fighting shell quoting. Report segment count, runtime, and word estimate.

> **Why WizWhisp, not the base Whisper pass in `/fetch-mp4`?** WizWhisp gives a higher-quality, already-segmented transcript with real timestamps. Prefer the longest/most-detailed source — see the project's "pick the longest transcript source" preference.

---

## Phase 2 — Extract & curate frames (the key step)

These recordings are **Zoom/screen captures**: most of the runtime is a webcam ("talking head") with a participant filmstrip; the presenter only occasionally shares their screen. The figures you want are the **screen-share demos**, not faces.

1. **Extract** at the interval, native resolution:
   ```
   ffmpeg -i "<mp4>" -vf "fps=1/<interval>" -q:v 2 "Input/{slug}_figs/frame_%04d.jpg" -y -loglevel error
   ```
   Frame `N` ≈ `(N-1) * interval` seconds.

2. **Build contact sheets** to review everything fast (one image shows ~48 frames, each labeled `#index  M:SS`). Template: `scripts/_montage_bbg03.py` (6×8 grid, 300px thumbs, yellow labels). Read every sheet.

3. **Curate by eye** — keep a frame ONLY if it is unique AND interesting:
   - ✅ Keep: screen-shares of the terminal / Claude Code / browser / docs / diagrams / slides — anything with real content.
   - ❌ Drop: **talking heads**, video-off placeholders, near-duplicates of an already-kept frame, and **partial reveals** of a later, more-complete frame (keep the most complete one).
   - ❌ Drop: the **recorder's own desktop** — a screen recording sometimes catches the *viewer's* browser/File Explorer (e.g. a Zoom Notes page, an EaseUS folder). These are not the presenter's content; exclude them.
   - When a demo spans several near-identical frames, keep ONE representative (or two if they show genuinely different states, e.g. "menu open" vs. "result").

4. **Confirm at full resolution**: open each candidate frame with the Read tool before keeping it, so captions describe what's actually on screen.

5. **Materialize the curated set** into `Input/{slug}_figs_filtered/` with timestamped names `frame_{MMM}m{SS}s_screen_{NNN}.jpg`, and write `Input/{slug}_frames_manifest.json` (figure_num, filename, timestamp, total_seconds, original_frame, caption_hint). Template: `scripts/_curate_bbg03.py`. (For slow, slide-heavy talks you can instead run `scripts/filter_frames.py --threshold 20 --crop-right 15`, but for Zoom Q&A the manual montage pass is what works — pHash dedup can't tell a moving face from a static slide.)

> Use *all* the genuinely unique/interesting screenshots — don't trim to keep the doc short. The Office-Hours example kept 7 (out of 746 raw frames); Sessions 1–2 added official slides on top of live-demo shots.

---

## Phase 3 — Write the formatted markdown

Output to `Output/Formatted/{Title_Case_With_Underscores}_FORMATTED_TRANSCRIPT.md`. Match the reference files exactly:

### Header block (top of file)
```
# {Title Derived from Content}

**Source:** ByteByteGo "Build with Claude Code" — {which session} (screen-capture recording)
**Presenter:** John Kim
**Runtime:** ~{Hh MMm}
**Figures:** {N official slides + }M live-demo / aside screenshots drawn from the recording

> This is a lightly cleaned, verbatim transcript of the session. {Methodology sentence: where slides vs. screenshots come from.} Timestamps (`*[~MM:SS]*`) mark roughly five-minute intervals from the start of the recording. {If artifacts were corrected, list the notable fixes.}
```

### Table of Contents
- A bulleted TOC with anchor links, nested H2 → H3.
- **Anchor convention (pandoc 3.6.x):** lowercase, spaces → `-`, drop `&`, `,`, `'`, `:`, `—`, parentheses, `?`. **BUT pandoc 3.6.x KEEPS the dot `.`** — so "vs." → `vs.` and "CLAUDE.md" → `claude.md` in the id (e.g. `#prd-vs.-spec-and-managing-claude.md-joe`). Never double a hyphen. To avoid surprises, prefer writing "vs" without the period in headings; otherwise keep the dot in the TOC href.

### Body
- **Detect topic changes** from BOTH the transcript text and the screenshots. For a **lecture**, use lesson/topic sections. For **office hours / Q&A**, group by **theme**, one H2 (or H3) per question, and name the asker in the heading and prose (e.g. "Agent Teams vs. Subagents (Nati)").
- **Lightly cleaned verbatim**: keep the speaker's words and phrasing; remove only filler (`um`, `uh`), false starts, and dead repetition. Do not summarize away content. Condense attendee chit-chat into a `>` blockquote that sets up the question; keep the presenter's substantive answers close to verbatim.
- **Speaker labels** in bold: `**John:**`, `**Nati:**`, etc. Identify askers from context.
- **Correct obvious transcription artifacts** and note them in the intro blockquote. Recurring fixes in this course: "Clock/Clod code" → **Claude Code**, "claw.md" → **CLAUDE.md**, "Kavati" → **Karpathy**, "Yon" → **Yann LeCun**, "Obama" → **Ollama**, "Quinn" → **Qwen**, "Heiko" → **Haiku**, "spell kit" → **SvelteKit**, "Excalibur" → **Excalidraw**, "ByPico" → **ByteByteGo**, "Comet/Cody" → Meta's **Comet**.
- **Timestamps** `*[~MM:SS]*` (or `*[~H:MM:SS]*` for multi-hour) under each H2/major section at ~5-minute intervals. Drop the raw per-line Whisper timestamps.
- **Figures** at the moment each demo appears:
  ```
  ![Figure N: Specific caption describing what's on screen](../../Input/{slug}_figs_filtered/frame_MMMmSSs_screen_NNN.jpg)
  ```
  Captions must be concrete (what app, what command, what's shown) — written from your full-res review, never "Screenshot at 12:00". Place official slides (if any) at the point each is presented; place live-demo shots at the matching answer.
- Use `> blockquotes` for memorable quotes, **bold** for tools/commands/key terms, bullet lists for enumerations, `---` horizontal rules between major sections.

### Footer
- A **Key Takeaways** table (`| Concept | Summary |`) distilling the session's main points — one row per major theme.

---

## Phase 4 — Build the portable HTML (house "emerald" theme)

The HTML must be **fully self-contained** (works after emailing to a machine with no shared paths/CDN). Do NOT use plain pandoc defaults — apply the project theme.

1. The theme lives in **`Refs/formatted_transcript_style.html`** (a `<style>` block: emerald accent `#059669`, sans-serif `-apple-system, "Segoe UI", Roboto…`, 880px column, boxed TOC via `h2#table-of-contents + ul`, green blockquote left-bars, green table headers, images with border/radius/shadow). If that file is missing, recreate it from the Session 2 HTML's custom `<style>` block.
2. **Build from `Output/Formatted/`** (so the `../../Input/...` image paths resolve), embedding everything:
   ```
   pandoc -f markdown-implicit_figures "{Title}_FORMATTED_TRANSCRIPT.md" \
     -s --embed-resources \
     -H "../../Refs/formatted_transcript_style.html" \
     --metadata title="{Title}" \
     -o "{Title}_FORMATTED_TRANSCRIPT.html"
   ```
   - `-H` (include-in-header) appends the theme AFTER pandoc's default CSS so it overrides. Don't use `--css` (won't embed).
   - `--embed-resources` base64-inlines every image.
   - `-f markdown-implicit_figures` keeps images inline (no `<figure>` wrapping).

3. **Verify** (do not skip):
   - Figures embedded: `grep -c 'data:image'` == number of figures.
   - Portable: `grep -c 'src="\.\.'` == **0** (no external image refs).
   - Theme applied: file contains `#059669` and `-apple-system`.
   - **Every TOC link resolves** — compare generated `<h2/3 id="...">` against TOC `href="#..."`:
     ```bash
     grep -oE '<h[23] id="[^"]+"' f.html | sed -E 's/.*id="([^"]+)"/\1/' | sort -u > ids
     grep -oE 'href="#[^"]+"'   f.html | sed -E 's/href="#([^"]+)"/\1/' | sort -u > hrefs
     comm -23 hrefs ids   # must be empty
     ```
     If not empty, fix the TOC hrefs to match the generated ids (remember pandoc keeps the dots).

---

## Phase 5 — Report & cleanup

- Report: runtime/resolution, transcript segment/word counts, raw → kept frame counts, output file paths and sizes, and verification results.
- **Keep**: `Output/Formatted/*.{md,html}` and `Input/{slug}_figs_filtered/` (the `.md` references the filtered figs by relative path; the `.html` has them embedded).
- **Offer to delete** (don't auto-delete — present sizes and let the user choose): raw frames `Input/{slug}_figs/` (large), contact sheets `Input/_montage*/`, and optionally `Input/{slug}_transcript.json`.

---

## Quality Checklist

- [ ] Transcript pulled from the WizWhisp DB (not a fresh Whisper pass); timestamps preserved.
- [ ] Every kept screenshot was reviewed at full resolution; talking-heads, dupes, partial reveals, and the *viewer's own desktop* excluded.
- [ ] ALL genuinely unique/interesting screenshots used; captions are specific.
- [ ] Header block + intro blockquote + Key Takeaways table present; speakers labeled; artifacts corrected and noted.
- [ ] Timestamps at ~5-min intervals; figures at the right demo points.
- [ ] HTML: emerald theme applied, every image base64-embedded, zero external refs, every TOC link resolves.
- [ ] Files named `{Title_Case}_FORMATTED_TRANSCRIPT.{md,html}` in `Output/Formatted/`.

## Reference templates in this repo
- `scripts/_export_wizwhisp.py` — DB → RAW_TRANSCRIPT.txt
- `scripts/_montage_bbg03.py` — contact-sheet generator
- `scripts/_curate_bbg03.py` — copy curated frames + write manifest
- `scripts/filter_frames.py` — pHash dedup (slide-heavy talks only)
- `Refs/formatted_transcript_style.html` — the emerald HTML theme

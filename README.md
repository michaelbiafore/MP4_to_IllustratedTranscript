# Transcript2MDSlides

A content-processing pipeline that turns talks, articles, videos, and threads into two
portable outputs:

1. **Illustrated formatted transcripts** — clean, structured Markdown (+ standalone HTML)
   with figures/screenshots placed where they belong.
2. **Portable HTML slide decks** — self-contained reveal.js decks that render correctly
   even when emailed to someone with no JavaScript tooling installed (images can be
   inlined as base64).

Everything is driven by [Claude Code](https://claude.ai/code) **slash commands** defined
in `.claude/commands/`. Python helpers in `scripts/` are invoked automatically via
[`uv run`](https://docs.astral.sh/uv/) — no manual `pip install`.

Supported sources: **YouTube**, **Substack**, **generic web articles**, **local MP4s**,
**slide PDFs / research papers**, **Udemy courses you own**, **Discord channels**, and
**Perplexity threads**.

## Table of Contents

- [Prerequisites](#prerequisites)
- [The Pipeline at a Glance](#the-pipeline-at-a-glance)
- [Slash Commands](#slash-commands)
  - [Collation commands (MP4 / PDF → transcript + deck) — start here](#collation-commands-mp4--pdf--transcript--deck--start-here)
    - [`/MP4+FasterWhisp` — one argument, fully automated (recommended)](#mp4fasterwhisp--one-argument-fully-automated-recommended)
    - [`/MP4+WizWhisp` — bring your own transcript](#mp4wizwhisp--bring-your-own-transcript)
    - [`/PDFSlides+WizWhisp` — a slides PDF instead of a video](#pdfslideswizwhisp--a-slides-pdf-instead-of-a-video)
  - [Fetchers — acquire a source](#fetchers--acquire-a-source)
  - [Formatters — build an illustrated transcript](#formatters--build-an-illustrated-transcript)
  - [Slidifiers — build a portable slide deck](#slidifiers--build-a-portable-slide-deck)
  - [Discord tooling](#discord-tooling)
  - [Slide & figure utilities](#slide--figure-utilities)
- [End-to-End Examples](#end-to-end-examples)
- [Credential Setup](#credential-setup)
- [Directory Layout](#directory-layout)
- [File Naming Conventions](#file-naming-conventions)
- [Viewing & Exporting Slide Decks](#viewing--exporting-slide-decks)
- [Figure Path Handling in Slides](#figure-path-handling-in-slides)

---

## Prerequisites

- [Claude Code](https://claude.ai/code) CLI installed and authenticated
- [uv](https://docs.astral.sh/uv/) — manages Python + dependencies automatically on first `uv run`
- [pandoc](https://pandoc.org/installing.html) — converts formatted Markdown to HTML with a clickable TOC
- Google Chrome / Chromium — for viewing decks and for cookie extraction (Substack, Udemy, Discord)
- **ffmpeg** — a *system* ffmpeg on `PATH` is only needed by `/fetch-mp4`, `/MP4+WizWhisp`, and `/lecture-figs`. The recommended `/MP4+FasterWhisp` and all YouTube commands use a **bundled** ffmpeg via `imageio-ffmpeg` — no install required.
- **NVIDIA GPU (optional)** — `/MP4+FasterWhisp` transcribes on CUDA if it's available and falls back to CPU automatically. A GPU makes a ~2-hour video transcribe in minutes; CPU works but is slower.

```bash
git clone <your-fork-url> Transcript2MDSlides
cd Transcript2MDSlides
uv --version        # installs Python + deps automatically on first run
pandoc --version
```

No `npm install`, no `pip install` — `uv run` reads inline script metadata and provisions
dependencies on first use.

---

## The Pipeline at a Glance

Every source funnels into the same three stages:

```
  ┌─ Fetch ──────────┐   ┌─ Format ─────────────┐   ┌─ Slidefy ────────────┐
  │ acquire source → │ → │ illustrated Markdown │ → │ portable HTML deck   │ → PPTX (optional)
  │ Input/*_RAW_*    │   │ Output/Formatted/*   │   │ Output/Slides/*.html │
  └──────────────────┘   └──────────────────────┘   └──────────────────────┘
```

| Source | Fetch | Format | Slidefy |
|--------|-------|--------|---------|
| YouTube (text only) | `/fetch-transcript` | `/format-transcript` | `/slidefy-transcript` |
| YouTube (with screenshots) | `/fetch-youtube` | `/format-youtube` | `/slidefy-youtube` |
| Substack / web article | `/fetch-substack`, `/fetch-article` | `/format-transcript` | `/slidefy-transcript` |
| Local MP4 | `/fetch-mp4` | `/format-mp4` | `/slidefy-mp4` |
| Local MP4 (one command, auto-transcribed) | `/MP4+FasterWhisp` (transcribe + format **and** slidefy) | | |
| Local MP4 + your own transcript | `/MP4+WizWhisp` (does format **and** slidefy) | | |
| Slides PDF + transcript | `/PDFSlides+WizWhisp` (format) | | `/slidefy-pdf` |
| Udemy course | `/fetch-udemy` | `/format-transcript` | `/slidefy-transcript` |
| Book summary | (paste/​write) | `/format-summary` | `/slidefy-transcript` |
| Discord channel | `/fetch-discord` | `/format-transcript` | `/slidefy-transcript` |
| Perplexity thread | `/perp-to-md` | `/format-transcript` | `/slidefy-transcript` |

Convert any finished deck to PowerPoint with `/html2pptx_image`. Preview all slides as a
grid with `/gridify-slides`.

---

## Slash Commands

Run each inside Claude Code by typing `/` followed by the command name. `$ARGUMENTS`
below is whatever you type after the command. Every command reports what it wrote and where.

### Collation commands (MP4 / PDF → transcript + deck) — start here

These are the flagship commands: a **single run** produces *both* finished outputs — an
illustrated formatted transcript (Markdown + portable HTML) **and** a portable slide deck —
from one recording. The other commands (fetch / format / slidefy) are the individual stages
you reach for when you want finer control.

All three share the same **figure-curation rule**: a screenshot is kept only if it is
*unique and informative*. Talking-heads/webcam frames, duplicates, partial reveals of a
slide that appears more completely later, and logo/ad frames are dropped. Every kept figure
appears in **both** the transcript and the deck, placed at the moment it's discussed.

#### `/MP4+FasterWhisp` — one argument, fully automated (recommended)

Give it **just a path to an MP4** (on a local drive or a `\\network\share`) and it does
everything else: transcribe the audio, curate screenshots, and write both outputs. Nothing
to install beyond the repo, no GPU required, no purchased app.

**Syntax**
```
/MP4+FasterWhisp <mp4_path> [--model NAME] [--language CODE] [--device auto|cuda|cpu]
                 [--interval SEC] [--title "..."] [--slides N] [--no-html] [--no-cleanup]
```

**What it does, step by step**
1. **Transcribe (this command's addition).** `scripts/transcribe_mp4.py` extracts a clean
   16 kHz mono WAV with a *bundled* ffmpeg (so odd containers like EaseUS/OBS recordings
   decode fully), then runs **faster-whisper `large-v3-turbo`** — the same Whisper model
   WizWhisp's "Large" setting uses — with Silero VAD. It runs on your **GPU (CUDA) if
   available, otherwise CPU**, and writes `Input/{slug}_RAW_TRANSCRIPT.txt` (`[M:SS] text`
   per line) as the source of truth.
2. **Extract + dedupe frames.** Samples one frame every `--interval` seconds, then collapses
   them to the *unique screens* with a perceptual-hash pass (a 2-hour deck of ~3,000 frames
   typically reduces to ~100–150 candidates).
3. **Curate.** Reviews the candidates, keeps only the interesting ones, and writes specific
   captions.
4. **Write the transcript.** Structured Markdown (H1/H2/H3, TOC with working anchors,
   5-minute `*[~MM:SS]*` timestamps, blockquotes, Key Takeaways table) with every kept
   figure placed inline, then a **portable HTML** build via pandoc (all images base64-inlined).
5. **Build the deck.** A Naked-Presenter reveal.js deck with a slide for every kept
   screenshot, reveal.js inlined and images base64-embedded — **no CDN, emailable**.

**Options**

| Option | Default | Meaning |
|--------|---------|---------|
| `<mp4_path>` | — | The video. Local path or UNC `\\host\share\file.mp4` (copied to a temp file first). |
| `--model NAME` | `large-v3-turbo` | Whisper model. `large-v3` = max accuracy (slower/heavier); `medium`/`small` = faster drafts. |
| `--language CODE` | `en` | Spoken language. `auto` to detect. |
| `--device` | `auto` | `auto` picks CUDA if present else CPU; force with `cuda`/`cpu`. |
| `--interval SEC` | `5` | Seconds between sampled frames. Use **`2`** for dense screen-shares/coding; `10–15` for slow slide talks. |
| `--title "..."` | derived | Override the H1 title. |
| `--slides N` | as needed | Target deck size; never drops a figure to hit it. |
| `--no-html` | off | Skip the HTML transcript build (still writes Markdown). |
| `--no-cleanup` | off | Keep the raw frame dump and contact sheets instead of offering to delete them. |

**Examples**
```
/MP4+FasterWhisp Input/MyTalk.mp4                              # simplest: one argument
/MP4+FasterWhisp "\\NAS\recordings\Lecture.mp4" --interval 2  # network path, dense screen-share
/MP4+FasterWhisp Input/MyTalk.mp4 --model large-v3            # maximum transcription accuracy
/MP4+FasterWhisp Input/MyTalk.mp4 --device cpu --model small  # quick draft on a laptop with no GPU
```

**Produces**
```
Output/Formatted/{Title}_FORMATTED_TRANSCRIPT.md      # structured transcript
Output/Formatted/{Title}_FORMATTED_TRANSCRIPT.html    # portable (base64 images, emailable)
Output/Slides/{Title}_{N}_SLIDES.html                 # portable reveal.js deck
```

**First-run notes**
- The model (~1.6 GB) downloads from Hugging Face on first use and is cached for later runs.
  Downloads use the classic LFS CDN by default (`HF_HUB_DISABLE_XET=1`), which gets through
  firewalls that block HF's newer Xet transport; set `HF_HUB_DISABLE_XET=0` to re-enable Xet.
- On a modern NVIDIA GPU a ~2-hour recording transcribes in a few minutes; on CPU expect
  longer — use `--model small` for a fast first pass.

#### `/MP4+WizWhisp` — bring your own transcript

Same curation/format/slidefy pipeline as above, but **you supply the transcript** instead of
having the command generate it. Use this when you already have a hand-made transcript (e.g.
from the [WizWhisp/WizScribe](https://apps.microsoft.com/) desktop app) and want its exact
wording. This variant is **Windows/platform-specific**: it uses the project `.venv` and a
*system* ffmpeg (e.g. installed via `winget install Gyan.FFmpeg`).

**Syntax**
```
/MP4+WizWhisp <mp4_path> [transcript_path] [--interval SEC] [--title "..."]
              [--slides N] [--no-html] [--no-cleanup]
```

- **`transcript_path`** — a timestamped text file, one segment per line as `MM:SS  text` or
  `HH:MM:SS text` (the shape WizWhisp exports). This is the source of truth; it is *not*
  re-transcribed.
- If **omitted**, the command pulls the transcript straight from WizWhisp's local SQLite
  history DB, matching the MP4's file name.
- `--interval` defaults to **5**; other options match `/MP4+FasterWhisp`.

**Example**
```
/MP4+WizWhisp Input/MyTalk.mp4 Input/MyTalk_timestamped.txt
/MP4+WizWhisp Input/MyTalk.mp4                 # pull transcript from the WizWhisp DB by filename
```
Produces the same three output files as `/MP4+FasterWhisp`.

> **Which one?** Prefer **`/MP4+FasterWhisp`** for one-command automation, network paths, and
> portability (no purchased app, no manual step). Use **`/MP4+WizWhisp`** only when you want a
> specific hand-made transcript verbatim.

#### `/PDFSlides+WizWhisp` — a slides PDF instead of a video

The **no-video** sibling: pair a lecture's **slide-deck PDF** (authoritative figures, one
slide per page) with a timestamped transcript to build a formatted transcript that uses
**every slide**, placed where it's discussed. There's no frame extraction or curation — the
slides are already clean figures.

**Syntax**
```
/PDFSlides+WizWhisp <transcript_path> <slides_pdf_path> [--out NAME] [--title "..."]
                    [--no-html] [--jpeg-width N]
```

- `--out NAME` — output base name (else derived from the H1 title).
- `--jpeg-width N` — max width of the portable-HTML slide images (default **1600**).

**Example**
```
/PDFSlides+WizWhisp Input/lecture_timestamped.txt Input/lecture_slides.pdf --out 01_CellularSheaves
```
Produces `Output/Formatted/{name}.{md,html}`. (For a *deck* from a PDF, use `/slidefy-pdf`.)

### Fetchers — acquire a source

#### `/fetch-transcript <youtube-url>`
Download a YouTube transcript (text only) to `Input/{title}_RAW_TRANSCRIPT.md`.
```
/fetch-transcript https://youtu.be/W-jdh08zEGM
/fetch-transcript https://www.youtube.com/watch?v=UclrVWafRAI
```

#### `/fetch-youtube <youtube-url> [--no-video | --high-res] [--offset <sec>] [--timestamps t1,t2,...]`
Download the transcript **and** the video, detect topic boundaries, capture a screenshot
at each one, and inject `![Figure N: ...]` references into the raw transcript.
```
/fetch-youtube https://youtu.be/16zrEPOsIcI --offset 2
/fetch-youtube https://youtu.be/16zrEPOsIcI --no-video           # talking-head: skip frames
/fetch-youtube https://youtu.be/16zrEPOsIcI --high-res           # readable spreadsheets/diagrams
/fetch-youtube https://youtu.be/16zrEPOsIcI --timestamps 3:51,5:38,12:06
```
Produces `Input/{slug}_RAW_TRANSCRIPT.md`, `_topics.json`, `_figs/`, and `_video.mp4`.
`--offset` (default `13`) captures each frame N seconds *before* the topic change.

#### `/fetch-substack <substack-url>`
Download a Substack article (including paywalled posts you subscribe to) plus all images.
Requires `cookies_substack.json` for paywalled content — see [Credential Setup](#credential-setup).
```
/fetch-substack https://pragmaticengineer.substack.com/p/the-pulse-162
/fetch-substack https://substack.com/inbox/post/188532718
```
Produces `Input/{slug}_RAW_SUBSTACK.md` and `Input/{slug}_figs/`.

#### `/fetch-article <url>`
Download any generic web article (blog post, news, docs page) with its figures.
```
/fetch-article https://simonwillison.net/2025/some-post/
```
Produces `Input/{slug}_RAW_ARTICLE.md` and its figures. Substack URLs are auto-routed
through the Substack path; Gmail URLs use `cookies_gmail.json`.

#### `/fetch-mp4 <mp4_path> [--interval SEC] [--threshold N] [--crop-right PCT] [--whisper-model MODEL]`
Extract audio from a local video, transcribe it with Whisper, capture frames at an
interval, and perceptually deduplicate the screenshots.
```
/fetch-mp4 Input/MyZoomCall.mp4
/fetch-mp4 Input/MyTalk.mp4 --interval 10 --threshold 12 --crop-right 0 --whisper-model small
```
`--crop-right 15` ignores a webcam sidebar when deduping Zoom recordings.
Produces `Input/{slug}_RAW_TRANSCRIPT.txt` and `Input/{slug}_figs/`.

#### `/fetch-udemy <course_url> [--sections 1,3-5] [--lectures 2,4-6] [--list] [--login <email>] [--srt] [--ui]`
Download Udemy-provided captions for sections/lectures of a course **you own**.
```
/fetch-udemy https://www.udemy.com/course/some-slug/ --list                # print curriculum
/fetch-udemy https://www.udemy.com/course/some-slug/ --login you@email.com  # one-time login
/fetch-udemy https://www.udemy.com/course/some-slug/ --sections 1,3-5
```
Saves per-section (and combined) Markdown under `Input/`, ready for `/format-transcript`.

#### `/fetch-discord <channel_id> [--token <token>] [--after YYYY-MM-DD] [--before YYYY-MM-DD]`
Export a Discord channel (messages, @mentions, images, embeds, reactions) to a single
Markdown file for the format/slidefy pipeline. Token falls back to `cookies_discord.txt`.
```
/fetch-discord 1473401675510452285
/fetch-discord 1473401675510452285 --after 2026-01-01 --before 2026-04-01
```
Produces `Input/{slug}_RAW_ARTICLE.md` + `{slug}_figs/`. See [Credential Setup](#credential-setup).

#### `/perp-to-md <perplexity-url>`
Download a shared Perplexity conversation thread — each question/answer turn plus its cited
sources — as a single Markdown file in `Input/`. Then run `/format-transcript` on it.
```
/perp-to-md https://www.perplexity.ai/search/some-thread-id
```
Produces `Input/{slug}_RAW_ARTICLE.md`.

### Formatters — build an illustrated transcript

#### `/format-transcript <filepath>`
The general formatter. Turns any `RAW_TRANSCRIPT` / `RAW_SUBSTACK` / `RAW_ARTICLE` file into
structured Markdown: H1/H2/H3 hierarchy, TOC with anchors, 5-minute `*[~0:00]*` timestamps
(transcripts), bold key phrases, blockquotes, and a Key Takeaways table. Runs pandoc for HTML.
```
/format-transcript Input/My_Video_RAW_TRANSCRIPT.md
/format-transcript Input/the-pulse-162_RAW_SUBSTACK.md
```
Produces `Output/{name}_FORMATTED_TRANSCRIPT.md` (or `_FORMATTED_SUBSTACK.md`) + HTML.

#### `/format-youtube <filepath>`
Like `/format-transcript`, but also discovers every screenshot from `/fetch-youtube`
(scanning both the raw transcript and `Input/{slug}_figs/` on disk), places each figure at
the start of its section, fixes relative paths, and verifies **no screenshot is omitted**.
```
/format-youtube The_Engineering_that_Runs_the_Digital_World_RAW_TRANSCRIPT.md
```
Produces `Output/Formatted/{name}_FORMATTED_TRANSCRIPT.md` + HTML.

#### `/format-mp4 <slug_or_file>`
Format a raw Whisper transcript from `/fetch-mp4` into a structured document with the
deduplicated screenshots embedded.
```
/format-mp4 20260409_204007
/format-mp4 Input/MyTalk_RAW_TRANSCRIPT.txt
```
Produces `Output/Formatted/{name}_FORMATTED_TRANSCRIPT.md` + HTML.

#### `/format-summary <filepath>`
Turn a raw book-summary Markdown file into a structured document (chaptered headings, TOC,
key-idea callouts, Key Takeaways table) plus a portable HTML build, keeping any figures the
source references. Use it for book/report summaries rather than spoken transcripts.
```
/format-summary Input/Atomic_Habits_summary.md
```
Produces `Output/Formatted/{name}_FORMATTED.md` + HTML.

#### `/format-bytebytego <arguments>`
Specialized, house-style formatter for a **local MP4 lecture/office-hours recording + its
WizWhisp transcript** (originally the ByteByteGo "Build with Claude Code" sessions). Bakes
in frame-curation rules (drop talking heads, dupes, partial reveals, logos) and produces a
polished self-contained Markdown + HTML transcript with screenshots inserted at the right points.
```
/format-bytebytego Input/Session_1.mp4 Input/Session_1_wizwhisp.txt
```
For the general local-MP4 flow prefer `/MP4+WizWhisp` below.

### Slidifiers — build a portable slide deck

All slidifiers apply [Naked Presenter](https://www.presentationzen.com/) design (Garr
Reynolds): one idea per slide, minimal text, big numbers as anchors, dark theme
(navy `#1a1a2e`, blue `#64b5f6`, red `#ef5350`, green `#66bb6a`), reveal.js 5.1.0.

#### `/slidefy-transcript <filepath> [num_slides]`
Summarize any formatted transcript into a deck (default **12** slides).
```
/slidefy-transcript Output/My_Video_FORMATTED_TRANSCRIPT.md
/slidefy-transcript Output/My_Video_FORMATTED_TRANSCRIPT.md 15
```
Produces `Output/{name}_SLIDES.html`.

#### `/slidefy-youtube <filepath> [num_slides]`
Like `/slidefy-transcript`, but adds a dedicated **screenshot slide** for every captured
video frame and guarantees all of them appear (slide count grows to fit).
```
/slidefy-youtube Output/Formatted/My_Video_FORMATTED_TRANSCRIPT.md
```

#### `/slidefy-mp4 <filepath> [num_slides]`
Slidify a `/format-mp4` transcript with its embedded screenshots (default **20** slides).
```
/slidefy-mp4 Output/Formatted/MyTalk_FORMATTED_TRANSCRIPT.md 24
```

#### `/slidefy-pdf <pdf_path> [num_slides] [--slug NAME] [--dpi N] [--out DIR]`
Extract text and **every** captioned figure/table from a research paper or report PDF, then
assemble a self-contained deck (default **30** slides) in which every figure appears.
```
/slidefy-pdf Input/attention_is_all_you_need.pdf
/slidefy-pdf Input/report.pdf 40 --slug Q3Report --dpi 200
```
Produces `Output/Slides/{name}_SLIDES.html`.

### Discord tooling

#### `/discord-to-wiki <arguments>`
Mirror a Discord channel as a **per-message wiki**: one `.md` per message (YAML frontmatter +
body), a shared `images/`, plus `INDEX.md` and a resume marker. For Obsidian/Logseq/static
sites — *not* the format/slidefy pipeline (use `/fetch-discord` for that).
```
/discord-to-wiki 1473401675510452285
```

#### `/filter-discord <channel_id> <context query>`
Fetch a channel and return only the messages relevant to a context query, ranked, with a
2–3 paragraph synthesis at the top.
```
/filter-discord 1473401675510452285 "what did people decide about the backtest engine?"
```

### Slide & figure utilities

#### `/html2pptx_image <filepath>`
Inject an in-browser **Export to PPTX** button into a reveal.js deck. Clicking it screenshots
each slide (2× scale, fragments forced visible, `.slide-logo` overlaid) and downloads a 16:9
PPTX. Image-based — exact fidelity, non-editable text. Edits the HTML in place.
```
/html2pptx_image Output/My_Video_SLIDES.html
```

#### `/gridify-slides <filepath>`
Generate an HTML page showing all slides of a deck as a thumbnail grid — a fast way to review
a deck's flow.
```
/gridify-slides Output/My_Video_SLIDES.html
```

#### `/lecture-figs <mp4_path> [options]`
Extract *unique, interesting* still frames from a screen-recorded lecture (e.g., a Udemy
section recorded at 2×): drops talking heads, near-blank frames, logo-only slides, and
progressive-reveal duplicates, keeping the most-revealed frame in each run.
```
/lecture-figs Input/Section8_recording.mp4
```

---

## End-to-End Examples

**YouTube (text only):**
```
/fetch-transcript https://youtu.be/W-jdh08zEGM
/format-transcript Input/AI_Arms_Race..._RAW_TRANSCRIPT.md
/slidefy-transcript Output/AI_Arms_Race..._FORMATTED_TRANSCRIPT.md
```

**YouTube (with screenshots):**
```
/fetch-youtube https://youtu.be/16zrEPOsIcI --offset 2
/format-youtube The_Engineering_that_Runs_the_Digital_World_RAW_TRANSCRIPT.md
/slidefy-youtube Output/Formatted/The_Engineering_that_Runs_the_Digital_World_FORMATTED_TRANSCRIPT.md
```
The deck interleaves content slides with one screenshot slide per topic boundary.

**Substack (one-shot):**
```
Execute this pipeline: https://pragmaticengineer.substack.com/p/the-pulse-162 > fetch-substack | format-transcript | slidefy-transcript
```

**Local MP4 (both outputs at once):**
```
/MP4+WizWhisp Input/MyTalk.mp4 Input/MyTalk_timestamped.txt
```

**Slides PDF → transcript + deck:**
```
/PDFSlides+WizWhisp Input/lecture_timestamped.txt Input/lecture_slides.pdf --out 01_Lecture
/slidefy-pdf Input/lecture_slides.pdf
```

---

## Credential Setup

Credential files live in the **project root** and are **git-ignored** (see `.gitignore`).
Never commit them.

### Substack cookies (`cookies_substack.json`)
For paywalled posts you subscribe to:
1. Install the **EditThisCookie2** Chrome extension
   ([store link](https://chromewebstore.google.com/detail/editthiscookie2/fphepnmjojnkhmgejocfhlhibalewkef)).
2. Log in at [substack.com](https://substack.com) and open a paywalled post to confirm access.
3. Click the extension → **Export** → paste into `cookies_substack.json` at the project root.

Cookies expire — re-export if `/fetch-substack` starts returning truncated posts. The script
also checks `~/cookies_substack.json`. Free posts need no cookies.

### Discord token (`cookies_discord.txt`)
1. Enable **Developer Mode** (Discord → Settings → Advanced → Developer Mode).
2. Right-click the channel → **Copy Channel ID**.
3. Open <https://discord.com/app>, press **F12** → **Network**, filter `api`, click a channel,
   open any `discord.com/api` request → **Headers** → copy the `Authorization:` value.
4. Save that value (one line) to `cookies_discord.txt`, or pass it with `--token`.

> This token grants full access to your Discord account. Never commit or share it; rotate it
> (change your password) after use.

### Udemy cookies (`cookies_udemy.json`)
Run `/fetch-udemy <course_url> --login you@email.com` once to complete the email + 6-digit-code
login in a visible browser; the command saves `cookies_udemy.json` for subsequent runs.

---

## Directory Layout

| Path | Purpose |
|------|---------|
| `Input/` | Raw fetched sources and their image assets *(git-ignored)* |
| `Output/` | Formatted transcripts (`.md`, `.html`) and slide decks (`.html`) *(git-ignored)* |
| `scripts/` | General-purpose Python/shell helpers invoked by the commands via `uv run` |
| `examples/` | Archived per-project one-off build scripts, kept as reference *(git-ignored)* |
| `.claude/commands/` | The slash-command definitions Claude Code reads |
| `Refs/` | Reference docs: formatting examples, Naked Presenter principles, slide-format options |
| `Mandates/` | Process specs and prompt templates for pipeline stages |
| `Notes/`, `plans/` | Working notes and planning docs *(git-ignored)* |

---

## File Naming Conventions

| Pattern | Meaning |
|---------|---------|
| `*_RAW_TRANSCRIPT.{md,txt}` | Unformatted YouTube/MP4 transcript |
| `*_RAW_SUBSTACK.md` | Unformatted Substack article |
| `*_RAW_ARTICLE.md` | Unformatted web article / Discord export |
| `*_FORMATTED_TRANSCRIPT.md` | Structured transcript from a `format-*` command |
| `*_FORMATTED_SUBSTACK.md` | Structured Substack article |
| `*_SLIDES.html` | reveal.js slide deck from a `slidefy-*` command |
| `*.pptx` | Image-based PowerPoint export from `/html2pptx_image` |
| `*_figs/` | Figures for an article, or screenshot frames for a video |
| `*_topics.json` | Topic-boundary sidecar from `/fetch-youtube` |
| `*_video.mp4` | Downloaded YouTube video (temporary, deletable after frame extraction) |

---

## Viewing & Exporting Slide Decks

`*_SLIDES.html` files are self-contained reveal.js presentations:

1. Open the `.html` in any modern browser.
2. Navigate with arrow keys, spacebar, or swipe.
3. `F` fullscreen · `S` speaker notes · `Esc` slide overview · `?` all shortcuts.

**Export to PDF** (highest fidelity) with [Decktape](https://github.com/astefanutti/decktape):
```bash
npx decktape reveal Output/Slides/MyDeck_SLIDES.html Output/Slides/MyDeck.pdf --size 1123x794 --pause 2000
```
`--size 1123x794` = A4 landscape; `--size 1920x1080` = 16:9. Or append `?print-pdf` to the URL
in Chrome and `Ctrl/Cmd+P` (lower fidelity).

**Export to PPTX:** run `/html2pptx_image` on the deck, open it in a browser, click
**Export to PPTX**.

---

## Figure Path Handling in Slides

When a `slidefy-*` command writes `<img src="">` tags, paths must be **relative from where
the HTML lives** (`Output/Slides/`) to the real files on disk. Getting this wrong = broken images.

1. **Trust `ls`, not the source document.** Verify the actual image directory before
   generating paths — source Markdown may reference subdirs (`images/assets/foo.png`) that
   don't exist on disk (files may be flat in `images/foo.png`).
2. **Images inside this repo** (e.g., Substack `_figs/`):
   `Output/Slides/ → ../../ → repo root → Input/{slug}_figs/fig_01.png`, i.e.
   `src="../../Input/{slug}_figs/fig_01.png"`.
3. **Images outside this repo:** add another `../`, e.g.
   `src="../../../OtherRepo/images/fig.png"`.
4. **After generating**, grep every unique image-path prefix and confirm each resolves to a
   real directory — catches broken images before the user sees them.

For maximum portability (email), the slidifiers can inline images as base64 data URIs so the
single HTML file needs no external assets.

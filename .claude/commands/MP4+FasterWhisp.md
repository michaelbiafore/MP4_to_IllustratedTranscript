# MP4+FasterWhisp — One-Argument Local MP4 → Formatted Transcript + Slide Deck

Turn a **single local (or network) MP4** into a polished, self-contained **formatted
transcript** (Markdown + portable HTML) and a **portable HTML slide deck** — with the
genuinely *interesting* screenshots inserted as figures — **without a separately supplied
transcript**. This command transcribes the audio itself with **faster-whisper** (Whisper
`large-v3-turbo`, the same model WizWhisp's "Large" setting uses), then runs the exact same
curation/format/slidefy procedure as `/MP4+WizWhisp`.

**This is the portable, single-argument sibling of `/MP4+WizWhisp`.** Use it when you want
one command and no manual transcription step. Use `/MP4+WizWhisp` when you already have a
hand-made WizWhisp transcript and want its byte-for-byte output.

- **Accuracy:** identical model weights to WizWhisp "Large" (Whisper large-v3-turbo) + Silero
  VAD. No GPU required — faster-whisper uses CUDA if present, else CPU (int8).
- **Dependencies:** `faster-whisper` (in `pyproject.toml`; `uv run` installs it and downloads
  the model on first use). Frame extraction uses the bundled ffmpeg from `imageio-ffmpeg` — no
  system ffmpeg install required.

**Arguments**: $ARGUMENTS

## Argument Parsing

Parse as: `<mp4_path> [--model NAME] [--language CODE] [--device auto|cuda|cpu] [--interval SEC] [--title "..."] [--slides N] [--no-html] [--no-cleanup]`

- **mp4_path** (required): Absolute or relative path to the MP4. May be on a **local or
  network drive** (UNC `\\host\share\...` paths are copied to a local temp before decoding).
- **--model NAME** (optional): Whisper model. **Default `large-v3-turbo`** (WizWhisp parity).
  Use `large-v3` for maximum accuracy (slower/heavier), or `small`/`medium` for speed.
- **--language CODE** (optional): Spoken language. **Default `en`.** Pass `auto` to detect.
- **--device auto|cuda|cpu** (optional): **Default `auto`** (CUDA if available, else CPU).
- **--interval SEC** (optional): Seconds between frame captures. **Default 5.**
- **--title "..."**, **--slides N**, **--no-html**, **--no-cleanup**: same as `/MP4+WizWhisp`.

Derive the **slug** from the MP4 filename without extension, spaces → underscores. All
intermediate paths use this slug.

---

## Phase A — Transcribe the audio (this command's only addition)

Run the headless transcriber. It writes the timestamped transcript that the rest of the
pipeline treats as the **source of truth** (exactly the shape `/MP4+WizWhisp` expects):

```
uv run python scripts/transcribe_mp4.py "<mp4_path>" --model large-v3-turbo --language en --device auto
```

Outputs:
- `Input/{slug}_RAW_TRANSCRIPT.txt` — one segment per line, `[M:SS] text`
- `Input/{slug}_transcript.json` — raw `{start,end,text}` segments for tooling

Notes:
- On CPU, `large-v3-turbo` is usable but not instant; `large-v3` is markedly slower. Warn the
  user before starting a long CPU run and suggest `--model small` for a quick draft if desired.
- First run downloads the model from Hugging Face (cached under the user's HF cache). This is a
  one-time cost.
- **You may start Phase 1/Phase 2 (probe + frame extraction) in parallel with transcription** —
  they are independent. Just make sure the transcript exists before Phase 3 curation.

---

## Phases 1–8 — Identical to `/MP4+WizWhisp`

From here, **follow `/MP4+WizWhisp` Phases 1 through 8 exactly**, with two substitutions:

1. **Transcript source:** use `Input/{slug}_RAW_TRANSCRIPT.txt` produced in Phase A above.
   Skip that command's "Transcript from the WizWhisp DB" fallback entirely — there is no
   WizWhisp dependency here.
2. **ffmpeg / Python portability (public-repo friendly):** do **not** assume the WinGet ffmpeg
   path or a `.venv`. Instead:
   - Run Python via `uv run python ...` (as in Phase A and the rest of this repo).
   - For frame extraction, resolve ffmpeg portably: prefer `ffmpeg` on PATH; otherwise use the
     bundled binary from `imageio-ffmpeg`:
     ```
     uv run python -c "import imageio_ffmpeg, sys; sys.stdout.write(imageio_ffmpeg.get_ffmpeg_exe())"
     ```
     Use that path for the `-vf "fps=1/<interval>"` frame extraction in Phase 2.

Everything else is unchanged, and the same reusable scripts apply:
- `scripts/mp4wizwhisp_montage.py` — raw frames → labeled contact sheets
- `scripts/mp4wizwhisp_curate.py` — `picks.json` → `*_figs_filtered/` + manifest
- `scripts/inline_reveal.py` — inline cached reveal.js v5.1.0 into the deck source
- `scripts/embed_slide_images.py` — base64-inline all slide images
- `Refs/formatted_transcript_style.html` — the emerald HTML transcript theme

The **Core principle — what counts as an "interesting" screenshot** section and the **Quality
Checklist** from `/MP4+WizWhisp` apply verbatim: keep only unique, informative screen frames
(drop humans/body-parts, duplicates, partial reveals, logos/ads); use **every** kept figure in
both the transcript and the deck; produce email-portable HTML (reveal.js inlined, all images
base64, zero external refs, every TOC link resolving).

---

## Output (same as `/MP4+WizWhisp`)

- `Output/Formatted/{Title_Case}_FORMATTED_TRANSCRIPT.{md,html}`
- `Output/Slides/{Title_Case}_{N}_SLIDES.html`

Report: model/device used and transcript segment/word counts (Phase A), plus the standard
runtime/resolution, raw → kept frame counts (with exclusions), output paths/sizes, and all
verification results.

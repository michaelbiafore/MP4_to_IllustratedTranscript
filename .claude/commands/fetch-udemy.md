# Fetch Udemy Course Transcripts

Download Udemy-provided captions for selected Sections (and Lectures within those Sections) of a course you own, and save them under `Input/` ready for `/format-transcript` and `/slidefy-transcript`.

**Arguments**: $ARGUMENTS

## Argument Parsing

Parse the arguments as: `<course_url> [--sections 1,3-5] [--lectures 2,4-6] [--list] [--login <email>] [--ui] [--srt] [--out-mode per-section|combined|both] [--cookies <path>] [--headless]`

- **course_url** (required unless using `--login` alone or `--list`): a `https://www.udemy.com/course/<slug>/...` URL.
- **--sections** (required unless `--list` or `--login`): comma-separated section indices and ranges, 1-based. `1,3-5,8` → sections {1, 3, 4, 5, 8}.
- **--lectures** (optional): comma-separated lecture indices within each selected section. Default = all.
- **--list**: fetch curriculum, print sections + lectures, save curriculum JSON, exit.
- **--login <email>**: open Playwright in a visible window, run the email + 6-digit-code login, save `cookies_udemy.json`, then continue (or exit if no course given).
- **--ui**: skip the API path; scrape transcripts from the player UI via Playwright. No timestamps available in this mode.
- **--srt**: also write a `.srt` per lecture (API mode only).
- **--out-mode**: which Markdown bundles to write. Default `both` (per-section + combined).
- **--cookies <path>**: alternate cookies file path. Default: `cookies_udemy.json` at project root.
- **--headless**: in UI mode, run the browser headless.

Examples:
```
/fetch-udemy https://www.udemy.com/course/obsidian-mastery/ --list
/fetch-udemy https://www.udemy.com/course/obsidian-mastery/ --sections 1,3-5
/fetch-udemy https://www.udemy.com/course/obsidian-mastery/ --sections 2 --lectures 1-3 --srt
/fetch-udemy --login me@example.com
/fetch-udemy https://www.udemy.com/course/obsidian-mastery/ --sections 1 --ui
```

## Prerequisites

You need ONE of the following (the script will tell you if it's missing):

### Option A — Cookies file (recommended)

1. Install **Cookie-Editor** (Chrome/Edge extension) or **EditThisCookie**.
2. Log into Udemy in your normal browser.
3. Click the extension while on a `udemy.com` tab → **Export → JSON**.
4. Save the result as `cookies_udemy.json` in the project root.

The file is automatically gitignored via the `cookies_*.json` pattern.

### Option B — Interactive login

Run once with `--login <your_email>`. A visible Chromium window opens, the script types your email, then **pauses for you to paste the 6-digit code from your email inbox** into the terminal. After verification it writes `cookies_udemy.json` for reuse. Subsequent runs use the saved cookies until they expire.

### Security

- `cookies_udemy.json` grants full access to your Udemy account. Treat it like a password.
- If the file leaks, rotate it by changing your Udemy password.
- The script reminds you to delete the file when you're done.

## Instructions

### Phase 1: List the curriculum

If the user has not yet decided which sections to fetch, run with `--list` first:

```bash
uv run python scripts/fetch_udemy.py "<course_url>" --list
```

This prints `Section N: <title>` and `Lecture M: <title>` to the terminal and saves `Input/{course_slug}_udemy_curriculum.json`. The user can then choose section/lecture numbers.

### Phase 2: Fetch the chosen sections

```bash
uv run python scripts/fetch_udemy.py "<course_url>" --sections <spec> [--lectures <spec>] [--srt]
```

The script:
- Resolves the course slug → numeric id, walks the curriculum.
- For each selected `(section, lecture)`, hits `api-2.0/users/me/subscribed-courses/{course_id}/lectures/{lecture_id}/` and downloads the English caption (VTT).
- Saves per-lecture files under `Input/{course_slug}_udemy/`:
  - `sec_NN_lec_NN_<safe-title>.txt` — paragraph-reflowed plain text
  - `sec_NN_lec_NN_<safe-title>.vtt` — original VTT
  - `sec_NN_lec_NN_<safe-title>.srt` — only when `--srt` is passed
- Aggregates into Markdown bundles ready for `/format-transcript`:
  - `Input/{course_slug}_section_NN_RAW_TRANSCRIPT.md` (one per section)
  - `Input/{course_slug}_RAW_TRANSCRIPT.md` (combined across selected sections, when `--out-mode` is `both` or `combined`)
- Writes a manifest at `Input/{course_slug}_udemy_manifest.json` recording per-lecture status (`ok`, `no_captions`, `skipped`, `error`).

### Phase 3: Pipeline integration

After the script returns, suggest the next pipeline steps to the user, e.g.:

```
/format-transcript Input/{course_slug}_section_03_RAW_TRANSCRIPT.md
/slidefy-transcript Output/Formatted/{course_slug}_section_03_FORMATTED_TRANSCRIPT.md 40
```

### Phase 4: Report

Summarize back to the user:
- Course title, sections fetched, success / no-captions / error counts (from the manifest).
- Output paths for the Markdown bundles.
- Reminder to delete `cookies_udemy.json` when finished.

## Error Handling

- **Missing `cookies_udemy.json`** → suggest `/fetch-udemy --login <email>`.
- **401 from API** → cookies expired. Suggest `--login` to refresh, then retry.
- **403 on curriculum / lecture** → account isn't enrolled in this course. Verify the URL and ownership.
- **404 on course resolve** → check the URL form; expects `https://www.udemy.com/course/<slug>/`.
- **Lecture has no captions** → manifest records `no_captions`; the per-section bundle inserts a stub line. This is normal — not every lecture has a transcript.
- **API path returns nothing useful** → suggest re-running with `--ui` for that course.
- **Verification-code lockout** (per Udemy's docs) → reused codes need a 5+ minute wait; max-attempts triggers a 15-minute lockout. Surface the wait time, don't retry blindly.

## Output Files

```
Input/
├── {course_slug}_udemy_curriculum.json     # full curriculum (all sections / lectures)
├── {course_slug}_udemy_manifest.json       # per-lecture status for THIS run
├── {course_slug}_udemy/
│   ├── sec_03_lec_02_<title>.txt
│   ├── sec_03_lec_02_<title>.vtt
│   ├── sec_03_lec_02_<title>.srt           # only when --srt
│   └── ...
├── {course_slug}_section_03_RAW_TRANSCRIPT.md
└── {course_slug}_RAW_TRANSCRIPT.md         # combined, when --out-mode includes it
```

## Implementation Notes

The script is split across four modules under `scripts/`:

- `fetch_udemy.py` — entry point: arg parsing, orchestration, manifest writing.
- `udemy_auth.py` — cookie loader, `requests.Session` builder, interactive login.
- `udemy_api.py` — typed wrappers around `api-2.0` endpoints (course, curriculum, captions).
- `udemy_ui.py` — Playwright fallback used when `--ui` is passed.
- `vtt_to_text.py` — inline VTT parser → plain text + SRT.

Companion plan: `plans/PLAN_Udemy_FetchTranscript.md`.

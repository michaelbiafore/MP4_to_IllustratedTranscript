# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **content processing workflow** (not a traditional software project) that transforms raw YouTube transcripts into structured markdown documents and HTML slide presentations. There is no build system, package manager, or test suite.

> **Full command reference:** every slash command in `.claude/commands/` is documented with
> usage examples in [`README.md`](README.md) ("Slash Commands"). Keep the two in sync. This
> file focuses on the core formatting pipeline; the README is the source of truth for the
> complete command list (fetchers, formatters, slidifiers, collation macros, Discord tooling,
> and slide/figure utilities).

## Three-Stage Pipeline

```
RAW TRANSCRIPT  -->  FORMATTED MARKDOWN  -->  HTML SLIDES  -->  PDF (optional)
   (Input/)         (Output/)                (Output/)         (Output/)
  /format-transcript    Manual prompt         reveal.js
   slash command        conversion            + Naked Presenter
```

## Primary Command

```
/format-transcript <filepath>
```

- Defined in `.claude/commands/format-transcript.md`
- Input: raw transcript file (`.md` or `.txt`) from `Input/`
- Output: structured markdown in current directory, with `RAW` replaced by `FORMATTED` in filename
- Applies: topic detection, H1/H2/H3 hierarchy, TOC with anchors, 5-minute interval timestamps (`*[~0:00]*`), bold key phrases, blockquotes, bullet lists, Key Takeaways table

## Directory Layout

| Directory | Purpose |
|-----------|---------|
| `Input/` | Raw transcript files and image assets (PNGs) |
| `Output/` | Generated formatted transcripts, HTML slide decks, PDFs |
| `Refs/` | Reference docs: formatting examples, Naked Presenter principles, slide format options |
| `Mandates/` | Process specifications and prompts that define the pipeline |
| `.claude/commands/` | Custom slash command definitions |
| `plans/` | Implementation planning documents |

## Slide Generation (Stage 2)

Slides are created manually by prompting with the formatted transcript plus two reference documents:

- `Refs/Slide presentation_ format in Markdown.md` — slide tool options (Marp, reveal.js, Quarto)
- `Refs/Core Principles from _The Naked Presenter_01.md` — design philosophy (Garr Reynolds)
- `Mandates/SlideFromMarkdown_PROMPT.md` — the prompt template

**Technology**: reveal.js 5.1.0 via CDN (`cdn.jsdelivr.net`). Output is self-contained HTML with one `<section>` per slide.

**Design rules** (Naked Presenter):
- Minimal text per slide; large numbers as visual anchors
- Impact over information; storytelling over bullet walls
- Dark background (`#1a1a2e`), blue accent (`#64b5f6`), red for warnings (`#ef5350`), green for success (`#66bb6a`)
- Embed images as base64 data URIs for email portability

## File Naming Conventions

| Pattern | Meaning |
|---------|---------|
| `*_RAW_TRANSCRIPT.{md,txt}` | Unformatted transcript from YouTube |
| `*_FORMATTED_TRANSCRIPT.md` | Processed by `/format-transcript` |
| `*_SLIDES.html` | HTML slide deck (reveal.js) |
| `*_PROMPT.md` | Prompt/instructions for a conversion task |

## Discord Channel Export

The `/fetch-discord` command exports a Discord channel to markdown for processing through the standard format/slidefy pipeline.

### How to Get the Required Credentials

#### 1. Enable Developer Mode in Discord
- Open Discord (app or browser)
- Go to **Settings → Advanced → Developer Mode → On**

#### 2. Get the Channel ID
- Right-click the target channel name in the sidebar
- Select **Copy Channel ID** (appears only with Developer Mode enabled)
- This is a numeric string like `1473401675510452285`

#### 3. Get Your Discord Authorization Token
- Open **https://discord.com/app** in Chrome or Edge
- Navigate to any channel in the target server
- Press **F12** to open DevTools → click the **Network** tab
- Type `api` in the Network filter box
- Click on a different channel to trigger API requests
- Click any request to `discord.com/api` (e.g., `messages?limit=50`)
- Click **Headers** in the right panel → scroll to **Request Headers**
- Copy the value of `Authorization:` — this is your token

**Security:** This token grants full access to your Discord account. Never commit it to git or share it. After use, rotate it by changing your Discord password.

#### 4. Optionally Save the Token
Save the token to `cookies_discord.txt` (one line, just the token) so you don't have to pass it every time. This file is in `.gitignore`.

### Pipeline Flow
```
/fetch-discord <channel_id>          → Input/{slug}_RAW_ARTICLE.md + _figs/
/format-transcript {slug}_RAW_ARTICLE.md  → Output/Formatted/{title}_FORMATTED_SUBSTACK.md
/slidefy-transcript Output/Formatted/...  → Output/Slides/{title}_{N}_SLIDES.html
```

### What Gets Exported
- All text messages with author names and timestamps
- @mentions resolved to display names
- Image attachments downloaded locally
- Link embeds (title + description)
- Reaction counts (emoji + number)
- Organized by date with conversation threading

## Key Reference Files

- `Refs/TAC_04_Transcript_EXAMPLE.md` — canonical formatting example showing expected output structure
- `Refs/Transcription_SummaryOfWorkDone.md` — comprehensive workflow documentation covering all three stages
- `Mandates/Mandate_TranscriptYouTube.md` — original formatting rules for transcript processing

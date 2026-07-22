# Transcription & Slide Workflow: Summary of Work Done

This document summarizes all work performed on (1) formatting raw YouTube transcripts into structured markdown, (2) creating a reusable slash command to automate that process, and (3) converting formatted transcripts into HTML slide presentations. It is intended as a reference for future sessions.

---

## 1. The Three-Stage Pipeline

```
RAW TRANSCRIPT          FORMATTED TRANSCRIPT           HTML SLIDES
(timestamped mess)  -->  (structured markdown)     -->  (browser presentation)
     Stage 1                   Stage 2                      Stage 3
  /format-transcript       Manual or prompted          reveal.js + Naked
     slash command            conversion               Presenter principles
```

---

## 2. Stage 1: Raw Transcript to Formatted Markdown

### 2.1 The Original Mandate

The process began with a manual mandate document that described how to convert raw YouTube transcripts into structured markdown.

- **File**: `./Mandate_TranscriptYouTube.md`

Key rules established:
- Detect topic changes to create logical section breaks
- H1 title, H2 major sections, H3 subsections
- Table of Contents with anchor links
- Remove per-line timestamps; replace with 5-minute interval markers (`*[~0:00]*`, `*[~5:00]*`, etc.)
- Bold key phrases, block quotes for notable statements, bullet lists, horizontal rules
- Key Takeaways table at the end

### 2.2 The Slash Command (`/format-transcript`)

The mandate was converted into a reusable Claude Code custom slash command.

- **Command definition**: `./.claude/commands/format-transcript.md`
- **Planning document**: `./plans/MakeSlashCommand.md`
- **Invocation**: `/format-transcript <filename>`

#### How It Works

1. Accepts a filepath via `$ARGUMENTS`
2. If filename-only (no directory separators), resolves to the current working directory
3. Reads the raw transcript
4. Detects topic changes and creates logical sections
5. Builds structured markdown with H1/H2/H3, TOC, formatting
6. Replaces raw timestamps with 5-minute interval markers
7. Adds a Key Takeaways summary table
8. Writes output as `{filename}_FORMATTED.md` (replaces "RAW" with "FORMATTED" if present)

#### Slash Command Location & Structure

Claude Code custom slash commands live at:
- **Project level**: `./.claude/commands/` (used here)
- **User level**: `~/.claude/commands/` (for global commands)

The file is plain markdown. The `$ARGUMENTS` placeholder receives whatever the user types after the command name.

### 2.3 Transcript Examples Produced

| Raw Input | Formatted Output | Notes |
|-----------|-----------------|-------|
| `./SystemsThinking_NateBJONES_RAW_TRANSCRIPT.md` | `./SystemsThinking_NateBJONES_FORMATTED_TRANSCRIPT.md` | 1058 lines raw --> 308 lines formatted |
| `./AgentOps_AnswerRocket_TRANSCRIPT_RAW.txt` | `./AgentOps_Transcript_Full.md` | 41 KB raw transcript |
| `./ManagementSkill_NATE_TRANSCRIPT.md` | `./ManagementSkill_NATE_FORMATTED_TRANSCRIPT.md` | 31.9 KB raw --> 14.9 KB formatted |
| `./AI_at_Honeycomb_CharityMAJORS.md` | `./AI_at_Honeycomb_CharityMajors_Formatted.md` | Early example, pre-slash-command |

#### What Changes Between Raw and Formatted

**Raw transcript** characteristics:
- Timestamps every 2-4 seconds interspersed with sentence fragments
- No section breaks, headings, or structure
- Continuous wall of text

**Formatted transcript** characteristics:
- H1 title derived from content
- Table of Contents with anchor links to each section
- H2/H3 headings at logical topic boundaries
- 5-minute interval timestamps (`*[~5:00]*`)
- **Bold** key phrases, `> blockquotes` for memorable quotes
- Bullet lists for enumerated points
- `---` horizontal rules between major sections
- Key Takeaways table at the end

### 2.4 Reference / Example Files

- `./TAC_04_Transcript_EXAMPLE.md` — formatting example referenced by the mandate
- `./ClaudeCowork_NateJones_Transcript.md` — another formatted transcript example
- `./Cowork_01_Transcript.md` — co-work session transcript

---

## 3. Stage 2: Formatted Transcript to HTML Slides

### 3.1 The Prompt

- **File**: `./SlideFromMarkdown_PROMPT.md`

The prompt instructs:
> Take the content in ManagementSkill_NATE_FORMATTED_TRANSCRIPT.md and convert it into a series of slides that can be displayed in a browser (perhaps as HTML). Use the options described in "Slide presentation_format in Markdown.md" and follow the principles for slide simplicity described in "The Naked Presenter".

### 3.2 Reference Documents Used

#### Slide Format Options
- **File**: `./Slide presentation_ format in Markdown.md`
- Describes Marp, reveal.js, Quarto, R Markdown as Markdown-to-slides tools
- Common pattern: `---` separates slides, headings become slide titles
- Recommended: reveal.js for HTML output

#### Naked Presenter Principles (Garr Reynolds)
- **File**: `./Core Principles from _The Naked Presenter_01.md`
- **The 10 Ps**: Preparation, Punch, Presence, Projection, Passion, Proximity, Play, Pace, Participation, Power
- **Core philosophy**: Authenticity over polish
- **Key rules applied to slides**:
  - Visual rather than text-heavy
  - Impact rather than information
  - Storytelling rather than fact counting
  - Minimize slides; technology should be invisible

### 3.3 Slides Produced

| File | Description |
|------|-------------|
| `./ManagementSkill_NATE_SLIDES.html` | First version. 28 slides using reveal.js via CDN. Dark theme, blue accents. User modified title to "Not an IT Skill" and attribution to "DymonAsia (Hong Kong)". |
| `./ManagementSkill_02.html` | Second version. Carries forward user's modifications. Added: (1) DymonAsia logo (`DymonAsiaLogo.png`) fixed in upper-left corner of every slide, (2) "Not" styled red and italic on title slide, (3) logo embedded as base64 data URI so the HTML is fully self-contained for emailing. |

### 3.4 How the HTML Slides Were Built

**Technology**: reveal.js 5.1.0 loaded via CDN (`cdn.jsdelivr.net`)

**Design choices following Naked Presenter**:
- Minimal text per slide — key phrases and numbers, not paragraphs
- Large numbers as visual anchors (300K, 80/20, +12%/-19%)
- Contrast pairs (101 vs 201 users, Centaur vs Cyborg)
- Blockquotes for impactful quotes instead of bullet walls
- Dark background (`#1a1a2e`) with blue accent (`#64b5f6`)
- Red (`#ef5350`) for danger/negative, green (`#66bb6a`) for positive

**Slide structure** (28 slides covering the full transcript):
1. Title
2-4. Microsoft 300K study + 80/20 problem
5. Why people abandon AI (3-step failure sequence with fragments)
6-8. The Missing Middle (201 gap + quote + question shift)
9-10. Management Skill (Mollick quote + intern analogy)
11-12. Jagged Frontier (BCG/Harvard stats + quote)
13. Centaurs vs Cyborgs (two-column comparison)
14-21. Six 201 Skills (title + one slide per skill + summary)
22-24. Adoption blockers (section title + permission gap + IT mismatch)
25. Apprentice model collapse
26-27. How to unlock 201 (section title + six moves table)
28-31. Closing (shadow IT quote, self-check, final quote, takeaways, end)

**Keyboard controls**: Arrow keys navigate, `F` for fullscreen, `Esc` for slide overview.

### 3.5 Embedding the Logo as Base64

When the HTML file is emailed, external image references break. The logo was "compiled" into the HTML by:

1. Base64-encoding the PNG: `base64 -w 0 DymonAsiaLogo.png`
2. Replacing `src="DymonAsiaLogo.png"` with `src="data:image/png;base64,<encoded_data>"`
3. This was done via `sed` substitution in bash

The resulting HTML is fully self-contained — no external dependencies except the reveal.js CDN.

**Logo placement**: A fixed-position `<img>` element inside `.reveal` but outside `.slides`, so it persists across all slide transitions:

```css
.slide-logo {
  position: fixed;
  top: 18px;
  left: 22px;
  height: 48px;
  z-index: 100;
  pointer-events: none;
  opacity: 0.9;
}
```

---

## 4. File Naming Conventions

| Pattern | Meaning |
|---------|---------|
| `*_RAW_TRANSCRIPT.md` | Unformatted transcript, raw from YouTube |
| `*_FORMATTED_TRANSCRIPT.md` | Processed by `/format-transcript` |
| `*_SLIDES.html` | HTML slide deck from formatted transcript |
| `*_PERP.pdf` | Perplexity AI research document |
| `ANNOT_*.pdf` | Annotated version of a document |
| `*_ctpp.pdf` | Web page capture |
| `*_PROMPT.md` | Prompt/instructions for a conversion task |

---

## 5. Project Configuration

- **Project instructions**: `./CLAUDE.md`
- **Local settings**: `./.claude/settings.local.json` (allows `python3` and `python` bash commands)
- **Slash commands directory**: `./.claude/commands/`

---

## 6. Reproducing This Workflow

### To format a new transcript:
```bash
/format-transcript SomeVideo_RAW_TRANSCRIPT.md
# Outputs: ./SomeVideo_FORMATTED_TRANSCRIPT.md
```

### To create slides from a formatted transcript:
1. Read the formatted transcript
2. Read `./Slide presentation_ format in Markdown.md` for format options
3. Read `./Core Principles from _The Naked Presenter_01.md` for design principles
4. Create an HTML file using reveal.js with:
   - One `<section>` per slide
   - Minimal text, large visual numbers, contrast pairs
   - Blockquotes for key quotes
   - Dark theme with accent colors
5. To embed images: base64-encode and use `data:image/png;base64,...` URIs
6. The prompt template is at `./SlideFromMarkdown_PROMPT.md`

### To make the HTML fully portable for email:
- Embed all images as base64 data URIs
- reveal.js loads from CDN (requires internet at viewing time)
- If offline viewing is needed, the reveal.js CSS/JS would also need to be inlined

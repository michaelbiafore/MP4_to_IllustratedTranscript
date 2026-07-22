# Format MP4 Transcript with Screenshots

Convert a raw Whisper transcript (from `/fetch-mp4`) into a well-structured markdown document with embedded video screenshots.

**Input**: $ARGUMENTS

## Argument Parsing

Parse the arguments as: `<slug_or_file>`

- **slug_or_file** (required): Either:
  - A slug name (e.g., `20260409_204007`) — will look for `Input/{slug}_RAW_TRANSCRIPT.txt`
  - A filename (e.g., `20260409_204007_RAW_TRANSCRIPT.txt`) — will look in `Input/`
  - A full path to the raw transcript file

Examples:
```
/format-mp4 20260409_204007
/format-mp4 20260409_204007_RAW_TRANSCRIPT.txt
/format-mp4 Input/my_recording_RAW_TRANSCRIPT.txt
```

## Instructions

1. **Resolve the input file and slug**:
   - Determine the slug from the input argument
   - Verify `Input/{slug}_RAW_TRANSCRIPT.txt` exists
   - Check for `Input/{slug}_frames_manifest.json` (figure manifest from `/fetch-mp4`)
   - Check for `Input/{slug}_figs_filtered/` (deduplicated screenshots)
   - If no filtered figures directory exists, check `Input/{slug}_figs/` as fallback

2. **Read the raw transcript** (`Input/{slug}_RAW_TRANSCRIPT.txt`).
   - Format: `[M:SS] Transcribed text here` per line (Whisper segment output)
   - Note: Whisper's base model may have transcription errors — preserve them as-is (the user can correct later)

3. **Read the frames manifest** (`Input/{slug}_frames_manifest.json`) to get the list of available screenshots with their timestamps.

4. **Visually review key screenshots**: Read 8-12 evenly-spaced screenshots from `Input/{slug}_figs_filtered/` using the Read tool. This is CRITICAL — the screenshots reveal what's actually on screen (code, slides, dashboards, documents, diagrams) and inform section headings and topic detection. The transcript alone often lacks this visual context.

5. **Detect topic changes** throughout the transcript:
   - Use BOTH the transcript text AND the visual content of screenshots to identify logical section breaks
   - Screen recordings often change context (switching tabs, opening files, navigating to different tools) — these are topic boundaries even if the speaker doesn't announce them
   - The frames manifest timestamps help correlate visual changes with transcript segments

6. **Preserve transcript verbatim** with minimal cleanup:
   - **Keep all original words** — do not summarize, paraphrase, or omit spoken content
   - **Remove only** obvious filler words (`um`, `uh`, `uh huh`), false starts, stutters, and meaningless repetitions
   - Do not rewrite sentences for grammar or clarity; preserve the speaker's natural phrasing
   - **Identify speakers** where possible from context (names mentioned, voice changes) and label them in bold (e.g., **Matt:**, **Mike:**)
   - If a passage is unrelated to the current section topic, prefix it with `*[Aside]*` rather than removing it

7. **Handle timestamps**:
   - Remove original per-line `[M:SS]` timestamps from Whisper
   - Replace with approximate timestamps at **5-minute intervals**
   - Format: `*[~0:00]*`, `*[~5:00]*`, `*[~10:00]*`, etc.

8. **Place figures at topic boundaries**:
   - For each section, find the screenshot(s) from the manifest whose timestamp falls within or near that section's time range
   - Insert a markdown image reference after the H2/H3 heading and timestamp line:
     ```
     ![Figure N: Descriptive caption](../../Input/{slug}_figs_filtered/frame_XXXmYYs_screen_NNN.jpg)
     ```
   - **Write descriptive captions** based on what you saw when you reviewed the screenshots (step 4). Captions like "VS Code showing Clinic 01 run sheet" are much more useful than generic "Screenshot at 12:00".
   - Include as many relevant screenshots as there are — don't skip screenshots to keep the document short
   - If a screenshot doesn't clearly match a section, place it at the nearest section boundary

9. **Apply formatting**:
   - Main title as H1 (`#`) — derived from the content (not the filename)
   - Major sections as H2 (`##`)
   - Subsections as H3 (`###`)
   - A Table of Contents with anchor links at the top
   - Anchor IDs must follow **pandoc convention**: lowercase, spaces to hyphens, strip all punctuation including `&`, `'`, `,`, `:`, `—` (e.g., `## Welcome & Session Goals` → `#welcome-session-goals`, `## Fanindra's Diagram` → `#fanindras-diagram`). Never double-up hyphens.
   - Use **bold** for key phrases, tool names, technical terms
   - Use block quotes (`>`) for memorable quotes
   - Use bullet lists for enumerated points
   - Add horizontal rules (`---`) between major sections
   - Include a **Key Takeaways** table at the end

10. **Write the output file**:
    - **Generate the output filename from the video title** (the H1 you created), NOT from the input slug:
      1. Take the H1 title of your formatted output
      2. Lowercase it, replace spaces with hyphens, strip punctuation except hyphens
      3. Truncate to ~6 words (enough to be recognizable)
      4. Append `_FORMATTED_TRANSCRIPT.md`
    - Output to `Output/Formatted/{title_slug}_FORMATTED_TRANSCRIPT.md`
    - Create `Output/Formatted/` directory if needed

11. **Generate HTML with clickable TOC** (if pandoc is available):
    ```bash
    pandoc -f markdown-implicit_figures "Output/Formatted/{slug}_FORMATTED_TRANSCRIPT.md" \
        -s -o "Output/Formatted/{slug}_FORMATTED_TRANSCRIPT.html"
    ```
    If pandoc is not available, skip this step silently.

---

## Output Format

```markdown
# [Main Title Derived from Content]

**[Source/Context — e.g., "Zoom Recording", "Screen Capture", "Presentation"]**
**Recorded:** [Date if known]
**Participants:** [Names if identifiable]

## Table of Contents

- [Section 1](#section-1)
  - [Subsection 1a](#subsection-1a)
- [Section 2](#section-2)

---

## Section 1
*[~0:00]*

![Figure 1: Description of what's on screen](../../Input/{slug}_figs_filtered/frame_000m00s_screen_001.jpg)

Content here...

### Subsection 1a

More content...

---

## Key Takeaways

| Concept | Description |
|---------|-------------|
| **Key Point 1** | Summary |
| **Key Point 2** | Summary |
```

## Quality Checklist

Before finalizing, verify:
- [ ] Screenshots were visually reviewed (Read tool) to inform section structure
- [ ] ALL figures from the manifest are included — none omitted
- [ ] Figure paths use `../../Input/{slug}_figs_filtered/` prefix (relative from `Output/Formatted/`)
- [ ] Figure captions are descriptive (based on visual review), not generic timestamps
- [ ] Timestamps appear at ~5-minute intervals
- [ ] Table of Contents has working anchor links
- [ ] Speaker's original words are preserved (not paraphrased)
- [ ] Speakers are identified by name where possible

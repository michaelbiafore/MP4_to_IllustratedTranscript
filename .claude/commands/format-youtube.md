# Format YouTube Transcript with Screenshots

Convert a raw YouTube transcript (with embedded figure references from `/fetch-youtube`) into a well-structured markdown document that includes video screenshots.

**Input file**: $ARGUMENTS

## Instructions

1. **Resolve the input file path**:
   - If the path contains only a filename (no directory separators), look for it in the `Input/` directory
   - If the path contains a full path, use that path directly

2. **Read the input file**

3. **Determine the source URL**:
   - Look for the URL in the raw transcript header, or reconstruct from the filename
   - If a `_topics.json` sidecar exists in `Input/`, read the `video_url` from it
   - If the URL cannot be determined, leave a placeholder `[Source URL]`

4. **Discover all screenshot figures — CRITICAL FIRST STEP**:
   - **Search the raw transcript** for all lines matching `![Figure N: Caption](path)`. These were injected by `/fetch-youtube`'s frame extraction step.
   - **Also check the `_figs/` directory on disk**: Derive the slug from the input filename (everything before `_RAW_TRANSCRIPT`), then run `ls Input/{slug}_figs/` to find all `.jpg` frame files. This is the authoritative source — if the directory has 25 images, all 25 MUST appear in the output.
   - **Also read the `_topics.json` sidecar** if it exists in `Input/`. It contains the topic label and timestamp for each figure, which tells you exactly which section heading each screenshot belongs under.
   - **Distinguish two types of figures**: Topic-boundary figures (named `frame_XXXmYYs_TopicSlug.jpg`) and extra-timestamp figures (named `frame_XXXmYYs_extra_NNN.jpg`). Both types are MANDATORY and MUST appear in the output. Extra-timestamp figures should be placed at the nearest section boundary based on their timestamp.
   - Build a complete list: figure number, caption/topic, filename, and which section it belongs to. **Every single screenshot MUST appear in the formatted output — do NOT skip any.**

5. **Detect topic changes** throughout the transcript to identify logical section breaks. If a `_topics.json` file exists, use its topic labels and structure as a guide for headings. Align screenshots to their corresponding section.

6. **Preserve transcript verbatim** with minimal cleanup:
   - **Keep all original words** — do not summarize, paraphrase, or omit spoken content
   - **Remove only** obvious filler words (`um`, `uh`, `uh huh`), false starts, stutters, and meaningless repetitions
   - Do not rewrite sentences for grammar or clarity; preserve the speaker's natural phrasing
   - If a passage is unrelated to the current section topic, prefix it with `*[Aside]*` rather than removing it

7. **Handle timestamps**:
   - Remove original line-by-line timestamps
   - Replace with approximate timestamps at **5-minute intervals**
   - Format: `*[~0:00]*`, `*[~5:00]*`, `*[~10:00]*`, etc.

8. **Place figures at topic boundaries — MANDATORY, DO NOT SKIP**:
   - For EVERY screenshot figure discovered in step 4, insert a markdown image reference at the **start of its corresponding section**, right after the H2/H3 heading and timestamp line.
   - The format for each figure line is:
     ```
     ![Figure N: Topic Caption](../../Input/{slug}_figs/frame_XXXmYYs_Topic.jpg)
     ```
   - **Extra-timestamp figures**: These have filenames like `frame_XXXmYYs_extra_NNN.jpg`. Place each one at the section whose timestamp is closest to the figure's timestamp. If multiple extra figures fall within the same section, include them all sequentially. Use the caption format `![Figure N: Screenshot at M:SS](...)`.
   - **Fix figure paths for Output directory**: The raw file is in `Input/` but output goes to `Output/Formatted/`. ALL figure paths MUST use the `../../Input/` prefix:
     - Change `{slug}_figs/frame_*.jpg` → `../../Input/{slug}_figs/frame_*.jpg`
   - **Verify figure files exist**: Run `ls` on the `Input/{slug}_figs/` directory. Count the files. The number of `![Figure N]` lines in your output MUST equal the number of `.jpg` files in that directory.
   - If a screenshot doesn't clearly match a section, place it at the nearest section boundary — do NOT omit it.

9. **Apply formatting**:
   - Main title as H1 (`#`) — derived from the content
   - Major sections as H2 (`##`)
   - Subsections as H3 (`###`)
   - A Table of Contents with anchor links at the top
   - Anchor IDs must follow **pandoc convention**: lowercase, spaces to hyphens, strip all punctuation including `&`, `'`, `,`, `:`, `—` (e.g., `## Welcome & Session Goals` → `#welcome-session-goals`, `## Fanindra's Diagram` → `#fanindras-diagram`). Never double-up hyphens.
   - Use **bold** for key phrases and speaker names
   - Use block quotes (`>`) for memorable quotes
   - Use bullet lists for enumerated points
   - Add horizontal rules (`---`) between major sections
   - Include a Key Takeaways table at the end

10. **Write the output file**:
    - **Generate the output filename from the article/video title** (the H1 you created), NOT from the input filename:
      1. Take the H1 title of your formatted output
      2. Lowercase it, replace spaces with hyphens, strip punctuation except hyphens
      3. Truncate to ~6 words (enough to be recognizable, e.g., `the-300-thermal-labyrinth-ancient-cooling`)
      4. Append `_FORMATTED_TRANSCRIPT.md`
    - Output to `Output/Formatted/` directory as: `Output/Formatted/{title_slug}_FORMATTED_TRANSCRIPT.md`

11. **Generate HTML with clickable TOC**:
    - Run pandoc to convert the markdown output to a standalone HTML file:
      ```
      pandoc -f markdown-implicit_figures "Output/Formatted/{modified_filename}.md" -s -o "Output/Formatted/{modified_filename}.html"
      ```

---

## Output Format

The output should follow this structure:

```markdown
# [Main Title Derived from Content]

**[Source] - [Author/Participants]**
**URL:** [https://youtu.be/VIDEO_ID]

## Table of Contents

- [Section 1](#section-1)
  - [Subsection 1a](#subsection-1a)
- [Section 2](#section-2)

---

## Section 1
*[~0:00]*

![Figure 1: Introduction](../../Input/{slug}_figs/frame_000m02s_Introduction.jpg)

Content here...

### Subsection 1a

More content...

---

## Section 2
*[~5:00]*

![Figure 2: New Topic](../../Input/{slug}_figs/frame_005m11s_New_Topic.jpg)

Content here...

---

## Key Takeaways

| Concept | Description |
|---------|-------------|
| **Key Point 1** | Summary |
| **Key Point 2** | Summary |
```

## Quality Checklist

Before finalizing, verify:
- [ ] ALL figures from the raw transcript are included — none omitted
- [ ] Figure paths use `../../Input/` prefix (relative from `Output/Formatted/`)
- [ ] Figure files verified to exist on disk via `ls`
- [ ] Timestamps appear at ~5-minute intervals
- [ ] Table of Contents has working anchor links
- [ ] Speaker's original words are preserved (not paraphrased)

# Format Transcript or Article

Convert a raw YouTube transcript or Substack article into a well-structured markdown document.

**Input file**: $ARGUMENTS

## Agent Delegation Policy

When delegating work to sub-agents:
- **Never use `run_in_background: true`** for agents whose primary job is writing output files. Background agents may execute in isolated worktrees whose writes do not persist to the main working directory.
- If a sub-agent is used for file writing, **always verify the output file exists** (via `ls -la`) in the main working directory after the agent returns — do not trust the agent's self-report.
- If verification fails, rewrite the file directly rather than re-launching another agent.

## Instructions

1. **Resolve the input file path**:
   - If the path contains only a filename (no directory separators), look for it in the `Input/` directory
   - If the path contains a full path, use that path directly

2. **Detect content type**:
   - If filename contains `_RAW_SUBSTACK` or `_RAW_ARTICLE`: treat as **Substack article** (same rules apply to any web article)
   - If filename contains `_RAW_TRANSCRIPT`: treat as **YouTube transcript**
   - This affects how timestamps, structure, and figures are handled

3. **Read the input file**

4. **Determine the source URL**:
   - If the input file was fetched from YouTube, the URL can be reconstructed from the filename or found in the raw transcript header
   - If a URL was provided as part of the pipeline invocation, use that
   - If the URL cannot be determined, leave a placeholder `[Source URL]`
   - Include the URL on the first page of the output, right after the source/author line

5. **Create a structured markdown file** with:
   - Main title as H1 (`#`) - derived from the content
   - Major sections as H2 (`##`)
   - Subsections as H3 (`###`)
   - A Table of Contents with anchor links at the top
   - Anchor IDs must follow **pandoc convention**: lowercase, spaces to hyphens, strip all punctuation including `&`, `'`, `,`, `:`, `—` (e.g., `## Welcome & Session Goals` → `#welcome-session-goals`, `## Fanindra's Diagram` → `#fanindras-diagram`). Never double-up hyphens.

---

## For YouTube Transcripts

5. **Detect topic changes** throughout the transcript to identify logical section breaks

6. **Preserve transcript verbatim** with minimal cleanup:
   - **Keep all original words** — do not summarize, paraphrase, or omit spoken content
   - **Remove only** obvious filler words (`um`, `uh`, `uh huh`), false starts, stutters, and meaningless repetitions
   - Do not rewrite sentences for grammar or clarity; preserve the speaker's natural phrasing
   - If a passage is unrelated to the current section topic (e.g., off-topic aside, sign-off, call to action), prefix it with `*[Aside]*` rather than removing it

7. **Handle timestamps**:
   - Remove original line-by-line timestamps
   - Replace with approximate timestamps at **5-minute intervals**
   - Format: `*[~0:00]*`, `*[~5:00]*`, `*[~10:00]*`, etc.

---

## For Substack Articles

5. **Preserve existing structure**:
   - Substack articles already have H2/H3 headings — preserve them
   - Generate Table of Contents from existing headings
   - Do not reorganize or reorder sections

6. **Preserve all content exactly**:
   - Keep all text as written (already edited, not spoken)
   - Preserve all hyperlinks
   - Do not remove any content

7. **Handle figures**:
   - Figures should already have alt text with figure numbers: `![Figure 1: Caption](path)`
   - If figures use broken syntax `[!](url)`, fix to `![](url)`
   - Keep figures in their original positions within the text
   - **IMPORTANT - Fix figure paths for Output directory**: The raw file is in `Input/` but output goes to `Output/Formatted/`. Adjust all figure paths:
     - Change `{slug}_figs/fig_01.png` → `../../Input/{slug}_figs/fig_01.png`
     - This ensures figures display correctly when viewing the formatted output
   - Verify figure files exist in `Input/{slug}_figs/`

8. **No timestamp processing** — articles don't have timestamps

---

## Common Formatting (Both Types)

8. **Apply formatting**:
   - Use **bold** for key phrases and speaker names
   - Use block quotes (`>`) for memorable quotes
   - Use bullet lists for enumerated points
   - Add horizontal rules (`---`) between major sections
   - Include a Key Takeaways table at the end

9. **Write the output file**:
   - **Generate the output filename from the article/video title** (the H1 you created), NOT from the input filename:
     1. Take the H1 title of your formatted output
     2. Lowercase it, replace spaces with hyphens, strip punctuation except hyphens
     3. Truncate to ~6 words (enough to be recognizable, e.g., `executive-briefing-valve-got-lord`)
     4. Append `_FORMATTED_SUBSTACK.md` (for articles) or `_FORMATTED_TRANSCRIPT.md` (for transcripts)
   - Output to the `Output/Formatted/` directory as: `Output/Formatted/{title_slug}_FORMATTED_SUBSTACK.md`

10. **Generate HTML with clickable TOC**:
    - Run pandoc to convert the markdown output to a standalone HTML file:
      ```
      pandoc -f markdown-implicit_figures "Output/Formatted/{title_slug}_FORMATTED_*.md" -s -o "Output/Formatted/{title_slug}_FORMATTED_*.html"
      ```
    - The `-f markdown-implicit_figures` flag prevents pandoc from duplicating image alt text as figcaptions
    - This produces an HTML file with working internal anchor links (suitable for browser print-to-PDF)

11. **Verify output files exist on disk**:
    - Run `ls -la` on both the `.md` and `.html` output files
    - If any file is missing or zero bytes, the write failed — rewrite directly (do not re-delegate to a sub-agent)
    - This catches silent failures from worktree isolation or agent sandboxing

---

## Output Format

The output should follow this structure:

```markdown
# [Main Title Derived from Content]

**[Source] - [Author/Participants]**
**URL:** [https://youtu.be/VIDEO_ID or Substack URL]

## Table of Contents

- [Section 1](#section-1)
  - [Subsection 1a](#subsection-1a)
- [Section 2](#section-2)

---

## Section 1
*[~0:00]* (for transcripts only)

Content here...

![Figure 1: Caption describing the image](slug_figs/fig_01.png)

### Subsection 1a

More content...

---

## Key Takeaways

| Concept | Description |
|---------|-------------|
| **Key Point 1** | Summary |
| **Key Point 2** | Summary |
```

# Format Book Summary

Convert a book summary markdown file into a well-structured, formatted markdown document with HTML output.

**Arguments**: $ARGUMENTS

## Agent Delegation Policy

When delegating work to sub-agents:
- **Never use `run_in_background: true`** for agents whose primary job is writing output files. Background agents may execute in isolated worktrees whose writes do not persist to the main working directory.
- If a sub-agent is used for file writing, **always verify the output file exists** (via `ls -la`) in the main working directory after the agent returns — do not trust the agent's self-report.
- If verification fails, rewrite the file directly rather than re-launching another agent.

## Argument Parsing

Parse the arguments as: `<input_file> [image_dir]`

- **input_file** (required): Path to a book summary markdown file (typically `Sum_*.md`)
- **image_dir** (optional): Path to a directory containing images/figures referenced in the source. If omitted, look for an `images/` subdirectory alongside the input file.

Examples:
```
/format-summary A:\Packages\EPUB2MD4Claude\md_out\Sum_BookTitle.md A:\Packages\EPUB2MD4Claude\md_out\images
/format-summary A:\Packages\EPUB2MD4Claude\md_out\Sum_BookTitle.md
```

## Instructions

1. **Resolve the input file path**:
   - If the path contains only a filename (no directory separators), look for it in the `Input/` directory
   - If the path contains a full path, use that path directly

2. **Resolve the image directory**:
   - If `image_dir` is provided, use it directly
   - Otherwise, check for an `images/` subdirectory alongside the input file
   - Run `ls` on the image directory to confirm it exists and inventory its contents
   - If no image directory is found or it is empty, proceed without images

3. **Read and analyze the input file**:
   - Identify the book title and author (usually derivable from the first H1 heading and content)
   - Inventory all `![...](...)` image references in the source
   - Identify all chapter/section headings
   - Note any artifact headings that need cleanup (see step 5)

4. **Preserve all content exactly**:
   - Keep all text as written — do not summarize, paraphrase, or omit any content
   - Preserve all hyperlinks
   - Preserve all bold, italic, blockquote, and list formatting
   - Preserve all horizontal rules between sections

5. **Normalize heading structure**:
   Book summaries from EPUB extraction often have redundant or artifact headings. Clean these up:

   - **Single H1 only**: The document should have exactly one H1 (`#`) — the book title at the very top. Remove or demote all other H1 lines that appear within the body (e.g., `# Summary: Chapter Title`, `# Chapter N: Title`).
   - **Chapters as H2**: Each chapter or major part should be an H2 (`##`). Normalize patterns like `## 1. BEYOND AUTOMATION` or `## Ck0 Split 001` into clean `## Chapter N: Title` headings.
   - **Subsections as H3**: Section headings within a chapter should be H3 (`###`).
   - **Remove artifact headings**: Delete headings that are EPUB split artifacts (e.g., `## Ck0 Split 001`, `## C1Hk`) but preserve their content by merging it into the preceding or following chapter.
   - **Preserve non-chapter top-level sections**: Headings like `## Glossary`, `## What Next`, or `## Upcoming Books` that are not numbered chapters should remain as H2 without a "Chapter N:" prefix.

6. **Build Table of Contents**:
   Generate a full TOC with anchor links placed after the title/author block:
   ```markdown
   ## Table of Contents

   - [Chapter 1: Title](#chapter-1-title)
     - [Subsection A](#subsection-a)
     - [Subsection B](#subsection-b)
   - [Chapter 2: Title](#chapter-2-title)
   ...
   ```
   - Include all H2 sections (chapters, glossary, etc.) as top-level TOC entries
   - Include all H3 subsections as indented sub-entries
   - Anchor IDs must follow **pandoc convention**: lowercase, spaces to hyphens, strip all punctuation including `&`, `'`, `,`, `:`, `—` (e.g., `## Welcome & Session Goals` → `#welcome-session-goals`, `## Fanindra's Diagram` → `#fanindras-diagram`). Never double-up hyphens.

7. **Handle figures**:
   - **ALL figures from the source MUST appear in the output** — do not omit any
   - Keep figures in their original positions within the text
   - Preserve figure captions (the italic `*Fig N.N: Caption*` lines that follow images)
   - If figures use broken syntax `[!](url)`, fix to `![](url)`

   **Fix figure paths for Output directory — CRITICAL**:
   - The output file lives in `Output/Formatted/`. All `![](...)` image paths must be **relative from that directory** to the actual image file on disk.
   - **Always verify the actual directory structure** before generating paths. Run `ls` on the image directory to confirm what exists. Do NOT assume subdirectories exist — check first.
   - Compute the correct relative path from `Output/Formatted/` to the actual image file. For example:
     - Images at `A:/Packages/EPUB2MD4Claude/md_out/images/` → path is `../../../EPUB2MD4Claude/md_out/images/filename.jpg`
     - Images at `Input/BookTitle_figs/` → path is `../../Input/BookTitle_figs/filename.png`
   - **After fixing all paths**, verify that every unique image directory prefix used resolves to an existing directory on disk. This catches stale or invented paths.
   - Common pitfall: source markdown may reference paths like `images/assets/foo.png` but the actual files may be flat in `images/foo.png` — always trust `ls`, not the source paths.

8. **Add author/source block** after the H1 title:
   ```markdown
   # Book Title

   **Author Name**

   ---
   ```
   - Derive the author name from the content if possible (look for author mentions, "the author argues" patterns, or dedicate sections)
   - If the author cannot be determined, use `**[Author]**` as a placeholder

9. **Add Key Takeaways table** at the end of the document:
   ```markdown
   ## Key Takeaways

   | Concept | Description |
   |---------|-------------|
   | **Key Point 1** | One-sentence summary |
   | **Key Point 2** | One-sentence summary |
   ```
   - Extract 8–15 of the book's most important concepts, frameworks, or arguments
   - Each row should capture a distinct idea, not repeat or overlap
   - Descriptions should be concise (one sentence) and self-contained

10. **Write the output markdown file**:
    - Extract the input filename (without path and extension)
    - Append `_FORMATTED` to the filename (e.g., `Sum_BookTitle` → `Sum_BookTitle_FORMATTED`)
    - Output to `Output/Formatted/` directory as: `Output/Formatted/{modified_filename}.md`

11. **Generate HTML with clickable TOC**:
    - Run pandoc to convert the markdown output to a standalone HTML file:
      ```
      pandoc -f markdown-implicit_figures "Output/Formatted/{modified_filename}.md" -s -o "Output/Formatted/{modified_filename}.html"
      ```
    - The `-f markdown-implicit_figures` flag prevents pandoc from duplicating image alt text as figcaptions
    - This produces an HTML file with working internal anchor links (suitable for browser print-to-PDF)

12. **Verify output files exist on disk**:
    - Run `ls -la` on both the `.md` and `.html` output files
    - If any file is missing or zero bytes, the write failed — rewrite directly (do not re-delegate to a sub-agent)
    - This catches silent failures from worktree isolation or agent sandboxing

13. **Report completion**:
    - Confirm both output filenames (.md and .html)
    - Report: total line count, number of chapters, number of figures included
    - List any figures that could not be resolved to files on disk

---

## Output Format

The output markdown should follow this structure:

```markdown
# [Book Title]

**[Author Name]**

---

## Table of Contents

- [Introduction](#introduction)
  - [Subsection](#subsection)
- [Chapter 1: Title](#chapter-1-title)
  - [Subsection A](#subsection-a)
- [Chapter 2: Title](#chapter-2-title)
...
- [Glossary](#glossary)
- [Key Takeaways](#key-takeaways)

---

## Introduction

Content here...

### Subsection

More content...

![](../../../path/to/images/figure.jpg)

*Fig. 1.1: Caption describing the figure*

---

## Chapter 1: Title

Content here...

---

## Key Takeaways

| Concept | Description |
|---------|-------------|
| **Key Point 1** | Summary |
| **Key Point 2** | Summary |
```

---

## Quality Checklist

Before finalizing, verify:
- [ ] Exactly one H1 heading (the book title) — no other H1 lines in the body
- [ ] All chapters are H2, all subsections are H3
- [ ] No artifact headings remain (Ck0 Split, C1Hk, etc.)
- [ ] TOC covers all H2 and H3 headings with working anchor links
- [ ] **ALL figures from source are included** — none omitted
- [ ] Figure paths are **verified against disk** — every unique image directory prefix confirmed via `ls`
- [ ] All content preserved verbatim — no paragraphs removed or rewritten
- [ ] Author attribution present after the title
- [ ] Key Takeaways table at end with 8–15 distinct concepts
- [ ] Pandoc HTML generated successfully
- [ ] Zero broken image paths (source paths replaced with correct relative paths)

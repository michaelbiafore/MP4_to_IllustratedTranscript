# Mandate: YouTube Transcript Processing

## Purpose

Convert raw YouTube transcripts into well-structured markdown documents with proper organization, headers, and navigation.

## Instructions

1. **Read the input transcript file** (e.g., `AI_at_Honeycomb_CharityMAJORS.md`)

2. **Detect changes in topic** throughout the transcript to identify logical section breaks

3. **Create a structured markdown file** with:
   - Main title as H1 (`#`)
   - Major sections as H2 (`##`)
   - Subsections as H3 (`###`)
   - A Table of Contents with anchor links at the top

4. **Reference the example file** `TAC_04_Transcript_EXAMPLE.md` for formatting guidance

5. **Handle timestamps**:
   - Remove original line-by-line timestamps
   - Replace with approximate timestamps at **5-minute intervals**
   - Format: `[~0:00]`, `[~5:00]`, `[~10:00]`, etc.

6. **Write the output** to a new markdown file with a descriptive name that includes the name of the Transcript file

## Example Usage

```
Input:  ClaudeCowork_NateJones_Transcript.md
Output: AgentOps_AnswerRocket_Transcript.md
```

## Output Format

```markdown
# [Main Title]

## Table of Contents

- [Section 1](#section-1)
  - [Subsection 1a](#subsection-1a)
- [Section 2](#section-2)

---

## Section 1
*[~0:00]*

Content here...

### Subsection 1a

More content...

---

## Section 2
*[~5:00]*

Content continues...
```

## Key Elements

| Element | Description |
|---------|-------------|
| H1 (`#`) | Main title of the transcript |
| H2 (`##`) | Major topic sections |
| H3 (`###`) | Subtopics within sections |
| `---` | Horizontal rules between major sections |
| `*[~X:00]*` | Approximate timestamp markers |
| ToC | Table of contents with anchor links |
| **Bold** | Key phrases and emphasis |
| Bullet lists | Enumerated points and examples |
| Block quotes | Direct quotes or example prompts |

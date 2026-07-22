# Perplexity Thread to Markdown

Download a Perplexity conversation thread and save as a single Markdown file in the Input directory.

**Perplexity URL**: $ARGUMENTS

## Prerequisites

You need a `cookies_perplexity.json` file in the project root:
1. Install a cookie export extension (EditThisCookie, Cookie-Editor, etc.)
2. Navigate to any Perplexity page while logged in
3. Export cookies and save as `cookies_perplexity.json` in the project root

## Instructions

1. **Run the fetch script** using uv:
   ```bash
   uv run python scripts/fetch_perplexity.py "$ARGUMENTS"
   ```

2. **Report the result**:
   - Confirm the output filename and location
   - Report how many user queries and Perplexity responses were found
   - Show a preview of the file (first 15-20 lines)
   - Report the total content length
   - If the thread appears truncated or mangled, suggest the user check the output and offer to help clean it up

## How It Works

The script uses Playwright browser automation:
- Launches a Chromium browser with exported cookies (Perplexity requires auth)
- Navigates to the thread URL and scrolls to load all content
- Extracts user queries and Perplexity responses in chronological order
- Strips UI artifacts (source counts, icon placeholders, nav buttons, follow-up suggestions)
- Fixes code block formatting and removes inline source references
- Builds a filename from content words in the thread title (stop words removed)

**Note**: A browser window will briefly open — this is normal.

## Output Format

The Markdown file contains:
- Title from the thread
- Source URL and save date
- Numbered `## User Query N` / `## Perplexity Response N` sections
- All code blocks, terminal output, and formatting preserved
- Horizontal rules between turns

## Filename Convention

The output filename is derived from the thread title:
- Stop words (a, the, is, my, etc.) are removed
- First 6 content words are kept, capitalized, joined with underscores
- Suffix: `_PERP.md`
- Example: "How to install Docker on Ubuntu" → `Install_Docker_Ubuntu_PERP.md`

## Error Handling

- If redirected to login: cookies are expired — re-export from browser
- If no turns found: page structure may have changed — suggest manual copy-paste
- If content looks truncated: thread may need more scroll time or page was partially loaded

## Example Usage

```
/perp-to-md https://www.perplexity.ai/search/how-to-install-docker-abcd1234
/perp-to-md https://www.perplexity.ai/search/i-have-a-new-dgx-spark-actuall-L0FygxCkTXWnBzHYvJypkg
```

Output: `Input/{ContentWords}_PERP.md`

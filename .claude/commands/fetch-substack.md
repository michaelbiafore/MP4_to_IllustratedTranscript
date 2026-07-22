# Fetch Substack Article

Download a Substack article (including paywalled content you subscribe to) and save it to the Input directory.

**Substack URL**: $ARGUMENTS

## Prerequisites

For paywalled content, you need a `cookies_substack.json` file in the project root:
1. Install EditThisCookie (or similar) browser extension
2. Navigate to any Substack page while logged in
3. Export cookies and save as `cookies_substack.json` in the project root

## Instructions

1. **Run the fetch script** using uv:
   ```bash
   uv run python scripts/fetch_substack.py "$ARGUMENTS"
   ```

2. **Report the result**:
   - Confirm the output filename and location
   - Report how many images were downloaded (if any)
   - Show a preview of the article (first 10-15 lines)
   - Report the total content length (to verify full article was fetched)
   - Remind the user they can run `/format-transcript <filename>` on the new file

## How It Works

The script uses Playwright browser automation:
- Launches a Chromium browser with your exported cookies
- Navigates to the article (resolves inbox URLs automatically)
- Waits for content to load and scrolls to trigger lazy loading
- Extracts the full article content (including paywalled sections)
- Downloads all images to a local folder
- Converts HTML to Markdown

**Note**: A browser window will briefly open - this is normal.

## Error Handling

- If no cookies file is found, the script will still run but may not access paywalled content
- If the URL format is invalid, show examples of valid formats:
  - `https://newsletter.substack.com/p/article-slug`
  - `https://substack.com/inbox/post/123456`
  - `https://www.customdomain.com/p/article-slug`
- If images fail to download, the script continues but reports warnings

## Example Usage

```
/fetch-substack https://pragmaticengineer.substack.com/p/the-pulse-126
/fetch-substack https://substack.com/inbox/post/188532718
```

Output will be saved as:
- `Input/{slug}_RAW_SUBSTACK.md` (article content)
- `Input/{slug}_images/` (downloaded images, if any)

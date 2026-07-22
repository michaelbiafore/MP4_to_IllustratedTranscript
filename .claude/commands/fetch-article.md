# Fetch Article

Download any web article (blog post, news article, etc.) including all figures and save to the Input directory.

**Article URL**: $ARGUMENTS

## Instructions

1. **Determine if cookies are needed** based on the URL:
   - If the URL contains `mail.google.com` → use `--cookies cookies_gmail.json`
   - If the URL contains `substack.com` → cookies are auto-handled by the script
   - Otherwise → no cookies needed

2. **Run the fetch script** using uv:
   ```bash
   # Without cookies (default):
   uv run python scripts/fetch_article.py "$ARGUMENTS"

   # With Gmail cookies (for mail.google.com URLs):
   uv run python scripts/fetch_article.py "$ARGUMENTS" --cookies cookies_gmail.json
   ```

3. **Report the result**:
   - Confirm the output filename and location
   - Report how many images were downloaded (if any)
   - Show a preview of the article (first 10-15 lines)
   - Report the total content length (to verify full article was fetched)
   - Remind the user they can run `/format-transcript <filename>` on the new file

## How It Works

The script uses Playwright browser automation:
- Launches a Chromium browser
- Navigates to the article URL
- Waits for content to load and scrolls to trigger lazy loading
- Finds the article content container (`<article>`, `<main>`, or largest content block)
- Downloads all article images, unwrapping platform-specific CDN wrappers:
  - Next.js `/_next/image?url=` → original static asset
  - Substack CDN resize → original URL
  - WordPress `i0.wp.com` → strip resize params
  - Medium `miro.medium.com/resize` → full size
  - Cloudinary, Ghost, Imgix → strip transforms
- Converts HTML to Markdown with figure references

**Note**: A browser window will briefly open — this is normal.

## Supported Platforms

Works with any server-rendered article page including:
- Next.js blogs (e.g., AgentField, Vercel blogs)
- WordPress sites
- Ghost blogs
- Medium (public articles)
- Substack (auto-detects paywalls and falls back to `fetch_substack.py` with `cookies_substack.json`)
- Gmail (email newsletters) — requires `--cookies cookies_gmail.json`
- Beehiiv newsletters (often delivered via Gmail)
- Static site generators (Hugo, Jekyll, etc.)

## Error Handling

- If the page fails to load, check that the URL is correct and the site is accessible
- If no images are found, the article may use JS-rendered charts or inline SVGs
- Images under 5 KB are skipped (likely icons/spacers)
- If cookies are needed, provide a JSON file: `--cookies cookies_article.json`
- For Substack paywalls, `cookies_substack.json` is auto-loaded and the script falls back to `fetch_substack.py`
- **Emoji in titles**: The script handles emoji characters in article titles (e.g., from newsletter subject lines). A UTF-8 stdout fix is built into the script to prevent Windows cp1252 encoding crashes. If you still see a `UnicodeEncodeError`, ensure the fix at the top of `fetch_article.py` is present (`sys.stdout = io.TextIOWrapper(...)`).

## Example Usage

```
/fetch-article https://agentfield.ai/blog/beyond-vibe-coding
/fetch-article https://example.com/blog/my-article
/fetch-article https://mail.google.com/mail/u/0/?ui=2&ik=...&permmsgid=msg-f:...
```

Output will be saved as:
- `Input/{slug}_RAW_ARTICLE.md` (article content)
- `Input/{slug}_figs/` (downloaded figures, if any)

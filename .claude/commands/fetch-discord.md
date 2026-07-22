# Fetch Discord Channel — Export and Convert a Discord Channel to Markdown

Export all messages and images from a Discord channel and save as a structured markdown file ready for the format/slidefy pipeline.

**Arguments**: $ARGUMENTS

## Argument Parsing

Parse the arguments as: `<channel_id> [--token <discord_token>] [--after <YYYY-MM-DD>] [--before <YYYY-MM-DD>]`

- **channel_id** (required): The Discord channel ID (a numeric string like `1473401675510452285`)
- **--token** (optional): Discord user authorization token. If not provided, look for it in `cookies_discord.txt` in the project root (one line, just the token).
- **--after** (optional): Only fetch messages after this date
- **--before** (optional): Only fetch messages before this date

Examples:
```
/fetch-discord 1473401675510452285
/fetch-discord 1473401675510452285 --token NzM4OT...pYDU
/fetch-discord 1473401675510452285 --after 2026-03-01
```

## Prerequisites

You need two pieces of information from Discord:

### 1. Discord User Token (Authorization header)

1. Open **https://discord.com/app** in Chrome or Edge (log in if needed)
2. Navigate to any channel in the target server
3. Press **F12** (or Ctrl+Shift+I) to open DevTools
4. Click the **Network** tab
5. Type `api` in the filter box to filter requests
6. Click on a different channel, then back — this triggers API requests
7. Click on any request to `discord.com/api` (e.g., `messages?limit=50`)
8. In the right panel, click **Headers** → scroll to **Request Headers**
9. Find `Authorization:` — copy the value (a long string)

**Security:** Never share this token publicly. It grants full access to your Discord account. Rotate it after use by changing your Discord password.

### 2. Channel ID

1. In Discord (app or browser): **Settings → Advanced → Enable Developer Mode**
2. Right-click the target channel name in the sidebar
3. Select **Copy Channel ID**

## Instructions

### Phase 1: Fetch messages via Discord REST API

1. **Set up headers:**
   ```python
   TOKEN = "<token>"
   HEADERS = {"Authorization": TOKEN}
   ```

2. **Paginate through all messages** (100 per page, newest first):
   ```python
   url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit=100"
   # After each page, use &before={oldest_message_id} to get the next page
   # Stop when a page returns fewer than 100 messages
   # Rate limit: sleep 0.5s between pages
   ```

3. **Reverse to chronological order** and save as `Input/{slug}_raw.json`

4. **Derive the slug** from the channel name. If unknown, use the channel ID.
   - To get the channel name: `GET /api/v10/channels/{CHANNEL_ID}` → `response["name"]`
   - To get the server name: `GET /api/v10/channels/{CHANNEL_ID}` → `response["guild_id"]` → `GET /api/v10/guilds/{guild_id}` → `response["name"]`

### Phase 2: Download image attachments

5. **Create figures directory:** `Input/{slug}_figs/`

6. **Download all image attachments** (content_type starts with `image/`):
   - Name files sequentially: `fig_001.png`, `fig_002.jpg`, etc.
   - Build a mapping of attachment_id → local filename

### Phase 3: Convert to Markdown

7. **Write `Input/{slug}_RAW_ARTICLE.md`** with this structure:

```markdown
# {Channel Name} Discord Channel Transcript

**Server:** {Server Name}
**Channel:** #{channel_name}
**Messages:** {count}
**Authors:** {unique_author_count}
**Date range:** {first_date} to {last_date}

---

## {YYYY-MM-DD}

**{Author Display Name}** ({HH:MM AM/PM}):
{message content with @mentions resolved}

![Figure N: filename](slug_figs/fig_NNN.ext)

{emoji} {count}  (for reactions)

---

## {next date}
...
```

8. **Resolve mentions:** Replace `<@USER_ID>` with `@{display_name}` using the mention objects in each message.

9. **Include embeds:** For link embeds, add blockquoted title + description + URL.

10. **Include reactions:** Show as `emoji count` on a line after the message.

### Phase 4: Report results

11. **Report:**
    - Message count, author count, date range
    - Number of images downloaded
    - Output file path and size
    - Remind the user to run:
      - `/format-transcript {slug}_RAW_ARTICLE.md` to format
      - `/slidefy-transcript Output/Formatted/{slug}_FORMATTED_*.md N` to create slides

## Error Handling

- If the token is invalid (401 response): instruct the user to re-extract from browser DevTools
- If the channel ID is invalid (404): show format examples
- If rate limited (429): wait the specified retry_after duration and retry
- If image download fails: continue with remaining images, report which failed
- If the channel has threads: note that thread messages require separate API calls to `/channels/{thread_id}/messages`

## Example Usage

```
/fetch-discord 1473401675510452285
/fetch-discord 1473401675510452285 --after 2026-03-01 --before 2026-04-01
/fetch-discord 1473401675510452285 --token NzM4OT...pYDU
```

Output will be saved as:
- `Input/{slug}_raw.json` (raw API response)
- `Input/{slug}_RAW_ARTICLE.md` (formatted markdown)
- `Input/{slug}_figs/` (downloaded images)

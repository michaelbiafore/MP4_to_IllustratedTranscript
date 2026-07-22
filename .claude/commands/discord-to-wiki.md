# Discord to Wiki — Per-Message Markdown Mirror of a Discord Channel

Export a Discord channel as a per-message wiki: one `.md` file per message
(YAML frontmatter + body), all images in a shared `images/` subdirectory,
plus an `INDEX.md` and a resume marker. Designed for Obsidian/Logseq/static-site
ingestion — *not* the format/slidefy pipeline (use `/fetch-discord` for that).

**Arguments**: $ARGUMENTS

## Argument parsing

Parse as: `<channel_id> --output-dir <path> [--token <token>] [--after <YYYY-MM-DD-hh-mm-ss>] [--before <YYYY-MM-DD>] [--include-system] [--no-replies]`

- **channel_id** (required): Discord channel ID, e.g. `1473401675510452285`.
- **--output-dir** (required): destination directory for the wiki, e.g. `A:\_Wikis\QSAtlas_Discord\inbox`. Will be created if missing.
- **--token** (optional): Discord user authorization token. If omitted, read from `cookies_discord.txt`.
- **--after** (optional): only process messages strictly newer than this UTC timestamp. Accepts either `YYYY-MM-DD` (start of day UTC) or `YYYY-MM-DD-HH-MM-SS`. The fine-grained form is what `Last_Message_Processed.md` records, so this round-trips for incremental re-runs.
- **--before** (optional, fetch-side only): only fetch messages before this YYYY-MM-DD.
- **--include-system** (optional): keep join/pin/system messages (default: skipped).
- **--no-replies** (optional): omit the inline parent-quote/wikilink in reply bodies (the `reply_to` frontmatter field is still populated).

Examples:

```
/discord-to-wiki 1473401675510452285 --output-dir A:\_Wikis\QSAtlas_Discord\inbox
/discord-to-wiki 1473401675510452285 --output-dir A:\_Wikis\QSAtlas_Discord\inbox --after 2026-04-29-14-22-37
```

## Pipeline

This command is a thin orchestrator over two scripts:

1. **`scripts/fetch_discord.py`** — paginates the Discord REST API and writes raw JSON to `Input/{slug}_raw.json`. Reads the token from `cookies_discord.txt` by default. Resolves channel + guild metadata. Reuses the same logic as `/fetch-discord` and `/filter-discord`.
2. **`scripts/discord_to_wiki.py`** — converts that raw JSON into the per-message wiki under `<output-dir>/`.

### Step 1 — fetch

Run:

```
.venv/Scripts/python.exe scripts/fetch_discord.py <channel_id> \
    [--token <token>] [--after <after>] [--before <before>] \
    --output Input/{slug}_raw.json
```

Capture stdout — `fetch_discord.py` prints `CHANNEL_NAME=`, `SERVER_NAME=`, `SLUG=`, `OUTPUT_PATH=`, `TOTAL_MESSAGES=`, `DATE_RANGE=`. Parse these into shell variables. The `slug` is what we use for filenames.

Note: `fetch_discord.py` accepts the same `--after YYYY-MM-DD-HH-MM-SS` format as the wiki script (extended in this commit). Passing it both places gives a Discord-side coarse cut and a Python-side exact cut, which is what the plan calls for.

The guild ID isn't printed — the script's `fetch_channel_info()` already calls `GET /guilds/{guild_id}`, so add a one-line print for `GUILD_ID=` if not already present, or fetch it inline here:

```
GUILD_ID=$(.venv/Scripts/python.exe -c "import json,requests,sys; \
    tok=open('cookies_discord.txt').read().strip().split(': ',1)[-1]; \
    r=requests.get('https://discord.com/api/v10/channels/<channel_id>', headers={'Authorization':tok}); \
    print(r.json().get('guild_id',''))")
```

### Step 2 — convert

Run:

```
.venv/Scripts/python.exe scripts/discord_to_wiki.py Input/{slug}_raw.json \
    --output-dir <output-dir> \
    --channel-slug {slug} \
    --channel-name "{CHANNEL_NAME}" \
    --server-name "{SERVER_NAME}" \
    --guild-id {GUILD_ID} \
    [--after <after>] \
    [--include-system] [--no-replies]
```

Capture stdout — the wiki script prints `FILES_WRITTEN=`, `IMAGES_DOWNLOADED=`, `IMAGES_EXISTED=`, `IMAGES_FAILED=`, `AUTHORS=`, `DATE_RANGE=`, `OUTPUT_DIR=`, `LAST_MESSAGE_TIMESTAMP=`.

### Step 3 — report

Show the user:

- Output directory + `INDEX.md` path
- Counts: messages written, new images downloaded, images skipped (already on disk), failures
- Date range covered
- The new `LAST_MESSAGE_TIMESTAMP` value, and the exact one-line command they'd use for the next incremental run

If `FILES_WRITTEN=0`, also report that `Last_Message_Processed.md` was **not** modified (the previous marker still stands).

## Output layout (recap)

```
<output-dir>/
├── INDEX.md
├── Last_Message_Processed.md
├── images/
│   └── {message-id}_{NN}.{ext}
└── messages/
    └── {YYYY-MM-DD}_{HHMM}_{author-slug}_{message-id}.md
```

## Per-message file shape

```markdown
---
message_id: "1473..."
channel: "qs-atlas"
server: "Quant Science Trading Community"
author: "Matt Dancho"
author_id: "..."
date: "2026-04-14"
time: "10:41"
timestamp: "2026-04-14T10:41:23.000+00:00"
edited: false
reply_to: "1473..."           # null if not a reply
mentions: ["Deax"]
attachments: 1
images: ["images/1473..._01.png"]
reactions:
  - emoji: "👍"
    count: 2
tags: ["matt-dancho", "2026-04-14", "qs-atlas"]
---

# Matt Dancho — 2026-04-14 10:41

> **Replying to** [[2026-04-14_1038_deax_1473...]]
> _Hi Matt, Great session today...._

Body content here, with @mentions resolved to display names.

![image0.jpg](../images/1473..._01.png)

**Reactions:** 👍 ×2

---

**Source:** Discord message [`1473...`](https://discord.com/channels/{guild}/{channel}/{message}) in `#qs-atlas`
```

## Idempotency / re-runs

- Image downloads are skipped if the file already exists with size > 0.
- Markdown writes overwrite cheaply.
- `Last_Message_Processed.md` is updated **only** when at least one new message was written; otherwise the previous marker is preserved so the next `--after` value remains correct.

## qs-atlas defaults

For the recurring qs-atlas mirror:

```
/discord-to-wiki 1473401675510452285 --output-dir A:\_Wikis\QSAtlas_Discord\inbox
```

The channel ID and guild ID are already documented in `qs-atlas_Discord_Auth_and_Channel_ID.txt`. The token lives in `cookies_discord.txt`. Threads aren't fetched in v1.

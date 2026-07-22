#!/usr/bin/env python3
"""
Fetch Discord channel messages via REST API with optional date filtering.

Shared fetch logic for /fetch-discord and /filter-discord commands.

Usage:
  python fetch_discord.py <channel_id> [--token TOKEN] [--after YYYY-MM-DD] [--before YYYY-MM-DD] [--output PATH]

Reads token from cookies_discord.txt if --token is not provided.
Outputs raw JSON to the specified path (default: Input/{slug}_raw.json).
Prints channel metadata (name, server, slug) to stdout for the calling command.
"""

import sys
import json
import time
import re
import argparse
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import requests


# Discord epoch: 2015-01-01T00:00:00Z in milliseconds
DISCORD_EPOCH = 1420070400000


def date_to_snowflake(date_str: str) -> str:
    """Convert YYYY-MM-DD or YYYY-MM-DD-HH-MM-SS (UTC) to a Discord snowflake ID."""
    for fmt in ("%Y-%m-%d-%H-%M-%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            break
        except ValueError:
            continue
    else:
        raise ValueError(
            f"Unrecognized date format: {date_str!r} "
            f"(expected YYYY-MM-DD or YYYY-MM-DD-HH-MM-SS)"
        )
    ms = int(dt.timestamp() * 1000)
    return str((ms - DISCORD_EPOCH) << 22)


def sanitize_slug(name: str) -> str:
    """Convert channel name to a filesystem-safe slug."""
    # Strip emoji and non-ASCII
    slug = re.sub(r'[^\x20-\x7E]', '', name).strip()
    slug = re.sub(r'[^a-zA-Z0-9-]', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-').lower()
    return slug or "channel"


def fetch_channel_info(channel_id: str, headers: dict) -> dict:
    """Get channel and server metadata."""
    r = requests.get(
        f"https://discord.com/api/v10/channels/{channel_id}",
        headers=headers,
    )
    if r.status_code == 401:
        print("ERROR: Invalid Discord token. Re-extract from browser DevTools.", file=sys.stderr)
        sys.exit(1)
    if r.status_code == 404:
        print(f"ERROR: Channel {channel_id} not found.", file=sys.stderr)
        sys.exit(1)
    r.raise_for_status()
    ch = r.json()

    server_name = ""
    guild_id = ch.get("guild_id")
    if guild_id:
        g = requests.get(
            f"https://discord.com/api/v10/guilds/{guild_id}",
            headers=headers,
        )
        if g.status_code == 200:
            server_name = g.json().get("name", "")

    return {
        "channel_name": ch.get("name", channel_id),
        "server_name": server_name,
        "guild_id": guild_id,
    }


def fetch_messages(
    channel_id: str,
    headers: dict,
    after_snowflake: str | None = None,
    before_snowflake: str | None = None,
) -> list:
    """Paginate messages backward from 'before', stopping at 'after'.

    Discord's `before`, `after`, and `around` are mutually exclusive, so we
    only ever pass `before` as the cursor and enforce `after` client-side by
    comparing snowflakes (snowflake order == chronological order).
    """
    all_messages = []
    cursor = before_snowflake
    page = 0
    after_int = int(after_snowflake) if after_snowflake else None

    while True:
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=100"
        if cursor:
            url += f"&before={cursor}"

        r = requests.get(url, headers=headers)
        if r.status_code == 429:
            retry_after = r.json().get("retry_after", 2)
            print(f"  Rate limited, waiting {retry_after}s...", file=sys.stderr)
            time.sleep(retry_after)
            continue
        r.raise_for_status()

        msgs = r.json()
        if not msgs:
            break

        # Discord returns newest-first; msgs[-1] is the oldest in the page.
        cursor = msgs[-1]["id"]

        if after_int is not None:
            kept = [m for m in msgs if int(m["id"]) > after_int]
            all_messages.extend(kept)
            page += 1
            print(f"  Page {page}: {len(msgs)} fetched, {len(kept)} kept (total: {len(all_messages)})", file=sys.stderr)
            # If any were filtered, we've crossed the 'after' threshold — done.
            if len(kept) < len(msgs):
                break
        else:
            all_messages.extend(msgs)
            page += 1
            print(f"  Page {page}: {len(msgs)} messages (total: {len(all_messages)})", file=sys.stderr)

        if len(msgs) < 100:
            break
        time.sleep(0.5)

    # Discord returns newest-first; reverse to chronological
    all_messages.reverse()
    return all_messages


def read_token(token_arg: str | None) -> str:
    """Read token from argument or cookies_discord.txt."""
    if token_arg:
        return token_arg

    token_file = Path("cookies_discord.txt")
    if not token_file.exists():
        print("ERROR: No --token provided and cookies_discord.txt not found.", file=sys.stderr)
        sys.exit(1)

    for line in token_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("Authorization:"):
            return line.split(":", 1)[1].strip()
        # If the line looks like a raw token (no prefix), use it
        if line and not line.startswith("#") and not line.startswith("Channel"):
            return line

    print("ERROR: Could not parse token from cookies_discord.txt.", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Fetch Discord channel messages")
    parser.add_argument("channel_id", help="Discord channel ID")
    parser.add_argument("--token", help="Discord authorization token")
    parser.add_argument("--after", help="Only fetch messages after YYYY-MM-DD")
    parser.add_argument("--before", help="Only fetch messages before YYYY-MM-DD")
    parser.add_argument("--output", help="Output JSON path (default: auto)")
    args = parser.parse_args()

    token = read_token(args.token)
    headers = {"Authorization": token}

    # Fetch channel info
    info = fetch_channel_info(args.channel_id, headers)
    slug = sanitize_slug(info["channel_name"])
    print(f"CHANNEL_NAME={info['channel_name']}", flush=True)
    print(f"SERVER_NAME={info['server_name']}", flush=True)
    print(f"SLUG={slug}", flush=True)

    # Convert dates to snowflakes
    after_sf = date_to_snowflake(args.after) if args.after else None
    before_sf = date_to_snowflake(args.before) if args.before else None

    # Fetch messages
    messages = fetch_messages(args.channel_id, headers, after_sf, before_sf)
    print(f"TOTAL_MESSAGES={len(messages)}", flush=True)

    # Save
    output_path = Path(args.output) if args.output else Path(f"Input/{slug}_filter_raw.json")
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(
        json.dumps(messages, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"OUTPUT_PATH={output_path}", flush=True)

    if messages:
        first_ts = messages[0]["timestamp"][:10]
        last_ts = messages[-1]["timestamp"][:10]
        print(f"DATE_RANGE={first_ts} to {last_ts}", flush=True)
    else:
        print("DATE_RANGE=empty", flush=True)


if __name__ == "__main__":
    main()

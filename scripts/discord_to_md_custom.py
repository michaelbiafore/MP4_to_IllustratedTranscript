#!/usr/bin/env python3
"""Convert a Discord raw JSON dump to a markdown file at a user-specified path.

Usage:
  python discord_to_md_custom.py <raw_json> <output_md> <server_name> <channel_name>

Images are downloaded into a sibling figs directory next to the output markdown,
named "<output_stem>_figs/", and referenced with relative paths in the markdown.
"""
import sys
import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main():
    if len(sys.argv) < 5:
        print("Usage: discord_to_md_custom.py <raw_json> <output_md> <server_name> <channel_name>", file=sys.stderr)
        sys.exit(1)

    raw_json = Path(sys.argv[1])
    output_md = Path(sys.argv[2])
    server_name = sys.argv[3]
    channel_name = sys.argv[4]

    figs_dir = output_md.parent / f"{output_md.stem}_figs"
    figs_rel = figs_dir.name

    with open(raw_json, "r", encoding="utf-8") as f:
        messages = json.load(f)

    print(f"Processing {len(messages)} messages")

    figs_dir.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    fig_num = 0
    attachment_map = {}
    for msg in messages:
        for att in msg.get("attachments", []):
            ct = att.get("content_type", "") or ""
            if ct.startswith("image/"):
                fig_num += 1
                ext = att.get("filename", "img.png").rsplit(".", 1)[-1]
                local = f"fig_{fig_num:03d}.{ext}"
                local_path = figs_dir / local
                if not local_path.exists():
                    try:
                        r = requests.get(att["url"], timeout=30)
                        r.raise_for_status()
                        local_path.write_bytes(r.content)
                        if fig_num % 10 == 0:
                            print(f"  Downloaded {fig_num} images so far ({local}, {len(r.content)//1024}KB)")
                    except Exception as e:
                        print(f"  FAILED {local}: {e}")
                attachment_map[att["id"]] = (fig_num, local)
                time.sleep(0.15)

    print(f"Images: {fig_num} total")

    authors = set()
    current_date = None
    lines = []

    first_ts = messages[0]["timestamp"][:10] if messages else "?"
    last_ts = messages[-1]["timestamp"][:10] if messages else "?"
    for msg in messages:
        authors.add(msg["author"].get("global_name") or msg["author"].get("username", "?"))

    lines.append(f"# {channel_name} Discord Channel Transcript\n")
    lines.append(f"**Server:** {server_name}")
    lines.append(f"**Channel:** {channel_name}")
    lines.append(f"**Messages:** {len(messages)}")
    lines.append(f"**Authors:** {len(authors)}")
    lines.append(f"**Date range:** {first_ts} to {last_ts}")
    lines.append("\n---\n")

    for msg in messages:
        ts = msg["timestamp"]
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%I:%M %p")

        if date_str != current_date:
            current_date = date_str
            lines.append(f"\n## {date_str}\n")

        author = msg["author"].get("global_name") or msg["author"].get("username", "Unknown")
        content = msg.get("content", "")

        for mention in msg.get("mentions", []):
            display = mention.get("global_name") or mention.get("username", "?")
            content = content.replace(f"<@{mention['id']}>", f"@{display}")
            content = content.replace(f"<@!{mention['id']}>", f"@{display}")

        content = re.sub(r"<#(\d+)>", r"#channel", content)
        content = re.sub(r"<@&(\d+)>", r"@role", content)

        if content.strip():
            lines.append(f"**{author}** ({time_str}):")
            lines.append(content)
            lines.append("")

        for att in msg.get("attachments", []):
            if att["id"] in attachment_map:
                fn, local = attachment_map[att["id"]]
                lines.append(f"![Figure {fn}: {att.get('filename', 'image')}]({figs_rel}/{local})")
                lines.append("")

        for embed in msg.get("embeds", []):
            title = embed.get("title", "")
            desc = embed.get("description", "")
            url = embed.get("url", "")
            if title or desc:
                lines.append(f"> **{title}**")
                if desc:
                    for dline in desc.split("\n")[:3]:
                        lines.append(f"> {dline}")
                if url:
                    lines.append(f"> {url}")
                lines.append("")

        for reaction in msg.get("reactions", []):
            emoji = reaction["emoji"].get("name", "?")
            count = reaction.get("count", 0)
            lines.append(f"{emoji} {count}")
        if msg.get("reactions"):
            lines.append("")

    output_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nOutput: {output_md} ({output_md.stat().st_size // 1024}KB)")
    print(f"Messages: {len(messages)}, Authors: {len(authors)}, Images: {fig_num}")
    print(f"Date range: {first_ts} to {last_ts}")


if __name__ == "__main__":
    main()

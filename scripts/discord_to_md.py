#!/usr/bin/env python3
"""Convert Discord raw JSON to markdown and download image attachments."""
import sys, json, os, re, requests, time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SLUG = "qs-atlas"
RAW_JSON = Path("Input/\U0001f310-qs-atlas_raw.json")
if not RAW_JSON.exists():
    # try without emoji
    RAW_JSON = Path("Input/qs-atlas_raw.json")
FIGS_DIR = Path(f"Input/{SLUG}_figs")
OUTPUT_MD = Path(f"Input/{SLUG}_RAW_ARTICLE.md")

SERVER_NAME = "Quant Science Trading Community"
CHANNEL_NAME = "#qs-atlas"

def main():
    with open(RAW_JSON, 'r', encoding='utf-8') as f:
        messages = json.load(f)

    print(f"Processing {len(messages)} messages")

    # Download images
    FIGS_DIR.mkdir(exist_ok=True)
    fig_num = 0
    attachment_map = {}
    for msg in messages:
        for att in msg.get('attachments', []):
            ct = att.get('content_type', '') or ''
            if ct.startswith('image/'):
                fig_num += 1
                ext = att.get('filename', 'img.png').rsplit('.', 1)[-1]
                local = f"fig_{fig_num:03d}.{ext}"
                local_path = FIGS_DIR / local
                if not local_path.exists():
                    try:
                        r = requests.get(att['url'], timeout=30)
                        r.raise_for_status()
                        local_path.write_bytes(r.content)
                        print(f"  Downloaded {local} ({len(r.content)//1024}KB)")
                    except Exception as e:
                        print(f"  FAILED {local}: {e}")
                else:
                    print(f"  Already exists: {local}")
                attachment_map[att['id']] = (fig_num, local)
                time.sleep(0.2)

    print(f"Images: {fig_num} total")

    # Build markdown
    authors = set()
    current_date = None
    lines = []

    # Header
    first_ts = messages[0]['timestamp'][:10] if messages else '?'
    last_ts = messages[-1]['timestamp'][:10] if messages else '?'
    for msg in messages:
        authors.add(msg['author'].get('global_name') or msg['author'].get('username', '?'))

    lines.append(f"# {CHANNEL_NAME} Discord Channel Transcript\n")
    lines.append(f"**Server:** {SERVER_NAME}")
    lines.append(f"**Channel:** {CHANNEL_NAME}")
    lines.append(f"**Messages:** {len(messages)}")
    lines.append(f"**Authors:** {len(authors)}")
    lines.append(f"**Date range:** {first_ts} to {last_ts}")
    lines.append("\n---\n")

    fig_counter = 0
    for msg in messages:
        ts = msg['timestamp']
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        date_str = dt.strftime('%Y-%m-%d')
        time_str = dt.strftime('%I:%M %p')

        if date_str != current_date:
            current_date = date_str
            lines.append(f"\n## {date_str}\n")

        author = msg['author'].get('global_name') or msg['author'].get('username', 'Unknown')
        content = msg.get('content', '')

        # Resolve mentions
        for mention in msg.get('mentions', []):
            display = mention.get('global_name') or mention.get('username', '?')
            content = content.replace(f"<@{mention['id']}>", f"@{display}")
            content = content.replace(f"<@!{mention['id']}>", f"@{display}")

        # Remove channel mentions formatting
        content = re.sub(r'<#(\d+)>', r'#channel', content)
        # Remove role mentions
        content = re.sub(r'<@&(\d+)>', r'@role', content)

        if content.strip():
            lines.append(f"**{author}** ({time_str}):")
            lines.append(content)
            lines.append("")

        # Attachments
        for att in msg.get('attachments', []):
            if att['id'] in attachment_map:
                fn, local = attachment_map[att['id']]
                lines.append(f"![Figure {fn}: {att.get('filename', 'image')}]({SLUG}_figs/{local})")
                lines.append("")

        # Embeds
        for embed in msg.get('embeds', []):
            title = embed.get('title', '')
            desc = embed.get('description', '')
            url = embed.get('url', '')
            if title or desc:
                lines.append(f"> **{title}**")
                if desc:
                    for dline in desc.split('\n')[:3]:
                        lines.append(f"> {dline}")
                if url:
                    lines.append(f"> {url}")
                lines.append("")

        # Reactions
        for reaction in msg.get('reactions', []):
            emoji = reaction['emoji'].get('name', '?')
            count = reaction.get('count', 0)
            lines.append(f"{emoji} {count}")
        if msg.get('reactions'):
            lines.append("")

    # Write output
    OUTPUT_MD.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\nOutput: {OUTPUT_MD} ({OUTPUT_MD.stat().st_size // 1024}KB)")
    print(f"Messages: {len(messages)}, Authors: {len(authors)}, Images: {fig_num}")
    print(f"Date range: {first_ts} to {last_ts}")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Convert a Discord raw JSON dump into a per-message wiki.

Each message becomes its own markdown file with YAML frontmatter, and all image
attachments are downloaded to a shared images/ directory. Sibling to
discord_to_md.py (which produces a single big article) — this one produces
N small files suitable for an Obsidian / Logseq vault or a static site.

Usage:
  python discord_to_wiki.py <input_json> --output-dir <OUT> \
      [--after YYYY-MM-DD-hh-mm-ss] \
      [--include-system] [--no-replies] [--cdn-timeout SEC] \
      [--channel-slug SLUG] [--channel-name NAME] \
      [--server-name NAME]  [--guild-id ID]

Outputs into <OUT>/:
  messages/<YYYY-MM-DD>_<HHMM>_<author-slug>_<message-id>.md
  images/<message-id>_<NN>.<ext>
  INDEX.md
  Last_Message_Processed.md  (the resume marker, only updated when >0 new msgs)
"""
import sys
import json
import re
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import requests


# Discord message types that are real user-facing content (vs. system events).
# 0 = DEFAULT, 19 = REPLY, 20 = CHAT_INPUT_COMMAND, 23 = CONTEXT_MENU_COMMAND
USER_MESSAGE_TYPES = {0, 19, 20, 23}

EXT_FROM_CT = {
    "image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg",
    "image/gif": "gif", "image/webp": "webp", "image/bmp": "bmp",
    "image/svg+xml": "svg",
}


def parse_after(s: str) -> datetime:
    for fmt in ("%Y-%m-%d-%H-%M-%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(
        f"Unrecognized --after value: {s!r} (expected YYYY-MM-DD or YYYY-MM-DD-HH-MM-SS)"
    )


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def author_slug(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", name or "").strip().lower()
    s = re.sub(r"[\s_-]+", "-", s)
    return s or "anon"


def display_name(user: dict) -> str:
    if not user:
        return "unknown"
    return user.get("global_name") or user.get("username") or user.get("id", "unknown")


def attachment_ext(att: dict) -> str:
    ct = (att.get("content_type") or "").lower().split(";")[0].strip()
    if ct in EXT_FROM_CT:
        return EXT_FROM_CT[ct]
    fn = att.get("filename") or ""
    if "." in fn:
        ext = fn.rsplit(".", 1)[-1].lower()
        ext = re.sub(r"[^a-z0-9]", "", ext)[:8]
        return ext or "bin"
    return "bin"


def is_image(att: dict) -> bool:
    return (att.get("content_type") or "").lower().startswith("image/")


def yaml_str(value) -> str:
    """Double-quoted YAML string with minimal escaping. Always safe for our values."""
    if value is None:
        return "null"
    s = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{s}"'


def yaml_list(items) -> str:
    if not items:
        return "[]"
    return "[" + ", ".join(yaml_str(i) for i in items) + "]"


def collapse(text: str, n: int = 80) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    return (t[:n] + "...") if len(t) > n else t


def download(url: str, dest: Path, timeout: int, session: requests.Session):
    """Idempotent: returns (ok, bytes_written). Skips if file already non-empty."""
    if dest.exists() and dest.stat().st_size > 0:
        return True, 0
    if not url:
        return False, 0
    try:
        r = session.get(url, timeout=timeout, stream=True)
        if r.status_code != 200:
            return False, 0
        total = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
                total += len(chunk)
        return True, total
    except Exception as e:
        print(f"    download error for {url[:80]}: {e}", file=sys.stderr)
        return False, 0


def main():
    ap = argparse.ArgumentParser(description="Convert Discord raw JSON to per-message wiki")
    ap.add_argument("input_json")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--after", help="Only keep messages strictly newer than this UTC timestamp")
    ap.add_argument("--include-system", action="store_true",
                    help="Include join/pin/system-type messages")
    ap.add_argument("--no-replies", action="store_true",
                    help="Skip inline reply quote/wikilink (frontmatter still records reply_to)")
    ap.add_argument("--cdn-timeout", type=int, default=30,
                    help="Per-image download timeout in seconds")
    ap.add_argument("--channel-slug", default="channel")
    ap.add_argument("--channel-name", default="")
    ap.add_argument("--server-name", default="")
    ap.add_argument("--guild-id", default="")
    args = ap.parse_args()

    out = Path(args.output_dir)
    msg_dir = out / "messages"
    img_dir = out / "images"
    msg_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    raw = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    print(f"Loaded {len(raw)} messages from {args.input_json}", file=sys.stderr)

    # 2. Apply --after (compare truncated-to-second so the round-tripped marker
    #    excludes the boundary message; see plan §4.9)
    after_dt = parse_after(args.after) if args.after else None
    if after_dt:
        before_n = len(raw)
        raw = [
            m for m in raw
            if parse_iso(m["timestamp"]).replace(microsecond=0) > after_dt
        ]
        print(f"--after {args.after}: kept {len(raw)} of {before_n}", file=sys.stderr)

    # 3. Filter system messages
    skipped_system = 0
    if not args.include_system:
        kept = []
        for m in raw:
            if m.get("type", 0) in USER_MESSAGE_TYPES:
                kept.append(m)
            else:
                skipped_system += 1
        raw = kept
        if skipped_system:
            print(f"Skipped {skipped_system} system messages", file=sys.stderr)

    if not raw:
        print("No messages to write after filtering.", file=sys.stderr)
        print("FILES_WRITTEN=0", flush=True)
        print(f"OUTPUT_DIR={out}", flush=True)
        # Per plan §4.8: do not modify Last_Message_Processed.md if 0 new messages
        return

    channel_name = args.channel_name or args.channel_slug

    # 3. Build mention lookup (across all kept messages and reply parents)
    mention_lookup = {}
    for m in raw:
        for u in m.get("mentions", []) or []:
            mention_lookup[u["id"]] = display_name(u)
        ref = m.get("referenced_message") or {}
        if ref.get("author"):
            mention_lookup[ref["author"]["id"]] = display_name(ref["author"])

    # 4. Build message_id -> filename index
    def compose_filename(m):
        ts = parse_iso(m["timestamp"])
        return (
            f"{ts.strftime('%Y-%m-%d')}_{ts.strftime('%H%M')}_"
            f"{author_slug(display_name(m['author']))}_{m['id']}.md"
        )

    message_index = {m["id"]: compose_filename(m) for m in raw}

    def resolve_text(text):
        if not text:
            return ""
        text = re.sub(
            r"<@!?(\d+)>",
            lambda mt: "@" + mention_lookup.get(mt.group(1), mt.group(1)),
            text,
        )
        text = re.sub(r"<#(\d+)>", "#channel", text)
        text = re.sub(r"<a?:(\w+):\d+>", r":\1:", text)
        text = re.sub(r"<@&(\d+)>", "@role", text)
        return text

    # 5. Process each message
    images_downloaded = 0
    images_existed = 0
    images_failed = 0
    files_written = 0
    authors = set()
    rows_for_index = []
    session = requests.Session()

    for m in raw:
        mid = m["id"]
        author = display_name(m["author"])
        authors.add(author)
        ts = parse_iso(m["timestamp"])
        date_s = ts.strftime("%Y-%m-%d")
        time_s = ts.strftime("%H:%M")
        filename = message_index[mid]

        # Download attachments
        att_local = []
        for seq, att in enumerate(m.get("attachments", []) or [], start=1):
            ext = attachment_ext(att)
            local_name = f"{mid}_{seq:02d}.{ext}"
            dest = img_dir / local_name
            existed = dest.exists() and dest.stat().st_size > 0
            ok, size = download(att.get("url", ""), dest, args.cdn_timeout, session)
            if ok:
                if existed:
                    images_existed += 1
                else:
                    images_downloaded += 1
                    print(
                        f"  [+] {local_name} ({(size // 1024) if size else 0}KB)",
                        file=sys.stderr,
                    )
                    time.sleep(0.15)
                att_local.append({
                    "name": local_name,
                    "is_image": is_image(att),
                    "orig_name": att.get("filename", local_name),
                })
            else:
                images_failed += 1
                print(f"  [!] FAILED {local_name}", file=sys.stderr)

        # Reply resolution
        ref_msg_raw = m.get("referenced_message") or {}
        front_reply_to = ref_msg_raw.get("id") or None

        ref = ref_msg_raw if (ref_msg_raw and not args.no_replies) else None
        ref_filename = message_index.get(ref["id"]) if ref else None
        ref_author = display_name(ref.get("author")) if ref else None
        ref_snippet = collapse(resolve_text(ref.get("content", "")), 80) if ref else ""

        body_text = resolve_text(m.get("content", ""))

        mention_names = [display_name(u) for u in (m.get("mentions") or [])]

        reactions = []
        for r in m.get("reactions", []) or []:
            emoji_name = (r.get("emoji") or {}).get("name") or "?"
            reactions.append({"emoji": emoji_name, "count": r.get("count", 0)})

        tags = sorted({author_slug(author), date_s, args.channel_slug})

        # ---- Frontmatter ----
        fm = ["---"]
        fm.append(f"message_id: {yaml_str(mid)}")
        fm.append(f"channel: {yaml_str(args.channel_slug)}")
        fm.append(f"server: {yaml_str(args.server_name)}")
        fm.append(f"author: {yaml_str(author)}")
        fm.append(f"author_id: {yaml_str(m['author'].get('id', ''))}")
        fm.append(f"date: {yaml_str(date_s)}")
        fm.append(f"time: {yaml_str(time_s)}")
        fm.append(f"timestamp: {yaml_str(m['timestamp'])}")
        fm.append(f"edited: {'true' if m.get('edited_timestamp') else 'false'}")
        fm.append(f"reply_to: {yaml_str(front_reply_to) if front_reply_to else 'null'}")
        fm.append(f"mentions: {yaml_list(mention_names)}")
        fm.append(f"attachments: {len(m.get('attachments', []) or [])}")
        image_paths = [f"images/{a['name']}" for a in att_local if a["is_image"]]
        fm.append(f"images: {yaml_list(image_paths)}")
        if reactions:
            fm.append("reactions:")
            for r in reactions:
                fm.append(f"  - emoji: {yaml_str(r['emoji'])}")
                fm.append(f"    count: {r['count']}")
        else:
            fm.append("reactions: []")
        fm.append(f"tags: {yaml_list(tags)}")
        if args.include_system and m.get("type", 0) not in (0, 19):
            fm.append(f"system_type: {m.get('type', 0)}")
        fm.append("---")
        fm.append("")

        # ---- Body ----
        body = []
        body.append(f"# {author} — {date_s} {time_s}")
        body.append("")

        if ref:
            if ref_filename:
                body.append(f"> **Replying to** [[{ref_filename[:-3]}]]")
            else:
                body.append(f"> **Replying to** **{ref_author}** _(parent out of range)_")
            if ref_snippet:
                body.append(f"> _{ref_snippet}_")
            body.append("")

        if body_text.strip():
            body.append(body_text.rstrip())
            body.append("")

        for a in att_local:
            if a["is_image"]:
                body.append(f"![{a['orig_name']}](../images/{a['name']})")
            else:
                body.append(f"[{a['orig_name']}](../images/{a['name']})")
            body.append("")

        for emb in m.get("embeds", []) or []:
            t = emb.get("title", "")
            d = emb.get("description", "")
            u = emb.get("url", "")
            if t or d or u:
                if t:
                    body.append(f"> **{t}**")
                if d:
                    for line in d.split("\n")[:3]:
                        body.append(f"> {line}")
                if u:
                    body.append(f"> {u}")
                body.append("")

        for st in m.get("sticker_items", []) or []:
            body.append(f"*[Sticker: {st.get('name', '?')}]*")
            body.append("")
        if m.get("poll"):
            q = (m["poll"].get("question") or {}).get("text", "?")
            body.append(f"*[Poll: {q}]*")
            body.append("")

        if reactions:
            parts = [f"{r['emoji']} ×{r['count']}" for r in reactions]
            body.append("**Reactions:** " + "  ".join(parts))
            body.append("")

        body.append("---")
        body.append("")
        per_msg_chan = m.get("channel_id", "")
        if args.guild_id and per_msg_chan:
            link = f"https://discord.com/channels/{args.guild_id}/{per_msg_chan}/{mid}"
            body.append(f"**Source:** Discord message [`{mid}`]({link}) in `#{channel_name}`")
        else:
            body.append(f"**Source:** Discord message `{mid}` in `#{channel_name}`")
        body.append("")

        if m.get("edited_timestamp"):
            body.append(f"<!-- edited at {m['edited_timestamp']} -->")

        out_path = msg_dir / filename
        out_path.write_text("\n".join(fm + body), encoding="utf-8")
        files_written += 1

        snippet = collapse(body_text, 80) or ("[image only]" if image_paths else "[no text]")
        rows_for_index.append((date_s, time_s, author, snippet, filename))

    # 6. INDEX.md
    first_ts = raw[0]["timestamp"][:10]
    last_ts = raw[-1]["timestamp"][:10]
    n_images_disk = sum(1 for p in img_dir.iterdir() if p.is_file())

    idx = []
    idx.append(f"# #{channel_name} — Discord Mirror")
    idx.append("")
    idx.append(f"**Server:** {args.server_name or '(unknown)'}")
    idx.append(f"**Channel:** #{channel_name}")
    idx.append(f"**Date range:** {first_ts} → {last_ts}")
    if args.include_system:
        idx.append(f"**Messages:** {files_written}")
    else:
        idx.append(f"**Messages:** {files_written} (system messages skipped: {skipped_system})")
    idx.append(f"**Images on disk:** {n_images_disk}")
    idx.append(f"**Authors:** {len(authors)}")
    idx.append("")
    idx.append("## Messages by date")
    idx.append("")
    idx.append("| Date | Time | Author | Snippet | File |")
    idx.append("|------|------|--------|---------|------|")
    for d, t, a, s, f in rows_for_index:
        s_safe = s.replace("|", "\\|")
        a_safe = a.replace("|", "\\|")
        idx.append(f"| {d} | {t} | {a_safe} | {s_safe} | [open](messages/{f}) |")
    (out / "INDEX.md").write_text("\n".join(idx), encoding="utf-8")

    # 7. Last_Message_Processed.md (only when this run produced messages)
    newest = raw[-1]
    newest_ts = parse_iso(newest["timestamp"]).astimezone(timezone.utc)
    marker_stamp = newest_ts.strftime("%Y-%m-%d-%H-%M-%S")
    marker_dt = newest_ts.strftime("%Y-%m-%d %H:%M:%S UTC")
    newest_author = display_name(newest["author"])
    newest_snippet = collapse(resolve_text(newest.get("content", "")), 80) or "[no text]"
    newest_chan = newest.get("channel_id", "")

    cmd_block = (
        f"    /discord-to-wiki {newest_chan} \\\n"
        f"        --output-dir {args.output_dir} \\\n"
        f"        --after {marker_stamp}"
    )

    marker = []
    marker.append("# Last Message Processed")
    marker.append("")
    marker.append(f"**Timestamp:** {marker_stamp}")
    marker.append(f"**Message ID:** {newest['id']}")
    marker.append(f"**Author:** {newest_author}")
    marker.append(f"**Datetime (UTC):** {marker_dt}")
    marker.append(f"**Snippet:** {newest_snippet}")
    marker.append("")
    marker.append("To resume from after this message:")
    marker.append("")
    marker.append(cmd_block)
    marker.append("")
    (out / "Last_Message_Processed.md").write_text("\n".join(marker), encoding="utf-8")

    # 8. Report
    print(f"FILES_WRITTEN={files_written}", flush=True)
    print(f"IMAGES_DOWNLOADED={images_downloaded}", flush=True)
    print(f"IMAGES_EXISTED={images_existed}", flush=True)
    print(f"IMAGES_FAILED={images_failed}", flush=True)
    print(f"AUTHORS={len(authors)}", flush=True)
    print(f"DATE_RANGE={first_ts} to {last_ts}", flush=True)
    print(f"OUTPUT_DIR={out}", flush=True)
    print(f"LAST_MESSAGE_TIMESTAMP={marker_stamp}", flush=True)


if __name__ == "__main__":
    main()

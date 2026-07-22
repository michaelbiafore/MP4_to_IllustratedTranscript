#!/usr/bin/env python3
"""
Convert Whisper SRT output to RAW_TRANSCRIPT.md format.

Takes an SRT file with timestamped subtitles and produces the MM:SS format
expected by /format-transcript.

Usage:
  python scripts/srt_to_raw.py <input.srt> [output.md]

If output path is omitted, prints to stdout.
"""

import re
import sys
from pathlib import Path


def parse_srt(srt_text: str) -> list[tuple[float, str]]:
    """Parse SRT into list of (start_seconds, text)."""
    entries = []
    blocks = re.split(r"\n\n+", srt_text.strip())
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        # Parse timestamp line: 00:01:23,456 --> 00:01:25,789
        ts_match = re.match(r"(\d+):(\d+):(\d+),(\d+)", lines[1])
        if ts_match:
            h, m, s, ms = ts_match.groups()
            start = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
            text = " ".join(lines[2:]).strip()
            if text:
                entries.append((start, text))
    return entries


def entries_to_raw_transcript(entries: list[tuple[float, str]], chunk_seconds: float = 30.0) -> str:
    """Group SRT entries into ~30-second chunks in MM:SS format."""
    if not entries:
        return ""

    lines = []
    chunk_start = 0.0
    chunk_texts = []

    for start, text in entries:
        if start - chunk_start > chunk_seconds and chunk_texts:
            m, s = divmod(int(chunk_start), 60)
            lines.append(f"{m}:{s:02d} {' '.join(chunk_texts)}")
            chunk_texts = []
            chunk_start = start
        chunk_texts.append(text)

    if chunk_texts:
        m, s = divmod(int(chunk_start), 60)
        lines.append(f"{m}:{s:02d} {' '.join(chunk_texts)}")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python srt_to_raw.py <input.srt> [output.md]")
        sys.exit(1)

    srt_path = Path(sys.argv[1])
    if not srt_path.exists():
        print(f"ERROR: SRT file not found: {srt_path}")
        sys.exit(1)

    entries = parse_srt(srt_path.read_text(encoding="utf-8"))
    print(f"Parsed {len(entries)} subtitle entries from {srt_path.name}")

    output = entries_to_raw_transcript(entries)

    if len(sys.argv) > 2:
        output_path = Path(sys.argv[2])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"Written to {output_path} ({len(output)} chars)")
    else:
        print(output)


if __name__ == "__main__":
    main()

"""Convert a fetch_transcript.py output (MM:SS text, with possible
continuation lines that lack a timestamp) into the standard "[M:SS] text"
per-line format expected by /format-mp4 downstream.

Usage:
    python scripts/_convert_yt_transcript_to_bracketed.py <in.md> <out.txt>
"""
import re
import sys
from pathlib import Path

TS_RE = re.compile(r"^(\d{1,2}):(\d{2})\s+(.*)$")


def main(src: str, dst: str) -> None:
    out: list[str] = []
    last_ts: str | None = None
    last_text_parts: list[str] = []

    def flush() -> None:
        if last_ts is not None and last_text_parts:
            joined = " ".join(p.strip() for p in last_text_parts if p.strip())
            if joined:
                out.append(f"[{last_ts}] {joined}")

    for raw in Path(src).read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = TS_RE.match(line)
        if m:
            flush()
            mm, ss, text = int(m.group(1)), int(m.group(2)), m.group(3)
            last_ts = f"{mm}:{ss:02d}"
            last_text_parts = [text]
        else:
            if last_ts is None:
                continue  # skip orphan content before the first timestamp
            last_text_parts.append(line)
    flush()

    Path(dst).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Wrote {len(out)} lines to {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

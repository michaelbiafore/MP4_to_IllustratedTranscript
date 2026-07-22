"""Convert a WizWhisp transcript file (MM:SS  text) to the [M:SS] text format
expected by /format-mp4, scaling timestamps by a constant multiplier.

The MP4 used here was recorded at 3x speed against the real YouTube video. The
WizWhisp timestamps refer to the 3x recording's wall time, so real-video time =
recording time x 3. Multiplying by 3 here makes downstream output (formatted
transcript and slides) reference real 1x YouTube times.

Usage:
    python scripts/_convert_wizwhisp_3x_to_1x.py <in_file> <out_file> [--multiplier N]
"""
import argparse
import re
from pathlib import Path

LINE_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s+(.*\S)\s*$")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("in_file")
    p.add_argument("out_file")
    p.add_argument("--multiplier", type=int, default=3)
    args = p.parse_args()

    raw = Path(args.in_file).read_text(encoding="utf-8", errors="ignore")
    out_lines = []
    for line in raw.splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue
        mm, ss, text = int(m.group(1)), int(m.group(2)), m.group(3)
        total = (mm * 60 + ss) * args.multiplier
        out_mm, out_ss = total // 60, total % 60
        out_lines.append(f"[{out_mm}:{out_ss:02d}] {text}")

    Path(args.out_file).write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(out_lines)} lines to {args.out_file}")


if __name__ == "__main__":
    main()

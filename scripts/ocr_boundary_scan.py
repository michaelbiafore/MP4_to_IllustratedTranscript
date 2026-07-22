#!/usr/bin/env python3
"""
ocr_boundary_scan.py — OCR the top region of each minute-sampled frame
to surface slide titles. Used to detect lecture boundaries in a long
recording where Udemy duration math has too much idle-time drift.

Usage:
  python scripts/ocr_boundary_scan.py <frames_dir> [--top-pct 25] [--out FILE]
"""
import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import pytesseract

TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESS):
    pytesseract.pytesseract.tesseract_cmd = TESS


def ocr_top(jpg_path: Path, top_pct: float) -> str:
    img = cv2.imread(str(jpg_path))
    if img is None:
        return "[unreadable]"
    h, w = img.shape[:2]
    crop = img[: int(h * top_pct / 100.0), :]
    txt = pytesseract.image_to_string(crop, config="--psm 6")
    return " | ".join(line.strip() for line in txt.splitlines() if line.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames_dir")
    ap.add_argument("--top-pct", type=float, default=25.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    fdir = Path(args.frames_dir)
    frames = sorted(fdir.glob("*.jpg"))
    print(f"OCR'ing top {args.top_pct}% of {len(frames)} frames in {fdir}", file=sys.stderr)

    rows = []
    for i, f in enumerate(frames):
        title = ocr_top(f, args.top_pct)
        # Each frame represents 60 sec; first frame is t=0
        t_sec = i * 60
        m, s = divmod(t_sec, 60)
        rows.append({"idx": i + 1, "filename": f.name, "t_sec": t_sec,
                     "t_str": f"{m}:{s:02d}", "title": title})

    out = args.out or str(fdir.parent / f"{fdir.name}_ocr.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)

    # Print human-readable
    for r in rows:
        print(f"  {r['idx']:3d}  t={r['t_str']:>6s}  {r['title'][:120]}")

    print(f"\nSaved → {out}", file=sys.stderr)


if __name__ == "__main__":
    main()

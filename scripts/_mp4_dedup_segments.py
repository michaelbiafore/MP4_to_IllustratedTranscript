#!/usr/bin/env python3
"""Change-point segmentation of 1-fps frames -> keep the LAST frame of each
static run (settled slide / fully-revealed build / final demo state).

Neighbor-based: a new run starts when frame[i] differs from frame[i-1] by more
than --threshold (Hamming on a 256-bit pHash, hash_size=16, which is far more
discriminating than the 64-bit default and does NOT over-merge structurally
similar light/text slides). Static holds collapse to one pick; progressive
reveals whose per-second delta stays under threshold also collapse to their
final frame; hard slide cuts and demo actions each start a new run.

Usage: _mp4_dedup_segments.py <figs_dir> <out_json> [--threshold N] [--interval S] [--min-run K]
"""
import sys, json, argparse
from pathlib import Path
from PIL import Image
import imagehash

ap = argparse.ArgumentParser()
ap.add_argument("figs_dir")
ap.add_argument("out_json")
ap.add_argument("--threshold", type=int, default=14, help="neighbor Hamming dist to start a new run")
ap.add_argument("--interval", type=int, default=1)
ap.add_argument("--hash-size", type=int, default=16)
args = ap.parse_args()

figs = Path(args.figs_dir)
frames = sorted(figs.glob("frame_*.jpg"))
print(f"hashing {len(frames)} frames (hash_size={args.hash_size})...", file=sys.stderr)

items = []
for i, f in enumerate(frames):
    try:
        h = imagehash.phash(Image.open(f), hash_size=args.hash_size)
    except Exception as e:
        print(f"  skip {f.name}: {e}", file=sys.stderr); h = None
    items.append((f, h))
    if i % 500 == 0:
        print(f"  {i}/{len(frames)}", file=sys.stderr)

def fnum(p):
    return int(p.stem.split("_")[1])

# Neighbor-based change detection
runs, run, prev = [], [], None
for f, h in items:
    if h is None:
        continue
    if prev is None:
        run = [(f, h)]; prev = h; continue
    if (h - prev) <= args.threshold:
        run.append((f, h))
    else:
        runs.append(run); run = [(f, h)]
    prev = h
if run:
    runs.append(run)

picks = []
for run in runs:
    f, h = run[-1]
    n = fnum(f)
    picks.append({
        "frame_index": n,
        "timestamp_sec": (n - 1) * args.interval,
        "run_len": len(run),
        "phash": str(h),
    })

Path(args.out_json).write_text(json.dumps(picks, indent=1), encoding="utf-8")
print(f"{len(frames)} frames -> {len(runs)} runs -> {len(picks)} candidates", file=sys.stderr)

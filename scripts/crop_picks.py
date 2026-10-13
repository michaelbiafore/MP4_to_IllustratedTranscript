#!/usr/bin/env python3
"""Materialize curated, cropped figures from a picks file.

picks.json is a JSON array of [orig_frame, [l,t,r,b], caption]. Each entry crops
the raw frame Input/{slug}_figs/frame_{NNNN}.jpg to the given box (removing the
YouTube player chrome / settings menu) and writes it to {slug}_figs_filtered/ as
fig_{NN}.jpg, plus a manifest with figure_num, filename, timestamp (real video
time = interval*speedup), and caption.

Usage:
  uv run python scripts/crop_picks.py <figs_dir> <out_dir> <manifest.json> <picks.json> <interval_sec> <speedup>
"""
import json
import sys
from pathlib import Path
from PIL import Image


def fmt(t):
    return f"{int(t)//60}:{int(t)%60:02d}"


def main():
    figs_dir, out_dir, manifest_path, picks_path, interval, speedup = sys.argv[1:7]
    interval = float(interval)
    speedup = float(speedup)
    figs = Path(figs_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    picks = json.loads(Path(picks_path).read_text(encoding="utf-8"))

    manifest = []
    for i, (frame, box, caption) in enumerate(picks, start=1):
        src = figs / f"frame_{frame:04d}.jpg"
        im = Image.open(src)
        l, t, r, b = box
        im = im.crop((l, t, r, b))
        name = f"fig_{i:02d}.jpg"
        im.save(out / name, quality=92)
        rec_s = (frame - 1) * interval
        real_s = rec_s * speedup
        manifest.append({
            "figure_num": i,
            "filename": name,
            "orig_frame": frame,
            "rec_timestamp": fmt(rec_s),
            "timestamp": fmt(real_s),
            "total_seconds": round(real_s),
            "crop": box,
            "caption_hint": caption,
        })
        print(f"fig_{i:02d}  frame {frame:>4}  rec {fmt(rec_s):>5}  real {fmt(real_s):>6}  {im.size[0]}x{im.size[1]}")

    Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWrote {len(manifest)} figures to {out} and manifest {manifest_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Crop each picked frame to the slide/app region (removing Zoom chrome) and
materialize into figs_filtered/ with the house naming, plus a manifest.

Usage: _mp4_crop_materialize.py <figs_dir> <out_dir> <manifest_json> <interval> <picks_json>
picks_json: [[frame_index, caption], ...] in document order.
Crop box is fixed for this recording: (16,200,1506,1000).
"""
import sys, json, shutil
from pathlib import Path
from PIL import Image

figs, out_dir, manifest_path, interval, picks_path = (
    sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5])
BOX = (16, 200, 1506, 1000)

out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
picks = json.load(open(picks_path, encoding="utf-8"))
figs = Path(figs)

manifest = []
for i, (idx, caption) in enumerate(picks, 1):
    total = (idx - 1) * interval
    mm, ss = total // 60, total % 60
    fn = f"frame_{mm:03d}m{ss:02d}s_screen_{i:03d}.jpg"
    src = figs / f"frame_{idx:04d}.jpg"
    im = Image.open(src).crop(BOX)
    im.save(out / fn, quality=88)
    manifest.append({
        "figure_num": i,
        "filename": fn,
        "timestamp": f"{mm}:{ss:02d}",
        "total_seconds": total,
        "original_frame": idx,
        "caption_hint": caption,
    })

json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"materialized {len(manifest)} figures -> {out_dir}")
print(f"manifest -> {manifest_path}")

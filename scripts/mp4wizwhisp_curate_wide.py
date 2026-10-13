"""Materialize curated frames + manifest, for figs dirs with >9999 frames.

Identical in behaviour and output to mp4wizwhisp_curate.py, except the source
frame filenames may use any zero-padding width (frame_00600.jpg, frame_0600.jpg,
frame_600.jpg all resolve), which is what you get when a long recording is
sampled finely enough to pass 9,999 frames.

Usage:
    python mp4wizwhisp_curate_wide.py <figs_dir> <out_dir> <manifest_path> <interval_seconds> <picks_json>

<picks_json> is a list of [frame_index, caption] pairs in document order. Each
picked frame is re-saved (quality 92) into <out_dir> as
    frame_<MMM>m<SS>s_screen_<NNN>.jpg
where the timestamp is (index-1)*interval seconds -- i.e. true recording time
when <interval_seconds> is expressed in real (un-sped-up) seconds.
"""
import glob
import json
import os
import sys

from PIL import Image

figs, out, manifest_path, interval, picks_json = (
    sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
)
os.makedirs(out, exist_ok=True)
picks = json.load(open(picks_json, encoding="utf-8"))


def find_frame(idx: int) -> str:
    """Locate frame <idx> regardless of the zero-padding width used."""
    for width in (5, 4, 6, 3, 0):
        cand = os.path.join(figs, f"frame_{idx:0{width}d}.jpg" if width else f"frame_{idx}.jpg")
        if os.path.exists(cand):
            return cand
    hits = [p for p in glob.glob(os.path.join(figs, "frame_*.jpg"))
            if int(os.path.basename(p)[6:-4]) == idx]
    if not hits:
        raise SystemExit(f"frame {idx} not found in {figs}")
    return hits[0]


manifest = []
for i, (idx, cap) in enumerate(picks, start=1):
    idx = int(idx)
    src = find_frame(idx)
    sec = (idx - 1) * interval
    mins, secs = sec // 60, sec % 60
    name = f"frame_{mins:03d}m{secs:02d}s_screen_{i:03d}.jpg"
    Image.open(src).save(os.path.join(out, name), quality=92)
    manifest.append({
        "figure_num": i, "filename": name, "timestamp": f"{mins}:{secs:02d}",
        "total_seconds": sec, "original_frame": os.path.basename(src), "caption_hint": cap,
    })
    print(f"{name}  <- {os.path.basename(src)}  ({mins}:{secs:02d})")

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
print(f"\nManifest: {manifest_path}  ({len(manifest)} figures)")

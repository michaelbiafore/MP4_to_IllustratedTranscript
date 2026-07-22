"""Materialize the curated 'interesting' frames + write a figure manifest.

Usage:
    python mp4wizwhisp_curate.py <figs_dir> <out_dir> <manifest_path> <interval_seconds> <picks_json>

<picks_json> is a JSON file containing a list of [frame_index, caption] pairs,
in the order the figures should appear in the document. Each picked
frame_<index>.jpg is re-saved (quality 92) into <out_dir> as
    frame_<MMM>m<SS>s_screen_<NNN>.jpg
where the timestamp is (index-1)*interval seconds and NNN is the figure number
(1-based, document order). A manifest JSON is written to <manifest_path>.
"""
import os, sys, json
from PIL import Image

figs, out, manifest_path, interval, picks_json = (
    sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
)
os.makedirs(out, exist_ok=True)
picks = json.load(open(picks_json, encoding="utf-8"))

manifest = []
for i, (idx, cap) in enumerate(picks, start=1):
    idx = int(idx)
    src = os.path.join(figs, f"frame_{idx:04d}.jpg")
    sec = (idx - 1) * interval
    mins, secs = sec // 60, sec % 60
    name = f"frame_{mins:03d}m{secs:02d}s_screen_{i:03d}.jpg"
    dst = os.path.join(out, name)
    Image.open(src).save(dst, quality=92)
    manifest.append({
        "figure_num": i, "filename": name, "timestamp": f"{mins}:{secs:02d}",
        "total_seconds": sec, "original_frame": f"frame_{idx:04d}.jpg", "caption_hint": cap,
    })
    print(f"{name}  <- frame_{idx:04d}.jpg  ({mins}:{secs:02d})")

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
print(f"\nManifest: {manifest_path}  ({len(manifest)} figures)")

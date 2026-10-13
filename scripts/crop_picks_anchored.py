"""Curate picked frames with optional crop + a real-time mapping.

Usage:
    python _curate_crop.py <figs_dir> <out_dir> <manifest_path> <picks_json> <scale> <offset>

picks_json entries are [frame_index, caption, crop|null] where crop is
[left, top, right, bottom] in source-frame pixels.

The recording is a screen-capture of a video played back at `scale`x, started
`offset` capture-seconds before the talk's 0:00, so

    real_seconds = scale * ((index - 1) * capture_interval - offset)

is baked in by the caller passing `scale` = seconds of real talk per frame step
and `offset` = real seconds to subtract. i.e. real = index*scale - offset.
"""
import os, sys, json
from PIL import Image

figs, out, manifest_path, picks_json = sys.argv[1:5]
scale, offset = float(sys.argv[5]), float(sys.argv[6])
os.makedirs(out, exist_ok=True)
picks = json.load(open(picks_json, encoding="utf-8"))

manifest = []
for i, entry in enumerate(picks, start=1):
    idx, cap = int(entry[0]), entry[1]
    crop = entry[2] if len(entry) > 2 else None
    src = os.path.join(figs, f"frame_{idx:04d}.jpg")
    sec = int(round(idx * scale - offset))
    mins, secs = sec // 60, sec % 60
    name = f"frame_{mins:03d}m{secs:02d}s_screen_{i:03d}.jpg"
    dst = os.path.join(out, name)
    im = Image.open(src)
    if crop:
        im = im.crop(tuple(crop))
    im.save(dst, quality=92)
    manifest.append({
        "figure_num": i, "filename": name, "timestamp": f"{mins}:{secs:02d}",
        "total_seconds": sec, "original_frame": f"frame_{idx:04d}.jpg",
        "crop": crop, "caption_hint": cap,
    })
    print(f"{name}  <- frame_{idx:04d}.jpg  ({mins}:{secs:02d}){'  [cropped]' if crop else ''}")

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
print(f"\nManifest: {manifest_path}  ({len(manifest)} figures)")

"""Contact sheets for an arbitrary list of candidate frames (e.g. the run
representatives emitted by _mp4_dedup_segments.py).

Unlike mp4wizwhisp_montage.py (which tiles EVERY frame), this tiles only the
frames named in a candidates JSON, so a long sped-up recording sampled at 1 s
can be triaged from a handful of sheets instead of dozens.

Candidates JSON: either a list of ints, or a list of objects with a
"frame_index" key (the shape _mp4_dedup_segments.py writes).

Usage:
    python scripts/_montage_from_runs.py <figs_dir> <candidates_json> <out_dir> \
        [--interval S] [--cols C] [--rows R] [--thumb-w W]

Each thumbnail is labeled "#<frame_index>  <M:SS>" where M:SS = (index-1)*interval,
so picks map straight back to <figs_dir>/frame_NNNN.jpg for mp4wizwhisp_curate.py.
"""
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("figs_dir")
ap.add_argument("candidates_json")
ap.add_argument("out_dir")
ap.add_argument("--interval", type=float, default=1.0)
ap.add_argument("--cols", type=int, default=5)
ap.add_argument("--rows", type=int, default=6)
ap.add_argument("--thumb-w", type=int, default=384)
args = ap.parse_args()

figs = Path(args.figs_dir)
out = Path(args.out_dir)
out.mkdir(parents=True, exist_ok=True)

raw = json.loads(Path(args.candidates_json).read_text(encoding="utf-8"))
idxs = [c if isinstance(c, int) else int(c["frame_index"]) for c in raw]

try:
    font = ImageFont.truetype("arial.ttf", 18)
except Exception:
    font = ImageFont.load_default()

PER = args.cols * args.rows
LABEL_H = 26
pages = math.ceil(len(idxs) / PER)

for pg in range(pages):
    chunk = idxs[pg * PER:(pg + 1) * PER]
    im0 = Image.open(figs / f"frame_{chunk[0]:04d}.jpg")
    th = int(args.thumb_w * im0.height / im0.width)
    cell_h = th + LABEL_H
    canvas = Image.new("RGB", (args.cols * args.thumb_w, args.rows * cell_h), (20, 20, 24))
    draw = ImageDraw.Draw(canvas)
    for i, idx in enumerate(chunk):
        r, c = divmod(i, args.cols)
        x, y = c * args.thumb_w, r * cell_h
        im = Image.open(figs / f"frame_{idx:04d}.jpg").resize((args.thumb_w, th))
        canvas.paste(im, (x, y + LABEL_H))
        sec = int(round((idx - 1) * args.interval))
        draw.rectangle([x, y, x + args.thumb_w, y + LABEL_H], fill=(0, 0, 0))
        draw.text((x + 4, y + 3), f"#{idx}  {sec // 60}:{sec % 60:02d}",
                  fill=(120, 230, 160), font=font)
    path = out / f"sheet_{pg + 1:02d}.jpg"
    canvas.save(path, quality=88)
    print(f"{path}  ({len(chunk)} frames)")

print(f"{len(idxs)} candidates -> {pages} sheets in {out}")

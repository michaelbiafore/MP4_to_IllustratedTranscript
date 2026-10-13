"""Per-frame features for figure detection on a sped-up screencast.

Usage: python _jev_detect.py <figs_dir> <out_features.json>

For each frame_NNNN.jpg writes:
  mot   mean abs grayscale diff vs the previous frame (0 = static)
  edge  mean abs gradient magnitude (UI/text is high, photographic b-roll is lower/smoother)
  sat   mean HSV saturation
  lum   mean luma
  flat  fraction of pixels within 12 luma of the modal luma (flat UI/title backgrounds)
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

figs = Path(sys.argv[1])
out = Path(sys.argv[2])

paths = sorted(figs.glob("frame_*.jpg"))
prev = None
rows = []
for i, p in enumerate(paths, start=1):
    im = Image.open(p).convert("RGB").resize((192, 108), Image.BILINEAR)
    a = np.asarray(im, dtype=np.float32)
    g = a.mean(axis=2)

    mot = 0.0 if prev is None else float(np.abs(g - prev).mean())
    prev = g

    gy, gx = np.gradient(g)
    edge = float(np.hypot(gx, gy).mean())

    mx = a.max(axis=2)
    mn = a.min(axis=2)
    sat = float(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0).mean())

    hist = np.bincount(g.astype(np.uint8).ravel(), minlength=256)
    mode = int(hist.argmax())
    flat = float((np.abs(g - mode) <= 12).mean())

    rows.append({
        "i": i, "sec": i - 1,
        "mot": round(mot, 3), "edge": round(edge, 3),
        "sat": round(sat, 4), "lum": round(float(g.mean()), 2), "flat": round(flat, 4),
    })
    if i % 400 == 0:
        print(f"  ...{i}/{len(paths)}", flush=True)

out.write_text(json.dumps(rows), encoding="utf-8")

m = np.array([r["mot"] for r in rows])
e = np.array([r["edge"] for r in rows])
f = np.array([r["flat"] for r in rows])
print(f"frames: {len(rows)}")
for name, arr in (("mot", m), ("edge", e), ("flat", f)):
    qs = np.percentile(arr, [5, 25, 50, 75, 90, 95])
    print(f"{name:5s} p5={qs[0]:.2f} p25={qs[1]:.2f} p50={qs[2]:.2f} p75={qs[3]:.2f} p90={qs[4]:.2f} p95={qs[5]:.2f}")
print(f"static (mot<1.0): {(m < 1.0).sum()}   mot<2.0: {(m < 2.0).sum()}   mot<3.0: {(m < 3.0).sum()}")

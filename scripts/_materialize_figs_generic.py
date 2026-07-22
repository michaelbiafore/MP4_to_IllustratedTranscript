"""Materialize a figure set from a figspec JSON (demos cropped, slide renders downscaled).

Usage: python _materialize_figs_generic.py <figspec.json> <manifest_out.json>
Demo figures are cropped to the named box (removing webcams/toolbar/chat) and
downscaled; slide figures are downscaled from the 4K official render.
"""
import os, re, json, sys
from PIL import Image

SPEC = json.load(open(sys.argv[1], encoding="utf-8"))
MANIFEST_OUT = sys.argv[2]
FIGS = SPEC["figs_dir"]; SLIDES = SPEC["slides_dir"]; OUT = SPEC["out_dir"]
BOXES = SPEC["boxes"]; W = SPEC["width"]
os.makedirs(OUT, exist_ok=True)

manifest = []
for i, fig in enumerate(SPEC["figures"], 1):
    if fig["type"] == "demo":
        src = os.path.join(FIGS, f"frame_{fig['frame']:04d}.jpg")
        im = Image.open(src).convert("RGB").crop(tuple(BOXES[fig["box"]]))
        kind = "demo"
    else:
        im = Image.open(os.path.join(SLIDES, fig["src"])).convert("RGB")
        kind = "slide"
    w, h = im.size
    if w > W:
        im = im.resize((W, int(W * h / w)), Image.LANCZOS)
    fn = f"fig_{i:02d}_{kind}.jpg"
    im.save(os.path.join(OUT, fn), quality=88)
    manifest.append({"figure_num": i, "filename": fn, "type": kind,
                     "ts": fig.get("ts", ""), "caption": fig["caption"]})
    print(f"  fig {i:02d} [{kind}] -> {fn}  ({im.size[0]}x{im.size[1]})")

json.dump(manifest, open(MANIFEST_OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"DONE — {len(manifest)} figures")

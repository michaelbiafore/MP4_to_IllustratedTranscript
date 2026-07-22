"""Segment extracted frames into distinct scenes via perceptual hashing.

Walks frame_NNNN.jpg in order, computes pHash, and starts a new scene whenever
the hash distance from the current scene's anchor exceeds THRESH. Picks the LAST
frame of each scene as its representative (most complete reveal). Writes a compact
contact sheet of representatives and a JSON list of [frame_index, timestamp_sec].
"""
import os, re, sys, json
from PIL import Image, ImageDraw
import imagehash

FIGS = sys.argv[1]
OUT_SHEET_DIR = sys.argv[2]
INTERVAL = int(sys.argv[3])
THRESH = int(sys.argv[4]) if len(sys.argv) > 4 else 12
MINLEN = int(sys.argv[5]) if len(sys.argv) > 5 else 1  # min frames in a scene to keep

os.makedirs(OUT_SHEET_DIR, exist_ok=True)

frames = sorted(
    [f for f in os.listdir(FIGS) if re.match(r"frame_\d+\.jpg$", f)],
    key=lambda f: int(re.search(r"\d+", f).group()),
)
print(f"{len(frames)} frames")

hashes = {}
def h(fn):
    if fn not in hashes:
        hashes[fn] = imagehash.phash(Image.open(os.path.join(FIGS, fn)).convert("L"))
    return hashes[fn]

scenes = []  # list of (start_idx, end_idx) inclusive into frames[]
anchor = 0
for i in range(1, len(frames)):
    if h(frames[i]) - h(frames[anchor]) > THRESH:
        scenes.append((anchor, i - 1))
        anchor = i
scenes.append((anchor, len(frames) - 1))

# keep scenes of at least MINLEN frames; representative = last frame of scene
reps = []
for s, e in scenes:
    if (e - s + 1) < MINLEN:
        continue
    rep = e  # last frame = most complete
    fn = frames[rep]
    idx = int(re.search(r"\d+", fn).group())
    sec = (idx - 1) * INTERVAL
    reps.append({"frame": idx, "file": fn, "sec": sec,
                 "scene_len": e - s + 1,
                 "start_sec": (int(re.search(r'\d+', frames[s]).group()) - 1) * INTERVAL})

print(f"{len(scenes)} scenes, {len(reps)} kept (THRESH={THRESH}, MINLEN={MINLEN})")

with open(os.path.join(OUT_SHEET_DIR, "scenes.json"), "w") as f:
    json.dump(reps, f, indent=0)

# Build contact sheets of representatives, labeled "#frame  M:SS  (len)"
COLS, ROWS = 5, 6
PER = COLS * ROWS
TW, PAD, LBL = 340, 6, 16
def mmss(s): return f"{s//60}:{s%60:02d}"

sheet_n = 0
for base in range(0, len(reps), PER):
    chunk = reps[base:base + PER]
    # measure
    thumbs = []
    for r in chunk:
        im = Image.open(os.path.join(FIGS, r["file"])).convert("RGB")
        w, ht = im.size
        th = int(TW * ht / w)
        thumbs.append((im.resize((TW, th)), r))
    CELL_H = max(t[0].size[1] for t in thumbs) + LBL
    W = COLS * (TW + PAD) + PAD
    H = ROWS * (CELL_H + PAD) + PAD
    sheet = Image.new("RGB", (W, H), (20, 20, 30))
    d = ImageDraw.Draw(sheet)
    for i, (im, r) in enumerate(thumbs):
        rr, cc = divmod(i, COLS)
        x = PAD + cc * (TW + PAD)
        y = PAD + rr * (CELL_H + PAD)
        d.text((x + 2, y), f"#{r['frame']}  {mmss(r['sec'])}  ({r['scene_len']})", fill=(120, 230, 160))
        sheet.paste(im, (x, y + LBL))
    sheet_n += 1
    sheet.save(os.path.join(OUT_SHEET_DIR, f"reps_{sheet_n:02d}.jpg"), quality=80)
    print(f"  wrote reps_{sheet_n:02d}.jpg ({len(chunk)} reps)")
print("DONE")

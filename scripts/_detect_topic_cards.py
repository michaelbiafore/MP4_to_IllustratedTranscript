"""Detect the numbered topic cards in the lower-right corner of a talking-head video.

Crops the lower-right corner of each frame_NNNN.jpg, perceptual-hashes it, and
starts a new "card" whenever the corner changes. Emits one representative frame
per distinct card (the middle frame, fully settled) and builds montages of the
cropped corners labeled "#frame  M:SS" so the labels can be transcribed by eye.
"""
import os, re, sys, json
from PIL import Image, ImageDraw
import imagehash

FIGS = sys.argv[1]
OUT = sys.argv[2]
INTERVAL = int(sys.argv[3])
# crop box for the lower-right label (1920x1080 source)
CX0, CY0, CX1, CY1 = 1120, 985, 1920, 1075
THRESH = int(sys.argv[4]) if len(sys.argv) > 4 else 8
MINLEN = int(sys.argv[5]) if len(sys.argv) > 5 else 2  # min frames to count as a real card

os.makedirs(OUT, exist_ok=True)
frames = sorted([f for f in os.listdir(FIGS) if re.match(r"frame_\d+\.jpg$", f)],
                key=lambda f: int(re.search(r"\d+", f).group()))
print(f"{len(frames)} frames")

def corner(fn):
    return Image.open(os.path.join(FIGS, fn)).crop((CX0, CY0, CX1, CY1)).convert("L")

hashes = {}
def h(fn):
    if fn not in hashes:
        hashes[fn] = imagehash.phash(corner(fn))
    return hashes[fn]

# segment by corner change
segs = []
anchor = 0
for i in range(1, len(frames)):
    if h(frames[i]) - h(frames[anchor]) > THRESH:
        segs.append((anchor, i - 1)); anchor = i
segs.append((anchor, len(frames) - 1))

cards = []
for s, e in segs:
    if (e - s + 1) < MINLEN:
        continue
    mid = (s + e) // 2
    fn = frames[mid]
    idx = int(re.search(r"\d+", fn).group())
    sec = (idx - 1) * INTERVAL
    cards.append({"frame": idx, "file": fn, "sec": sec, "len": e - s + 1,
                  "start_sec": (int(re.search(r'\d+', frames[s]).group()) - 1) * INTERVAL})
print(f"{len(segs)} segments, {len(cards)} cards (THRESH={THRESH}, MINLEN={MINLEN})")
json.dump(cards, open(os.path.join(OUT, "cards.json"), "w"), indent=0)

# montage of cropped corners, enlarged, labeled
def mmss(s): return f"{s//60}:{s%60:02d}"
COLS, ROWS = 3, 10
PER = COLS * ROWS
TW = 560
sheet_n = 0
for base in range(0, len(cards), PER):
    chunk = cards[base:base+PER]
    thumbs = []
    for c in chunk:
        im = Image.open(os.path.join(FIGS, c["file"])).crop((CX0, CY0, CX1, CY1)).convert("RGB")
        w, ht = im.size; th = int(TW*ht/w)
        thumbs.append((im.resize((TW, th)), c))
    CELL_H = max(t[0].size[1] for t in thumbs) + 18
    W = COLS*(TW+8)+8; H = ROWS*(CELL_H+8)+8
    sheet = Image.new("RGB", (W, H), (15,15,25)); d = ImageDraw.Draw(sheet)
    for i,(im,c) in enumerate(thumbs):
        r,cc = divmod(i, COLS); x=8+cc*(TW+8); y=8+r*(CELL_H+8)
        d.text((x+2,y), f"#{c['frame']}  {mmss(c['sec'])}", fill=(120,230,160))
        sheet.paste(im,(x,y+16))
    sheet_n+=1
    sheet.save(os.path.join(OUT, f"cards_{sheet_n:02d}.jpg"), quality=88)
    print(f"  wrote cards_{sheet_n:02d}.jpg ({len(chunk)})")
print("DONE")

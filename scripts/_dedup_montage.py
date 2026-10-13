"""Perceptual-dedup frames, then build contact sheets labeled with ORIGINAL frame numbers.

Usage:
    python _dedup_montage.py <figs_dir> <uniq_dir> <montage_dir> <interval> <threshold> [crop_right_pct]

- Computes pHash (hash_size=16) on each frame_NNNN.jpg (optionally ignoring a right-side crop).
- Keeps a frame only if its hash distance from the last KEPT frame >= threshold.
- Copies survivors into <uniq_dir> preserving the original frame_NNNN.jpg name.
- Builds 6x8 contact sheets in <montage_dir>, each thumb labeled "#<origNum>  M:SS",
  where M:SS = (origNum-1)*interval (i.e. the true recording time), so picks map
  straight back to the original figs dir for mp4wizwhisp_curate.py.
"""
import os, sys, shutil
from PIL import Image, ImageDraw, ImageFont
import imagehash

figs, uniq, montage, interval, threshold = (
    sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
)
crop_right = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
os.makedirs(uniq, exist_ok=True)
os.makedirs(montage, exist_ok=True)

frames = sorted(f for f in os.listdir(figs) if f.endswith(".jpg"))
print(f"Total frames: {len(frames)}")

def phash_of(path):
    img = Image.open(path)
    if crop_right > 0:
        w, h = img.size
        img = img.crop((0, 0, int(w * (1 - crop_right / 100)), h))
    return imagehash.phash(img, hash_size=16)

kept = []          # list of (filename, orignum)
last_hash = None
for f in frames:
    num = int(f.replace("frame_", "").replace(".jpg", ""))
    h = phash_of(os.path.join(figs, f))
    if last_hash is None or (h - last_hash) >= threshold:
        kept.append((f, num))
        last_hash = h
        shutil.copy2(os.path.join(figs, f), os.path.join(uniq, f))

print(f"Kept after dedup (threshold={threshold}, crop_right={crop_right}%): {len(kept)}")

# ---- contact sheets ----
COLS, ROWS = 6, 8
PER = COLS * ROWS
TW, TH, LBL, PAD = 300, 169, 20, 2
CELL_H = TH + LBL
try:
    font = ImageFont.truetype("arialbd.ttf", 15)
except Exception:
    font = ImageFont.load_default()

def ts(num):
    s = (num - 1) * interval
    return f"{s//60}:{s%60:02d}"

n_sheets = (len(kept) + PER - 1) // PER
for sheet in range(n_sheets):
    batch = kept[sheet*PER:(sheet+1)*PER]
    W = COLS * (TW + PAD) + PAD
    H = ROWS * (CELL_H + PAD) + PAD
    canvas = Image.new("RGB", (W, H), (20, 20, 28))
    draw = ImageDraw.Draw(canvas)
    for i, (fn, num) in enumerate(batch):
        r, c = divmod(i, COLS)
        x = PAD + c * (TW + PAD)
        y = PAD + r * (CELL_H + PAD)
        try:
            thumb = Image.open(os.path.join(figs, fn)).resize((TW, TH))
            canvas.paste(thumb, (x, y + LBL))
        except Exception as e:
            print("skip", fn, e)
        draw.text((x + 2, y + 2), f"#{num}  {ts(num)}", fill=(120, 230, 160), font=font)
    out = os.path.join(montage, f"sheet_{sheet+1:02d}.jpg")
    canvas.save(out, quality=85)
    print(f"  {out}  ({len(batch)} thumbs)")
print(f"\n{n_sheets} sheets written to {montage}")

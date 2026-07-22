"""Readable contact sheets: fewer, larger thumbnails so slide text is legible.

Usage: _mp4_montage_big.py <figs_dir> <out_dir> <interval_sec> [cols] [rows] [tw]
Default 4x4 @ 460px wide. Labels each thumb "#<index>  <M:SS>".
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

figs, out_dir, interval = sys.argv[1], sys.argv[2], int(sys.argv[3])
COLS = int(sys.argv[4]) if len(sys.argv) > 4 else 4
ROWS = int(sys.argv[5]) if len(sys.argv) > 5 else 4
TW = int(sys.argv[6]) if len(sys.argv) > 6 else 460
TH = int(TW * 9 / 16)
os.makedirs(out_dir, exist_ok=True)
PER = COLS * ROWS
LBL, PAD = 22, 3
CELL_H = TH + LBL

frames = sorted(f for f in os.listdir(figs) if f.endswith(".jpg"))
try:
    font = ImageFont.truetype("arialbd.ttf", 16)
except Exception:
    font = ImageFont.load_default()

def ts(idx):
    s = (idx - 1) * interval
    return f"{s//60}:{s%60:02d}"

n_sheets = (len(frames) + PER - 1) // PER
for sheet in range(n_sheets):
    batch = frames[sheet*PER:(sheet+1)*PER]
    W = COLS * (TW + PAD) + PAD
    H = ROWS * (CELL_H + PAD) + PAD
    canvas = Image.new("RGB", (W, H), (20, 20, 28))
    draw = ImageDraw.Draw(canvas)
    for i, fn in enumerate(batch):
        r, c = divmod(i, COLS)
        x = PAD + c * (TW + PAD)
        y = PAD + r * (CELL_H + PAD)
        try:
            im = Image.open(os.path.join(figs, fn)).resize((TW, TH))
            canvas.paste(im, (x, y))
        except Exception:
            pass
        idx = int(fn.replace("frame_", "").replace(".jpg", ""))
        draw.rectangle([x, y+TH, x+TW, y+TH+LBL], fill=(0, 0, 0))
        draw.text((x+4, y+TH+3), f"#{idx}  {ts(idx)}", fill=(255, 255, 0), font=font)
    op = os.path.join(out_dir, f"big_{sheet+1:02d}.jpg")
    canvas.save(op, quality=82)
    print(f"big_{sheet+1:02d}: #{int(batch[0][6:10])}-#{int(batch[-1][6:10])} ({len(batch)})")
print(f"Total {len(frames)} -> {n_sheets} sheets")

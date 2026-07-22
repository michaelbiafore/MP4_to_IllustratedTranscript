"""Build labeled contact sheets from raw frames for fast visual review.

Usage:
    python mp4wizwhisp_montage.py <figs_dir> <out_dir> <interval_seconds>

Tiles every frame_NNNN.jpg in <figs_dir> into 6x8 grids (48 per sheet),
each thumbnail labeled "#<index>  <M:SS>" where the timestamp is
(index-1)*interval seconds. Sheets are written as sheet_NN.jpg in <out_dir>.
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

figs, out_dir, interval = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.makedirs(out_dir, exist_ok=True)

COLS, ROWS = 6, 8
PER = COLS * ROWS
TW, TH, LBL, PAD = 300, 169, 18, 2
CELL_H = TH + LBL

frames = sorted(f for f in os.listdir(figs) if f.endswith(".jpg"))
try:
    font = ImageFont.truetype("arial.ttf", 13)
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
        draw.text((x+3, y+TH+2), f"#{idx}  {ts(idx)}", fill=(255, 255, 0), font=font)
    op = os.path.join(out_dir, f"sheet_{sheet+1:02d}.jpg")
    canvas.save(op, quality=80)
    print(f"sheet_{sheet+1:02d}: #{int(batch[0][6:10])}-#{int(batch[-1][6:10])}")
print(f"Total {len(frames)} frames -> {n_sheets} sheets")

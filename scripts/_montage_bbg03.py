import os
from PIL import Image, ImageDraw, ImageFont

figs = r"A:\Packages\Transcript2MDSlides\Input\BBG_ClaudeCode_03_hires_20260604_195833_figs"
out_dir = r"A:\Packages\Transcript2MDSlides\Input\_montage_bbg03"
os.makedirs(out_dir, exist_ok=True)

INTERVAL = 10
COLS = 6
ROWS = 8
PER = COLS * ROWS
TW = 300
TH = 169
LBL = 18
CELL_H = TH + LBL
PAD = 2

frames = sorted(f for f in os.listdir(figs) if f.endswith(".jpg"))
try:
    font = ImageFont.truetype("arial.ttf", 13)
except Exception:
    font = ImageFont.load_default()

def ts(idx):
    s = (idx - 1) * INTERVAL
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
        label = f"#{idx}  {ts(idx)}"
        draw.rectangle([x, y+TH, x+TW, y+TH+LBL], fill=(0, 0, 0))
        draw.text((x+3, y+TH+2), label, fill=(255, 255, 0), font=font)
    op = os.path.join(out_dir, f"sheet_{sheet+1:02d}.jpg")
    canvas.save(op, quality=80)
    print(f"sheet_{sheet+1:02d}: #{int(batch[0][6:10])}-#{int(batch[-1][6:10])}")

print(f"Total {len(frames)} frames -> {n_sheets} sheets")

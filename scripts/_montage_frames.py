"""Tile filtered frames into labeled montage grids for fast review."""
import os, json, math
from PIL import Image, ImageDraw, ImageFont

FILT = r"A:\Packages\Transcript2MDSlides\Input\BBG_ClaudeCode_02_hires_figs_filtered"
MAN = r"A:\Packages\Transcript2MDSlides\Input\BBG_ClaudeCode_02_hires_frames_manifest.json"
OUT = r"A:\Packages\Transcript2MDSlides\Input\BBG_ClaudeCode_02_montages"
os.makedirs(OUT, exist_ok=True)

man = json.load(open(MAN))
COLS, ROWS = 5, 6              # 30 per montage
THUMB_W = 384
PER = COLS * ROWS
LABEL_H = 26

try:
    font = ImageFont.truetype("arial.ttf", 18)
except Exception:
    font = ImageFont.load_default()

pages = math.ceil(len(man) / PER)
for pg in range(pages):
    chunk = man[pg*PER:(pg+1)*PER]
    # establish thumb height from first image aspect
    im0 = Image.open(os.path.join(FILT, chunk[0]["filename"]))
    ar = im0.height / im0.width
    th = int(THUMB_W * ar)
    cell_h = th + LABEL_H
    canvas = Image.new("RGB", (COLS*THUMB_W, ROWS*cell_h), (20, 20, 24))
    draw = ImageDraw.Draw(canvas)
    for i, item in enumerate(chunk):
        r, c = divmod(i, COLS)
        x, y = c*THUMB_W, r*cell_h
        im = Image.open(os.path.join(FILT, item["filename"])).resize((THUMB_W, th))
        canvas.paste(im, (x, y+LABEL_H))
        lbl = f"#{item['figure_num']}  {item['timestamp']}"
        draw.rectangle([x, y, x+THUMB_W, y+LABEL_H], fill=(0,0,0))
        draw.text((x+4, y+3), lbl, fill=(120, 230, 160), font=font)
    fn = os.path.join(OUT, f"montage_{pg+1:02d}.jpg")
    canvas.save(fn, quality=82)
    print(f"wrote {fn}  ({len(chunk)} frames, #{chunk[0]['figure_num']}-#{chunk[-1]['figure_num']})")
print(f"DONE {pages} montages for {len(man)} frames")

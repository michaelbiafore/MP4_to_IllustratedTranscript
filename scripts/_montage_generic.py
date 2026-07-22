"""Tile filtered frames into labeled montage grids. Args: <filtered_dir> <manifest_json> <out_dir>"""
import os, json, math, sys
from PIL import Image, ImageDraw, ImageFont

FILT, MAN, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
man = json.load(open(MAN))
COLS, ROWS, THUMB_W, LABEL_H = 5, 6, 384, 26
PER = COLS * ROWS
try:
    font = ImageFont.truetype("arial.ttf", 18)
except Exception:
    font = ImageFont.load_default()
pages = math.ceil(len(man) / PER)
for pg in range(pages):
    chunk = man[pg*PER:(pg+1)*PER]
    im0 = Image.open(os.path.join(FILT, chunk[0]["filename"]))
    th = int(THUMB_W * im0.height / im0.width)
    cell_h = th + LABEL_H
    canvas = Image.new("RGB", (COLS*THUMB_W, ROWS*cell_h), (20, 20, 24))
    draw = ImageDraw.Draw(canvas)
    for i, item in enumerate(chunk):
        r, c = divmod(i, COLS)
        x, y = c*THUMB_W, r*cell_h
        im = Image.open(os.path.join(FILT, item["filename"])).resize((THUMB_W, th))
        canvas.paste(im, (x, y+LABEL_H))
        draw.rectangle([x, y, x+THUMB_W, y+LABEL_H], fill=(0, 0, 0))
        draw.text((x+4, y+3), f"#{item['figure_num']}  {item['timestamp']}", fill=(120, 230, 160), font=font)
    fn = os.path.join(OUT, f"montage_{pg+1:02d}.jpg")
    canvas.save(fn, quality=82)
    print(f"wrote {fn} (#{chunk[0]['figure_num']}-#{chunk[-1]['figure_num']})")
print(f"DONE {pages} montages / {len(man)} frames")

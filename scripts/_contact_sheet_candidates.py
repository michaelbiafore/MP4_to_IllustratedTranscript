"""Build a contact sheet of all candidate (non-talking-head) frames."""
import sys
from pathlib import Path
import cv2
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

src = Path("Input/20260517_152934_figs_filtered")
out = Path(".cache/build_buy_candidates.jpg")
out.parent.mkdir(exist_ok=True)

# Candidates: files <400KB
files = sorted(p for p in src.glob("*.jpg") if p.stat().st_size < 400 * 1024)
print(f"{len(files)} candidate frames")

cols = 4
thumb_w = 480
sample = cv2.imread(str(files[0]))
h0, w0 = sample.shape[:2]
th = int(thumb_w * h0 / w0)
label_h = 60
cell_w = thumb_w + 8
cell_h = th + label_h + 8
rows = (len(files) + cols - 1) // cols

sheet = np.full((rows * cell_h, cols * cell_w, 3), 30, dtype=np.uint8)
font = cv2.FONT_HERSHEY_SIMPLEX

for i, fp in enumerate(files):
    img = cv2.imread(str(fp))
    thumb = cv2.resize(img, (thumb_w, th))
    r, c = divmod(i, cols)
    y, x = r * cell_h, c * cell_w
    sheet[y:y+th, x:x+thumb_w] = thumb
    # Timestamp + size in label
    name = fp.stem  # frame_000m20s_screen_005
    parts = name.split("_")
    ts = parts[1]  # 000m20s
    idx = parts[3]  # 005
    kb = fp.stat().st_size // 1024
    lbl = f"#{idx}  t={ts}  {kb}KB"
    cv2.rectangle(sheet, (x+2, y+2), (x+360, y+38), (0,0,0), -1)
    cv2.putText(sheet, lbl, (x+8, y+28), font, 0.75, (100, 220, 255), 2, cv2.LINE_AA)

cv2.imwrite(str(out), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
print(f"Wrote {out} ({out.stat().st_size//1024}KB, {sheet.shape[1]}x{sheet.shape[0]})")

"""Drop talking-head frames from a deduplicated frames directory.

A frame is rejected if:
- OpenCV Haar cascade detects any face whose bounding-box area exceeds
  FACE_AREA_THRESHOLD of the frame area (default 3%), OR
- The frame consists mostly of YouTube post-video recommendation thumbnails
  (heuristic: top 60% of the frame is mostly black AND the bottom strip
  contains multiple small face-shaped regions).

Surviving frames are kept in place; rejected frames are moved to a
`_rejected_talking_heads` subdirectory so they can be reviewed later.

The frames manifest is rebuilt with only the kept frames.
"""

from pathlib import Path
import json
import shutil
import sys

import cv2
import numpy as np

ROOT = Path(r"A:/Packages/Transcript2MDSlides")
FIGS = ROOT / "Input" / "LeCun_1B_JEPA_figs_filtered"
REJECTED = ROOT / "Input" / "LeCun_1B_JEPA_figs_rejected_talking_heads"
MANIFEST = ROOT / "Input" / "LeCun_1B_JEPA_frames_manifest.json"

# Reject if any face occupies >= this fraction of the frame
FACE_AREA_THRESHOLD = 0.03

# Reject as "post-video" if top half is nearly black (mean brightness < this)
DARK_MEAN_THRESHOLD = 12

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

REJECTED.mkdir(parents=True, exist_ok=True)

manifest = json.loads(MANIFEST.read_text())

kept = []
dropped = []

for entry in manifest:
    fpath = FIGS / entry["filename"]
    if not fpath.exists():
        dropped.append((entry["filename"], "missing"))
        continue
    img = cv2.imread(str(fpath))
    if img is None:
        dropped.append((entry["filename"], "unreadable"))
        continue
    h, w = img.shape[:2]
    frame_area = h * w

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )

    max_face_area = 0
    for (fx, fy, fw, fh) in faces:
        a = fw * fh
        if a > max_face_area:
            max_face_area = a
    face_frac = max_face_area / frame_area if frame_area else 0.0

    # Detect "post-video" YouTube end-card: upper half mostly dark and
    # there are multiple small faces in the bottom strip.
    upper = gray[: h // 2, :]
    upper_mean = float(np.mean(upper))
    bottom = gray[h // 2 :, :]
    bottom_faces = face_cascade.detectMultiScale(
        bottom, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
    )
    is_endcard = upper_mean < DARK_MEAN_THRESHOLD and len(bottom_faces) >= 2

    reason = None
    if face_frac >= FACE_AREA_THRESHOLD:
        reason = f"talking_head face_frac={face_frac:.3f}"
    elif is_endcard:
        reason = f"endcard upper_mean={upper_mean:.1f} bottom_faces={len(bottom_faces)}"

    if reason:
        shutil.move(str(fpath), str(REJECTED / entry["filename"]))
        dropped.append((entry["filename"], reason))
    else:
        kept.append(entry)

# Renumber figure_num for kept entries
for i, e in enumerate(kept, start=1):
    e["figure_num"] = i

MANIFEST.write_text(json.dumps(kept, indent=2))

print(f"Kept: {len(kept)}")
print(f"Dropped: {len(dropped)}")
print("First 5 dropped:")
for fn, reason in dropped[:5]:
    print(f"  {fn}: {reason}")
print("Last 5 dropped:")
for fn, reason in dropped[-5:]:
    print(f"  {fn}: {reason}")

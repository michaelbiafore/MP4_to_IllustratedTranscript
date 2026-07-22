#!/usr/bin/env python3
"""OCR the on-screen player counter at several MP4 timestamps to derive the
mp4_t -> original_t mapping. The user said the recording was at 2x speed and
started a few seconds before the video — this script confirms both empirically.
"""
import sys, re
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import cv2, pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def ocr_counter(path: str) -> str:
    img = cv2.imread(path)
    h, w = img.shape[:2]
    crop = img[int(h * 0.90):h, 0:int(w * 0.25)]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    _, th = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    cfg = "--psm 7 -c tessedit_char_whitelist=0123456789:/ "
    return pytesseract.image_to_string(th, config=cfg).strip()


for f in sorted(Path("/tmp/calib").glob("*.jpg"),
                key=lambda p: int(re.search(r"(\d+)", p.name).group(1))):
    mp4_t = int(re.search(r"(\d+)", f.name).group(1))
    print(f"mp4_t={mp4_t:4d}s  ocr={ocr_counter(str(f))!r}", flush=True)

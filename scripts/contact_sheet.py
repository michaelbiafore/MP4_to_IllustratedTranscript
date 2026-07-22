#!/usr/bin/env python3
"""Build a contact-sheet image from a directory of figures.

Usage:
  contact_sheet.py <figs_dir> <out_path> [--cols 5] [--thumb-w 480]
                   [--manifest <manifest.json>]

If --manifest is given, each thumb is labeled with its target original-time
(read from the frames manifest produced by extract_slide_frames.py).
"""
import sys, json, argparse
from pathlib import Path

import cv2
import numpy as np


def load_target_labels(manifest_path: Path) -> dict[str, str]:
    """Map fig_filename -> 'NN orig MM:SS (mp4 X.Xs)' label."""
    labels = {}
    if not manifest_path or not manifest_path.exists():
        return labels
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    for tgt in m.get("targets", []):
        ot = tgt.get("original_label", "")
        for c in tgt.get("clusters", []):
            fn = c.get("fig_filename")
            if fn:
                labels[fn] = f"orig {ot} -> {c.get('approx_original_label','?')} (sz {c.get('cluster_size','?')})"
    return labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("figs_dir")
    ap.add_argument("out_path")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--thumb-w", type=int, default=480)
    ap.add_argument("--manifest", default=None)
    args = ap.parse_args()

    figs = sorted(Path(args.figs_dir).glob("fig_*.jpg"),
                  key=lambda p: int(p.stem.split("_")[1]))
    if not figs:
        print("No fig_*.jpg in", args.figs_dir, file=sys.stderr); sys.exit(2)

    labels = load_target_labels(Path(args.manifest)) if args.manifest else {}

    # Probe first image for aspect ratio
    sample = cv2.imread(str(figs[0]))
    h0, w0 = sample.shape[:2]
    tw = args.thumb_w
    th = int(tw * h0 / w0)

    label_h = 50
    cell_w = tw + 8
    cell_h = th + label_h + 8
    cols = args.cols
    rows = (len(figs) + cols - 1) // cols

    sheet = np.full((rows * cell_h, cols * cell_w, 3), 30, dtype=np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX

    for i, fp in enumerate(figs):
        img = cv2.imread(str(fp))
        if img is None: continue
        thumb = cv2.resize(img, (tw, th))
        r, c = divmod(i, cols)
        y, x = r * cell_h, c * cell_w
        sheet[y:y+th, x:x+tw] = thumb
        # Label below
        name = fp.stem  # fig_NN
        lbl = name + (" — " + labels[fp.name] if fp.name in labels else "")
        cv2.putText(sheet, lbl[:60], (x + 4, y + th + 22),
                    font, 0.55, (220, 220, 220), 1, cv2.LINE_AA)
        # Index sticker top-left
        idx = name.split("_")[1]
        cv2.rectangle(sheet, (x+2, y+2), (x+70, y+34), (0,0,0), -1)
        cv2.putText(sheet, "#"+idx, (x+8, y+26),
                    font, 0.85, (100, 200, 255), 2, cv2.LINE_AA)

    cv2.imwrite(args.out_path, sheet)
    print(f"wrote: {args.out_path}  ({sheet.shape[1]}x{sheet.shape[0]})")


if __name__ == "__main__":
    main()

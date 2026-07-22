"""Classify frames as talking-head vs slide-content using perceptual hash distance.

The presenter (Cdr. Robert Johnson) is shot against a fixed backdrop with the
American flag and an F-15/F-18 painting. Every "talking head" frame shares that
backdrop, so we can identify them by phash similarity to one or more reference
talking-head frames. Slide frames (white text on light backgrounds) are
substantially different from those references.

Usage:
    python scripts/_classify_talking_heads.py <figs_dir> <manifest_path> \
        --reference <ref1.jpg> [--reference <ref2.jpg> ...] \
        [--threshold N] [--output classification.json]
"""
import argparse
import json
from pathlib import Path
from PIL import Image
import imagehash


def main():
    p = argparse.ArgumentParser()
    p.add_argument("figs_dir")
    p.add_argument("manifest_path")
    p.add_argument("--reference", action="append", required=True)
    p.add_argument("--threshold", type=int, default=24,
                   help="phash distance below this = talking head")
    p.add_argument("--output", default=None)
    args = p.parse_args()

    figs_dir = Path(args.figs_dir)
    manifest = json.loads(Path(args.manifest_path).read_text())

    ref_hashes = []
    for ref_path in args.reference:
        img = Image.open(ref_path)
        ref_hashes.append(imagehash.phash(img, hash_size=16))

    classifications = []
    for entry in manifest:
        fpath = figs_dir / entry["filename"]
        img = Image.open(fpath)
        h = imagehash.phash(img, hash_size=16)
        min_dist = min(h - r for r in ref_hashes)
        is_talking_head = bool(min_dist < args.threshold)
        classifications.append({
            "filename": entry["filename"],
            "timestamp": entry["timestamp"],
            "min_dist_to_talking_head": int(min_dist),
            "is_talking_head": is_talking_head,
        })

    talking_heads = [c for c in classifications if c["is_talking_head"]]
    slides = [c for c in classifications if not c["is_talking_head"]]
    print(f"Total frames: {len(classifications)}")
    print(f"  Talking heads (skip in deck): {len(talking_heads)}")
    print(f"  Slide content (include in deck): {len(slides)}")

    if args.output:
        Path(args.output).write_text(json.dumps(classifications, indent=2))
        print(f"Wrote {args.output}")

    # Print talking heads for review
    print("\nTalking-head frames:")
    for c in talking_heads:
        print(f"  {c['filename']:48s} t={c['timestamp']:6s} d={c['min_dist_to_talking_head']}")


if __name__ == "__main__":
    main()

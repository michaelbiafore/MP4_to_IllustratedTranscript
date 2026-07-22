"""Create downsampled thumbnails of frames for sub-agent review.

The 4K source frames (3840x2160) exceed the multi-image dimension limit for
Read in sub-agent contexts. This script creates 1280-wide thumbnails in a
sibling directory so an agent can survey all frames quickly. The originals
stay untouched for slide embedding.

Usage:
    python scripts/_make_thumbnails.py <src_dir> <dst_dir> [--max-width N]
"""
import argparse
from pathlib import Path
from PIL import Image


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src_dir")
    p.add_argument("dst_dir")
    p.add_argument("--max-width", type=int, default=1280)
    p.add_argument("--quality", type=int, default=80)
    args = p.parse_args()

    src = Path(args.src_dir)
    dst = Path(args.dst_dir)
    dst.mkdir(parents=True, exist_ok=True)

    count = 0
    for f in sorted(src.glob("*.jpg")):
        img = Image.open(f)
        if img.width > args.max_width:
            new_h = int(img.height * args.max_width / img.width)
            img = img.resize((args.max_width, new_h), Image.LANCZOS)
        img.save(dst / f.name, quality=args.quality, optimize=True)
        count += 1
    print(f"Wrote {count} thumbnails to {dst}")


if __name__ == "__main__":
    main()

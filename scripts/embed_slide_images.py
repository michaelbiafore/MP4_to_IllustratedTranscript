#!/usr/bin/env python3
"""
Inline every local <img src> in an HTML slide deck as a base64 data URI.

Why: Slide decks produced by /slidefy-youtube, /slidefy-transcript, and /slidefy-mp4
live in Output/Slides/ and reference images via relative paths like
  ../../Input/{slug}_figs/frame_XXX.jpg
That works locally. On a remote system (email, shared drive, colleague's laptop)
those paths don't resolve and every image renders as a broken icon.

This script reads the HTML, finds every <img src="...">, resolves each path
relative to the HTML file's directory, optionally downsamples very large images,
re-encodes as JPEG (quality 85 by default), and replaces the src with
  data:image/jpeg;base64,AAAA...
so the HTML becomes fully self-contained.

Behavior:
- data: URIs and http(s):// URLs are left as-is (CDN links for reveal.js stay).
- Missing images are reported but don't abort the run.
- Default: images wider than 1600px are downsampled to 1600px with Lanczos.
- Default: re-encoded as JPEG quality 85 (90-95% size savings vs raw 4K JPEG).
- PNGs with alpha channels are flattened onto a white background before JPEG.

Usage:
    .venv/Scripts/python.exe scripts/embed_slide_images.py <html_file>
    .venv/Scripts/python.exe scripts/embed_slide_images.py deck.html --max-width 1920
    .venv/Scripts/python.exe scripts/embed_slide_images.py deck.html --no-resize --jpeg-quality 92
    .venv/Scripts/python.exe scripts/embed_slide_images.py deck.html --output portable.html

The default modifies the HTML file in place. Use --output to write to a new path.
"""

from __future__ import annotations

import argparse
import base64
import io
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required. Install with: .venv/Scripts/pip3.exe install pillow", file=sys.stderr)
    sys.exit(1)


# Match <img ... src="..."> — captures the src attribute value.
# Tolerant of attribute order and single or double quotes.
IMG_SRC_PATTERN = re.compile(
    r'<img\b[^>]*?\bsrc\s*=\s*(?P<q>["\'])(?P<src>[^"\']+?)(?P=q)[^>]*?>',
    re.IGNORECASE,
)


def encode_image(img_path: Path, max_width: int | None, jpeg_quality: int) -> tuple[str, int]:
    """Load, optionally downsample, JPEG-encode, base64. Returns (data_uri, bytes_len)."""
    with Image.open(img_path) as im:
        # Flatten alpha to white (JPEG can't carry alpha)
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
            im = bg
        elif im.mode != "RGB":
            im = im.convert("RGB")

        # Downsample if wider than max_width
        if max_width and im.width > max_width:
            new_h = round(im.height * max_width / im.width)
            im = im.resize((max_width, new_h), Image.LANCZOS)

        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=jpeg_quality, optimize=True, progressive=True)
        data = buf.getvalue()

    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/jpeg;base64,{b64}", len(data)


def process(html_path: Path, output_path: Path, max_width: int | None, jpeg_quality: int) -> int:
    html = html_path.read_text(encoding="utf-8")
    html_dir = html_path.parent

    seen = embedded = skipped_data = skipped_remote = missing = 0
    total_bytes = 0
    unresolved: list[str] = []

    def replace(m: re.Match) -> str:
        nonlocal seen, embedded, skipped_data, skipped_remote, missing, total_bytes
        seen += 1
        src = m.group("src")

        if src.startswith("data:"):
            skipped_data += 1
            return m.group(0)

        if src.startswith(("http://", "https://", "//")):
            skipped_remote += 1
            return m.group(0)

        # Resolve relative to HTML directory
        img_path = (html_dir / src).resolve()
        if not img_path.exists():
            missing += 1
            unresolved.append(src)
            return m.group(0)

        try:
            data_uri, byte_count = encode_image(img_path, max_width, jpeg_quality)
        except Exception as exc:
            print(f"  FAILED {src}: {exc}", file=sys.stderr)
            missing += 1
            unresolved.append(src)
            return m.group(0)

        embedded += 1
        total_bytes += byte_count
        if embedded % 20 == 0:
            print(f"  ... embedded {embedded}")

        # Replace the src attribute value, leaving the rest of the tag intact
        q = m.group("q")
        start, end = m.span("src")
        tag = m.group(0)
        # span("src") is relative to the full match; translate to tag-local
        rel_start = start - m.start()
        rel_end = end - m.start()
        return tag[:rel_start] + data_uri + tag[rel_end:]

    new_html = IMG_SRC_PATTERN.sub(replace, html)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(new_html, encoding="utf-8")
    final_size = output_path.stat().st_size

    print("\n=== SUMMARY ===")
    print(f"  <img> tags seen:      {seen}")
    print(f"  embedded as base64:   {embedded}")
    print(f"  already data: URI:    {skipped_data}")
    print(f"  remote URL (kept):    {skipped_remote}")
    print(f"  missing on disk:      {missing}")
    print(f"  total image payload:  {total_bytes / 1024 / 1024:.1f} MB")
    print(f"  final HTML size:      {final_size / 1024 / 1024:.1f} MB")
    print(f"  output:               {output_path}")

    if unresolved:
        print("\nUnresolved image references:")
        for u in unresolved[:20]:
            print(f"  - {u}")
        if len(unresolved) > 20:
            print(f"  ... and {len(unresolved) - 20} more")

    return 2 if missing else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inline <img src> images in an HTML slide deck as base64 data URIs.",
    )
    parser.add_argument("html_file", type=Path, help="Path to the HTML slide deck to process.")
    parser.add_argument(
        "--max-width",
        type=int,
        default=1600,
        help="Downsample images wider than this (default: 1600). Use with --no-resize to disable.",
    )
    parser.add_argument(
        "--no-resize",
        action="store_true",
        help="Keep original image dimensions (no downsampling).",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=85,
        help="JPEG re-encode quality 1-100 (default: 85).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the portable HTML to this path. Default: overwrite the input file in place.",
    )
    args = parser.parse_args()

    if not args.html_file.exists():
        print(f"ERROR: {args.html_file} does not exist", file=sys.stderr)
        return 1

    max_width = None if args.no_resize else args.max_width
    output_path = args.output or args.html_file

    return process(args.html_file, output_path, max_width, args.jpeg_quality)


if __name__ == "__main__":
    sys.exit(main())

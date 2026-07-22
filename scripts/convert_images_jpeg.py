"""
Convert book figures to JPEG and replace base64 images in an HTML slide deck.

Usage:
    .venv/Scripts/python.exe scripts/convert_images_jpeg.py

Called by:
    No slash command calls this directly. It is a manual post-processing step
    for book summary slide decks that use base64-embedded images.
    Referenced as a "reference implementation" in /slidefy-transcript
    (.claude/commands/slidefy-transcript.md) for base64 image inlining.

What it does:
    1. Reads all images from a source directory (currently hardcoded to
       B:\\Books\\Stats_ML\\AI\\Fast_Future_Blur\\images).
    2. Converts each image to JPEG at max 1280px wide, quality 85, handling
       RGBA and palette-mode PNGs (converts to RGB first).
    3. Reads the existing HTML slide deck (Output/Slides/Sum_The_Fast_Future_Blur_SLIDES.html).
    4. Matches embedded base64 images by content fingerprinting — compares the
       first 60 characters of each base64 data URI against the original image
       files to establish identity. This is ORDER-INDEPENDENT and avoids the
       bug where positional matching silently swaps images when HTML order
       differs from alphabetical directory listing order.
    5. Replaces each PNG base64 URI with the smaller JPEG base64 URI.
    6. Writes the result to JPEG_Sum_The_Fast_Future_Blur_SLIDES.html.

    Typical size reduction: 90-95% (e.g., 45MB → 3MB).

Output files:
    Output/Slides/JPEG_Sum_The_Fast_Future_Blur_SLIDES.html

Dependencies:
    Pillow (PIL)

Cross-script references:
    - Operates on the output of build_fast_future_slides.py (reads the HTML it
      produced and creates a JPEG-optimized variant).

Notes:
    - The source directory and file paths are hardcoded — edit SRC_DIR and the
      file paths in main() to reuse for other book summaries.
    - The content-fingerprint matching technique (comparing first 60 chars of
      base64 data) is documented in /slidefy-transcript as the correct approach
      for image replacement, after discovering that positional matching fails.
"""
import os, sys, base64, re

from PIL import Image

SRC_DIR = r"B:\Books\Stats_ML\AI\Fast_Future_Blur\images"
MAX_WIDTH = 1280
JPEG_QUALITY = 85
SKIP = {"hyphen.png"}


def convert_all():
    """Convert images and return dict of {original_name: (jpeg_bytes, width, height)}."""
    results = {}
    for fname in sorted(os.listdir(SRC_DIR)):
        if fname in SKIP:
            continue
        src = os.path.join(SRC_DIR, fname)
        if not os.path.isfile(src):
            continue

        img = Image.open(src)
        # Convert palette/RGBA to RGB for JPEG
        if img.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Resize if wider than MAX_WIDTH
        w, h = img.size
        if w > MAX_WIDTH:
            ratio = MAX_WIDTH / w
            new_h = int(h * ratio)
            img = img.resize((MAX_WIDTH, new_h), Image.LANCZOS)

        # Save to bytes
        from io import BytesIO
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        jpeg_bytes = buf.getvalue()
        results[fname] = jpeg_bytes
        w2, h2 = img.size
        orig_sz = os.path.getsize(src)
        print(f"  {fname:25s}  {orig_sz/1e6:5.1f} MB -> {len(jpeg_bytes)/1e6:5.2f} MB  ({w2}x{h2})")

    return results


def build_fingerprints():
    """Build a lookup from first 64 bytes of file content to filename."""
    fingerprints = {}
    for fname in os.listdir(SRC_DIR):
        if fname in SKIP:
            continue
        src = os.path.join(SRC_DIR, fname)
        if not os.path.isfile(src):
            continue
        with open(src, "rb") as f:
            raw = f.read()
        # Base64-encode the first 200 raw bytes as a fingerprint
        b64_prefix = base64.b64encode(raw[:200]).decode("ascii")[:60]
        fingerprints[b64_prefix] = fname
    return fingerprints


def rebuild_slides(jpeg_map):
    """Read the existing slides HTML, match each image by content fingerprint, replace with JPEG."""
    slides_path = r"A:\Packages\Transcript2MDSlides\Output\Slides\Sum_The_Fast_Future_Blur_SLIDES.html"
    out_path = r"A:\Packages\Transcript2MDSlides\Output\Slides\JPEG_Sum_The_Fast_Future_Blur_SLIDES.html"

    print(f"\nReading slides from: {slides_path}")
    with open(slides_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Build fingerprints: first N chars of base64 data -> source filename
    fingerprints = build_fingerprints()
    print(f"Built {len(fingerprints)} content fingerprints")

    # Find all <img> tags with data URIs
    img_pattern = re.compile(
        r'(<img\s[^>]*src=")data:image/(?:png|jpeg|jpg);base64,([A-Za-z0-9+/=]+)(")'
    )
    matches = list(img_pattern.finditer(html))
    print(f"Found {len(matches)} base64 images in HTML")

    replacements = 0
    matched_files = []

    # Replace from end to start to preserve string positions
    for m in reversed(matches):
        b64_data = m.group(2)
        # Match fingerprint: check first 60 chars of base64 data against our fingerprints
        b64_prefix = b64_data[:60]
        fname = fingerprints.get(b64_prefix)

        if fname and fname in jpeg_map:
            b64_new = base64.b64encode(jpeg_map[fname]).decode("ascii")
            new_src = f'{m.group(1)}data:image/jpeg;base64,{b64_new}{m.group(3)}'
            html = html[:m.start()] + new_src + html[m.end():]
            replacements += 1
            matched_files.append(fname)
        else:
            # Fallback: try shorter prefix
            for prefix, fn in fingerprints.items():
                if b64_data[:40].startswith(prefix[:40]) and fn in jpeg_map:
                    b64_new = base64.b64encode(jpeg_map[fn]).decode("ascii")
                    new_src = f'{m.group(1)}data:image/jpeg;base64,{b64_new}{m.group(3)}'
                    html = html[:m.start()] + new_src + html[m.end():]
                    replacements += 1
                    matched_files.append(fn)
                    break
            else:
                print(f"  WARNING: Could not match image at position {m.start()}")

    print(f"Replaced {replacements} images by content fingerprint")
    for fn in sorted(set(matched_files)):
        print(f"  matched: {fn}")

    print(f"\nWriting to: {out_path}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    orig_sz = os.path.getsize(slides_path)
    new_sz = os.path.getsize(out_path)
    print(f"\nOriginal: {orig_sz/1e6:.1f} MB")
    print(f"JPEG version: {new_sz/1e6:.1f} MB")
    print(f"Savings: {(orig_sz - new_sz)/1e6:.1f} MB ({100*(orig_sz-new_sz)/orig_sz:.0f}%)")


if __name__ == "__main__":
    print("Converting images to JPEG...")
    jpeg_map = convert_all()
    total_orig = sum(os.path.getsize(os.path.join(SRC_DIR, f)) for f in jpeg_map)
    total_jpeg = sum(len(b) for b in jpeg_map.values())
    print(f"\nImage totals: {total_orig/1e6:.1f} MB -> {total_jpeg/1e6:.1f} MB ({100*(total_orig-total_jpeg)/total_orig:.0f}% reduction)")

    rebuild_slides(jpeg_map)

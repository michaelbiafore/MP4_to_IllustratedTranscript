"""
Embed images as base64 data URIs in an HTML file.

Usage:
    .venv/Scripts/python.exe scripts/embed_base64_images.py

Called by:
    No slash command calls this directly. It is a manual post-processing step
    used to make formatted HTML documents self-contained for email distribution.

What it does:
    Reads a specific HTML file (currently hardcoded to the Reshuffle formatted
    transcript), finds all <img> tags whose src attributes point to local file
    paths (e.g., B:/Books/...), reads those image files from disk, base64-encodes
    them, and replaces each src with an inline data:image/jpeg;base64,... URI.
    The result is a single self-contained HTML file with no external dependencies.

Output files:
    Overwrites the input HTML file in-place with embedded images.

Dependencies:
    None beyond stdlib (re, base64, pathlib).

Cross-script references:
    None — standalone script. Conceptually similar to the base64 embedding done
    inside build_fast_future_slides.py and build_reshuffle_slides.py, but this
    operates as a post-processor on existing HTML rather than generating new HTML.

Pipeline position:
    Post-processing step after /format-transcript or /format-summary produces an
    HTML file with external image references. Makes the HTML email-portable per
    the project mandate (see MEMORY.md: "Email-Portable HTML Slide Decks").

Notes:
    - The target HTML path is hardcoded — edit html_path to reuse for other files.
    - Only processes <img> tags with file:// or absolute Windows paths in src.
    - Does not resize or compress images; for size reduction, run
      convert_images_jpeg.py first to create JPEG versions.
"""
import re
import base64
import sys
from pathlib import Path

html_path = Path(r"A:\Packages\Transcript2MDSlides\Output\Formatted\JPEG_Sum_Reshuffle_Who_wins_when_AI_restacks_the_knowledge_economy_FORMATTED.html")

html = html_path.read_text(encoding="utf-8")

def replace_img_src(match):
    full_tag = match.group(0)
    src = match.group(1)
    # Normalize path separators
    file_path = Path(src.replace("/", "\\"))
    if not file_path.exists():
        print(f"WARNING: image not found: {file_path}")
        return full_tag
    data = file_path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    new_src = f"data:image/jpeg;base64,{b64}"
    new_tag = full_tag.replace(src, new_src)
    print(f"Embedded: {file_path.name} ({len(data)} bytes)")
    return new_tag

# Match img tags with src pointing to B:/Books/...
pattern = r'<img\s[^>]*src="(B:/Books/[^"]+)"[^>]*/?>|<img\s[^>]*src="(B:/Books/[^"]+)"[^>]*>'

def replace_all(match):
    full = match.group(0)
    src = match.group(1) or match.group(2)
    file_path = Path(src.replace("/", "\\"))
    if not file_path.exists():
        print(f"WARNING: image not found: {file_path}")
        return full
    data = file_path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    new_src = f"data:image/jpeg;base64,{b64}"
    return full.replace(src, new_src)

result = re.sub(r'<img\s[^>]*?src="(B:/Books/[^"]+)"[^>]*?/?>', replace_all, html)

count_before = html.count("B:/Books/")
count_after = result.count("B:/Books/")
print(f"\nReferences before: {count_before}, after: {count_after}")

html_path.write_text(result, encoding="utf-8")
print("Done.")

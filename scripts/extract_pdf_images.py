"""
Extract per-page text + EVERY embedded raster image from a PDF (web-article friendly).

Unlike extract_pdf_content.py (which only finds visuals with a formal "Figure N:"
caption), this pulls every embedded image at its native resolution — the right tool
for Towards Data Science / Medium / blog PDFs whose figures are uncaptioned.

Output (under <out_dir>, default Input/):
  <slug>_RAW_PAPER.md            — full per-page text
  <slug>_figs/figNN.png          — one PNG per kept image (native res, re-encoded PNG)
  <slug>_figs_manifest.json      — [{num,page,filename,relpath,native_w,native_h,
                                     place_w_pt,place_h_pt,caption_hint}]

Filtering (drop obvious non-figures):
  - dedup identical images (same xref, or same pixel content across pages → logos)
  - drop images whose native min dimension < --min-dim (icons, avatars, bullets)
  - drop extreme aspect ratios > --max-aspect (rules, thin banners)
  - drop images placed tiny on the page (< --min-place-pt points wide → inline icons)

Kept images are numbered in reading order (page, then top-to-bottom).
Visually review the PNGs afterwards and delete any that are still boilerplate.

Usage:
  .venv/Scripts/python.exe scripts/extract_pdf_images.py <input.pdf> --out Input --slug NAME
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import sys
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image


def slugify(s: str, maxlen: int = 80) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s[:maxlen] or "x"


def caption_below(page: "fitz.Page", bbox, max_gap: float = 46.0) -> str:
    """Return the text block immediately below an image bbox (likely its caption)."""
    try:
        blocks = page.get_text("blocks")  # (x0,y0,x1,y1,text,block_no,block_type)
    except Exception:
        return ""
    cands = []
    for b in blocks:
        if len(b) < 5 or (len(b) >= 7 and b[6] != 0):
            continue
        x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
        if not text or not text.strip():
            continue
        # block starts just below the image, horizontally overlapping it
        if 0 <= (y0 - bbox[3]) <= max_gap and x1 > bbox[0] and x0 < bbox[2]:
            cands.append((y0, text.strip().replace("\n", " ")))
    if not cands:
        return ""
    cands.sort(key=lambda t: t[0])
    cap = cands[0][1]
    return cap[:240]


def extract(pdf_path: Path, out_dir: Path, slug: str, min_dim: int, max_aspect: float,
            min_place_pt: float) -> dict:
    figs_dir = out_dir / f"{slug}_figs"
    md_path = out_dir / f"{slug}_RAW_PAPER.md"
    manifest_path = out_dir / f"{slug}_figs_manifest.json"

    if figs_dir.exists():
        shutil.rmtree(figs_dir)
    figs_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    n_pages = doc.page_count
    print(f"opened: {pdf_path.name}  pages={n_pages}")

    pages_text: list[str] = []
    seen_xref: dict[int, str] = {}     # xref -> filename (already saved)
    seen_hash: dict[str, str] = {}     # pixel hash -> filename (dedup logos)
    kept: list[dict] = []
    dropped = {"small": 0, "aspect": 0, "place": 0, "dup": 0, "decode": 0}

    for pno in range(n_pages):
        page = doc.load_page(pno)
        pages_text.append(page.get_text("text"))
        # image xrefs on this page, in placement order
        try:
            imgs = page.get_images(full=True)
        except Exception:
            imgs = []
        # order by vertical placement
        placed = []
        for info in imgs:
            xref = info[0]
            try:
                rects = page.get_image_rects(xref)
            except Exception:
                rects = []
            rect = rects[0] if rects else None
            y0 = rect.y0 if rect else 0.0
            placed.append((y0, xref, rect))
        placed.sort(key=lambda t: t[0])

        for _, xref, rect in placed:
            if xref in seen_xref:
                dropped["dup"] += 1
                continue
            try:
                ext = doc.extract_image(xref)
                raw = ext["image"]
                im = Image.open(io.BytesIO(raw)).convert("RGB")
            except Exception:
                dropped["decode"] += 1
                continue
            w, h = im.size
            # filters
            if min(w, h) < min_dim:
                dropped["small"] += 1
                continue
            ar = max(w, h) / max(1, min(w, h))
            if ar > max_aspect:
                dropped["aspect"] += 1
                continue
            if rect is not None and rect.width < min_place_pt:
                dropped["place"] += 1
                continue
            # dedup by downscaled pixel hash
            thumb = im.resize((16, 16))
            phash = hashlib.md5(thumb.tobytes()).hexdigest()
            if phash in seen_hash:
                dropped["dup"] += 1
                seen_xref[xref] = seen_hash[phash]
                continue

            num = len(kept) + 1
            fname = f"fig{num:02d}.png"
            im.save(figs_dir / fname)
            seen_xref[xref] = fname
            seen_hash[phash] = fname
            cap = caption_below(page, rect) if rect is not None else ""
            kept.append({
                "num": num,
                "page": pno + 1,
                "filename": fname,
                "relpath": f"{slug}_figs/{fname}",
                "native_w": w,
                "native_h": h,
                "place_w_pt": round(rect.width, 1) if rect is not None else None,
                "place_h_pt": round(rect.height, 1) if rect is not None else None,
                "caption_hint": cap,
            })
            print(f"  kept fig{num:02d}  p{pno+1:>3}  {w}x{h}px  cap: {cap[:70]}")

    # markdown (text only)
    parts = [
        f"# {pdf_path.stem} — Raw PDF Extract\n\n",
        f"_Source: `{pdf_path.name}`_\n\n",
        f"_Pages: {n_pages}   Kept images: {len(kept)}_\n\n---\n\n",
    ]
    for pno, txt in enumerate(pages_text):
        parts.append(f"\n## Page {pno+1}\n\n{txt.strip()}\n")
        for k in kept:
            if k["page"] == pno + 1:
                parts.append(f"\n![fig{k['num']:02d} ({k['native_w']}x{k['native_h']})]"
                             f"({k['relpath']}) — _{k['caption_hint']}_\n")
    md_path.write_text("".join(parts), encoding="utf-8")
    manifest_path.write_text(json.dumps(kept, indent=2), encoding="utf-8")

    print(f"\nkept {len(kept)} images   dropped {dropped}")
    print(f"markdown : {md_path}  ({md_path.stat().st_size:,} bytes)")
    print(f"figs dir : {figs_dir}")
    print(f"manifest : {manifest_path}")
    return {"slug": slug, "pages": n_pages, "kept": len(kept), "dropped": dropped,
            "md": str(md_path), "figs_dir": str(figs_dir), "manifest": str(manifest_path)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Extract text + all embedded images from a PDF.")
    p.add_argument("pdf", type=Path)
    p.add_argument("--out", type=Path, default=Path("Input"))
    p.add_argument("--slug", type=str, default=None)
    p.add_argument("--min-dim", type=int, default=200,
                   help="drop images whose native min dimension is below this (px)")
    p.add_argument("--max-aspect", type=float, default=7.0,
                   help="drop images with aspect ratio above this")
    p.add_argument("--min-place-pt", type=float, default=70.0,
                   help="drop images placed narrower than this (PDF points)")
    args = p.parse_args(argv)

    if not args.pdf.exists():
        print(f"ERROR: PDF not found: {args.pdf}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    slug = args.slug or slugify(args.pdf.stem)
    extract(args.pdf, args.out, slug, args.min_dim, args.max_aspect, args.min_place_pt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

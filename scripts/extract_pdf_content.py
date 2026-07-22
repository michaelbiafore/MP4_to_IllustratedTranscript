"""
Extract text + every Figure/Table region from a PDF as a slide-ready bundle.

Output (under <out_dir>, default `Input/`):
  <slug>_RAW_PAPER.md                    — full per-page text with inline figure refs
  <slug>_figs/{fig|tab}NN_<slug>.png     — high-DPI render of every captioned visual
  <slug>_figs_manifest.json              — list of {page, kind, num, title, filename, relpath}

Strategy:
  - Captions are detected by regex on per-page text ("Figure N: ..." or "Table N: ...").
  - Figures are assumed to sit ABOVE their caption → crop top-of-page to caption bottom.
  - Tables are assumed to sit BELOW their caption → use `page.find_tables()` for a tight
    bbox when available, otherwise crop caption-top to bottom-of-page.
  - All rendering uses PyMuPDF; no shell-out, no OCR.

Usage:
  .venv/Scripts/python.exe scripts/extract_pdf_content.py <input.pdf> [--out Input] [--slug NAME] [--dpi 220]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import fitz  # PyMuPDF


CAPTION_RE = re.compile(
    r"^\s*(Figure|Fig\.?|FIGURE|Table|TABLE)\s*(\d+[A-Za-z]?)\s*[:\.\-]\s*(.+?)\s*$"
)


def slugify(s: str, maxlen: int = 60) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s[:maxlen] or "x"


def find_caption_rect(page: "fitz.Page", kind: str, num: str):
    for needle in (f"{kind} {num}:", f"{kind} {num}.", f"{kind}.{num}", f"{kind}. {num}"):
        rects = page.search_for(needle)
        if rects:
            return rects[0]
    return None


def crop_for_figure(page: "fitz.Page", cap_rect: "fitz.Rect", pad: float) -> "fitz.Rect":
    page_rect = page.rect
    return fitz.Rect(0, 40, page_rect.width, min(page_rect.height, cap_rect.y1 + pad))


def crop_for_table(page: "fitz.Page", cap_rect: "fitz.Rect", pad: float) -> "fitz.Rect":
    page_rect = page.rect
    table_bbox = None
    if hasattr(page, "find_tables"):
        try:
            tabs = page.find_tables()
            for t in tabs.tables:
                # Match table whose top is just below the caption.
                if cap_rect.y0 - 2 <= t.bbox[1] <= cap_rect.y1 + 80:
                    table_bbox = t.bbox
                    break
            if table_bbox is None and tabs.tables:
                table_bbox = tabs.tables[0].bbox
        except Exception:
            table_bbox = None
    if table_bbox:
        return fitz.Rect(
            max(0, table_bbox[0] - pad),
            max(0, cap_rect.y0 - pad),
            min(page_rect.width, table_bbox[2] + pad),
            min(page_rect.height, table_bbox[3] + pad),
        )
    return fitz.Rect(0, max(0, cap_rect.y0 - pad), page_rect.width, page_rect.height - 30)


def extract(pdf_path: Path, out_dir: Path, slug: str, dpi: int = 220, pad: float = 6.0) -> dict:
    figs_dir = out_dir / f"{slug}_figs"
    md_path = out_dir / f"{slug}_RAW_PAPER.md"
    manifest_path = out_dir / f"{slug}_figs_manifest.json"

    if figs_dir.exists():
        shutil.rmtree(figs_dir)
    figs_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    n_pages = doc.page_count
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    print(f"opened: {pdf_path.name}  pages={n_pages}  dpi={dpi}")

    # ---------- Pass 1: collect text per page ----------
    pages_text: list[str] = []
    for pno in range(n_pages):
        pages_text.append(doc.load_page(pno).get_text("text"))

    # ---------- Pass 2: locate caption lines ----------
    caps: list[dict] = []
    for pno, txt in enumerate(pages_text):
        for line in txt.splitlines():
            m = CAPTION_RE.match(line.strip())
            if not m:
                continue
            kind_raw, num, rest = m.groups()
            kind = "Figure" if kind_raw.lower().startswith(("fig", "figure")) else "Table"
            caps.append({
                "page": pno + 1,
                "kind": kind,
                "num": num,
                "title": rest.strip().rstrip("."),
            })

    print(f"detected {len(caps)} captioned visuals")
    for c in caps:
        print(f"  p{c['page']:>3}  {c['kind']} {c['num']}: {c['title'][:80]}")

    # ---------- Pass 3: render each caption region ----------
    figures: list[dict] = []
    for c in caps:
        page = doc.load_page(c["page"] - 1)
        cap_rect = find_caption_rect(page, c["kind"], c["num"])
        if cap_rect is None:
            print(f"  WARN: caption {c['kind']} {c['num']} on p{c['page']} not locatable, skipped")
            continue

        clip = crop_for_figure(page, cap_rect, pad) if c["kind"] == "Figure" else crop_for_table(page, cap_rect, pad)

        slug_part = slugify(c["title"], 40)
        kind_prefix = "fig" if c["kind"] == "Figure" else "tab"
        fname = f"{kind_prefix}{c['num']}_{slug_part}.png"
        fpath = figs_dir / fname
        try:
            pix = page.get_pixmap(matrix=matrix, clip=clip, alpha=False)
            pix.save(fpath)
        except Exception as e:
            print(f"  ERROR rendering {c['kind']} {c['num']}: {e}")
            continue

        figures.append({
            "page": c["page"],
            "kind": c["kind"],
            "num": c["num"],
            "title": c["title"],
            "filename": fname,
            "relpath": f"{slug}_figs/{fname}",
        })
        print(f"  rendered p{c['page']:>3}  {c['kind']} {c['num']}  -> {fname}  ({fpath.stat().st_size // 1024} KB)")

    # ---------- Pass 4: build the markdown ----------
    parts: list[str] = [
        f"# {pdf_path.stem} — Raw PDF Extract\n\n",
        f"_Source: `{pdf_path.name}`_\n\n",
        f"_Pages: {n_pages}_\n\n",
        f"_Figures + tables: {len(figures)}_\n\n",
        "---\n\n",
    ]
    for pno, txt in enumerate(pages_text):
        parts.append(f"\n## Page {pno + 1}\n\n")
        parts.append(txt.strip())
        parts.append("\n")
        for f in figures:
            if f["page"] == pno + 1:
                parts.append(f"\n![{f['kind']} {f['num']}: {f['title']}]({f['relpath']})\n")
                parts.append(f"_{f['kind']} {f['num']}: {f['title']}_\n\n")

    md_path.write_text("".join(parts), encoding="utf-8")
    manifest_path.write_text(json.dumps(figures, indent=2), encoding="utf-8")

    summary = {
        "pdf_path": str(pdf_path),
        "out_dir": str(out_dir),
        "slug": slug,
        "pages": n_pages,
        "figures_count": sum(1 for f in figures if f["kind"] == "Figure"),
        "tables_count": sum(1 for f in figures if f["kind"] == "Table"),
        "markdown_path": str(md_path),
        "figs_dir": str(figs_dir),
        "manifest_path": str(manifest_path),
        "figures": figures,
    }

    print()
    print(f"markdown : {md_path}  ({md_path.stat().st_size:,} bytes)")
    print(f"figs dir : {figs_dir}  ({summary['figures_count']} figures + {summary['tables_count']} tables)")
    print(f"manifest : {manifest_path}")
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Extract text + captioned figures/tables from a PDF.")
    p.add_argument("pdf", type=Path, help="Path to the source PDF")
    p.add_argument("--out", type=Path, default=Path("Input"), help="Output directory (default: Input/)")
    p.add_argument("--slug", type=str, default=None, help="Override slug (default: derived from PDF stem)")
    p.add_argument("--dpi", type=int, default=220, help="Render DPI for figures (default: 220)")
    p.add_argument("--pad", type=float, default=6.0, help="Padding around caption bbox in PDF points (default: 6)")
    args = p.parse_args(argv)

    pdf_path: Path = args.pdf
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        return 2

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    slug = args.slug or slugify(pdf_path.stem, maxlen=80)

    summary = extract(pdf_path, out_dir, slug, dpi=args.dpi, pad=args.pad)
    print(f"\nSUMMARY: {summary['figures_count']} figures + {summary['tables_count']} tables across {summary['pages']} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

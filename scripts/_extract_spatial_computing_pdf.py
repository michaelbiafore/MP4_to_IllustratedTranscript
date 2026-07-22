"""
Extract text + render every Figure/Table region from the VR research paper.
(Project-specific one-off — for the general reusable form see scripts/extract_pdf_content.py.)

Reads:  A:/VR/2026/Spatial Computing_202401_35pp.pdf
Writes:
  A:/Packages/Transcript2MDSlides/Input/Spatial_Computing_VR_2026_RAW_PAPER.md
  A:/Packages/Transcript2MDSlides/Input/Spatial_Computing_VR_2026_figs/{fig|tab}_NN.png

Run with the local venv:
  .venv/Scripts/python.exe scripts/_extract_spatial_computing_pdf.py
"""
import re
import shutil
from pathlib import Path

import fitz  # PyMuPDF

PDF_PATH = Path(r"A:/VR/2026/Spatial Computing_202401_35pp.pdf")
OUT_DIR = Path(r"A:/Packages/Transcript2MDSlides/Input")
FIGS_DIR = OUT_DIR / "Spatial_Computing_VR_2026_figs"
MD_PATH = OUT_DIR / "Spatial_Computing_VR_2026_RAW_PAPER.md"

# Wipe stale figs from prior runs (only this single subfolder).
if FIGS_DIR.exists():
    shutil.rmtree(FIGS_DIR)
FIGS_DIR.mkdir(parents=True, exist_ok=True)

DPI = 220
ZOOM = DPI / 72.0
PAD = 6  # padding (PDF user-space points) around caption when cropping

CAPTION_RE = re.compile(
    r"^\s*(Figure|Fig\.?|FIGURE|Table|TABLE)\s*(\d+[A-Za-z]?)\s*[:\.\-]\s*(.+?)\s*$"
)


def slugify(s: str, maxlen: int = 50) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s[:maxlen] or "x"


def find_caption_block(page, kind: str, num: str):
    """Return (caption_rect, full_caption_text) for the given Figure/Table number on the page."""
    needle_variants = [
        f"{kind} {num}:",
        f"{kind} {num}.",
        f"{kind}. {num}",
        f"{kind}.{num}",
    ]
    rects = []
    for nv in needle_variants:
        rects = page.search_for(nv)
        if rects:
            break
    if not rects:
        return None, None
    cap_rect = rects[0]

    # Extract the full caption text by walking text blocks that start near cap_rect.
    blocks = page.get_text("blocks")
    caption_full = ""
    cap_bottom = cap_rect.y1
    for b in blocks:
        x0, y0, x1, y1, txt, *_ = b
        if y0 <= cap_rect.y0 + 1 <= y1:
            caption_full = txt.strip().replace("\n", " ")
            cap_bottom = max(cap_bottom, y1)
            break
    return cap_rect, caption_full or f"{kind} {num}"


def render_region(page, clip: fitz.Rect, out_path: Path):
    mat = fitz.Matrix(ZOOM, ZOOM)
    pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
    pix.save(out_path)


def main():
    doc = fitz.open(PDF_PATH)
    print(f"opened {PDF_PATH.name}  pages={doc.page_count}")

    text_parts: list[str] = []
    text_parts.append("# Spatial Computing — VR Research Paper (Raw Extract)\n\n")
    text_parts.append(f"_Source: `{PDF_PATH.name}`_\n\n")
    text_parts.append(f"_Pages: {doc.page_count}_\n\n---\n\n")

    figures: list[dict] = []  # records for downstream slide builder

    # First pass: get text + locate captions.
    pages_text: list[str] = []
    for pno in range(doc.page_count):
        page = doc.load_page(pno)
        pages_text.append(page.get_text("text"))

    # Find every Figure/Table caption by scanning page text.
    caps_found: list[dict] = []
    for pno, txt in enumerate(pages_text):
        for line in txt.splitlines():
            m = CAPTION_RE.match(line.strip())
            if not m:
                continue
            kind_raw, num, rest = m.groups()
            kind = "Figure" if kind_raw.lower().startswith(("fig", "figure")) else "Table"
            caps_found.append({
                "page": pno + 1,
                "kind": kind,
                "num": num,
                "title": rest.strip().rstrip("."),
                "line": line.strip(),
            })

    print(f"detected {len(caps_found)} captions:")
    for c in caps_found:
        print(f"  p{c['page']:>2}  {c['kind']} {c['num']}: {c['title'][:80]}")

    # Render each caption's region.
    for c in caps_found:
        page = doc.load_page(c["page"] - 1)
        page_rect = page.rect
        cap_rect, cap_full = find_caption_block(page, c["kind"], c["num"])
        if cap_rect is None:
            print(f"  WARN: caption {c['kind']} {c['num']} on p{c['page']} not located, skipping render")
            continue

        if c["kind"] == "Figure":
            # Figure body sits above its caption.  Crop from top of page to caption bottom.
            clip = fitz.Rect(0, max(0, 40), page_rect.width, cap_rect.y1 + PAD)
        else:
            # Table body sits below its caption.  Use find_tables() to get tight bbox.
            table_bbox = None
            if hasattr(page, "find_tables"):
                try:
                    tabs = page.find_tables()
                    # Pick the table whose top is just below the caption.
                    for t in tabs.tables:
                        if t.bbox[1] >= cap_rect.y0 - 2 and t.bbox[1] <= cap_rect.y1 + 80:
                            table_bbox = t.bbox
                            break
                    if table_bbox is None and tabs.tables:
                        table_bbox = tabs.tables[0].bbox
                except Exception:
                    pass
            if table_bbox:
                # Include caption + table only (no body-text spillover).
                clip = fitz.Rect(
                    max(0, table_bbox[0] - PAD),
                    max(0, cap_rect.y0 - PAD),
                    min(page_rect.width, table_bbox[2] + PAD),
                    min(page_rect.height, table_bbox[3] + PAD),
                )
            else:
                clip = fitz.Rect(0, max(0, cap_rect.y0 - PAD), page_rect.width, page_rect.height - 30)

        slug = f"{c['kind'][:3].lower()}{c['num']}_{slugify(c['title'], 40)}"
        out_path = FIGS_DIR / f"{slug}.png"
        render_region(page, clip, out_path)
        size_kb = out_path.stat().st_size // 1024
        print(f"  rendered  p{c['page']:>2}  {c['kind']} {c['num']}  -> {out_path.name}  ({size_kb} KB)")
        figures.append({
            "page": c["page"],
            "kind": c["kind"],
            "num": c["num"],
            "title": c["title"],
            "filename": out_path.name,
            "relpath": f"Spatial_Computing_VR_2026_figs/{out_path.name}",
        })

    # Build markdown: full text per page + inline figure refs.
    for pno, txt in enumerate(pages_text):
        text_parts.append(f"\n## Page {pno + 1}\n\n")
        text_parts.append(txt.strip())
        text_parts.append("\n")
        for f in figures:
            if f["page"] == pno + 1:
                text_parts.append(f"\n![{f['kind']} {f['num']}: {f['title']}]({f['relpath']})\n")
                text_parts.append(f"_{f['kind']} {f['num']}: {f['title']}_\n\n")

    MD_PATH.write_text("".join(text_parts), encoding="utf-8")
    print(f"\nwrote markdown: {MD_PATH}  ({MD_PATH.stat().st_size:,} bytes)")
    print(f"figures saved : {len(figures)}")
    print(f"figs dir      : {FIGS_DIR}")

    # Emit figure manifest as JSON for the slide builder.
    import json
    manifest = OUT_DIR / "Spatial_Computing_VR_2026_figs_manifest.json"
    manifest.write_text(json.dumps(figures, indent=2), encoding="utf-8")
    print(f"manifest      : {manifest}")


if __name__ == "__main__":
    main()

# PDFSlides+WizWhisp — Collate a Slides PDF and Its Transcript into a Formatted Transcript

Turn a **slide deck PDF** (e.g. a lecture's exported slides) plus its **transcript** (from WizWhisp/WizScribe, or any `MM:SS text` timestamped file) into a polished, self-contained **formatted transcript** (Markdown + portable HTML) that uses **every slide**, inserted at the point in the talk where it is discussed.

This is the **no-video** sibling of `MP4+WizWhisp`. There is no frame extraction or "interesting-frame" curation: the slides are already clean, authoritative figures — render them, map each to the transcript, and place them. Platform-specific to this Windows machine (uses the project `.venv`, PyMuPDF, and pandoc).

### Example invocation (the query this command was distilled from)

> Use the transcript `A:\Packages\Transcript2MDSlides\Input\Sheaf_Course_1_20260614_025253_timestamped.txt` and the individual slides in `A:\Theory\Math\Sheaves\2026\Cellular_Sheaves_Part_01_GHRIST_42cslides.pdf` to produce a "formatted transcript" in `Output/Formatted` that uses the slides, inserted at the appropriate places, to produce `01_CellularSheaves_Applications.{md|html}`, the HTML to be portable.

**Arguments**: $ARGUMENTS

---

## Argument Parsing

Parse as: `<transcript_path> <slides_pdf_path> [--out BASENAME] [--title "..."] [--no-html] [--jpeg-width N]`

- **transcript_path** (required): a timestamped text file, one segment per line as `MM:SS  text` or `HH:MM:SS text` (the WizWhisp `*_timestamped.txt` shape). This is the **source of truth** — do not re-run Whisper. (If only a video + WizWhisp DB exists, fall back to the `MP4+WizWhisp` export step first.)
- **slides_pdf_path** (required): the lecture's slide deck as a PDF (one slide per page).
- **--out BASENAME** (optional): output base name. The command writes `Output/Formatted/{BASENAME}.md` and `{BASENAME}.html`. If omitted, derive a Title_Case name from the H1 title. (The user often dictates the exact name, e.g. `01_CellularSheaves_Applications`.)
- **--title "..."** (optional): override the H1; otherwise take it from the title slide / content.
- **--no-html** (optional): skip the HTML build (still writes the Markdown).
- **--jpeg-width N** (optional): max width for the portable-HTML slide JPEGs. **Default 1600.**

Derive a **slug** from the PDF basename (spaces → underscores) for the figures directory, e.g. `CellularSheaves_01`.

---

## Core principle

**Use every slide. Place each one at the moment it is discussed.** The slides are clean and authoritative — never screenshot them out of the talk, never drop one to keep the document short, never pad. The figure for a slide goes immediately before/around the transcript passage that depicts it. Slides advance roughly linearly with the talk, so numeric slide order ≈ transcript order — but place by **content**, not blindly by number (a teaser/section image may belong a little later, where it is actually explained).

---

## Phase 0 — Prerequisites

1. **Python**: use the project venv `.venv/Scripts/python.exe` (NOT `python3`). Verify PyMuPDF + Pillow:
   ```
   .venv/Scripts/python.exe -c "import fitz, PIL; print('OK', fitz.__doc__[:20])"
   ```
   (PyMuPDF renders PDF pages; `/c/poppler/.../pdftoppm` is an alternative if PyMuPDF is absent.)
2. **pandoc**: `pandoc --version` (3.6.x expected — anchor rules below assume it).
3. **Theme file**: `Refs/formatted_transcript_style.html` (the emerald HTML theme). Required for the portable HTML.

---

## Phase 1 — Read the transcript first

Read the **entire** transcript before touching the slides — the spoken content tells you what each slide is and where the section boundaries fall, and it is the basis for placement. Note:
- **Speaker count.** A single-narrator lecture is written as **flowing prose** (no speaker labels); an interview / multi-speaker recording / Q&A uses **bold speaker labels** (`**Name:**`).
- **Transcription artifacts to correct** (and later list in the intro blockquote). WizWhisp routinely mangles technical terms and proper names — collect them as you read. Real examples from the cellular-sheaves lecture: "stocks" → **stalks**, "other characteristic" → **Euler characteristic**, "co-chief" → **cosheaf**, plus author names (Schapira, Viro, Kashiwara, MacPherson, Baryshnikov, Bröcker–Kuppe, Billera, Iversen, Hegselmann–Krause). Correct these throughout and note the notable fixes.

---

## Phase 2 — Render the slides and map them to the transcript

1. **Render every PDF page to an image** at review resolution into `Input/{slug}_slides/`:
   ```python
   import fitz, os
   doc = fitz.open(PDF); out = rf"Input/{slug}_slides"; os.makedirs(out, exist_ok=True)
   for i, page in enumerate(doc, 1):
       page.get_pixmap(matrix=fitz.Matrix(2.1, 2.1)).save(os.path.join(out, f"slide_{i:02d}.png"))   # ~150 dpi
   ```
2. **Build labeled contact sheets** so you can review every slide fast. Use **few, large cells (3×3)** — small thumbnails are not legible for slide titles:
   ```python
   from PIL import Image, ImageDraw
   import glob, os, shutil
   files = sorted(glob.glob(rf"Input/{slug}_slides/slide_*.png"))
   cols, rows, tw, th = 3, 3, 660, 392
   shutil.rmtree(rf"Input/_{slug}_montage", ignore_errors=True); os.makedirs(rf"Input/_{slug}_montage")
   for si in range(0, len(files), cols*rows):
       group = files[si:si+cols*rows]
       sheet = Image.new("RGB", (cols*tw, rows*th), (40,40,40)); d = ImageDraw.Draw(sheet)
       for idx, f in enumerate(group):
           im = Image.open(f).convert("RGB"); im.thumbnail((tw-8, th-26))
           x, y = (idx%cols)*tw, (idx//cols)*th
           sheet.paste(im, (x+4, y+22)); d.text((x+6, y+5), os.path.basename(f), fill="white")
       sheet.save(rf"Input/_{slug}_montage/sheet_{si//(cols*rows)+1:02d}.jpg", quality=88)
   ```
3. **Read every contact sheet** with the Read tool. **The `slide_NN.png` filenames are ground truth** — montage labels and your eyeball numbering can drift by one, so always confirm a slide's number against its filename. Read any ambiguous slide at **full resolution** before captioning it (faded "question" slides, near-duplicate diagrams, dense formula slides).
4. **Build the slide → transcript map**: for each slide, note the timestamp/passage where its content is spoken. Most are monotonic; a few section-divider or teaser images belong where the topic is actually explained rather than where the PDF places them.

---

## Phase 3 — Place the slides

Insert **all** slides in content order, each as a figure with a **specific caption** written from the slide's actual content (what it shows / states / who it credits) — never "Slide N" or "a diagram." Number figures in document order. Example placements (cellular-sheaves lecture): title → outline → the running concept slides → the worked-example slides → the closing/credits slides, each next to the matching spoken passage.

---

## Phase 4 — Write the formatted Markdown

Output to `Output/Formatted/{BASENAME}.md`.

### Header block
```
# {Title from the title slide / content}

**Source:** {what kind of recording — e.g. "Mini-course lecture (screen-shared slides + talk), Lecture 1 of 3"}
**Presenter:** {name(s)}
**Runtime:** ~{MMm}
**Figures:** all {N} lecture slides, placed at the moment each is discussed

> This is a lightly cleaned, verbatim transcript … Timestamps (`*[~MM:SS]*`) mark roughly five-minute intervals. {List the notable transcription artifacts you corrected — bold the corrected forms.}
```

### Body
- **TOC** with anchor links (H2 → nested H3).
- **Anchor convention (pandoc 3.6.x):** lowercase, spaces → `-`, **drop** `:`, `?`, `&`, `,`, `'`, `—`, `()`; **pandoc keeps the dot `.`**. Never double a hyphen (an em-dash "Part 1 — X" yields `part-1-x`, single hyphen). **Avoid non-ASCII in headings** (`χ`, `é`) — spell them out (`Euler Characteristic`, `Bezier`) so ids are predictable. The Phase-5 link check is the backstop.
- **Lightly cleaned verbatim**: keep the speaker's words and phrasing; remove only filler, false starts, and dead repetition; do not summarize away content. Single narrator → flowing prose; multi-speaker → bold labels. Correct the transcription artifacts; lightly mask gratuitous profanity.
- **Timestamps** `*[~MM:SS]*` under each major section at ~5-minute intervals.
- **Figures** at the moment each slide appears:
  ```
  ![Figure N: Specific caption describing exactly what the slide shows.](../../Input/{slug}_slides/slide_NN.png)
  ```
  Use **every** slide, numbered in document order.
- `>` blockquotes for memorable quotes/asides, **bold** for key terms, `---` between major sections.

### Footer
- A **Key Takeaways** table (`| Concept | Summary |`), one row per major theme.

---

## Phase 5 — Build the portable HTML (house "emerald" theme)

Must be fully self-contained AND **email-portable in size**. High-res slide PNGs balloon the file (42 PNGs ≈ 28 MB — over a 25 MB mail limit), so **down-convert the slides to JPEG first**, then embed.

1. **Convert the slides to optimized JPEGs** (this is the size lever — ~28 MB → ~8 MB):
   ```python
   from PIL import Image
   import glob
   for f in sorted(glob.glob(rf"Input/{slug}_slides/slide_*.png")):
       im = Image.open(f).convert("RGB")
       if im.width > JPEG_WIDTH:   # default 1600
           im = im.resize((JPEG_WIDTH, round(im.height*JPEG_WIDTH/im.width)), Image.LANCZOS)
       im.save(f[:-4] + ".jpg", quality=88, optimize=True)
   ```
   Then point the Markdown figures at `.jpg` (global `slide_NN.png` → `slide_NN.jpg`). JPEG q88 keeps slide text crisp; pure line-art decks can use a higher `--jpeg-width` if a diagram looks soft.
2. **Build with pandoc** from inside `Output/Formatted/` so the `../../Input/...` paths resolve:
   ```
   pandoc -f markdown-implicit_figures "{BASENAME}.md" \
     -s --embed-resources \
     -H "../../Refs/formatted_transcript_style.html" \
     --metadata title="{Title}" \
     -o "{BASENAME}.html"
   ```
   `-H` appends the emerald theme **after** pandoc's default CSS (don't use `--css`). `--embed-resources` base64-inlines every image. `-f markdown-implicit_figures` keeps images inline.

**Verify (do not skip):**
- Images embedded: `grep -c 'data:image' f.html` **==** number of slides.
- Portable: `grep -c 'src="\.\."' f.html` **== 0** (no external image refs).
- Theme applied: file contains `#059669` and `apple-system`.
- **Every TOC link resolves** — the diff must be empty:
  ```bash
  grep -oE '<h[123] id="[^"]+"' f.html | sed -E 's/.*id="([^"]+)"/\1/' | sort -u > ids
  grep -oE 'href="#[^"]+"'      f.html | sed -E 's/href="#([^"]+)"/\1/' | sort -u > hrefs
  comm -23 hrefs ids   # MUST be empty; if not, fix the TOC hrefs to match the generated ids
  ```
- Report the final HTML size (target well under 25 MB for email).

---

## Phase 6 — Report & cleanup

- Report: presenter/runtime, transcript line count, slide count, output paths + sizes, and all verification results.
- **Keep**: `Output/Formatted/{BASENAME}.{md,html}` and `Input/{slug}_slides/` (the `.md` references the slide JPEGs; the `.html` has them embedded).
- **Delete** the temporary review montage `Input/_{slug}_montage/`. (Offer to also remove the original render PNGs if the JPEGs replaced them and the `.md` now points at `.jpg`.)

---

## Quality Checklist

- [ ] Read the whole transcript first; identified single- vs multi-speaker; collected transcription artifacts.
- [ ] Rendered every PDF page; reviewed every contact sheet; confirmed slide numbers against **filenames**, not montage labels.
- [ ] **All** slides used, each placed at the moment it is discussed, with a **specific** caption.
- [ ] Header block + intro blockquote (with artifact list) + Key Takeaways table present; prose vs bold-labels handled correctly.
- [ ] Timestamps at ~5-min intervals.
- [ ] HTML: emerald theme applied; **every** slide base64-embedded; zero external refs; **every TOC link resolves** (`comm` empty); ASCII-only heading anchors.
- [ ] Slides converted to optimized JPEG so the portable HTML is comfortably emailable; final size reported.
- [ ] Files named exactly as requested (e.g. `01_CellularSheaves_Applications.{md,html}`) in `Output/Formatted/`.

## Reusable assets this command uses
- `Refs/formatted_transcript_style.html` — the emerald HTML transcript theme
- PyMuPDF (`fitz`) for PDF→PNG; Pillow for montages and the PNG→JPEG size pass
- pandoc 3.6.x with `--embed-resources` + `-H` emerald theme
- Sibling commands: `MP4+WizWhisp` (video version, with frame extraction/curation), `slidefy-pdf` (PDF → slide *deck*)

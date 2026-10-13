# Chinese character/word reference pack for coding agents

Drop this folder into a repo (e.g. `refs/zh/`) and point Claude Code at it for rough,
offline translation of Chinese text extracted from a PDF.

## Files

| File | Size | What it is |
|---|---|---|
| `cc-cedict.txt` | ~10 MB | Full CC-CEDICT: ~124,700 entries (single chars + compounds/words), `traditional simplified [pinyin] /def/def/`. **Grep this, don't read it into context.** |
| `hanzi_top3000.md` | ~330 KB | Markdown table of the 3,000 most frequent simplified characters: rank, traditional form, pinyin, meaning, radical, stroke count, HSK level, IDS component decomposition. |
| `hanzi_top1000.md` | ~120 KB | Same, top 1,000 only — small enough to paste into a prompt/context window wholesale (covers roughly 90% of running text). |
| `hanzi_top3000.json` / `hanzi_top1000.json` | | Same data as JSON keyed by character, including every CC-CEDICT reading per character (`all_readings`) for disambiguating polyphones. |
| `lookup.py` | 2 KB | Zero-dependency helper: greedy longest-match segmentation + gloss. |

## Recommended agent workflow

1. Extract text layer from the PDF (`pdftotext -enc UTF-8`, or `pymupdf`). If it's a scan,
   OCR first with Tesseract `chi_sim`/`chi_tra` or PaddleOCR.
2. Run `python lookup.py --file page.txt` to get a segmented, glossed token list.
3. Have the model translate from the glossed token list rather than raw characters —
   this anchors it and prevents hallucinated readings for rare/technical terms.
4. Fall back to `grep '^\S* 术语 ' cc-cedict.txt` for anything unresolved.

## Usage

```bash
python lookup.py 机器学习模型的训练数据
# 机器学习  [ji1 qi4 xue2 xi2]  (computing) machine learning
# 模型      [mo2 xing2]         model; mold; matrix
# 训练      [xun4 lian4]        to train; to drill; training
# 数据      [shu4 ju4]          data

python lookup.py --chars 机器学习   # per-character only
python lookup.py --file page3.txt   # whole file
grep -P '^\S+ 数据 ' cc-cedict.txt  # raw dictionary lookup
```

## Caveats

- Greedy longest-match segmentation is crude. For better boundaries use `jieba`
  (`pip install jieba`) and feed its tokens into the same CC-CEDICT lookup.
- CC-CEDICT is learner-oriented; specialized legal/medical/financial jargon is thin.
- Pinyin in CC-CEDICT is numbered-tone (`xue2`); HanziDB fields use diacritics (`xué`).
- This produces a *gloss*, not a translation. Word order, aspect, measure words, and
  topic-comment structure still need the model to do real work.

## Sources & licenses

- [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cc-cedict) — CC BY-SA 4.0.
  Redistribution requires attribution and share-alike.
- [Make Me a Hanzi](https://github.com/skishore/makemeahanzi) — LGPL; `dictionary.txt`
  derived from Unihan and CJKlib (component decompositions, etymology).
- [hanziDB.csv](https://github.com/ruddfawcett/hanziDB.csv) — frequency ranks, radicals,
  stroke counts, HSK levels.
- [Unihan / UAX #38](https://www.unicode.org/reports/tr38/) — upstream Unicode Han database,
  if you need variants, dictionary indices, or Cantonese/Japanese readings.

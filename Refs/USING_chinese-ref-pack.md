Yes — and I built you a ready-to-drop-in bundle rather than just pointing at URLs.

## The canonical sources

- [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cc-cedict) — the one you actually want. ~124,700 entries covering single characters *and* compounds, plain text, `traditional simplified [pinyin] /def/def/`, CC BY-SA 4.0.
- [Make Me a Hanzi](https://github.com/skishore/makemeahanzi) — line-delimited JSON for ~9,500 characters with IDS component decomposition and etymology, derived from Unihan and CJKlib.
- [hanziDB.csv](https://github.com/ruddfawcett/hanziDB.csv) — frequency ranks, radicals, stroke counts, HSK levels.
- [Unihan / UAX #38](https://www.unicode.org/reports/tr38/) — upstream Unicode Han database if you need variants or non-Mandarin readings.

## What's in the zip

I merged all three into `chinese-ref-pack/`:

- `cc-cedict.txt` (~10 MB) — full dictionary, meant to be grepped, not loaded into context
- `hanzi_top3000.md` / `.json` — top 3,000 characters with traditional form, pinyin, meaning, radical, strokes, HSK level, and component decomposition
- `hanzi_top1000.md` (~120 KB) — small enough to paste wholesale into a prompt; covers roughly 90% of running text
- `lookup.py` — zero-dependency greedy longest-match segmenter + glosser
- `README.md` — workflow notes and license/attribution requirements

Tested output:

```
$ python lookup.py 机器学习模型的训练数据
机器学习  [ji1 qi4 xue2 xi2]  (computing) machine learning
模型      [mo2 xing2]         model; mold; matrix
的        [de5]               possessive particle
训练      [xun4 lian4]        to train; to drill; training
数据      [shu4 ju4]          data
```

## Suggested pipeline for Claude Code

Extract the text layer (`pdftotext -enc UTF-8`, or OCR with Tesseract `chi_sim` if it's a scan) → run it through `lookup.py --file` → have the model translate from the glossed token list rather than raw characters. That anchoring is what kills hallucinated readings on technical terms. Swap the greedy segmenter for `jieba` if boundary quality matters.

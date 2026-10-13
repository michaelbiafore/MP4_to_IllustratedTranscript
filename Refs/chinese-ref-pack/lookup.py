#!/usr/bin/env python3
"""Offline Chinese lookup helper for rough PDF translation.

Usage:
  python lookup.py 机器学习模型          # gloss a string (greedy longest-match segmentation)
  python lookup.py --chars 机器学习      # per-character gloss only
  python lookup.py --file page3.txt      # gloss a text file
Data files expected next to this script: cc-cedict.txt, hanzi_top3000.json
"""
import json, os, re, sys

D = os.path.dirname(os.path.abspath(__file__))
LINE = re.compile(r"^(\S+) (\S+) \[([^\]]*)\] /(.*)/$")


def load_cedict(path=None):
    d = {}
    with open(path or os.path.join(D, "cc-cedict.txt"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            m = LINE.match(line.strip())
            if not m:
                continue
            trad, simp, pin, defs = m.groups()
            for key in {simp, trad}:
                d.setdefault(key, []).append({"pinyin": pin, "defs": defs.split("/")})
    return d


def segment(text, dic, maxlen=6):
    """Greedy longest-match segmentation against CC-CEDICT."""
    out, i = [], 0
    while i < len(text):
        for n in range(min(maxlen, len(text) - i), 0, -1):
            chunk = text[i:i + n]
            if chunk in dic:
                out.append((chunk, dic[chunk]))
                i += n
                break
        else:
            out.append((text[i], None))
            i += 1
    return out


def gloss(text, dic, chars_only=False):
    lines = []
    items = [(c, dic.get(c)) for c in text] if chars_only else segment(text, dic)
    for tok, entries in items:
        if not re.search(r"[\u3400-\u9fff]", tok):
            continue
        if entries:
            e = entries[0]
            defs = "; ".join([x for x in e["defs"] if x][:3])
            lines.append(f"{tok}\t[{e['pinyin']}]\t{defs}")
        else:
            lines.append(f"{tok}\t[?]\t(not in dictionary)")
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    chars_only = "--chars" in args
    args = [a for a in args if a != "--chars"]
    if args and args[0] == "--file":
        text = open(args[1], encoding="utf-8").read()
    else:
        text = " ".join(args)
    print(gloss(text, load_cedict(), chars_only))

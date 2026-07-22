import sqlite3, json, os

db = r"C:\Users\biafo\AppData\Local\Packages\49657NowSmartStudio.WizScribe_agnvvc9c4qtza\LocalCache\Local\WizWhisp\TaskHistory.db"
slug = "BBG_ClaudeCode_03_hires_20260604_195833"
out = rf"A:\Packages\Transcript2MDSlides\Input\{slug}_RAW_TRANSCRIPT.txt"
jout = rf"A:\Packages\Transcript2MDSlides\Input\{slug}_transcript.json"

c = sqlite3.connect(db)
cur = c.cursor()
cur.execute("SELECT ResultItemsJson FROM TaskHistory WHERE Id=25")
data = json.loads(cur.fetchone()[0])

def to_sec(ts):
    # format HH:MM:SS(.fff)
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)

lines = []
for seg in data:
    start = to_sec(seg["Start"])
    mins = int(start // 60)
    secs = int(start % 60)
    txt = seg["Text"].strip()
    if txt:
        lines.append(f"[{mins}:{secs:02d}] {txt}")

with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

with open(jout, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

total = to_sec(data[-1]["End"])
words = sum(len(s["Text"].split()) for s in data)
print(f"Wrote {len(lines)} segments to {out}")
print(f"Duration ~{int(total//60)}m{int(total%60):02d}s, ~{words} words")

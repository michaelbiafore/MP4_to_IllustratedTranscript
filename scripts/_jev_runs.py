"""Group static frames into runs and pick a representative per run.

Usage: python _jev_runs.py <features.json> <out_runs.json> [mot_max] [gap]

A "run" is a maximal stretch of frames whose motion is below mot_max, allowing
up to `gap` non-qualifying frames inside it. The representative is the frame in
the run with the highest edge density (most on-screen content).
"""
import json
import sys
from pathlib import Path

feats = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out = Path(sys.argv[2])
mot_max = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
gap = int(sys.argv[4]) if len(sys.argv) > 4 else 2

hits = [r for r in feats if r["mot"] < mot_max]
runs = []
cur = []
for r in hits:
    if cur and r["i"] - cur[-1]["i"] > gap + 1:
        runs.append(cur)
        cur = []
    cur.append(r)
if cur:
    runs.append(cur)

recs = []
for n, run in enumerate(runs, start=1):
    rep = max(run, key=lambda r: r["edge"])
    recs.append({
        "run": n,
        "start_sec": run[0]["sec"],
        "end_sec": run[-1]["sec"],
        "len": len(run),
        "rep_i": rep["i"],
        "rep_sec": rep["sec"],
        "edge": rep["edge"],
        "flat": rep["flat"],
        "lum": rep["lum"],
        "sat": rep["sat"],
    })

out.write_text(json.dumps(recs, indent=1), encoding="utf-8")
print(f"static frames: {len(hits)}   runs: {len(recs)}")
long_runs = [r for r in recs if r["len"] >= 3]
print(f"runs with >=3 static seconds: {len(long_runs)}")
for r in recs[:12]:
    m, s = divmod(r["rep_sec"], 60)
    print(f"  run {r['run']:3d}  {m}:{s:02d}  len={r['len']:3d}  edge={r['edge']:.2f} lum={r['lum']:.0f}")

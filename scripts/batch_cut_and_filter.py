#!/usr/bin/env python3
"""
batch_cut_and_filter.py — for each lecture in a manifest, cut a per-lecture
MP4 (-c copy from the cropped 1x source) and run dense frame extraction +
filter_lecture_frames.py to produce a deduplicated set of unique slides.

Usage:
  python scripts/batch_cut_and_filter.py <manifest.json> [--slug-prefix cowork_s2]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def find_ffmpeg() -> str:
    p = shutil.which("ffmpeg")
    if p: return p
    for root in ["/c/Users/biafo/AppData/Local/Microsoft/WinGet/Packages"]:
        for f in Path(root).rglob("ffmpeg.exe"):
            return str(f)
    raise SystemExit("ffmpeg not found")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--slug-prefix", default="cowork_s2")
    ap.add_argument("--interval", type=int, default=8)
    ap.add_argument("--skip-cut", action="store_true", help="Reuse existing per-lecture MP4s")
    ap.add_argument("--skip-figs", action="store_true", help="Reuse existing fig folders")
    args = ap.parse_args()

    ffmpeg = find_ffmpeg()
    manifest = json.load(open(args.manifest))
    src = Path(manifest["source_mp4"])
    if not src.exists():
        raise SystemExit(f"source missing: {src}")

    summary = []
    for lec in manifest["lectures"]:
        idx  = lec["idx"]
        slug = f"{args.slug_prefix}_l{idx:02d}"
        mp4_path = Path(f"Input/{slug}_video.mp4")
        figs_raw_dir = Path(f"Input/{slug}_figs_raw")
        figs_filtered_dir = Path(f"Input/{slug}_figs_raw_filtered")

        start = lec["start_sec"]
        end   = lec["end_sec"]
        dur   = end - start
        print(f"\n=== L{idx:02d} ({dur}s) {lec['title']}")

        # 1. Cut
        if not (args.skip_cut and mp4_path.exists()):
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                   "-ss", str(start), "-to", str(end), "-i", str(src),
                   "-c", "copy", "-movflags", "+faststart", str(mp4_path)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"  CUT FAILED: {r.stderr[-500:]}")
                continue
        size_mb = mp4_path.stat().st_size / 1048576
        print(f"  cut → {mp4_path} ({size_mb:.1f} MB)")

        # 2. Dense frame extraction
        if not args.skip_figs:
            if figs_raw_dir.exists():
                shutil.rmtree(figs_raw_dir)
            figs_raw_dir.mkdir(parents=True, exist_ok=True)
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                   "-i", str(mp4_path),
                   "-vf", f"fps=1/{args.interval},scale=1920:1080",
                   "-q:v", "2",
                   str(figs_raw_dir / "frame_%04d.jpg")]
            subprocess.run(cmd, check=True)
        n_raw = len(list(figs_raw_dir.glob("*.jpg")))
        print(f"  raw frames: {n_raw}")

        # 3. Filter
        if not args.skip_figs:
            if figs_filtered_dir.exists():
                shutil.rmtree(figs_filtered_dir)
            cmd = [sys.executable, "scripts/filter_lecture_frames.py",
                   str(figs_raw_dir), str(args.interval)]
            subprocess.run(cmd, check=True)
        n_filt = len(list(figs_filtered_dir.glob("frame_*.jpg")))
        print(f"  filtered → {n_filt}")

        summary.append({"idx": idx, "slug": slug, "title": lec["title"],
                        "duration_sec": dur, "mp4": str(mp4_path),
                        "n_raw": n_raw, "n_filtered": n_filt})

    # Write summary
    out = Path(args.manifest).with_suffix(".processed.json")
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n=== DONE — summary at {out}")
    for s in summary:
        print(f"  L{s['idx']:02d}  {s['n_filtered']:3d} unique frames  {s['title']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
filter_lecture_frames.py — pick "interesting and unique" frames from a dense
sampling of a lecture-style video.

Drops:
  * talking-head frames           (large skin-tone region)
  * near-blank screens            (low pixel variance, low edge density)
  * logo-only screens             (most of frame is background, tiny content)
  * progressive-reveal duplicates (within a run of phash-similar frames,
                                   keep only the most-revealed one)

Then deduplicates across surviving frames so the final pool is unique slides.

Usage:
    python scripts/filter_lecture_frames.py <frames_dir> <interval_sec>
        [--phash-run N]      # max phash distance considered "same slide" (default 8)
        [--phash-final N]    # final dedup distance threshold (default 18)
        [--min-edge PCT]     # min edge density to be considered content-rich
                             # (default 1.5 — frames below this are blank/logo)
        [--max-skin PCT]     # frame is talking-head if >PCT skin-toned
                             # (default 18)
        [--output DIR]       # output dir (default: <frames_dir>_filtered)

Output:
  <output_dir>/          renamed surviving frames + all-frames-debug.json
  <output_dir>/manifest.json   list of {filename, time_sec, time_str, score}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import cv2
import numpy as np
from PIL import Image
import imagehash


# ---------------------------------------------------------------------------
# Per-frame feature extraction
# ---------------------------------------------------------------------------

@dataclass
class FrameStat:
    idx: int                 # 1-based extraction index → time_sec = (idx-1)*interval
    time_sec: int
    filename: str
    edge_pct: float          # % of pixels that are Canny edges
    std_dev: float           # global pixel std-dev (low = blank)
    skin_pct: float          # % of pixels in HSV skin range
    content_score: float     # composite "how much content is here"
    phash: str               # 16x16 perceptual hash, hex


def _skin_pct(bgr: np.ndarray) -> float:
    """% of frame pixels in the typical skin-tone HSV range."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    # Two H ranges to cover most skin tones
    lo1 = np.array([0,  30,  60], dtype=np.uint8)
    hi1 = np.array([20, 150, 255], dtype=np.uint8)
    lo2 = np.array([170, 30,  60], dtype=np.uint8)
    hi2 = np.array([180, 150, 255], dtype=np.uint8)
    m1 = cv2.inRange(hsv, lo1, hi1)
    m2 = cv2.inRange(hsv, lo2, hi2)
    mask = cv2.bitwise_or(m1, m2)
    return 100.0 * float(mask.sum()) / (mask.size * 255.0)


def _edge_pct(gray: np.ndarray) -> float:
    """% of frame pixels that are Canny edges (proxy for slide content)."""
    edges = cv2.Canny(gray, 80, 200)
    return 100.0 * float((edges > 0).sum()) / edges.size


def _content_score(edge_pct: float, std_dev: float, skin_pct: float) -> float:
    """
    Composite "how informationally rich is this frame".
    Higher = more text/diagrams/charts. Penalize skin (talking-head).
    """
    skin_penalty = max(0.0, 1.0 - (skin_pct / 25.0))  # 25%+ skin = full penalty
    return edge_pct * (std_dev / 60.0) * skin_penalty


def analyze_frame(path: Path) -> FrameStat:
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise RuntimeError(f"failed to read {path}")
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edge_pct = _edge_pct(gray)
    std_dev = float(gray.std())
    skin_pct = _skin_pct(bgr)
    content_score = _content_score(edge_pct, std_dev, skin_pct)
    pil = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    phash = str(imagehash.phash(pil, hash_size=16))
    # idx parsed by caller
    return FrameStat(
        idx=0, time_sec=0, filename=path.name,
        edge_pct=edge_pct, std_dev=std_dev, skin_pct=skin_pct,
        content_score=content_score, phash=phash,
    )


# ---------------------------------------------------------------------------
# Filtering pipeline
# ---------------------------------------------------------------------------

def is_uninteresting(s: FrameStat, min_edge: float, max_skin: float) -> tuple[bool, str]:
    """Return (drop, reason)."""
    if s.edge_pct < min_edge:
        return True, "blank_or_logo"
    if s.std_dev < 20.0:
        return True, "blank"
    if s.skin_pct > max_skin and s.edge_pct < 4.0:
        # talking head with little overlay text/slide
        return True, "talking_head"
    return False, ""


def _phash_dist(a: str, b: str) -> int:
    return imagehash.hex_to_hash(a) - imagehash.hex_to_hash(b)


def group_runs(stats: list[FrameStat], phash_run_threshold: int) -> list[list[FrameStat]]:
    """
    Walk frames in time order; each frame extends the current run if its phash
    is close to the run's representative; otherwise start a new run.
    """
    runs: list[list[FrameStat]] = []
    if not stats:
        return runs
    current = [stats[0]]
    for s in stats[1:]:
        # Compare against most recent frame in run
        prev = current[-1]
        if _phash_dist(s.phash, prev.phash) <= phash_run_threshold:
            current.append(s)
        else:
            runs.append(current)
            current = [s]
    runs.append(current)
    return runs


def pick_run_winners(runs: list[list[FrameStat]]) -> list[FrameStat]:
    """
    For each run, keep ONLY the frame with the highest content_score.
    This captures the maximally-revealed frame in a progressive-reveal sequence.
    """
    winners: list[FrameStat] = []
    for run in runs:
        best = max(run, key=lambda s: s.content_score)
        winners.append(best)
    return winners


def final_dedup(stats: list[FrameStat], threshold: int) -> list[FrameStat]:
    """Greedy: keep frame N only if its phash is far from every kept frame."""
    kept: list[FrameStat] = []
    for s in stats:
        too_close = False
        for k in kept:
            if _phash_dist(s.phash, k.phash) < threshold:
                # Within threshold → consider them duplicates.
                # If new one has higher content score, replace.
                if s.content_score > k.content_score * 1.05:
                    kept.remove(k)
                    kept.append(s)
                too_close = True
                break
        if not too_close:
            kept.append(s)
    kept.sort(key=lambda s: s.time_sec)
    return kept


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def fmt_ts(sec: int) -> str:
    m, s = divmod(sec, 60)
    return f"{m:03d}m{s:02d}s"


def fmt_clock(sec: int) -> str:
    m, s = divmod(sec, 60)
    return f"{m}:{s:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames_dir")
    ap.add_argument("interval_sec", type=int)
    ap.add_argument("--phash-run", type=int, default=8)
    ap.add_argument("--phash-final", type=int, default=18)
    ap.add_argument("--min-edge", type=float, default=1.5)
    ap.add_argument("--max-skin", type=float, default=18.0)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    frames_dir = Path(args.frames_dir)
    if not frames_dir.is_dir():
        sys.exit(f"not a directory: {frames_dir}")

    output_dir = Path(args.output) if args.output else Path(str(frames_dir) + "_filtered")
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in frames_dir.iterdir() if p.suffix.lower() == ".jpg")
    if not files:
        sys.exit(f"no .jpg in {frames_dir}")

    print(f"Analyzing {len(files)} frames at {args.interval_sec}s intervals …")
    stats: list[FrameStat] = []
    for i, f in enumerate(files, start=1):
        s = analyze_frame(f)
        s.idx = i
        # frame_NNNN.jpg → idx N → time_sec = (N-1)*interval
        try:
            n = int(f.stem.split("_")[-1])
        except ValueError:
            n = i
        s.time_sec = (n - 1) * args.interval_sec
        stats.append(s)
        if i % 50 == 0:
            print(f"  {i}/{len(files)}")

    # Step 1: drop uninteresting frames
    survivors_step1 = []
    drops_log: list[dict] = []
    for s in stats:
        drop, reason = is_uninteresting(s, args.min_edge, args.max_skin)
        if drop:
            drops_log.append({
                "filename": s.filename, "time_sec": s.time_sec,
                "reason": reason,
                "edge_pct": round(s.edge_pct, 2),
                "std_dev": round(s.std_dev, 2),
                "skin_pct": round(s.skin_pct, 2),
            })
        else:
            survivors_step1.append(s)
    print(
        f"  drop talking/blank/logo: kept {len(survivors_step1)}/{len(stats)} "
        f"(removed {len(drops_log)})"
    )

    # Step 2: group into runs of phash-similar frames; keep best per run
    runs = group_runs(survivors_step1, args.phash_run)
    winners = pick_run_winners(runs)
    print(
        f"  pick run winners (handles partial reveals): "
        f"{len(runs)} runs → {len(winners)} winners"
    )

    # Step 3: final dedup across runs
    kept = final_dedup(winners, args.phash_final)
    print(f"  final dedup (threshold {args.phash_final}): {len(kept)} unique frames")

    # Save kept frames with descriptive names
    manifest: list[dict] = []
    for k in kept:
        new_name = f"frame_{fmt_ts(k.time_sec)}_score_{k.content_score:05.1f}.jpg"
        src = frames_dir / k.filename
        dst = output_dir / new_name
        # Re-encode at quality 90 (filter input was already JPEG so re-saving
        # is cheap; this also normalizes dimensions if the source is variable).
        img = Image.open(src)
        img.save(dst, quality=90)
        manifest.append({
            "filename": new_name,
            "time_sec": k.time_sec,
            "time_str": fmt_clock(k.time_sec),
            "edge_pct": round(k.edge_pct, 2),
            "std_dev": round(k.std_dev, 2),
            "skin_pct": round(k.skin_pct, 2),
            "content_score": round(k.content_score, 2),
        })

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (output_dir / "drops.json").write_text(
        json.dumps(drops_log, indent=2), encoding="utf-8"
    )
    (output_dir / "all_stats.json").write_text(
        json.dumps([asdict(s) for s in stats], indent=2), encoding="utf-8"
    )

    print()
    print(f"Wrote {len(kept)} frames → {output_dir}")
    print(f"Manifest:    {output_dir/'manifest.json'}")
    print(f"Drops log:   {output_dir/'drops.json'}")


if __name__ == "__main__":
    main()

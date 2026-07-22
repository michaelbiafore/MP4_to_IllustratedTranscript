#!/usr/bin/env python3
"""
Extract slide/diagram frames from a screen-recorded talking-head video, given
a list of *original-video* timestamps where slides are known to appear.

Tailored for the Substack-video case: the local MP4 plays at 2x the original
speed (mp4_t = original_t / 2). Per the user's hint, valuable slide frames are
brief (sometimes <1s) and may appear as line-by-line reveal sequences — so we
sample densely around each target window, drop talking-head frames, cluster
near-duplicates, and keep the richest (most content) frame per cluster.

Usage:
  extract_slide_frames.py <mp4_path> --slug <slug> \
      --targets "MM:SS,MM:SS,..." \
      [--speed 2.0] [--offset 0.0] \
      [--window 3.0] [--fps 4.0] \
      [--out-dir Input]
"""
import sys, os, re, json, argparse, subprocess, shutil, tempfile
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import cv2
import numpy as np
import imagehash
from PIL import Image

_FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def parse_mmss(s: str) -> float:
    s = s.strip()
    if ":" not in s:
        return float(s)
    parts = s.split(":")
    if len(parts) == 2:
        m, sec = parts
        return int(m) * 60 + float(sec)
    if len(parts) == 3:
        h, m, sec = parts
        return int(h) * 3600 + int(m) * 60 + float(sec)
    raise ValueError(f"Bad timestamp: {s!r}")


def fmt_mmss(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m:02d}:{s:02d}"


# ---------------- frame analysis ----------------

def skin_ratio(bgr: np.ndarray) -> float:
    """Fraction of pixels that look like human skin (in HSV)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    # Two-band skin range
    m1 = cv2.inRange(hsv, (0,  30, 60), (25, 180, 255))
    m2 = cv2.inRange(hsv, (160, 30, 60), (180, 180, 255))
    mask = cv2.bitwise_or(m1, m2)
    return float(mask.sum()) / (mask.size * 255.0)


def edge_density(bgr: np.ndarray) -> float:
    """Fraction of pixels that are Canny edges. Slides/charts have many sharp edges."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 200)
    return float((edges > 0).sum()) / edges.size


def whitespace_ratio(bgr: np.ndarray) -> float:
    """Fraction of pixels that are bright/near-white. Slides tend to have a lot."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return float((gray > 220).sum()) / gray.size


def detect_face(bgr: np.ndarray, min_size: int = 120) -> int:
    """Return the side-length of the largest detected frontal face, or 0."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    faces = _FACE_CASCADE.detectMultiScale(
        gray, scaleFactor=1.2, minNeighbors=5, minSize=(min_size, min_size)
    )
    if len(faces) == 0:
        return 0
    return int(max(w for (_, _, w, _) in faces))


def is_talking_head(bgr: np.ndarray) -> tuple[bool, dict]:
    """Drop the frame if a frontal face is detected OR signature looks like a portrait."""
    face = detect_face(bgr, min_size=120)
    sk = skin_ratio(bgr)
    ed = edge_density(bgr)
    ws = whitespace_ratio(bgr)
    is_th = (face > 0) or (sk > 0.10 and ed < 0.04)
    return is_th, {
        "face_px": face,
        "skin": round(sk, 4),
        "edges": round(ed, 4),
        "white": round(ws, 4),
    }


def is_too_dim(bgr: np.ndarray) -> bool:
    """A near-black transition frame: almost no edges and almost no bright pixels."""
    ed = edge_density(bgr)
    ws = whitespace_ratio(bgr)
    return (ed < 0.005) and (ws < 0.01)


def slide_score(bgr: np.ndarray) -> float:
    """Higher = more 'rich' slide content. Prefers high edge density + brightness."""
    ed = edge_density(bgr)
    ws = whitespace_ratio(bgr)
    return ed * 100 + ws * 10  # weight edges heavily


# ---------------- main pipeline ----------------

def extract_window_frames(mp4: Path, mp4_center: float, window_mp4: float,
                          fps: float, tmp_dir: Path) -> list[tuple[float, Path]]:
    """Extract frames in [mp4_center - window, mp4_center + window] at the given fps.

    Returns list of (mp4_t, jpg_path) sorted by mp4_t.
    """
    start = max(0.0, mp4_center - window_mp4)
    duration = window_mp4 * 2
    pattern = tmp_dir / "frame_%04d.jpg"

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-i", str(mp4),
        "-t", f"{duration:.3f}",
        "-vf", f"fps={fps}",
        "-q:v", "3",
        str(pattern),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    frames = sorted(tmp_dir.glob("frame_*.jpg"))
    out = []
    for i, f in enumerate(frames):
        mp4_t = start + (i / fps)
        out.append((mp4_t, f))
    return out


def cluster_by_phash(items: list[tuple[float, Path, np.ndarray]],
                     hash_threshold: int = 6) -> list[list[int]]:
    """Group near-duplicate frames by perceptual hash. Returns list of index-lists."""
    hashes = []
    for _, _, bgr in items:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        hashes.append(imagehash.phash(pil))

    n = len(items)
    visited = [False] * n
    clusters = []
    for i in range(n):
        if visited[i]:
            continue
        cluster = [i]
        visited[i] = True
        for j in range(i + 1, n):
            if visited[j]:
                continue
            if hashes[i] - hashes[j] <= hash_threshold:
                cluster.append(j)
                visited[j] = True
        clusters.append(cluster)
    return clusters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mp4")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--targets", required=True,
                    help="Comma-separated MM:SS list in ORIGINAL video time")
    ap.add_argument("--speed", type=float, default=2.0,
                    help="Playback-speed ratio (mp4_t = original_t / speed)")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="MP4-time offset for original_t=0 (seconds)")
    ap.add_argument("--window", type=float, default=3.0,
                    help="Half-window in MP4 seconds around each target")
    ap.add_argument("--fps", type=float, default=4.0,
                    help="Sampling fps within each window (in MP4 time)")
    ap.add_argument("--out-dir", default="Input")
    ap.add_argument("--keep-talking-heads", action="store_true",
                    help="Don't filter out portrait/talking-head frames")
    args = ap.parse_args()

    mp4 = Path(args.mp4)
    if not mp4.exists():
        print(f"ERROR: MP4 not found: {mp4}", file=sys.stderr)
        sys.exit(2)

    targets_orig = [parse_mmss(t) for t in args.targets.split(",") if t.strip()]
    print(f"Targets ({len(targets_orig)} in original-video seconds):", flush=True)
    for t in targets_orig:
        print(f"  {fmt_mmss(t)} ({t:.1f}s) -> mp4 {fmt_mmss((t/args.speed)+args.offset)} ({(t/args.speed)+args.offset:.2f}s)")

    figs_dir = Path(args.out_dir) / f"{args.slug}_figs"
    figs_dir.mkdir(parents=True, exist_ok=True)

    # Wipe previous fig_*.jpg from this slug to avoid stale numbering — but keep
    # any non-fig files (manifests, etc.).
    for old in figs_dir.glob("fig_*.jpg"):
        old.unlink()

    manifest = {
        "mp4_path": str(mp4),
        "slug": args.slug,
        "speed": args.speed,
        "offset_mp4_seconds": args.offset,
        "window_mp4_seconds": args.window,
        "sample_fps_mp4": args.fps,
        "targets": [],
    }

    fig_counter = 0

    with tempfile.TemporaryDirectory(prefix="slide_extract_") as tmp:
        tmp_dir = Path(tmp)

        for ti, orig_t in enumerate(targets_orig, start=1):
            mp4_t = orig_t / args.speed + args.offset
            target_label = fmt_mmss(orig_t)
            print(f"\n=== target {ti}/{len(targets_orig)}: orig {target_label} -> mp4 {mp4_t:.2f}s ===", flush=True)

            # Wipe tmp between targets
            for f in tmp_dir.glob("frame_*.jpg"):
                f.unlink()

            try:
                frames = extract_window_frames(mp4, mp4_t, args.window, args.fps, tmp_dir)
            except subprocess.CalledProcessError as e:
                print(f"  ffmpeg failed: {e.stderr.decode(errors='replace')[:300]}", file=sys.stderr)
                continue

            # Read frames + score
            scored = []
            for mp4_ts, fp in frames:
                bgr = cv2.imread(str(fp))
                if bgr is None:
                    continue
                is_th, sig = is_talking_head(bgr)
                dim = is_too_dim(bgr)
                score = slide_score(bgr)
                drop = (is_th and not args.keep_talking_heads) or dim
                if is_th and not args.keep_talking_heads:
                    tag = "DROP-FACE" if sig["face_px"] else "DROP-TH"
                elif dim:
                    tag = "DROP-DIM"
                else:
                    tag = "kept"
                print(f"  [{tag:9s}] mp4 {mp4_ts:6.2f}s  face={sig['face_px']:>4d}px skin={sig['skin']:.3f} edges={sig['edges']:.3f} white={sig['white']:.3f} score={score:.2f}",
                      flush=True)
                if not drop:
                    scored.append((mp4_ts, fp, bgr, score, sig))

            if not scored:
                print(f"  (no slide-like frames in window — keeping single best from raw)", flush=True)
                # Fallback: pick the single richest frame ignoring talking-head filter
                fallback = []
                for mp4_ts, fp in frames:
                    bgr = cv2.imread(str(fp))
                    if bgr is None: continue
                    fallback.append((mp4_ts, fp, bgr, slide_score(bgr), {}))
                if fallback:
                    fallback.sort(key=lambda x: x[3], reverse=True)
                    scored = fallback[:1]

            # Cluster by perceptual hash, keep richest in each cluster.
            # Use a loose threshold so partial-reveal sequences group together
            # — within a cluster the highest-score frame wins, which naturally
            # picks the fully-revealed final slide.
            items_for_cluster = [(t, p, b) for (t, p, b, _, _) in scored]
            clusters = cluster_by_phash(items_for_cluster, hash_threshold=14)

            target_record = {
                "original_seconds": orig_t,
                "original_label": target_label,
                "mp4_seconds_center": mp4_t,
                "frames_sampled": len(frames),
                "frames_kept_after_filter": len(scored),
                "clusters": [],
            }

            for cluster in clusters:
                cluster_items = [scored[i] for i in cluster]
                # Pick richest (highest slide_score)
                cluster_items.sort(key=lambda x: x[3], reverse=True)
                best = cluster_items[0]
                mp4_ts_b, src_path, bgr, score, sig = best

                fig_counter += 1
                dst_name = f"fig_{fig_counter:02d}.jpg"
                dst_path = figs_dir / dst_name
                # Copy/transcode to JPEG (preserves resolution)
                shutil.copy(src_path, dst_path)

                approx_orig = (mp4_ts_b - args.offset) * args.speed
                target_record["clusters"].append({
                    "fig_filename": dst_name,
                    "mp4_seconds": round(mp4_ts_b, 2),
                    "approx_original_seconds": round(approx_orig, 2),
                    "approx_original_label": fmt_mmss(approx_orig),
                    "cluster_size": len(cluster),
                    "score": round(score, 3),
                    "skin": sig.get("skin"),
                    "edges": sig.get("edges"),
                    "white": sig.get("white"),
                })
                print(f"  -> SAVED {dst_name}  mp4={mp4_ts_b:.2f}s ~orig={fmt_mmss(approx_orig)} cluster_size={len(cluster)} score={score:.2f}", flush=True)

            manifest["targets"].append(target_record)

    manifest_path = Path(args.out_dir) / f"{args.slug}_frames_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== summary ===", flush=True)
    print(f"figures saved : {fig_counter}", flush=True)
    print(f"figures dir   : {figs_dir}", flush=True)
    print(f"manifest      : {manifest_path}", flush=True)


if __name__ == "__main__":
    main()

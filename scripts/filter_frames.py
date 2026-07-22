"""
Filter extracted video frames to find substantially unique screenshots.

Usage:
    python scripts/filter_frames.py <frames_dir> [--threshold N] [--crop-right PCT] [--interval SEC]

Arguments:
    frames_dir      Directory containing frame_NNNN.jpg files from ffmpeg extraction
    --threshold N   Perceptual hash distance threshold for dedup (default: 20).
                    Higher = more aggressive dedup (fewer frames kept).
                    Suggested: 12 for slow-changing content, 20 for fast coding sessions, 30+ for very similar frames.
    --crop-right PCT  Percentage of the right side to ignore (e.g., webcam sidebar). Default: 15.
                      Set to 0 if there's no sidebar to exclude.
    --interval SEC  Seconds between extracted frames (must match the ffmpeg fps= value). Default: 15.

Outputs:
    {frames_dir}_filtered/    Directory of deduplicated frames, renamed with timestamps
    {frames_dir}/../{slug}_frames_manifest.json    JSON manifest of kept frames

Dependencies:
    pip install Pillow imagehash

How it works:
    1. Computes a perceptual hash (pHash) on the main content region of each frame,
       excluding an optional right-side crop (e.g., a webcam sidebar in Zoom recordings).
    2. Walks frames in order. Keeps a frame only if its hash distance from the
       previously kept frame exceeds the threshold.
    3. Renames kept frames with human-readable timestamps (frame_003m15s_screen_007.jpg).
    4. Writes a JSON manifest mapping figure numbers to filenames and timestamps.
"""
import argparse
import os
import json
from PIL import Image
import imagehash


def analyze_frame(path, crop_right_pct):
    """Compute perceptual hash on the main content area, ignoring right sidebar."""
    img = Image.open(path)
    w, h = img.size
    if crop_right_pct > 0:
        content_region = img.crop((0, 0, int(w * (1 - crop_right_pct / 100)), h))
    else:
        content_region = img
    phash = imagehash.phash(content_region, hash_size=16)
    return phash


def main():
    parser = argparse.ArgumentParser(description="Filter video frames for unique screenshots")
    parser.add_argument("frames_dir", help="Directory containing frame_NNNN.jpg files")
    parser.add_argument("--threshold", type=int, default=20,
                        help="Hash distance threshold for dedup (default: 20)")
    parser.add_argument("--crop-right", type=float, default=15,
                        help="Percentage of right side to ignore (default: 15)")
    parser.add_argument("--interval", type=int, default=15,
                        help="Seconds between extracted frames (default: 15)")
    args = parser.parse_args()

    frames_dir = args.frames_dir.rstrip("/\\")
    output_dir = frames_dir + "_filtered"
    os.makedirs(output_dir, exist_ok=True)

    # Derive slug from directory name (e.g., Input/my_video_figs -> my_video)
    dir_basename = os.path.basename(frames_dir)
    slug = dir_basename.replace("_figs", "")
    parent_dir = os.path.dirname(frames_dir)

    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith('.jpg')])
    if not frames:
        print(f"No .jpg frames found in {frames_dir}")
        return

    print(f"Total frames to analyze: {len(frames)}")

    # Compute hashes
    frame_data = []
    for f in frames:
        path = os.path.join(frames_dir, f)
        phash = analyze_frame(path, args.crop_right)
        frame_data.append({"filename": f, "path": path, "phash": phash})

    # Filter: keep frames sufficiently different from the last kept frame
    kept = [frame_data[0]]  # always keep first frame
    for info in frame_data[1:]:
        dist = info["phash"] - kept[-1]["phash"]
        if dist >= args.threshold:
            kept.append(info)

    print(f"Frames after dedup (threshold={args.threshold}): {len(kept)}")

    # Save kept frames with timestamp-based names
    manifest = []
    for i, info in enumerate(kept):
        frame_num = int(info["filename"].replace("frame_", "").replace(".jpg", ""))
        total_seconds = (frame_num - 1) * args.interval
        mins = total_seconds // 60
        secs = total_seconds % 60

        new_name = f"frame_{mins:03d}m{secs:02d}s_screen_{i+1:03d}.jpg"
        src = os.path.join(frames_dir, info["filename"])
        dst = os.path.join(output_dir, new_name)

        img = Image.open(src)
        img.save(dst, quality=90)

        manifest.append({
            "figure_num": i + 1,
            "filename": new_name,
            "timestamp": f"{mins}:{secs:02d}",
            "total_seconds": total_seconds,
            "original_frame": info["filename"]
        })
        print(f"  Kept: {info['filename']} -> {new_name} ({mins}:{secs:02d})")

    manifest_path = os.path.join(parent_dir, f"{slug}_frames_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone. {len(kept)} unique frames saved to {output_dir}")
    print(f"Manifest saved to {manifest_path}")


if __name__ == "__main__":
    main()

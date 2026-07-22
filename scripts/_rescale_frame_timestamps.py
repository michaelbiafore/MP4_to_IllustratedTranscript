"""Rescale frame filenames + manifest from MP4-wall-time to real-video time.

The source MP4 was recorded at 3x against the real YouTube video, so every
captured frame's MP4 wall time corresponds to MP4_time * 3 in the real video.
Downstream tools (format-mp4, slidefy-mp4) expect timestamps to match the
transcript, which is already in real 1x time -- so we apply the same multiplier
here.

Usage:
    python scripts/_rescale_frame_timestamps.py <filtered_dir> <manifest_path>
        [--multiplier N]
"""
import argparse
import json
import re
from pathlib import Path

FRAME_RE = re.compile(r"^frame_(\d{3})m(\d{2})s_screen_(\d{3})\.jpg$")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("filtered_dir")
    p.add_argument("manifest_path")
    p.add_argument("--multiplier", type=int, default=3)
    args = p.parse_args()

    filtered = Path(args.filtered_dir)
    manifest_path = Path(args.manifest_path)
    manifest = json.loads(manifest_path.read_text())

    new_manifest = []
    rename_pairs = []
    for entry in manifest:
        m = FRAME_RE.match(entry["filename"])
        if not m:
            raise SystemExit(f"Unexpected filename: {entry['filename']}")
        mins_old, secs_old, screen = int(m.group(1)), int(m.group(2)), int(m.group(3))
        total_new = (mins_old * 60 + secs_old) * args.multiplier
        mins_new, secs_new = total_new // 60, total_new % 60
        new_name = f"frame_{mins_new:03d}m{secs_new:02d}s_screen_{screen:03d}.jpg"

        rename_pairs.append((entry["filename"], new_name))
        new_manifest.append({
            "figure_num": entry["figure_num"],
            "filename": new_name,
            "timestamp": f"{mins_new}:{secs_new:02d}",
            "total_seconds": total_new,
            "original_frame": entry["original_frame"],
            "mp4_wall_timestamp": entry["timestamp"],
        })

    # Two-pass rename via temp suffix to avoid collisions (though unlikely)
    for old, new in rename_pairs:
        src = filtered / old
        tmp = filtered / (old + ".tmp")
        if src.exists():
            src.rename(tmp)
    for old, new in rename_pairs:
        tmp = filtered / (old + ".tmp")
        dst = filtered / new
        if tmp.exists():
            tmp.rename(dst)

    manifest_path.write_text(json.dumps(new_manifest, indent=2))
    print(f"Renamed {len(rename_pairs)} files; manifest updated at {manifest_path}")
    print(f"First entry: {new_manifest[0]['filename']} @ {new_manifest[0]['timestamp']}")
    print(f"Last entry:  {new_manifest[-1]['filename']} @ {new_manifest[-1]['timestamp']}")


if __name__ == "__main__":
    main()

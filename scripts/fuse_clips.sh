#!/usr/bin/env bash
# fuse_clips.sh — Concatenate normalized MP4 clips into a single video
#
# Usage: ./scripts/fuse_clips.sh <clips_dir> <output.mp4>
# Example: ./scripts/fuse_clips.sh Input/courses/quantra_380/normalized Input/courses/quantra_380/merged/quantra_380_s01.mp4
#
# Clips must already be normalized to the same codec/resolution/framerate.

set -euo pipefail

CLIPS_DIR="${1:?Usage: $0 clips_dir output.mp4}"
OUTPUT="${2:?Usage: $0 clips_dir output.mp4}"

# Find ffmpeg
FFMPEG=$(which ffmpeg 2>/dev/null || true)
if [ -z "$FFMPEG" ]; then
    FFMPEG=$(.venv/Scripts/python.exe -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())" 2>/dev/null || true)
fi
if [ -z "$FFMPEG" ]; then
    echo "ERROR: ffmpeg not found. Install with: winget install Gyan.FFmpeg"
    exit 1
fi
echo "Using ffmpeg: $FFMPEG"

# Build sorted file list
FILELIST=$(mktemp)
for f in $(ls "$CLIPS_DIR"/*.mp4 | sort); do
    echo "file '$(cd "$CLIPS_DIR" && pwd)/$(basename "$f")'" >> "$FILELIST"
done

COUNT=$(wc -l < "$FILELIST")
echo "Concatenating $COUNT clips..."
cat "$FILELIST"
echo ""

mkdir -p "$(dirname "$OUTPUT")"

# Since clips are normalized to same format, use -c copy (no re-encoding)
"$FFMPEG" -hide_banner -loglevel warning \
    -f concat -safe 0 -i "$FILELIST" \
    -c copy \
    -y "$OUTPUT"

rm "$FILELIST"

echo "Output: $OUTPUT"
ls -lh "$OUTPUT" | awk '{print "Size:", $5}'

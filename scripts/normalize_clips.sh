#!/usr/bin/env bash
# normalize_clips.sh — Re-encode all MP4 clips in a directory to uniform format
#
# Usage: ./scripts/normalize_clips.sh <input_dir> <output_dir>
# Example: ./scripts/normalize_clips.sh Input/courses/quantra_380/raw Input/courses/quantra_380/normalized
#
# Settings: 720p, 30fps, H.264+AAC, CRF 20

set -euo pipefail

INPUT_DIR="${1:?Usage: $0 input_dir output_dir}"
OUTPUT_DIR="${2:?Usage: $0 input_dir output_dir}"

# Find ffmpeg — system PATH first, then imageio-ffmpeg bundled binary
FFMPEG=$(which ffmpeg 2>/dev/null || true)
if [ -z "$FFMPEG" ]; then
    FFMPEG=$(.venv/Scripts/python.exe -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())" 2>/dev/null || true)
fi
if [ -z "$FFMPEG" ]; then
    echo "ERROR: ffmpeg not found. Install with: winget install Gyan.FFmpeg"
    exit 1
fi
echo "Using ffmpeg: $FFMPEG"

mkdir -p "$OUTPUT_DIR"

count=0
total=$(ls "$INPUT_DIR"/*.mp4 2>/dev/null | wc -l)

if [ "$total" -eq 0 ]; then
    echo "No MP4 files found in $INPUT_DIR"
    exit 1
fi

echo "Normalizing $total clips to 720p/30fps/H.264..."
echo ""

for f in "$INPUT_DIR"/*.mp4; do
    count=$((count + 1))
    base=$(basename "$f")
    echo "[$count/$total] $base"

    "$FFMPEG" -hide_banner -loglevel warning \
        -i "$f" \
        -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2" \
        -r 30 \
        -c:v libx264 -crf 20 -preset medium \
        -c:a aac -b:a 128k -ar 44100 \
        -y "$OUTPUT_DIR/$base"
done

echo ""
echo "Normalized $count clips to $OUTPUT_DIR"

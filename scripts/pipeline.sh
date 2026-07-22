#!/bin/bash
# pipeline.sh - Run the full transcript-to-slides pipeline for a YouTube URL
# Usage: ./scripts/pipeline.sh <youtube_url>
#
# Pipeline: fetch transcript -> format markdown -> generate slides
# Each Claude step runs in its own context window (via claude -p)

set -euo pipefail

# Allow running from within an existing Claude Code session
unset CLAUDECODE 2>/dev/null || true

if [ $# -lt 1 ]; then
    echo "Usage: $0 <youtube_url>"
    echo "Example: $0 https://youtu.be/VIDEO_ID"
    exit 1
fi

URL="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Pipeline: $URL"
echo "=========================================="

# --- Step 1: Fetch transcript (Python script, no AI needed) ---
echo ""
echo ">>> Step 1: Fetching transcript..."
cd "$PROJECT_DIR"
FETCH_OUTPUT=$(uv run python scripts/fetch_transcript.py "$URL" 2>&1) || {
    echo "ERROR: Failed to fetch transcript"
    echo "$FETCH_OUTPUT"
    exit 1
}
echo "$FETCH_OUTPUT"

# Extract the output filename from the fetch script's output
RAW_FILE=$(echo "$FETCH_OUTPUT" | grep "Transcript saved to:" | sed 's/.*Transcript saved to: //')
if [ -z "$RAW_FILE" ]; then
    echo "ERROR: Could not determine raw transcript filename"
    exit 1
fi
RAW_BASENAME=$(basename "$RAW_FILE")
echo ">>> Raw transcript: $RAW_BASENAME"

# Derive expected output filenames
FORMATTED_BASENAME="${RAW_BASENAME/_RAW_TRANSCRIPT/_FORMATTED_TRANSCRIPT}"
SLIDES_BASENAME="${FORMATTED_BASENAME/_FORMATTED_TRANSCRIPT.md/_SLIDES.html}"

# --- Step 2: Format transcript (AI-powered, separate context) ---
echo ""
echo ">>> Step 2: Formatting transcript..."
cd "$PROJECT_DIR"
claude -p "/format-transcript $RAW_BASENAME" \
    --dangerously-skip-permissions \
    --model sonnet \
    --no-session-persistence

# Verify output was created
if [ ! -f "Output/$FORMATTED_BASENAME" ]; then
    echo "WARNING: Expected Output/$FORMATTED_BASENAME not found"
    # Try to find the actual output
    FORMATTED_FILE=$(ls -t Output/*_FORMATTED_TRANSCRIPT.md 2>/dev/null | head -1)
    if [ -n "$FORMATTED_FILE" ]; then
        FORMATTED_BASENAME=$(basename "$FORMATTED_FILE")
        SLIDES_BASENAME="${FORMATTED_BASENAME/_FORMATTED_TRANSCRIPT.md/_SLIDES.html}"
        echo ">>> Found formatted transcript: $FORMATTED_BASENAME"
    else
        echo "ERROR: No formatted transcript found"
        exit 1
    fi
fi
echo ">>> Formatted transcript: $FORMATTED_BASENAME"

# --- Step 3: Create slides (AI-powered, separate context) ---
echo ""
echo ">>> Step 3: Creating slides..."
cd "$PROJECT_DIR"
claude -p "/slidefy-transcript Output/$FORMATTED_BASENAME" \
    --dangerously-skip-permissions \
    --model sonnet \
    --no-session-persistence

# Verify output was created
if [ ! -f "Output/$SLIDES_BASENAME" ]; then
    echo "WARNING: Expected Output/$SLIDES_BASENAME not found"
    SLIDES_FILE=$(ls -t Output/*_SLIDES.html 2>/dev/null | head -1)
    if [ -n "$SLIDES_FILE" ]; then
        SLIDES_BASENAME=$(basename "$SLIDES_FILE")
        echo ">>> Found slides: $SLIDES_BASENAME"
    else
        echo "ERROR: No slides file found"
        exit 1
    fi
fi
echo ">>> Slides: $SLIDES_BASENAME"

echo ""
echo "=========================================="
echo "Pipeline complete!"
echo "  Raw:       Input/$RAW_BASENAME"
echo "  Formatted: Output/$FORMATTED_BASENAME"
echo "  Slides:    Output/$SLIDES_BASENAME"
echo "=========================================="

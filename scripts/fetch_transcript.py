#!/usr/bin/env python3
"""
Fetch YouTube transcript and save to Input/ directory.
Usage: python fetch_transcript.py <youtube_url>
"""

import sys
import re
import json
import urllib.request
import urllib.parse
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp


def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'  # bare video ID
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from: {url}")


def _get_title_via_oembed(url: str) -> str:
    """Fallback: fetch title via YouTube's public oEmbed endpoint.

    Works without a JavaScript runtime, unlike yt-dlp's newer extractor path.
    """
    oembed = "https://www.youtube.com/oembed?" + urllib.parse.urlencode({
        "url": url,
        "format": "json",
    })
    req = urllib.request.Request(oembed, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("title", "Untitled")


def get_video_title(url: str) -> str:
    """Get video title for filename generation.

    Tries yt-dlp first; on failure (e.g., no JS runtime available for YouTube's
    newer player protection) falls back to YouTube's oEmbed endpoint.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('title', 'Untitled')
    except Exception as e:
        print(f"  yt-dlp title fetch failed ({e.__class__.__name__}); falling back to oEmbed...")
        return _get_title_via_oembed(url)


def sanitize_filename(title: str) -> str:
    """Convert title to safe filename."""
    # Remove/replace invalid characters
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = re.sub(r'\s+', '_', safe)
    safe = safe[:80]  # Truncate long titles
    return safe


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"


def fetch_transcript(video_id: str) -> list:
    """Fetch transcript from YouTube."""
    ytt_api = YouTubeTranscriptApi()
    try:
        # Try English first
        transcript = ytt_api.fetch(video_id, languages=['en'])
        return list(transcript)
    except Exception:
        # Fall back to any available language
        transcript = ytt_api.fetch(video_id)
        return list(transcript)


def format_transcript(transcript: list) -> str:
    """Format transcript with timestamps."""
    lines = []
    for entry in transcript:
        timestamp = format_timestamp(entry.start)
        text = entry.text
        lines.append(f"{timestamp} {text}")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_transcript.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]

    print(f"Extracting video ID from: {url}")
    video_id = extract_video_id(url)
    print(f"Video ID: {video_id}")

    # Get title for filename
    print("Fetching video title...")
    title = get_video_title(url)
    print(f"Title: {title}")
    safe_title = sanitize_filename(title)

    # Fetch and format transcript
    print("Fetching transcript...")
    transcript = fetch_transcript(video_id)
    formatted = format_transcript(transcript)
    print(f"Retrieved {len(transcript)} transcript segments")

    # Ensure Input directory exists
    input_dir = Path("Input")
    input_dir.mkdir(exist_ok=True)

    # Write to Input/ directory
    output_path = input_dir / f"{safe_title}_RAW_TRANSCRIPT.md"
    output_path.write_text(formatted, encoding='utf-8')

    print(f"\nTranscript saved to: {output_path}")
    print(f"\nFirst 5 lines:")
    for line in formatted.split('\n')[:5]:
        print(f"  {line}")


if __name__ == "__main__":
    main()

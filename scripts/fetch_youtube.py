#!/usr/bin/env python3
"""
Fetch YouTube transcript and download video for frame extraction.

Phase 1 of the /fetch-youtube pipeline:
  - Fetches transcript via youtube-transcript-api
  - Downloads video via yt-dlp (for later frame extraction)
  - Saves raw transcript to Input/{slug}_RAW_TRANSCRIPT.md
  - Reports video path for Phase 2

Usage:
  python fetch_youtube.py <youtube_url>
  python fetch_youtube.py <youtube_url> --no-video   # transcript only, skip download
"""

import sys
import os
import re
import json
import subprocess
import shutil
import time
import random
import urllib.request
import urllib.parse
from pathlib import Path

# Fix Windows console encoding for Unicode video titles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

# ---------------------------------------------------------------------------
# Anti-throttle: realistic browser headers, delays, retry with backoff
# ---------------------------------------------------------------------------

_CHROME_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
]

# Pick one UA per invocation (session stickiness)
_SESSION_UA = random.choice(_CHROME_USER_AGENTS)

_BROWSER_HEADERS = {
    "User-Agent": _SESSION_UA,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Clients tried in order until one returns a downloadable format. The `android`
# client currently bypasses the n-challenge signature decryption that breaks
# the `default` (tv) client when yt-dlp's EJS solver lags behind YouTube's
# player. `default` is kept as a fallback for when upstream catches up.
# Other clients (ios, web_embedded, mweb) need a PO token to return real
# formats, so they're not useful without user intervention.
_YT_CLIENT_CASCADE = ["android", "default"]


def _throttle_delay(lo: float = 3.0, hi: float = 8.0, label: str = ""):
    """Sleep a random interval to look human. Prints status."""
    delay = random.uniform(lo, hi)
    if label:
        print(f"  (waiting {delay:.1f}s before {label}...)")
    time.sleep(delay)


def _retry_with_backoff(fn, description: str, max_retries: int = 5):
    """Call fn() with exponential backoff + jitter on failure.

    Backoff schedule (base 10s, 2x multiplier, ±30% jitter):
      attempt 1:  ~10s    attempt 2:  ~20s
      attempt 3:  ~40s    attempt 4:  ~80s
      attempt 5: ~160s  (cap at 300s)
    Total worst-case wait before final attempt: ~5 minutes.
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt == max_retries:
                break
            base_delay = min(10 * (2 ** attempt), 300)
            jitter = base_delay * random.uniform(-0.3, 0.3)
            wait = base_delay + jitter
            print(f"  WARNING: {description} failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
            print(f"  Retrying in {wait:.0f}s...")
            if attempt >= 2:
                print("  TIP: If retries keep failing, try switching your VPN server location for a fresh IP.")
            time.sleep(wait)
    raise last_exc


def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
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
    req = urllib.request.Request(oembed, headers={"User-Agent": _SESSION_UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("title", "Untitled")


def _ydl_base_opts(client: str) -> dict:
    """Base yt-dlp opts for a given player_client. `default` leaves it alone."""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': _BROWSER_HEADERS,
    }
    if client != "default":
        opts['extractor_args'] = {'youtube': {'player_client': [client]}}
    return opts


def get_video_title(url: str) -> str:
    """Get video title.

    Cascade: try each yt-dlp client in _YT_CLIENT_CASCADE; if all fail, fall
    back to YouTube's oEmbed endpoint (works without JS runtime).
    """
    for client in _YT_CLIENT_CASCADE:
        opts = _ydl_base_opts(client)
        opts['extract_flat'] = True
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('title', 'Untitled')
        except Exception as e:
            print(f"  yt-dlp title fetch via '{client}' client failed ({e.__class__.__name__}); trying next...")
    print("  All yt-dlp clients failed; falling back to oEmbed...")
    return _get_title_via_oembed(url)


def sanitize_filename(title: str) -> str:
    """Convert title to safe filename."""
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = re.sub(r'\s+', '_', safe)
    safe = safe[:80]
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
        transcript = ytt_api.fetch(video_id, languages=['en'])
        return list(transcript)
    except Exception:
        transcript = ytt_api.fetch(video_id)
        return list(transcript)


def format_transcript_text(transcript: list) -> str:
    """Format transcript with timestamps."""
    lines = []
    for entry in transcript:
        timestamp = format_timestamp(entry.start)
        text = entry.text
        lines.append(f"{timestamp} {text}")
    return "\n".join(lines)


def _find_ffmpeg() -> str | None:
    """Find ffmpeg binary — system PATH first, then imageio-ffmpeg."""
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def download_video(url: str, output_path: Path) -> Path:
    """Download video using yt-dlp. Returns path to downloaded file.

    Tries each client in _YT_CLIENT_CASCADE until one produces a downloadable
    file. The `android` client typically only offers a single combined 360p
    stream (format 18) — the `best[...]` format selector falls back to it
    correctly.
    """
    ffmpeg_path = _find_ffmpeg()

    # If ffmpeg is available, allow format merging; otherwise request single stream
    if ffmpeg_path:
        fmt = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
    else:
        fmt = 'best[height<=1080]'

    last_exc = None
    for client in _YT_CLIENT_CASCADE:
        ydl_opts = _ydl_base_opts(client)
        ydl_opts.update({
            'format': fmt,
            'outtmpl': str(output_path),
            'quiet': False,
            'no_warnings': False,
        })
        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = str(Path(ffmpeg_path).parent)
            ydl_opts['merge_output_format'] = 'mp4'

        try:
            print(f"  Attempting download via '{client}' client...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            break
        except Exception as e:
            last_exc = e
            print(f"  '{client}' client download failed ({e.__class__.__name__}); trying next...")
    else:
        raise last_exc

    # yt-dlp may add extension — find the actual file
    if output_path.exists():
        return output_path
    # Check for .mp4 variant
    mp4_path = output_path.with_suffix('.mp4')
    if mp4_path.exists():
        return mp4_path
    # Search for any file matching the stem
    for p in output_path.parent.glob(f"{output_path.stem}.*"):
        if p.suffix in ('.mp4', '.mkv', '.webm'):
            return p
    raise FileNotFoundError(f"Downloaded video not found at {output_path}")


def _print_high_res_instructions(slug: str, video_path: Path, video_url: str) -> None:
    """Print the screen-recording workflow for --high-res mode."""
    abs_target = str(video_path.resolve())
    print("\n" + "=" * 70)
    print("HIGH-RES MODE — manual screen-recording workflow required")
    print("=" * 70)
    print(f"""
yt-dlp's fallback path delivers 360p only. For videos where you need to
read spreadsheet cells, technical diagram labels, or other fine details,
capture the video at full browser resolution yourself and restore the
speed afterward.

STEP 1 — Set up the browser
  * Open {video_url} in Chrome or Edge.
  * Settings -> Quality -> 1080p (or highest available).
  * Press 'f' for fullscreen. Move mouse once so controls auto-hide.
  * Mute OS audio — the pipeline doesn't use sound.

STEP 2 — Speed up playback via DevTools (F12 -> Console)
      document.querySelector('video').playbackRate = 4
  Sweet spot: 2x-4x. Beyond 4x Chrome drops frames.
  Estimated recording time = video_duration / speedup.

STEP 3 — Record with EaseUS RecExperts (or any window recorder)
  * Region or Window mode targeting the fullscreen browser.
  * 1920x1080, 30 fps, H.264/MP4. Save as e.g. recording_raw.mp4.

STEP 4 — Restore normal speed and place the file
  Run the helper script (drops audio, verifies duration):
      uv run python scripts/restore_speed.py <recording_raw.mp4> \\
          --speedup 4 --slug "{slug}"
  This writes to: {abs_target}

STEP 5 — Continue the pipeline
  Tell Claude the video is ready. It will proceed with topic detection
  and frame extraction using the high-res MP4. No need to re-run this
  command.
""")
    print("=" * 70)


def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_youtube.py <youtube_url> [--no-video | --high-res]")
        sys.exit(1)

    url = sys.argv[1]
    skip_video = '--no-video' in sys.argv
    high_res = '--high-res' in sys.argv
    if skip_video and high_res:
        print("ERROR: --no-video and --high-res are mutually exclusive.")
        sys.exit(2)

    # Extract video ID
    print(f"Extracting video ID from: {url}")
    video_id = extract_video_id(url)
    print(f"Video ID: {video_id}")

    # Get title (with retry)
    print("Fetching video title...")
    title = _retry_with_backoff(lambda: get_video_title(url), "title fetch")
    print(f"Title: {title}")
    slug = sanitize_filename(title)

    # Ensure directories exist
    input_dir = Path("Input")
    input_dir.mkdir(exist_ok=True)

    # Throttle delay before transcript fetch — use the lighter delay whenever
    # we're not going to hit yt-dlp's download path (no-video and high-res).
    if skip_video or high_res:
        _throttle_delay(1, 3, "transcript fetch")
    else:
        _throttle_delay(3, 8, "transcript fetch")

    # Fetch transcript (with retry)
    print("Fetching transcript...")
    transcript = _retry_with_backoff(lambda: fetch_transcript(video_id), "transcript fetch")
    formatted = format_transcript_text(transcript)
    print(f"Retrieved {len(transcript)} transcript segments")

    # Save raw transcript
    raw_path = input_dir / f"{slug}_RAW_TRANSCRIPT.md"
    raw_path.write_text(formatted, encoding='utf-8')
    print(f"\nTranscript saved to: {raw_path}")

    # Show preview
    print(f"\nFirst 5 lines:")
    for line in formatted.split('\n')[:5]:
        print(f"  {line}")

    if skip_video:
        print("\n--no-video flag set, skipping video download.")
        print(f"\nSlug: {slug}")
        print(f"Video URL: {url}")
        print(f"Video ID: {video_id}")
        print("\nRun /format-transcript on the raw transcript to produce formatted output.")
        return

    if high_res:
        expected_video_path = input_dir / f"{slug}_video.mp4"
        _print_high_res_instructions(slug, expected_video_path, url)
        print(f"\n--- FETCH SUMMARY (high-res pause) ---")
        print(f"Slug: {slug}")
        print(f"Video URL: {url}")
        print(f"Video ID: {video_id}")
        print(f"Transcript: {raw_path}")
        print(f"Expected video path: {expected_video_path}")
        print(f"Segments: {len(transcript)}")
        return

    # Throttle delay before video download
    _throttle_delay(5, 12, "video download")

    # Download video (with retry)
    print("\nDownloading video for frame extraction...")
    video_path = input_dir / f"{slug}_video.mp4"
    try:
        actual_video_path = _retry_with_backoff(
            lambda: download_video(url, video_path), "video download"
        )
        print(f"Video saved to: {actual_video_path}")
    except Exception as e:
        print(f"\nWARNING: Video download failed after all retries: {e}")
        print("TIP: Try switching your VPN server location and re-running.")
        print("Transcript was saved successfully. Frame extraction will not be possible.")
        print("You can still use /format-transcript on the raw transcript.")
        actual_video_path = None

    # Output summary for the slash command to consume
    print(f"\n--- FETCH SUMMARY ---")
    print(f"Slug: {slug}")
    print(f"Video URL: {url}")
    print(f"Video ID: {video_id}")
    print(f"Transcript: {raw_path}")
    if actual_video_path:
        print(f"Video file: {actual_video_path}")
    else:
        print(f"Video file: NONE")
    print(f"Segments: {len(transcript)}")


if __name__ == "__main__":
    main()

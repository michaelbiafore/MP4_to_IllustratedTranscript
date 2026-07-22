#!/usr/bin/env python3
"""
Extract video frames at topic-change timestamps and inject figure references.

Phase 2 of the /fetch-youtube pipeline:
  - Reads a topics JSON file (produced by Claude's topic detection)
  - Extracts one frame per topic boundary using ffmpeg
  - Optionally extracts additional frames at user-specified timestamps
  - Injects ![Figure N: ...] references into the raw transcript

Usage:
  python extract_frames.py <video_path> <topics_json> <raw_transcript_path> [--extra-timestamps t1,t2,...]

The --extra-timestamps argument accepts a comma-separated list of M:SS timestamps
(e.g., 3:51,5:38,12:06) that will be captured in addition to topic-boundary frames.
"""

import sys
import json
import re
import subprocess
import shutil
from pathlib import Path

# Fix Windows console encoding for Unicode filenames
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def find_ffmpeg() -> str:
    """Find ffmpeg binary — system PATH first, then imageio-ffmpeg bundled binary."""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    print("ERROR: ffmpeg is not installed or not on PATH.")
    print("")
    print("Install ffmpeg using one of:")
    print("  uv add imageio-ffmpeg   (bundles ffmpeg automatically)")
    print("  winget install Gyan.FFmpeg")
    print("  scoop install ffmpeg")
    sys.exit(1)


def slugify(text: str) -> str:
    """Convert text to a safe filename fragment."""
    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', text.strip())
    safe = re.sub(r'_+', '_', safe)
    return safe[:40].strip('_')


def capture_time_to_filename(capture_time: str) -> str:
    """Convert HH:MM:SS or MM:SS to a filename-safe string like 12m34s."""
    parts = capture_time.split(':')
    if len(parts) == 3:
        h, m, s = parts
        total_min = int(h) * 60 + int(m)
        sec = int(float(s))
    elif len(parts) == 2:
        total_min = int(parts[0])
        sec = int(float(parts[1]))
    else:
        return capture_time.replace(':', '-').replace('.', '-')
    return f"{total_min:03d}m{sec:02d}s"


def extract_frame(ffmpeg_bin: str, video_path: str, capture_time: str, output_path: str) -> bool:
    """Extract a single frame from video at the given timestamp."""
    result = subprocess.run(
        [
            ffmpeg_bin, "-hide_banner", "-loglevel", "error",
            "-ss", capture_time,
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",
            "-y",
            output_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  WARNING: ffmpeg failed for {capture_time}: {result.stderr.strip()}")
        return False
    return True


def parse_timestamp_to_sec(ts: str) -> float:
    """Convert M:SS or MM:SS or HH:MM:SS to seconds."""
    parts = ts.strip().split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(ts)


def inject_figure_refs(raw_path: Path, topics: list, figs_dir_name: str,
                       extra_frames: list | None = None):
    """Insert ![Figure N: ...] references into the raw transcript.

    Handles both topic-boundary figures and extra-timestamp figures.
    extra_frames is a list of (time_sec, filename, label) tuples.
    """
    text = raw_path.read_text(encoding='utf-8')
    lines = text.split('\n')

    # Build list of (time_sec, figure_markdown) to insert
    insertions = []

    # Topic-boundary figures
    fig_num = 0
    for topic in topics:
        fname = topic.get('_frame_filename')
        if not fname:
            continue
        fig_num += 1
        fig_md = f"\n![Figure {fig_num}: {topic['topic']}]({figs_dir_name}/{fname})\n"
        insertions.append((topic['start_time_sec'], fig_md))

    # Extra-timestamp figures
    if extra_frames:
        for time_sec, fname, label in extra_frames:
            fig_num += 1
            fig_md = f"\n![Figure {fig_num}: {label}]({figs_dir_name}/{fname})\n"
            insertions.append((time_sec, fig_md))

    if not insertions:
        return

    # Parse each line's timestamp (MM:SS at start of line)
    def line_timestamp_sec(line: str) -> float | None:
        m = re.match(r'^(\d+):(\d{2})\s', line)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))
        return None

    # Insert figure refs — work backwards to preserve line indices
    for start_sec, fig_md in reversed(sorted(insertions, key=lambda x: x[0])):
        insert_after = None
        for idx, line in enumerate(lines):
            ts = line_timestamp_sec(line)
            if ts is not None and ts >= start_sec:
                insert_after = idx
                break
        if insert_after is not None:
            lines.insert(insert_after + 1, fig_md)
        else:
            # Append at end if timestamp not found
            lines.append(fig_md)

    raw_path.write_text('\n'.join(lines), encoding='utf-8')


def clean_slug(slug: str) -> str:
    """Remove non-ASCII characters (emoji etc.) from slug for output filenames."""
    cleaned = re.sub(r'[^\x00-\x7F]+', '', slug)
    cleaned = re.sub(r'_+', '_', cleaned).strip('_')
    return cleaned


def write_topics_file(topics: list, slug: str, video_url: str):
    """Write a TOPICS_*.md debug file to Output/ listing all detected topic boundaries."""
    output_dir = Path("Output")
    output_dir.mkdir(exist_ok=True)

    name = clean_slug(slug)
    output_path = output_dir / f"TOPICS_{name}.md"

    lines = [
        f"# Topic Boundaries: {name.replace('_', ' ')}",
        "",
        f"**Source:** {video_url}",
        f"**Topics detected:** {len(topics)}",
        "",
        "| # | Timestamp | Capture Time | Level | Topic |",
        "|---|-----------|--------------|-------|-------|",
    ]

    for i, t in enumerate(topics, 1):
        start = t.get('start_time_sec', 0)
        # Format start_time_sec as MM:SS
        mins, secs = divmod(int(start), 60)
        ts = f"{mins}:{secs:02d}"
        capture = t.get('capture_time', '')
        level = t.get('heading_level', 2)
        heading = 'H2' if level == 2 else 'H3'
        topic = t.get('topic', '')
        lines.append(f"| {i} | {ts} | {capture} | {heading} | {topic} |")

    lines.append("")
    output_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"Topics debug file written: {output_path}")


def main():
    if len(sys.argv) < 4:
        print("Usage: python extract_frames.py <video_path> <topics_json> <raw_transcript> [--extra-timestamps t1,t2,...]")
        sys.exit(1)

    # Parse --extra-timestamps if provided
    extra_timestamps_raw = []
    positional = []
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--extra-timestamps' and i + 1 < len(sys.argv):
            extra_timestamps_raw = [t.strip() for t in sys.argv[i + 1].split(',') if t.strip()]
            i += 2
        else:
            positional.append(sys.argv[i])
            i += 1

    if len(positional) < 3:
        print("Usage: python extract_frames.py <video_path> <topics_json> <raw_transcript> [--extra-timestamps t1,t2,...]")
        sys.exit(1)

    ffmpeg_bin = find_ffmpeg()
    print(f"Using ffmpeg: {ffmpeg_bin}")

    video_path = Path(positional[0])
    topics_json_path = Path(positional[1])
    raw_transcript_path = Path(positional[2])

    if not video_path.exists():
        print(f"ERROR: Video file not found: {video_path}")
        sys.exit(1)
    if not topics_json_path.exists():
        print(f"ERROR: Topics JSON not found: {topics_json_path}")
        sys.exit(1)
    if not raw_transcript_path.exists():
        print(f"ERROR: Raw transcript not found: {raw_transcript_path}")
        sys.exit(1)

    # Load topics
    data = json.loads(topics_json_path.read_text(encoding='utf-8'))
    topics = data.get('topics', [])
    slug = data.get('slug', video_path.stem.replace('_video', ''))

    if not topics and not extra_timestamps_raw:
        print("No topics found in JSON and no extra timestamps. Nothing to extract.")
        sys.exit(0)

    # Write topics debug file
    video_url = data.get('video_url', '')
    if topics:
        write_topics_file(topics, slug, video_url)

    # Create figures directory
    figs_dir = Path("Input") / f"{slug}_figs"
    figs_dir.mkdir(exist_ok=True)
    figs_dir_name = f"{slug}_figs"

    # --- Phase A: Extract topic-boundary frames ---
    extracted = 0
    if topics:
        print(f"Extracting {len(topics)} topic-boundary frames from {video_path.name}...")
        print(f"Output directory: {figs_dir}")
        print()

        for i, topic in enumerate(topics, 1):
            capture_time = topic.get('capture_time', '')
            topic_label = topic.get('topic', f'topic_{i}')

            if not capture_time:
                print(f"  [{i}] Skipping '{topic_label}' — no capture_time")
                continue

            time_slug = capture_time_to_filename(capture_time)
            topic_slug = slugify(topic_label)
            frame_filename = f"frame_{time_slug}_{topic_slug}.jpg"
            frame_path = figs_dir / frame_filename

            print(f"  [{i}] {capture_time} — {topic_label}")
            ok = extract_frame(ffmpeg_bin, str(video_path), capture_time, str(frame_path))
            if ok and frame_path.exists():
                topic['_frame_filename'] = frame_filename
                extracted += 1
                print(f"       -> {frame_path}")
            else:
                print(f"       -> FAILED")

        print(f"\nExtracted {extracted}/{len(topics)} topic-boundary frames.")

    # --- Phase B: Extract extra-timestamp frames ---
    extra_frames = []  # list of (time_sec, filename, label) for injection
    extra_extracted = 0
    if extra_timestamps_raw:
        print(f"\nExtracting {len(extra_timestamps_raw)} extra-timestamp frames...")
        print()

        for idx, ts in enumerate(extra_timestamps_raw, 1):
            time_sec = parse_timestamp_to_sec(ts)
            # Normalize to HH:MM:SS for ffmpeg
            h = int(time_sec // 3600)
            m = int((time_sec % 3600) // 60)
            s = int(time_sec % 60)
            capture_time_fmt = f"{h:02d}:{m:02d}:{s:02d}"

            time_slug = capture_time_to_filename(capture_time_fmt)
            frame_filename = f"frame_{time_slug}_extra_{idx:03d}.jpg"
            frame_path = figs_dir / frame_filename
            label = f"Screenshot at {ts}"

            print(f"  [extra {idx}] {capture_time_fmt} — {label}")
            ok = extract_frame(ffmpeg_bin, str(video_path), capture_time_fmt, str(frame_path))
            if ok and frame_path.exists():
                extra_frames.append((time_sec, frame_filename, label))
                extra_extracted += 1
                print(f"       -> {frame_path}")
            else:
                print(f"       -> FAILED")

        print(f"\nExtracted {extra_extracted}/{len(extra_timestamps_raw)} extra-timestamp frames.")

    # Inject figure references into raw transcript
    total = extracted + extra_extracted
    if total > 0:
        print(f"\nInjecting figure references into {raw_transcript_path.name}...")
        inject_figure_refs(raw_transcript_path, topics, figs_dir_name,
                           extra_frames=extra_frames if extra_frames else None)
        print("Done.")

    print(f"\n--- EXTRACTION SUMMARY ---")
    print(f"Topic-boundary frames: {extracted}")
    print(f"Extra-timestamp frames: {extra_extracted}")
    print(f"Total frames extracted: {total}")
    print(f"Figures directory: {figs_dir}")
    print(f"Transcript updated: {raw_transcript_path}")


if __name__ == "__main__":
    main()

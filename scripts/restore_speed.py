#!/usr/bin/env python3
"""
Restore original speed to a sped-up screen recording of a YouTube video and
place the result where the /fetch-youtube pipeline expects it.

Companion to `fetch_youtube.py --high-res`. The high-res workflow is:
  1. Play a YouTube video at 2x-4x via DevTools in Chrome/Edge.
  2. Screen-record the browser at 1080p with EaseUS or similar.
  3. Run this script with the recording and the speedup factor. It slows
     the video back to real time (so frame-extraction timestamps match
     the transcript) and writes it to `Input/{slug}_video.mp4`.

ffmpeg's `setpts=N*PTS` filter multiplies each frame's presentation
timestamp by N — recording at 4x means N=4 to restore normal speed.
Audio is dropped: the frame-extraction pipeline doesn't use it, and
slowing audio to 0.25x with `atempo` is lossy anyway.

Usage:
  python restore_speed.py <recording.mp4> --speedup 4 --slug "My_Video"
  python restore_speed.py <recording.mp4> --speedup 4 --output Input/custom_video.mp4
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _find_ffmpeg() -> str:
    """Locate ffmpeg — system PATH first, then imageio-ffmpeg fallback."""
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        print("ERROR: ffmpeg not found. Install ffmpeg or `uv pip install imageio-ffmpeg`.")
        sys.exit(1)


def _find_ffprobe(ffmpeg_path: str) -> str:
    """ffprobe usually sits next to ffmpeg."""
    system = shutil.which("ffprobe")
    if system:
        return system
    sibling = Path(ffmpeg_path).parent / "ffprobe.exe"
    if sibling.exists():
        return str(sibling)
    sibling = Path(ffmpeg_path).parent / "ffprobe"
    if sibling.exists():
        return str(sibling)
    print("WARNING: ffprobe not found — duration verification will be skipped.")
    return ""


def probe_duration(ffprobe: str, path: Path) -> float | None:
    """Return duration in seconds, or None if ffprobe unavailable or probe fails."""
    if not ffprobe:
        return None
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "json", str(path)],
            capture_output=True, text=True, check=True
        )
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception as e:
        print(f"  (ffprobe failed: {e})")
        return None


def fmt_duration(seconds: float) -> str:
    mins, secs = divmod(int(round(seconds)), 60)
    return f"{mins}:{secs:02d}"


def main():
    parser = argparse.ArgumentParser(
        description="Restore original speed to a sped-up screen recording."
    )
    parser.add_argument("recording", help="Path to the sped-up screen recording (MP4)")
    parser.add_argument("--speedup", type=float, required=True,
                        help="Playback rate used during recording (e.g., 4 for 4x)")
    parser.add_argument("--slug", help="Video slug — writes to Input/{slug}_video.mp4")
    parser.add_argument("--output", help="Explicit output path (overrides --slug)")
    parser.add_argument("--keep-audio", action="store_true",
                        help="Keep audio (slowed with atempo). Default: drop audio.")
    args = parser.parse_args()

    if args.speedup <= 0:
        print("ERROR: --speedup must be positive.")
        sys.exit(2)
    if not args.slug and not args.output:
        print("ERROR: provide --slug or --output.")
        sys.exit(2)

    recording = Path(args.recording)
    if not recording.exists():
        print(f"ERROR: recording not found: {recording}")
        sys.exit(2)

    if args.output:
        output = Path(args.output)
    else:
        output = Path("Input") / f"{args.slug}_video.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists():
        print(f"WARNING: {output} already exists and will be overwritten.")

    ffmpeg = _find_ffmpeg()
    ffprobe = _find_ffprobe(ffmpeg)

    # Report input duration
    in_dur = probe_duration(ffprobe, recording)
    if in_dur is not None:
        expected_out = in_dur * args.speedup
        print(f"Input:    {fmt_duration(in_dur)} ({in_dur:.1f}s)")
        print(f"Speedup:  {args.speedup}x")
        print(f"Expected output: ~{fmt_duration(expected_out)} ({expected_out:.1f}s)")

    # Build ffmpeg command.
    #   Video:  setpts=N*PTS stretches each frame's timestamp, slowing playback N-fold.
    #   Audio:  atempo=1/N slows audio to match. atempo supports 0.5-2.0 per call, so
    #           chain multiple for larger N. For N=4: atempo=0.5,atempo=0.5.
    cmd = [ffmpeg, "-y", "-i", str(recording),
           "-filter:v", f"setpts={args.speedup}*PTS"]
    if args.keep_audio:
        # Chain atempo filters to handle speedups > 2
        slow = 1.0 / args.speedup
        atempo_chain = []
        remaining = slow
        while remaining < 0.5:
            atempo_chain.append("atempo=0.5")
            remaining /= 0.5
        atempo_chain.append(f"atempo={remaining:.4f}")
        cmd += ["-filter:a", ",".join(atempo_chain)]
    else:
        cmd += ["-an"]
    cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "20", str(output)]

    print(f"\nRunning ffmpeg... (target: {output})")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: ffmpeg failed (exit {result.returncode}).")
        print(result.stderr[-2000:])
        sys.exit(result.returncode)

    # Verify output
    out_dur = probe_duration(ffprobe, output)
    if out_dur is not None and in_dur is not None:
        print(f"\nActual output: {fmt_duration(out_dur)} ({out_dur:.1f}s)")
        drift = abs(out_dur - (in_dur * args.speedup))
        if drift > 2.0:
            print(f"WARNING: duration drift {drift:.1f}s — check the speedup value matches what you actually recorded.")
        else:
            print(f"Duration matches expected (drift {drift:.2f}s). Good.")

    print(f"\nRestored video at: {output.resolve()}")
    print("\nNext: tell Claude the video is ready and it will continue with frame extraction.")


if __name__ == "__main__":
    main()

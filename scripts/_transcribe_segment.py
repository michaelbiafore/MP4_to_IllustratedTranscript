#!/usr/bin/env python3
"""
Transcribe a TIME SLICE of a screen-recording whose playback rate differs from 1x,
and emit timestamps on the SOURCE VIDEO's clock.

Why this exists (beyond scripts/_transcribe_slowed.py): a screen-capture of a web player
does not always run at one constant rate for its whole length. A recording may open with
the viewer scrubbing or fiddling with the speed control and only settle into a clean N x
some minutes in. Transcribing the whole file with a single `atempo` then garbles the messy
head and shifts every timestamp.

This script takes the slice you actually trust:

    content_seconds = offset + speedup * (recording_seconds - start)

  --start    where the trusted slice begins in the RECORDING (seconds)
  --speedup  the playback rate over that slice (2 = recorded at 2x)
  --offset   the SOURCE-VIDEO position, in seconds, that --start corresponds to

Audio is retimed to natural tempo with a pitch-preserving `atempo` chain before Whisper
(see scripts/_transcribe_slowed.py for why), then every emitted timestamp has --offset
added, so the transcript shares one clock with the source video and with frames extracted
using the same mapping.

Outputs (same shape as scripts/transcribe_mp4.py so the pipeline is unchanged):
  - Input/{slug}_RAW_TRANSCRIPT.txt   one segment per line, "[M:SS] text"
  - Input/{slug}_transcript.json      raw segments (start/end/text)

Usage:
  uv run python scripts/_transcribe_segment.py "<mp4>" --start 208 --speedup 2 --offset 393
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def parse_args():
    p = argparse.ArgumentParser(description="Transcribe a slice of a sped-up recording onto source-video time.")
    p.add_argument("mp4_path")
    p.add_argument("--start", type=float, default=0.0,
                   help="Start of the trusted slice, in RECORDING seconds (default 0).")
    p.add_argument("--end", type=float, default=None,
                   help="Optional end of the slice, in RECORDING seconds.")
    p.add_argument("--speedup", type=float, default=2.0,
                   help="Playback rate over the slice (default 2).")
    p.add_argument("--offset", type=float, default=0.0,
                   help="SOURCE-VIDEO seconds corresponding to --start (added to every timestamp).")
    p.add_argument("--model", default="large-v3-turbo")
    p.add_argument("--language", default="en", help="Spoken language; 'auto' to detect.")
    p.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--compute-type", default="auto")
    p.add_argument("--no-vad", action="store_true")
    p.add_argument("--out", default=None)
    p.add_argument("--tag", default="", help="Suffix for the output slug (e.g. 'head').")
    return p.parse_args()


def atempo_chain(factor: float) -> str:
    """atempo accepts 0.5..2.0 per instance; chain to reach an arbitrary factor."""
    parts, remaining = [], factor
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    parts.append(f"atempo={remaining:.6f}")
    return ",".join(parts)


def load_model(size, device, compute_type):
    from faster_whisper import WhisperModel
    if compute_type != "auto":
        attempts = [(device, compute_type)]
    elif device == "cpu":
        attempts = [("cpu", "int8")]
    else:
        attempts = [(device, "float16"), ("cpu", "int8")]
    last_err = None
    for dev, ct in attempts:
        try:
            return WhisperModel(size, device=dev, compute_type=ct), dev, ct
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"  (could not load device={dev} compute={ct}: {e}; trying next)", file=sys.stderr)
    raise SystemExit(f"Failed to load Whisper model '{size}': {last_err}")


def fmt_ts(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


def main():
    args = parse_args()
    src = Path(args.mp4_path)
    if not src.exists():
        raise SystemExit(f"MP4 not found: {src}")

    slug = src.stem.replace(" ", "_") + (f"_{args.tag}" if args.tag else "")
    input_dir = Path("Input")
    input_dir.mkdir(exist_ok=True)
    out_txt = Path(args.out) if args.out else input_dir / f"{slug}_RAW_TRANSCRIPT.txt"
    out_json = input_dir / f"{slug}_transcript.json"
    out_txt.parent.mkdir(parents=True, exist_ok=True)

    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    tmp_wav = Path(tempfile.gettempdir()) / f"{slug}_1x_16k.wav"
    af = atempo_chain(1.0 / args.speedup)

    cmd = [ffmpeg, "-nostdin", "-ss", str(args.start)]
    if args.end is not None:
        cmd += ["-to", str(args.end)]
    cmd += ["-i", str(src), "-vn", "-af", af, "-ac", "1", "-ar", "16000",
            "-f", "wav", "-y", str(tmp_wav), "-loglevel", "error"]
    span = f"rec {fmt_ts(args.start)}" + (f"-{fmt_ts(args.end)}" if args.end is not None else "-end")
    print(f"Slicing {span}, retiming {args.speedup}x -> 1x ({af}) ...", flush=True)
    subprocess.run(cmd, check=True)

    print(f"Loading model '{args.model}' (device={args.device}) ...", flush=True)
    model, dev, ct = load_model(args.model, args.device, args.compute_type)
    print(f"Model ready on device={dev} compute={ct}. Transcribing ...", flush=True)

    language = None if args.language == "auto" else args.language
    segments, info = model.transcribe(
        str(tmp_wav), language=language, vad_filter=not args.no_vad, beam_size=5,
    )

    off = args.offset
    lines, raw = [], []
    for seg in segments:
        text = seg.text.strip()
        s, e = seg.start + off, seg.end + off
        raw.append({"Start": fmt_ts(s), "End": fmt_ts(e), "start": s, "end": e, "Text": seg.text})
        if text:
            lines.append(f"[{fmt_ts(s)}] {text}")
        if len(raw) % 50 == 0:
            print(f"  ...{fmt_ts(e)} ({len(raw)} segments)", flush=True)

    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    if tmp_wav.exists():
        tmp_wav.unlink()

    words = sum(len(l.split()) for l in lines)
    last = raw[-1]["end"] if raw else off
    print(f"\nWrote {len(lines)} segments to {out_txt}")
    print(f"Source-video span covered: {fmt_ts(off)} -> {fmt_ts(last)}  (~{words} words)")
    print(f"Detected language: {getattr(info, 'language', args.language)} "
          f"(prob {getattr(info, 'language_probability', 0):.2f})")
    print(f"JSON: {out_json}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Transcribe a screen-recording that was captured at N-times playback speed.

EaseUS/OBS "record at 3x" produces an MP4 whose audio is 3x fast (chipmunk).
Whisper transcribes natural-tempo speech far better than sped-up speech, so this
helper first slows the audio back to 1x with ffmpeg's `atempo` (pitch-preserving),
then runs faster-whisper on the restored-tempo audio. Because the slowed audio is
literally real-content time, the emitted segment timestamps are already on the
real-content timeline (0..duration*speedup) with NO further rescaling — which is
exactly the convention the rest of this repo uses for 3x recordings (see
scripts/_convert_wizwhisp_3x_to_1x.py). Frames extracted from the MP4 at a 1-second
recording interval map to the same timeline when montage/curate are run with
--interval == speedup.

Outputs (identical shape to scripts/transcribe_mp4.py so the pipeline is unchanged):
  - Input/{slug}_RAW_TRANSCRIPT.txt   one segment per line, "[M:SS] text"  (real time)
  - Input/{slug}_transcript.json      raw segments (start/end/text)         (real time)

Usage:
  uv run python scripts/_transcribe_slowed.py "<mp4>" --speedup 3 --model large-v3-turbo --language en
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
    p = argparse.ArgumentParser(description="Slow a sped-up recording to 1x, then transcribe.")
    p.add_argument("mp4_path")
    p.add_argument("--speedup", type=float, default=3.0,
                   help="Playback rate used during recording (default 3).")
    p.add_argument("--model", default="large-v3-turbo")
    p.add_argument("--language", default="en", help="Spoken language; 'auto' to detect.")
    p.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--compute-type", default="auto")
    p.add_argument("--no-vad", action="store_true")
    p.add_argument("--out", default=None)
    return p.parse_args()


def atempo_chain(slow: float) -> str:
    """atempo accepts 0.5..2.0 per instance; chain to reach an arbitrary slow factor."""
    parts, remaining = [], slow
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
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

    slug = src.stem.replace(" ", "_")
    input_dir = Path("Input")
    input_dir.mkdir(exist_ok=True)
    out_txt = Path(args.out) if args.out else input_dir / f"{slug}_RAW_TRANSCRIPT.txt"
    out_json = input_dir / f"{slug}_transcript.json"
    out_txt.parent.mkdir(parents=True, exist_ok=True)

    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    tmp_wav = Path(tempfile.gettempdir()) / f"{slug}_1x_16k.wav"
    af = atempo_chain(1.0 / args.speedup)
    print(f"Slowing audio {args.speedup}x -> 1x ({af}) and extracting 16 kHz mono WAV ...", flush=True)
    subprocess.run(
        [ffmpeg, "-nostdin", "-i", str(src), "-vn", "-af", af, "-ac", "1", "-ar", "16000",
         "-f", "wav", "-y", str(tmp_wav), "-loglevel", "error"],
        check=True,
    )

    print(f"Loading model '{args.model}' (device={args.device}, compute={args.compute_type}) ...", flush=True)
    model, dev, ct = load_model(args.model, args.device, args.compute_type)
    print(f"Model ready on device={dev} compute={ct}. Transcribing restored-tempo audio ...", flush=True)

    language = None if args.language == "auto" else args.language
    segments, info = model.transcribe(
        str(tmp_wav), language=language, vad_filter=not args.no_vad, beam_size=5,
    )

    lines, raw = [], []
    for seg in segments:
        text = seg.text.strip()
        raw.append({"Start": fmt_ts(seg.start), "End": fmt_ts(seg.end),
                    "start": seg.start, "end": seg.end, "Text": seg.text})
        if text:
            lines.append(f"[{fmt_ts(seg.start)}] {text}")
        if len(raw) % 50 == 0:
            print(f"  ...{fmt_ts(seg.end)} ({len(raw)} segments)", flush=True)

    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    if tmp_wav.exists():
        tmp_wav.unlink()

    words = sum(len(l.split()) for l in lines)
    dur = info.duration if info and getattr(info, "duration", None) else (raw[-1]["end"] if raw else 0)
    print(f"\nWrote {len(lines)} segments to {out_txt}")
    print(f"Detected language: {getattr(info, 'language', args.language)} "
          f"(prob {getattr(info, 'language_probability', 0):.2f})")
    print(f"Real-content duration ~{int(dur // 60)}m{int(dur % 60):02d}s, ~{words} words, "
          f"model={args.model}, device={dev}, speedup={args.speedup}x")
    print(f"JSON: {out_json}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Transcribe a local (or network) MP4 into a timestamped transcript, headlessly.

This is the auto-transcription front-end for the /MP4+FasterWhisp command. It
reproduces the accuracy of a WizWhisp "Large" run (same underlying Whisper
large-v3-turbo weights + Silero VAD) but needs no GUI, no purchased app, and no
specific GPU: it uses faster-whisper with device auto-detection (CUDA if present,
otherwise CPU int8) and downloads the model from Hugging Face on first run.

Output matches scripts/_export_wizwhisp.py so the rest of the MP4+WizWhisp
pipeline consumes it unchanged:
  - Input/{slug}_RAW_TRANSCRIPT.txt   one segment per line, "[M:SS] text"
  - Input/{slug}_transcript.json      raw segments (start/end/text) for tooling

Usage:
  uv run python scripts/transcribe_mp4.py "<mp4_path>"
  uv run python scripts/transcribe_mp4.py "\\\\NAS\\share\\talk.mp4" --model large-v3
  uv run python scripts/transcribe_mp4.py rec.mp4 --language en --device cpu --out Input/foo_RAW_TRANSCRIPT.txt
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Hugging Face's newer "Xet" transfer protocol (cas-bridge.xethub.hf.co) is blocked by many
# corporate/consumer firewalls, which shows up as a model download that stalls at 0 bytes while
# the small config files still succeed. Default to the classic LFS CDN, which is far more
# universally reachable. Set HF_HUB_DISABLE_XET=0 in your environment to re-enable Xet.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def parse_args():
    p = argparse.ArgumentParser(description="Headless MP4 -> timestamped transcript (faster-whisper).")
    p.add_argument("mp4_path", help="Path to the MP4 (local drive or UNC/network path).")
    p.add_argument("--model", default="large-v3-turbo",
                   help="Whisper model. Default: large-v3-turbo (what WizWhisp uses). "
                        "Use large-v3 for max accuracy, or small/medium for speed.")
    p.add_argument("--language", default="en",
                   help="Spoken language code (default: en). Pass 'auto' to auto-detect.")
    p.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"],
                   help="Compute device. Default auto: CUDA if available, else CPU.")
    p.add_argument("--compute-type", default="auto",
                   help="ctranslate2 compute type (e.g. float16, int8_float16, int8). "
                        "Default auto: float16 on GPU, int8 on CPU.")
    p.add_argument("--no-vad", action="store_true",
                   help="Disable Silero VAD filtering (WizWhisp keeps VAD on).")
    p.add_argument("--out", default=None,
                   help="Output transcript path. Default: Input/{slug}_RAW_TRANSCRIPT.txt")
    p.add_argument("--copy-local", action="store_true",
                   help="Copy the source to a local temp file before transcribing "
                        "(automatic for UNC \\\\ paths).")
    return p.parse_args()


def load_model(size: str, device: str, compute_type: str):
    """Load a WhisperModel, degrading gracefully to CPU/int8 for portability."""
    from faster_whisper import WhisperModel

    if compute_type != "auto":
        attempts = [(device, compute_type)]
    elif device == "cpu":
        attempts = [("cpu", "int8")]
    else:  # auto or cuda: try GPU first, then fall back to CPU
        attempts = [(device, "float16"), ("cpu", "int8")]

    last_err = None
    for dev, ct in attempts:
        try:
            model = WhisperModel(size, device=dev, compute_type=ct)
            return model, dev, ct
        except Exception as e:  # noqa: BLE001 - portability fallback is intentional
            last_err = e
            print(f"  (could not load on device={dev} compute_type={ct}: {e}; trying next)",
                  file=sys.stderr)
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

    # Decode audio to a clean 16 kHz mono WAV with ffmpeg BEFORE transcribing. Passing the raw
    # MP4 straight to faster-whisper lets its internal PyAV decoder choke on quirky containers
    # (e.g. EaseUS/OBS recordings whose AAC track uses "gain control", which PyAV silently
    # truncates mid-file). The bundled ffmpeg decodes the full stream and resamples cleanly, and
    # it reads UNC/network paths directly, so this also removes the need to pre-copy the source.
    import imageio_ffmpeg
    tmp_wav = Path(tempfile.gettempdir()) / f"{slug}_16k.wav"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"Extracting audio to {tmp_wav} (16 kHz mono) via ffmpeg ...", flush=True)
    subprocess.run(
        [ffmpeg, "-nostdin", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000",
         "-f", "wav", "-y", str(tmp_wav), "-loglevel", "error"],
        check=True,
    )
    audio_path = str(tmp_wav)

    print(f"Loading model '{args.model}' (device={args.device}, compute={args.compute_type}) ...",
          flush=True)
    model, dev, ct = load_model(args.model, args.device, args.compute_type)
    print(f"Model ready on device={dev} compute_type={ct}. Transcribing {src.name} ...", flush=True)

    language = None if args.language == "auto" else args.language
    segments, info = model.transcribe(
        audio_path,
        language=language,
        vad_filter=not args.no_vad,
        beam_size=5,
    )

    lines = []
    raw = []
    for seg in segments:  # generator: consuming it runs the transcription
        text = seg.text.strip()
        raw.append({"Start": fmt_ts(seg.start), "End": fmt_ts(seg.end),
                    "start": seg.start, "end": seg.end, "Text": seg.text})
        if text:
            lines.append(f"[{fmt_ts(seg.start)}] {text}")
        # progress heartbeat every ~2 min of audio
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
    print(f"Duration ~{int(dur // 60)}m{int(dur % 60):02d}s, ~{words} words, "
          f"model={args.model}, device={dev}")
    print(f"JSON: {out_json}")


if __name__ == "__main__":
    main()

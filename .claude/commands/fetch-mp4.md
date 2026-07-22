# Fetch MP4 — Extract Transcript and Screenshots from a Local Video

Extract audio, transcribe with Whisper, capture frames, and deduplicate screenshots from a local MP4 file (screen recording, Zoom call, presentation capture, etc.).

**Arguments**: $ARGUMENTS

## Argument Parsing

Parse the arguments as: `<mp4_path> [--interval SEC] [--threshold N] [--crop-right PCT] [--whisper-model MODEL]`

- **mp4_path** (required): Absolute or relative path to the MP4 file
- **--interval** (optional): Seconds between frame captures (default: 15). Lower = more frames to analyze. Suggested: 10 for fast-paced content, 15 for normal, 30 for slow presentations.
- **--threshold** (optional): Perceptual hash dedup threshold (default: 20). Higher = more aggressive dedup. Suggested: 12 for slow content, 20 for coding sessions, 30 for mostly static slides.
- **--crop-right** (optional): Percentage of right side to ignore for dedup (default: 15). Use 15 for Zoom recordings with webcam sidebar, 0 for clean screen recordings.
- **--whisper-model** (optional): Whisper model size (default: base). Options: tiny, base, small, medium, large.

Examples:
```
/fetch-mp4 "C:/Users/me/Videos/recording.mp4"
/fetch-mp4 "C:/Users/me/Videos/zoom_call.mp4" --interval 10 --threshold 12
/fetch-mp4 recording.mp4 --crop-right 0 --whisper-model small
```

## Instructions

### Phase 0: Resolve paths and prerequisites

1. **Resolve the MP4 path**: If relative, search common locations (`Input/`, current directory, user's Videos folder).

2. **Derive the slug** from the MP4 filename (without extension). Replace spaces with underscores.

3. **Locate ffmpeg**: Check these locations in order:
   - `ffmpeg` on PATH
   - `/c/Users/*/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe` (Windows/WinGet)
   - `/c/ProgramData/chocolatey/bin/ffmpeg.exe` (Windows/Chocolatey)

   If not found, install via `winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements` and locate the binary in the WinGet packages folder. **Important**: The newly installed binary may not be on PATH in the current shell — find it by searching `find "/c/Users/$USER/AppData/Local/Microsoft/WinGet/Packages" -name "ffmpeg.exe"`.

4. **Verify Python dependencies**:
   ```bash
   .venv/Scripts/python.exe -c "import whisper; import imagehash; import PIL; print('OK')"
   ```
   If any are missing, install them:
   ```bash
   .venv/Scripts/pip3.exe install openai-whisper opencv-python-headless imagehash
   ```
   **Note**: Whisper requires ffmpeg on PATH to load audio files. If using a non-PATH ffmpeg, set the PATH before running Python:
   ```bash
   export PATH="/path/to/ffmpeg/bin:$PATH"
   ```

### Phase 1: Get video metadata

5. **Probe the video**:
   ```bash
   "$FFPROBE" -v quiet -print_format json -show_format -show_streams "$MP4_PATH"
   ```
   Extract and report: duration, resolution, codec. This informs the frame extraction interval.

### Phase 2: Extract audio and transcribe

6. **Extract audio** as 16kHz mono WAV (optimal for Whisper):
   ```bash
   "$FFMPEG" -i "$MP4_PATH" -vn -acodec pcm_s16le -ar 16000 -ac 1 "Input/{slug}_audio.wav" -y
   ```

7. **Transcribe with Whisper**:
   ```python
   export PATH="/path/to/ffmpeg/bin:$PATH"
   .venv/Scripts/python.exe -c "
   import whisper, json
   model = whisper.load_model('MODEL')
   result = model.transcribe('Input/{slug}_audio.wav', language='en', verbose=False)

   with open('Input/{slug}_transcript.json', 'w') as f:
       json.dump(result, f, indent=2)

   with open('Input/{slug}_RAW_TRANSCRIPT.txt', 'w') as f:
       for seg in result['segments']:
           start = seg['start']
           mins = int(start // 60)
           secs = int(start % 60)
           f.write(f'[{mins}:{secs:02d}] {seg[\"text\"].strip()}\n')

   print(f'Done. {len(result[\"segments\"])} segments')
   "
   ```
   **Important**: Whisper on CPU is slow (~1/5 real-time for base model). For a 43-minute video, expect ~6 minutes. Use `timeout` of 600000ms.

### Phase 3: Extract and deduplicate frames

8. **Extract raw frames** at the specified interval:
   ```bash
   mkdir -p "Input/{slug}_figs"
   "$FFMPEG" -i "$MP4_PATH" -vf "fps=1/INTERVAL" -q:v 2 "Input/{slug}_figs/frame_%04d.jpg" -y
   ```
   Frames are extracted at native resolution to preserve text readability in screenshots.

9. **Run the dedup filter**:
   ```bash
   .venv/Scripts/python.exe scripts/filter_frames.py "Input/{slug}_figs" \
       --threshold THRESHOLD --crop-right CROP_RIGHT --interval INTERVAL
   ```
   This produces:
   - `Input/{slug}_figs_filtered/` — deduplicated frames with timestamp-based names
   - `Input/{slug}_frames_manifest.json` — JSON manifest of kept frames

### Phase 4: Review filtered frames

10. **Report initial results** and let Claude visually review a sample of the filtered frames (read 5-6 evenly spaced frames using the Read tool) to understand what the video contains. This informs the topic detection in the format step.

### Phase 5: Cleanup

11. **Ask the user** if they want to:
    - Delete the WAV audio file (`Input/{slug}_audio.wav`) — usually safe to delete
    - Delete the raw unfiltered frames (`Input/{slug}_figs/`) — safe if filtered set looks good
    - Keep the transcript JSON (`Input/{slug}_transcript.json`) — useful for programmatic access

### Report results

12. **Report**:
    - Video duration and resolution
    - Transcript: path, segment count, word count estimate
    - Frames: total extracted → kept after dedup
    - Remind the user to run:
      - `/format-mp4 {slug}` to create a formatted transcript with embedded screenshots
      - `/slidefy-mp4 Output/Formatted/{slug}_FORMATTED_TRANSCRIPT.md [N]` to create slides

## Error Handling

- If ffmpeg is not found and cannot be installed: report error with manual install instructions
- If Whisper fails with "FileNotFoundError": ffmpeg is not on PATH — set PATH before running Python
- If Whisper runs out of memory: suggest using `--whisper-model tiny` or chunking the audio
- If the MP4 has no audio stream: skip transcription, report error, still extract frames
- If frame extraction produces 0 frames: check video codec compatibility, try without scale filter
- If dedup produces 0 frames: lower the threshold (e.g., `--threshold 8`)

## Example Usage

```
/fetch-mp4 "C:/Users/biafo/Videos/EaseUS RecExperts/20260409_204007.mp4"
/fetch-mp4 "C:/Users/biafo/Videos/zoom_recording.mp4" --interval 10 --crop-right 15
/fetch-mp4 Input/presentation.mp4 --crop-right 0 --threshold 30
```

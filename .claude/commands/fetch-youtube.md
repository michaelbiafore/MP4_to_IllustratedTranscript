# Fetch YouTube Video with Screenshots

Download a YouTube transcript AND capture screenshots at topic-change timestamps.

**Arguments**: $ARGUMENTS

## Argument Parsing

Parse the arguments as: `<youtube_url> [--no-video | --high-res] [--offset <seconds>] [--timestamps t1,t2,...]`

- **youtube_url** (required): The YouTube URL to fetch
- **--no-video** (optional): Transcript-only mode — skip video download and frame extraction. Use this for talking-head videos where there are no informative screenshots to capture. The script will fetch the transcript and exit. The user should then run `/format-transcript` on the raw transcript.
- **--high-res** (optional): For videos containing **fine-grained visual detail** (spreadsheets where cells must be readable, technical diagrams with small labels, dense data tables, code screenshots). yt-dlp's current fallback client only returns 360p; this flag switches to a manual screen-recording workflow that captures at full browser resolution (1080p+). See "High-Res Workflow" below. Mutually exclusive with `--no-video`.
- **--offset** (optional): Number of seconds before each topic change to capture the screenshot frame. Default: `13`. For example, `--offset 2` captures the frame 2 seconds before each detected topic boundary. Ignored if `--no-video` is set.
- **--timestamps** (optional): Comma-separated list of exact timestamps in `M:SS` format (e.g., `3:51,5:38,12:06`) that MUST be captured as additional screenshots, regardless of whether they overlap with topic-boundary timestamps. These are passed through to `extract_frames.py` as `--extra-timestamps`. Ignored if `--no-video` is set.

Examples:
```
/fetch-youtube https://youtu.be/uVZMc-i5EEs
/fetch-youtube https://youtu.be/uVZMc-i5EEs --no-video
/fetch-youtube https://youtu.be/uVZMc-i5EEs --high-res
/fetch-youtube https://youtu.be/uVZMc-i5EEs --offset 2
/fetch-youtube https://youtu.be/uVZMc-i5EEs --timestamps 3:51,5:38,12:06
/fetch-youtube https://youtu.be/uVZMc-i5EEs --offset 5 --timestamps 3:51,5:38,12:06,22:07
```

Store the parsed offset value and timestamps list for use in Phase 2 and Phase 3.

## Instructions

### Phase 1: Fetch transcript and download video

1. **Run the fetch script**, passing through the `--no-video` or `--high-res` flag if given:
   ```bash
   uv run python scripts/fetch_youtube.py "<youtube_url>"
   uv run python scripts/fetch_youtube.py "<youtube_url>" --no-video
   uv run python scripts/fetch_youtube.py "<youtube_url>" --high-res
   ```
   This downloads the transcript to `Input/{slug}_RAW_TRANSCRIPT.md`. In the default mode it also downloads the video to `Input/{slug}_video.mp4`.

2. **If `--no-video` was passed**, the script already skipped the download. Skip directly to "Report results" — do not run Phases 2, 2b, 3, or 4.

3. **If `--high-res` was passed**, the script skipped the yt-dlp download and printed screen-recording instructions. Follow the "High-Res Workflow" section below before proceeding to Phase 2.

4. **If the video download fails**, report the error but continue — the transcript is still usable with `/format-transcript`. Skip to the "Report results" step.

### Phase 1b: High-Res Workflow (only when `--high-res` was passed)

The script has fetched the transcript and stopped. The user now produces a high-resolution MP4 manually:

1. **Wait for the user to confirm** the recording is in place. Do NOT proceed to Phase 2 until they say so.

2. **User-side steps** (already printed by the script; included here so Claude can help if asked):
   - Play the YouTube URL at 2×–4× in Chrome/Edge (DevTools Console: `document.querySelector('video').playbackRate = 4`).
   - Record the browser window with EaseUS RecExperts (or any window recorder) at 1080p.
   - Run the helper to slow it back to real time and place it at the expected path:
     ```bash
     uv run python scripts/restore_speed.py <recording_raw.mp4> --speedup <N> --slug "<slug>"
     ```
     The `restore_speed.py` script uses ffmpeg's `setpts` filter, drops audio, and verifies the output duration matches what the speedup implies.

3. **Verify the target file exists** before proceeding:
   ```bash
   ls -la "Input/{slug}_video.mp4"
   ```
   If it's missing, ask the user whether they've completed the restore step.

4. **Then proceed to Phase 2** exactly as in the default flow. All downstream phases are identical — the extracted frames will be at the native 1080p resolution rather than 360p.

### Phase 2: Detect topic changes

3. **Read the raw transcript** that was saved to `Input/`.

4. **Analyze the transcript for semantic topic changes.** Detect where the subject shifts meaningfully — not every speaker turn, but real topic boundaries (the same boundaries that would become H2/H3 headings in a formatted transcript).

5. **Write a topics JSON file** to `Input/{slug}_topics.json` with this exact schema:

```json
{
  "video_url": "https://youtu.be/VIDEO_ID",
  "slug": "{slug}",
  "topics": [
    {
      "topic": "Short topic label",
      "heading_level": 2,
      "start_time_sec": 0.0,
      "capture_time": "00:00:02"
    },
    {
      "topic": "Next topic",
      "heading_level": 2,
      "start_time_sec": 312.0,
      "capture_time": "00:05:11"
    }
  ]
}
```

Rules for topic detection:
- `start_time_sec`: the transcript timestamp (in seconds) where the topic begins
- `capture_time`: format as `HH:MM:SS`, set to `max(0, start_time - OFFSET)` seconds where OFFSET is the parsed `--offset` value (default 13.0) — this biases earlier to capture the visual context before the speaker transitions topics
- `heading_level`: 2 for major topics, 3 for subtopics
- Include **all** topic boundaries you would use for H2/H3 headings
- The first topic should start at or near 0:00

### Phase 2b: Capture charts and graphs (not just talking heads)

Most YouTube presenters spend the majority of screen time as a talking head. Charts, graphs, maps, headlines, and other visual assets appear only briefly — typically while the speaker is citing a specific statistic. The goal of this phase is to **maximize the yield of visually interesting frames** rather than capturing dozens of identical head-and-torso shots.

**Offset strategy:** Use `--offset 0` (or a very small value like 2) when the video is a data-heavy explainer. Charts appear DURING the discussion of a statistic, not 13 seconds before the next topic. The default offset of 13 is designed to catch the tail end of a previous topic's visual; for chart-hunting, you want to capture the moment the speaker is actively referencing data.

**Generating extra timestamps for chart-likely moments:** After reading the transcript, scan for these patterns and add their timestamps as `--extra-timestamps`:

1. **Specific numbers being cited** — When the transcript says "89% of wireless subscribers" or "$661,000" or "ranking of 71st", the speaker is very likely showing a chart, table, or infographic at that moment. Target the timestamp 2–5 seconds after the number first appears in the transcript.

2. **Source attributions** — Mentions of publications or institutions ("The Economist", "Statistics Canada", "Bloomberg", "The Globe and Mail", "Fraser Institute", "Financial Times") often correspond to showing that source's chart or headline on screen. Target the timestamp where the source name appears.

3. **Comparative/ranking language** — Phrases like "compared to", "ranked Nth", "fallen from X to Y", "gap has widened" usually accompany a visual comparison (bar chart, line graph, map). Target these moments.

4. **Dense data clusters** — When multiple numbers appear within a 10–20 second span (e.g., listing province-by-province rankings, or year-over-year price changes), there is almost certainly a data table or chart on screen. Target the midpoint of the cluster.

5. **Transition phrases that introduce visuals** — "If you look at the data", "this chart shows", "as you can see" are explicit signals. Target a few seconds after these phrases.

**Practical workflow:**
- After writing the topics JSON (Phase 2), do a second pass through the transcript looking for the patterns above.
- Collect timestamps for each chart-likely moment.
- Deduplicate: if an extra timestamp is within 5 seconds of an existing topic-boundary capture_time, skip it (the topic boundary frame will already capture it).
- Pass the collected timestamps as `--extra-timestamps` to `extract_frames.py`.
- Aim for roughly 1 extra timestamp per 1–2 minutes of video in data-heavy content. A 30-minute economics video might yield 15–25 extra timestamps.

### Phase 3: Extract frames

6. **Run the frame extraction script**:
   ```bash
   uv run python scripts/extract_frames.py "Input/{slug}_video.mp4" "Input/{slug}_topics.json" "Input/{slug}_RAW_TRANSCRIPT.md"
   ```
   If `--timestamps` was provided, append it as `--extra-timestamps`:
   ```bash
   uv run python scripts/extract_frames.py "Input/{slug}_video.mp4" "Input/{slug}_topics.json" "Input/{slug}_RAW_TRANSCRIPT.md" --extra-timestamps 3:51,5:38,12:06
   ```
   This extracts one screenshot per topic boundary PLUS one per extra timestamp, and injects `![Figure N: ...]` references into the raw transcript. Extra-timestamp frames are named `frame_XXXmYYs_extra_NNN.jpg`.

### Phase 4: Cleanup (optional)

7. **Ask the user** if they want to keep or delete the video file (`Input/{slug}_video.mp4`), since it can be large (hundreds of MB). Default recommendation is to delete it.

### Report results

8. **Report**:
   - Transcript path and line count
   - Number of topic boundaries detected
   - Number of screenshots captured (and their directory)
   - Remind the user they can run:
     - `/format-youtube {slug}_RAW_TRANSCRIPT.md` to create a formatted transcript with embedded figures
     - `/slidefy-youtube Output/Formatted/{slug}_FORMATTED_TRANSCRIPT.md` to create slides with screenshots

## Error Handling

- If the video has no transcript: report to the user, stop
- If the URL is invalid: show valid format examples
- If ffmpeg is not installed: the extract_frames.py script will print install instructions
- If video download fails: still save transcript, skip frame extraction, suggest using `/format-transcript` instead
- If some frames fail to extract: continue with the rest, report which ones failed

## Anti-Throttling

The `fetch_youtube.py` script includes built-in anti-throttle measures:

- **Randomized delays** between API calls (3-8s for video mode, 1-3s for transcript-only)
- **Realistic Chrome browser headers** (User-Agent, Accept-Language) — one UA per session
- **Retry with exponential backoff** on failures (5 retries, up to ~5 min wait before final retry)

### VPN Server Rotation

If retries keep failing, the script will suggest switching your VPN server. When processing multiple videos:

- **After every 3-5 videos**, consider switching your NordVPN server location for a fresh IP
- **After a throttle/failure**, always switch servers before retrying
- Switching servers takes a few seconds — wait for the connection to re-establish before continuing

### Batch Processing

When processing multiple videos in one session:

- **With video download**: wait 30-60 seconds between videos; process no more than 5-10 per hour
- **Transcript-only** (`--no-video`): can go faster, ~15-20 second gaps between videos
- If you hit throttling, switch VPN server and wait 2-3 minutes before resuming

## Example Usage

```
/fetch-youtube https://youtu.be/uVZMc-i5EEs
/fetch-youtube https://youtu.be/uVZMc-i5EEs --no-video
/fetch-youtube https://youtu.be/uVZMc-i5EEs --offset 2
/fetch-youtube https://youtu.be/uVZMc-i5EEs --timestamps 3:51,5:38,12:06
```

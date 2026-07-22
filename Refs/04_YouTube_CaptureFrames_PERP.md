<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Show me the FFmpeg script to batch extract frames at multiple timestamps from a first pass through the transcript

Yes — the cleanest way is to make the slash command produce a timestamp file first, then feed that file into a tiny FFmpeg batch script. FFmpeg handles the actual frame extraction, while the ClaudeCode command handles topic detection and timestamp generation.[^1][^2]

## Recommended flow

1. ClaudeCode reads the transcript and emits topic boundaries as timestamps.
2. Your script converts those boundaries into capture timestamps, usually a bit earlier.
3. FFmpeg is run once per timestamp to extract a single frame.
4. The script writes a CSV or JSON manifest so you can inspect what was captured.[^3][^1]

This is better than trying to force FFmpeg to infer topic changes itself, because the transcript pass already gives you the semantic boundaries.[^4][^5]

## Bash batch script

Here is a practical Bash version that reads a TSV file with `topic`, `start_time`, and `capture_time`, then extracts one image per row:

```bash
#!/usr/bin/env bash
set -euo pipefail

VIDEO="${1:?usage: $0 input.mp4 timestamps.tsv output_dir}"
TSV="${2:?usage: $0 input.mp4 timestamps.tsv output_dir}"
OUTDIR="${3:?usage: $0 input.mp4 timestamps.tsv output_dir}"

mkdir -p "$OUTDIR"

tail -n +2 "$TSV" | while IFS=$'\t' read -r topic start_time capture_time; do
  safe_topic=$(echo "$topic" | tr '[:space:]/:' '_' | tr -cd '[:alnum:]_-')
  safe_time=$(echo "$capture_time" | tr ':' '-' | tr '.' '-')
  out="$OUTDIR/${safe_time}_${safe_topic}.jpg"

  ffmpeg -hide_banner -loglevel error \
    -ss "$capture_time" -i "$VIDEO" \
    -frames:v 1 -q:v 2 "$out"
done
```

That pattern uses `-ss` and `-frames:v 1` to grab a single frame at each requested timestamp.[^2][^3]

## Python version

If you want more control, Python is usually nicer because you can parse the transcript output and generate the capture timestamps in one pass:

```python
import csv
import os
import subprocess
from pathlib import Path

video = "input.mp4"
tsv = "timestamps.tsv"
outdir = Path("frames")
outdir.mkdir(exist_ok=True)

def slug(s):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s.strip())

with open(tsv, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for row in reader:
        topic = row["topic"]
        capture_time = row["capture_time"]
        safe = f"{capture_time.replace(':','-').replace('.','-')}_{slug(topic)}.jpg"
        out = outdir / safe

        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-ss", capture_time,
            "-i", video,
            "-frames:v", "1",
            "-q:v", "2",
            str(out),
        ], check=True)
```

This is easy to extend with fallback timestamps like `capture_time - 1.0s` if you want a backup frame.[^6][^7]

## Timestamp file format

I would have ClaudeCode output a TSV or CSV like this:

```tsv
topic	start_time	capture_time
intro	00:00:12.400	00:00:11.400
model architecture	00:12:34.500	00:12:33.500
evaluation	00:21:08.200	00:21:07.200
```

That structure is simple to generate and simple to consume, and it keeps topic detection separate from media extraction.[^8][^9]

## Better extraction behavior

For thumbnails or topic previews, I would usually capture at `start_time - 1.0s` and optionally also save `start_time - 2.0s` as a fallback. FFmpeg seeking behavior can be influenced by keyframes, so having a nearby backup frame helps if the first capture lands on a transition or a visually awkward moment.[^10][^11]

A strong implementation pattern is:

- Use transcript boundaries from ClaudeCode.
- Write `capture_time = max(0, start_time - 1.0s)`.
- Extract one primary frame and one fallback frame.
- Keep both in the output directory, or pick the better one later.[^2][^6]


## How to wire it into ClaudeCode

Your slash command should output the timestamp manifest only, not call FFmpeg directly. Then a wrapper script can:

1. run the slash command,
2. save its JSON/TSV output,
3. invoke the batch extractor.

That separation makes the workflow easier to debug and lets you reuse the same timestamp manifest for other tasks later, like clipping or chaptering.[^12][^13]
<span style="display:none">[^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24]</span>

<div align="center">⁂</div>

[^1]: https://stackoverflow.com/questions/24433341/using-ffmpeg-to-extract-multiple-images-from-video-and-get-timestamp-of-extracte

[^2]: https://ottverse.com/extract-frames-using-ffmpeg-a-comprehensive-guide/

[^3]: https://shotstack.io/learn/ffmpeg-extract-frames/

[^4]: https://www.reddit.com/r/youtube/comments/1jvuwpa/how_to_convert_yt_transcript_to_topic_timestamps/

[^5]: https://gotranscript.com/en/blog/fix-timestamps-timecodes-auto-generated-transcripts

[^6]: https://a.osmarks.net/content/superuser.com_en_all_2020-04/A/question/1044569.html

[^7]: https://stackoverflow.com/questions/33746719/ffmpeg-how-can-i-capture-the-timestamp-of-a-screenshot-using-a-seek-and-findin\&rut=c999cde8d37bd1e8dc472627e664a92692aef6d131740ab4a45de8d6bf5cad74

[^8]: https://platform.claude.com/docs/en/agent-sdk/slash-commands

[^9]: https://github.com/jftuga/transcript-critic

[^10]: https://github.com/mifi/lossless-cut/issues/1216

[^11]: https://fftrac-bg.ffmpeg.org/wiki/Seeking

[^12]: https://platform.claude.com/cookbook/claude-agent-sdk-01-the-chief-of-staff-agent

[^13]: https://code.claude.com/docs/en/slash-commands

[^14]: https://www.reddit.com/r/ffmpeg/comments/nz94i7/extract_frames_at_multiple_timestamp/

[^15]: https://lists.ffmpeg.org/lore/ffmpeg-user/CAMdBu3E1vzjLidNGF7bWEXhtTODVm4RmwncRD2RHq2c06dq_8g@mail.gmail.com/

[^16]: https://forum.videohelp.com/threads/404084-script-to-extract-1st-frame-of-each-second-(ffmpeg)?p=2641860

[^17]: https://kkroening.github.io/ffmpeg-python/

[^18]: https://gist.github.com/blurymind/f6c11ee8eacde4a50f711e46dafd37b0

[^19]: https://github.com/stevenrick/imagesToVideo

[^20]: https://www.gumlet.com/learn/ffmpeg-extract-frames/

[^21]: http://zulko.github.io/blog/2013/09/27/read-and-write-video-frames-in-python-using-ffmpeg

[^22]: https://www.mux.com/articles/clip-sections-of-a-video-with-ffmpeg

[^23]: https://www.youtube.com/watch?v=xH_KEOxeHac

[^24]: https://www.reddit.com/r/ffmpeg/comments/162kl22/consecutively_pipe_individual_frames_through_a/


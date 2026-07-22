<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Show me OpenCV Python code for frame capture at transcript timestamps

Here’s a solid OpenCV pattern for capturing one frame per transcript timestamp, with an optional small “capture earlier” offset. OpenCV’s `VideoCapture` can seek by millisecond position with `CAP_PROP_POS_MSEC`, and then `read()` returns the frame at that position, though exact seeking can vary by codec/keyframes.[^1][^2]

## Python script

```python
import cv2
from pathlib import Path
import csv

video_path = "input.mp4"
timestamps_csv = "timestamps.csv"   # columns: topic,start_time,capture_time
outdir = Path("frames")
outdir.mkdir(exist_ok=True)

def hms_to_seconds(s):
    h, m, rest = s.split(":")
    sec = float(rest)
    return int(h) * 3600 + int(m) * 60 + sec

def seconds_to_slug_time(sec):
    ms = int(round(sec * 1000))
    return f"{ms:010d}"

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    raise RuntimeError(f"Could not open video: {video_path}")

with open(timestamps_csv, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        topic = row["topic"].strip()
        capture_time = hms_to_seconds(row["capture_time"])

        cap.set(cv2.CAP_PROP_POS_MSEC, capture_time * 1000.0)
        ok, frame = cap.read()
        if not ok:
            print(f"Failed at {row['capture_time']} ({topic})")
            continue

        safe_topic = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic)
        out_path = outdir / f"{seconds_to_slug_time(capture_time)}_{safe_topic}.jpg"
        cv2.imwrite(str(out_path), frame)
        print(f"Saved {out_path}")

cap.release()
```

This reads a CSV of transcript-derived timestamps and extracts one frame for each row.[^3][^1]

## CSV format

Use something like this:

```csv
topic,start_time,capture_time
intro,00:00:12.400,00:00:11.400
model architecture,00:12:34.500,00:12:33.500
evaluation,00:21:08.200,00:21:07.200
```

The `capture_time` is what OpenCV will seek to, so your transcript pass can remain semantic while your frame extraction stays visual.[^2][^4]

## Better seeking behavior

If you find `CAP_PROP_POS_MSEC` lands inconsistently on some files, a robust fallback is to seek a little earlier than the target and read forward a few frames until you reach or pass the requested timestamp. That helps with nontrivial codecs because precise seeking often depends on keyframes.[^5][^2]

A simple refinement is:

- seek to `capture_time - 1.0s`,
- read 3 to 10 frames,
- keep the last frame before the boundary or the first frame after it, depending on your preference.


## More accurate alternative

If you need more reliable timestamp-level control than OpenCV alone provides, FFmpeg-backed libraries or PyAV are often better for exact seeking because they work closer to the codec internals and keyframe logic. For your use case, though, OpenCV is usually good enough if you are already subtracting a small offset from topic boundaries.[^6][^7][^1][^2]

## Practical recommendation

For transcript topic changes, I would do this:

- topic boundary from transcript,
- `capture_time = boundary - 1.0s`,
- OpenCV seek to `capture_time`,
- optionally capture a second fallback frame at `boundary - 2.0s`.

That gives you a frame that usually shows the setup for the new topic rather than the exact transition moment.[^4][^1]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://forum.opencv.org/t/cap-set-cv2-cap-prop-pos-msec-changes-to-unreachable-timestamp/6561

[^2]: https://github.com/opencv/opencv/issues/9053

[^3]: https://www.geeksforgeeks.org/python/save-frames-of-live-video-with-timestamps-python-opencv/

[^4]: https://gotranscript.com/en/blog/fix-timestamps-timecodes-auto-generated-transcripts

[^5]: https://forum.opencv.org/t/cv2-cap-prop-pos-frames-sometimes-starts-at-a-keyframe-sometimes-doesnt/5380

[^6]: https://forum.opencv.org/t/display-time-in-video/6756

[^7]: https://fftrac-bg.ffmpeg.org/wiki/Seeking

[^8]: https://forum.opencv.org/t/cap-prop-pos-msec-of-a-live-camera-stream/17810

[^9]: https://stackoverflow.com/questions/70522473/how-cap-getcv2-cap-prop-pos-msec-works

[^10]: https://stackoverflow.com/questions/55069809/python-opencv-get-camera-frame-timestamp-in-system-time-accurately

[^11]: https://www.youtube.com/watch?v=JMkACAyyKRU

[^12]: https://www.futurelearn.com/info/courses/introduction-to-image-analysis-for-plant-phenotyping/0/steps/305359

[^13]: https://opencv.org/reading-and-writing-videos-using-opencv/

[^14]: https://forum.opencv.org/t/get-framerate-and-frame-timestamp-from-live-webcam-stream/14475

[^15]: https://forums.developer.nvidia.com/t/accurate-frame-timestamping-gstreamer-opencv/274320

[^16]: https://forum.opencv.org/t/extract-timestamp-of-each-frame-in-a-video-cap-prop-pos-msec-incorrect-timing-issues/5393

[^17]: https://forum.opencv.org/t/how-to-automatically-detect-video-start-timestamp-from-in-opencv/21099


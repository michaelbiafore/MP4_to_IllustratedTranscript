# Lecture Figs — Extract Unique Slides from a Lecture-Style MP4

Capture *interesting and unique* still frames from a screen-recorded lecture (e.g., a Udemy section played at 2× and recorded with EaseUS). Drops talking-heads, near-blank screens, logo-only slides, and progressive-reveal duplicates — keeps only the maximally-revealed frame in each "run" of phash-similar frames.

**Arguments**: $ARGUMENTS

## Argument Parsing

Parse the arguments as: `<mp4_path> <slug> [--speedup N] [--interval SEC] [--phash-run N] [--phash-final N] [--min-edge PCT] [--max-skin PCT]`

- **mp4_path** (required): absolute path to the source MP4. If recorded at 2×/4×, the script restores to 1× first.
- **slug** (required): short identifier used for filenames (e.g. `mlflow_s5`, `quantra_module_3`).
- **--speedup** (optional, default `2`): playback speedup the MP4 was recorded at. `1` skips the restore step.
- **--interval** (optional, default `8`): seconds between candidate frames. Smaller values = more candidates.
- **--phash-run / --phash-final / --min-edge / --max-skin** (optional): see filter tuning below.

Examples:
```
/lecture-figs "C:/Users/biafo/Videos/EaseUS RecExperts/20260505_080000.mp4" mlflow_s5
/lecture-figs path/to/recording.mp4 quantra_3 --speedup 2 --interval 6
/lecture-figs path/to/recording.mp4 udemy_dl_s2 --phash-run 4 --phash-final 12 --min-edge 1.0
```

## Pipeline

1. **Restore the MP4 to 1× speed** (only if `--speedup > 1`):
   ```bash
   .venv/Scripts/python.exe scripts/restore_speed.py "<mp4_path>" --speedup <N> --slug "<slug>"
   ```
   Writes `Input/{slug}_video.mp4`. Verify ffprobe duration ≈ `input_duration × N` (drift < 2 s).

2. **Dense ffmpeg extraction** at 1920×1080:
   ```bash
   mkdir -p Input/{slug}_figs_raw
   "$FFMPEG" -i Input/{slug}_video.mp4 -vf "fps=1/<INTERVAL>,scale=1920:1080" \
     -q:v 2 Input/{slug}_figs_raw/frame_%04d.jpg -y
   ```

3. **Smart filter**:
   ```bash
   .venv/Scripts/python.exe scripts/filter_lecture_frames.py \
     Input/{slug}_figs_raw <INTERVAL> \
     [--phash-run N] [--phash-final N] [--min-edge PCT]
   ```
   Three stages:
   - **Stage 1** drops talking-heads (HSV skin %), blanks (low std-dev), logo-only screens (low edge density).
   - **Stage 2** groups consecutive phash-similar frames into "runs" and keeps only the highest-content-score frame per run — captures the **fully-revealed** end of every progressive-reveal sequence.
   - **Stage 3** does a final phash-distance dedup across runs.
   Outputs go to `Input/{slug}_figs_raw_filtered/` with `manifest.json`.

4. **Contact sheet** for human review:
   ```bash
   .venv/Scripts/python.exe -c "
   from pathlib import Path
   import cv2, numpy as np, json
   d = Path('Input/{slug}_figs_raw_filtered')
   m = {e['filename']: e for e in json.load(open(d/'manifest.json'))}
   figs = sorted(d.glob('frame_*.jpg'))
   tw = 480; cols = 6
   sample = cv2.imread(str(figs[0])); h0,w0 = sample.shape[:2]
   th = int(tw*h0/w0); cw = tw+8; ch = th+60+8
   rows = (len(figs)+cols-1)//cols
   canvas = np.full((rows*ch, cols*cw, 3), 30, dtype=np.uint8)
   for i,f in enumerate(figs):
       r,c = divmod(i,cols); x = c*cw+4; y = r*ch+4
       canvas[y:y+th, x:x+tw] = cv2.resize(cv2.imread(str(f)), (tw,th))
       e = m[f.name]
       cv2.putText(canvas, f'#{i+1:02d} t={e[\"time_str\"]} sc={e[\"content_score\"]:.1f}',
           (x+4, y+th+25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,220,255), 2)
   cv2.imwrite('Input/{slug}_contact_sheet.jpg', canvas, [cv2.IMWRITE_JPEG_QUALITY, 78])
   "
   ```
   Read the contact sheet with the Read tool to assess filter quality at a glance.

5. **Curate** the surviving frames into `Input/{slug}_figs/` with descriptive names (e.g., `fig_07_precedence_diagram.jpg`). This step is manual — guided by the contact sheet plus reading individual frames the model is unsure about.

## Filter tuning by content type — IMPORTANT

The defaults (`--phash-run 8 --phash-final 18 --min-edge 1.5 --max-skin 18`) are calibrated for **slide-heavy** lecture content (white-background slides, occasional code, ~1 slide every 30–90s). Use them as the first attempt.

When the section is **code-heavy** (e.g., a long PyCharm walkthrough where the screen evolves slowly with one or two new lines added at a time), the defaults collapse too many useful intermediate code states into single run-winners. Symptom: filter output of 20–25 frames when you needed 40+.

In that case, **loosen the thresholds**:

```
--phash-run 4 --phash-final 12 --min-edge 1.0
```

This change recovers ~3× more frames while still dropping all the talking-heads and partial-reveal duplicates. Empirical evidence: MLflow course Section 4 (10 lectures, mostly PyCharm code) went from 24 → 46 unique frames with these settings — enough to support a 45-slide deck. The Section 2+3 video (mostly bullet slides) needed only the defaults to surface 60 unique frames.

| Content type | --phash-run | --phash-final | --min-edge |
|---|---|---|---|
| Slide-heavy (bullets, diagrams) | 8 (default) | 18 (default) | 1.5 (default) |
| Code-heavy (long IDE work) | **4** | **12** | **1.0** |
| Mixed | start with defaults; loosen if filter output < N target |

If you go too loose you'll see near-duplicate code frames in the contact sheet — pull `--phash-run` back up to 6 or 7. If you go too tight you'll miss the "fully revealed" frame at the end of a long reveal sequence — drop it to 3.

## Why this filter exists (and why `filter_frames.py` isn't enough)

The older `scripts/filter_frames.py` does plain perceptual-hash dedup. That works for fast-changing content but fails on lecture videos two ways:

1. It **keeps talking-head frames** that pass the hash distance check but carry no content.
2. It picks the **first frame** of a phash-similar run, which means it grabs the *first* partial reveal of a 4-box diagram and ignores the fully-revealed final frame.

`filter_lecture_frames.py` fixes both: it scores each frame by edge density × std-dev × (1 − skin penalty), and within each phash run it keeps the *highest-scoring* frame — which is reliably the maximally-revealed final state.

## Output Files

```
Input/
├── {slug}_video.mp4                 # 1×-restored MP4 (if --speedup > 1)
├── {slug}_figs_raw/                 # dense ffmpeg extraction (~400-500 candidates)
├── {slug}_figs_raw_filtered/        # post-filter survivors
│   ├── frame_NNNmSSs_score_N.N.jpg
│   ├── manifest.json                # per-frame stats: edge_pct, std_dev, skin_pct, score, phash
│   ├── drops.json                   # what was rejected and why
│   └── all_stats.json
├── {slug}_contact_sheet.jpg         # 6-column thumb grid for visual review
└── {slug}_figs/                     # final curated set (filled by hand after review)
```

## Next pipeline step

After curation, build the formatted Markdown + slides referencing `Input/{slug}_figs/`:

```
# in the formatted markdown:
![Figure N: Caption](../../Input/{slug}_figs/fig_NN_descriptive_name.jpg)

# in the slide deck:
<img src="../../Input/{slug}_figs/fig_NN_descriptive_name.jpg" alt="...">
```

Then run `scripts/embed_slide_images.py` on the slide HTML to base64-inline everything for email portability.

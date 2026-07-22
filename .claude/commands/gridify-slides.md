# Gridify Slides — Thumbnail Grid Viewer

Generate an HTML file that displays all slides from a reveal.js deck as a grid of thumbnails.

**Input file**: $ARGUMENTS

## Instructions

1. **Resolve the input file path**:
   - If the path contains only a filename (no directory separators), look for it in the `Output/Slides/` directory
   - If the path contains a full path, use that path directly

2. **Read the input HTML file** and verify it is a reveal.js presentation (contains `<div class="reveal">` and `<div class="slides">`)

3. **Count the number of slides** by counting top-level `<section>` elements inside `<div class="slides">` (do not count nested `<section>` elements used for vertical slides)

4. **Derive the output filename**:
   - Extract the base filename (without path and without `.html` extension)
   - The output filename is: `{base_filename}_grid.html`
   - Place the output in the same directory as the input file

5. **Generate the grid HTML file** with this exact structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{base_filename} — Thumbnail Grid</title>
<style>
  body { background: #111; margin: 0; padding: 20px; }
  .grid { display: flex; flex-wrap: wrap; gap: 16px; justify-content: center; }
  .cell { position: relative; width: 320px; height: 240px; overflow: hidden; border: 1px solid #333; border-radius: 6px; }
  .cell iframe { width: 960px; height: 700px; transform: scale(0.333); transform-origin: top left; border: none; pointer-events: none; }
  .label { position: absolute; bottom: 4px; right: 8px; color: #888; font: bold 12px sans-serif; }
</style>
</head>
<body>
<div class="grid">
<script>
for (let i = 0; i < SLIDE_COUNT; i++) {
  document.write(
    '<div class="cell">' +
    '<iframe src="INPUT_FILENAME#/' + i + '"></iframe>' +
    '<div class="label">' + (i+1) + '</div>' +
    '</div>'
  );
}
</script>
</div>
</body>
</html>
```

Replace:
- `SLIDE_COUNT` with the actual number of slides counted in step 3
- `INPUT_FILENAME` with just the filename (not full path) of the input HTML file, since the grid file is in the same directory

6. **Report** the output file path and the number of slides found.

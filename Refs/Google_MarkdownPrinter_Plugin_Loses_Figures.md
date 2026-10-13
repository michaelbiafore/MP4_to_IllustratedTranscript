## Yes — confirmed by reading the source

I pulled [levz0r/markdown-printer](https://github.com/levz0r/markdown-printer) and traced the pipeline. Two findings:

**1. Relative paths are emitted verbatim, not resolved.** Conversion goes through the bundled Turndown, whose image rule is unmodified:

```js
rules.image = {
  filter: 'img',
  replacement: function (content, node) {
    var alt = cleanAttribute(node.getAttribute('alt'));
    var src = node.getAttribute('src') || '';
    ...
```

`getAttribute('src')` returns the literal attribute string. (Had it used the `node.src` *property*, the DOM would have resolved it against `baseURI` for free — that one-word difference is the whole bug.) A grep across `src/background.js`, `utils.js`, and `extension-pro/` turns up zero references to `baseURI`, `URL()`, `new URL`, or any absolutization step. Same story for links via `getAttribute('href')`. So `<img src="/assets/fig1.png">` lands in your `.md` as `![](/assets/fig1.png)` — a dangling path relative to wherever the file sits.

**2. Nothing is embedded or downloaded, ever.** There is no fetch of image bytes, no base64 inlining, no sidecar assets folder. Even absolute-URL images are only *referenced*, so they're hotlinks subject to rot, auth walls, and hotlink blocking. So for a Karpathy-style wiki ingest, figures are lost in both the relative case (broken path) and the absolute case (fragile remote reference).

One mitigating detail: the extension does write `**Source:** <url>` into the header ([background.js](https://github.com/levz0r/markdown-printer)), which means the information needed to reconstruct the paths is preserved in the file — the resolution just never happens.

## Fix

Since the base URL survives in the header, this is recoverable in post-processing. I wrote and tested [md_absolutize.py](computer://md_absolutize.py): it reads the `**Source:**` line, `urljoin`s every relative image and link target against it, and optionally fetches images into a local assets dir and rewrites paths to point there.

```bash
python md_absolutize.py clippings/*.md                          # absolutize only
python md_absolutize.py --download-dir assets clippings/page.md # archive figures
```

It skips `http(s)`, `data:`, `mailto:`, and anchors, dedupes downloads by URL, and content-sniffs extensions when the URL has none.

## Two remaining gaps worth knowing

- **Lazy-loaded images.** Pages using `data-src`/`srcset` with a placeholder `src` will yield a spacer GIF or empty target regardless of absolutization. The extension's auto-scroll pass helps trigger loading, but not universally. If your Karpathy-wiki sources are heavy on lazy loading, a Playwright render-then-convert pass is more reliable than an extension.
- **`<figure>`/`<figcaption>`.** Default Turndown has no figure rule, so captions get flattened into loose paragraphs and decouple from the image — likely to matter if you want claim-level figure grounding, which connects to your evidence-grounded PDF summarization work.

Worth filing upstream, incidentally — a `converter.WithDomain`-style base-URL option is a ~3-line change to that rule, and the maintainer takes issues on the repo.
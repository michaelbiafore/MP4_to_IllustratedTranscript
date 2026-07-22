<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Some of these substack posts will be behind paywalls where I am a subscriber. I want reliable, repeatable pipelines and am otherwise indifferent to format---my understanding is that you can read Markdown most easily, HTML almost as easily and PDF with some difficulty and losses. I want to create a command which takes such a URL (which may be something I subscrible to), downloaded it, including figures if possible,  in whatever format you prefer, probably Markdown, and then write a Markdown summary, identifying topics and subtopics, reflecting them in h1 and h2 headers, including all figures at the appropriate point. Which of 1 or 3 do you recommend?

Between 1 and 3, you want a **CLI downloader**, not a generic browser extension. So: use a dedicated Substack → Markdown tool (Option 1), specifically one that supports paid posts plus image download.

## Recommended: CLI downloader → Markdown (+ images)

Two solid candidates:

- **Substack2Markdown (Python)** – downloads free and premium posts you’re subscribed to, and saves them as Markdown + HTML.[^1][^2]
- **sbstck-dl (Go)** – downloads individual posts or whole archives; can save in Markdown and download images/files, updating links to local paths.[^3]

Both are scriptable, so you can wrap them in a single command that:

1. Takes a Substack post URL (free or paywalled for you).
2. Downloads it as Markdown, with images saved locally and paths rewritten.[^3][^1]
3. Calls a second step (your script or Makefile) that:
    - Reads the `.md` file.
    - Sends it to me.
    - Writes back a **summary.md** that:
        - Uses `#` for the main topic and `##` for subtopics.
        - Inlines all figure references where they appear in the text (using the local image paths the downloader already inserted).[^3]

Because these tools are built for Substack, they handle quirks like premium access, pagination, and consistent front-matter better than a generic “webpage to Markdown” extension, and they can be run headless in a repeatable pipeline.[^1][^3]

## Why not a browser “Web to Markdown” extension?

Extensions like “Save — Web to Markdown” are fast for ad‑hoc saving, but they:

- Don’t reliably handle paywalled content that requires authenticated fetches.[^4]
- Are harder to automate in a non-interactive, repeatable pipeline.
- Often miss images or embed metadata, and output structure can vary between versions.[^4]

Given your goals (subscriptions, repeatability, images, and downstream summarization), a CLI downloader (Substack2Markdown or sbstck-dl) is clearly the better foundation.[^1][^3]

If you tell me your preferred language (Python vs Go) and OS, I can sketch an explicit command or script like:

```bash
substack2md "$URL" --format md --download-images --out ./archive/
# then call a script that posts ./archive/<slug>.md to me and writes <slug>.summary.md
```

wired into your existing tooling.
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://github.com/timf34/Substack2Markdown

[^2]: https://www.reddit.com/r/Substack/comments/18zovty/substack2markdown_convert_substack_posts_to/

[^3]: https://github.com/alexferrari88/sbstck-dl

[^4]: https://chromewebstore.google.com/detail/save-—-web-to-markdown/mamnlljnkigkhppbjhmpdeocobcbobdp

[^5]: https://www.substacktools.com/downloader

[^6]: https://apify.com/stanvanrooy6/substack-scraper

[^7]: https://github.com/zxt-tzx/substack-archives-downloader

[^8]: https://bradgarland.substack.com/p/copy-content-using-markdown-into

[^9]: https://www.reddit.com/r/coolgithubprojects/comments/156cx8l/sbstckdl_substack_downloader_cli_tool_written_in/

[^10]: https://github.com/kyurikotpq/substack-exports-to-md

[^11]: https://subsnacker.com

[^12]: https://thechipletter.substack.com/p/markdown-and-substack-a-bear-workflow

[^13]: https://github.com/nosajio/substack-dl

[^14]: https://unfoldai.substack.com/p/converting-documents-to-markdown

[^15]: https://github.com/alberba/SubstackDownloader

[^16]: https://github.com/nosajio/substack-dl/


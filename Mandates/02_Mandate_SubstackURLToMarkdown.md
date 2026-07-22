<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# I prefer Python. My OS is Windows 11. Produce a detailed plan including the installation of any packages or CLIs that are required, mentioning the URLs where these can be downloaded from. Include any necessary instructions for authenticating paid Substack subscriptions.

Here’s a concrete, end‑to‑end plan for Windows 11 + Python that (a) downloads Substack posts you have access to, including paywalled ones, (b) saves them as Markdown with images, and (c) produces a structured Markdown summary.

I’ll base this on:

- A Python‑friendly Substack downloader that supports paid content via cookies (e.g., Substack2Markdown / derivatives).[^1][^2]
- The `substack_api` library for explicit cookie‑based authentication, if you want more control.[^3][^4][^5]

You can swap components, but the overall pipeline will be the same.

***

## 1. Install Python and Git (if needed)

1. Install Python (if not already):
    - Go to the official download page: https://www.python.org/downloads/windows/ (choose the latest stable 64‑bit installer).[^6]
    - During install, check “Add Python 3.x to PATH”, then “Install Now”.[^6]
    - Verify in a new Command Prompt: `python --version`. You should see something like `Python 3.11.x`.[^6]
2. Install Git (for cloning GitHub repos):
    - Download from https://git-scm.com/download/win and run the installer with defaults.
    - Verify: `git --version`.

***

## 2. Set up a project directory and virtual environment

In a terminal (Windows Terminal / Command Prompt):

```bash
mkdir C:\Users\YOUR_USER\substack_pipeline
cd C:\Users\YOUR_USER\substack_pipeline

python -m venv .venv
.\.venv\Scripts\activate
```

You should see `(.venv)` in the prompt.

***

## 3. Install a Substack → Markdown downloader (Python‑based)

### 3.1 Choose and clone the downloader

Use a Python‑based Substack2Markdown implementation that can handle premium posts. For example, the “original” script specifically advertises support for free and premium posts.[^2]

```bash
git clone https://github.com/avibathula/OrigSubstack2Markdown.git
cd OrigSubstack2Markdown
```

(The main Substack2Markdown repo by `timf34` also targets free + premium posts.  You can pick either; the auth patterns are similar.)[^7][^1]

### 3.2 Install its Python dependencies

Most of these repos use a `requirements.txt`:

```bash
pip install -r requirements.txt
```

If there isn’t one, install at least:

```bash
pip install requests beautifulsoup4 lxml markdownify
```

(Exact names may differ slightly depending on the repo; check its README.)[^8][^2]

***

## 4. Authentication for paid Substack posts (cookies‑based)

Paid posts require that the script present your authenticated cookies, just as your browser does. Several tools and libraries use a cookie JSON file for this, e.g. `substack_api`.[^4][^5][^3]

### 4.1 Export your Substack cookies

You need your Substack session cookies from the browser where you’re logged in as a paying subscriber.

Typical approach:

1. Install a cookie‑export extension in your browser (e.g., “Export cookies to JSON” for Chrome or Firefox; these are commonly used with scripts like `substack_api`). Tools like `SubstackAuth` assume a JSON cookie file.[^5][^3]
2. Log into https://substack.com and then visit any post from the newsletter you subscribe to.
3. Use the extension to export cookies for the `*.substack.com` domain as a JSON file, e.g. `cookies_substack.json`.
4. Save this file into your project directory, e.g. `C:\Users\YOUR_USER\substack_pipeline\cookies_substack.json`.

### 4.2 Wire cookies into your downloader

If the downloader has built‑in support for cookie files, follow its README; many scripts accept something like `--cookies cookies_substack.json`.[^9]

If not, you can use the `substack_api` library as an authentication helper and then fetch the content yourself.

Install `substack-api`:

```bash
pip install substack-api
```

Example auth usage (from its docs):

```python
from substack_api import Newsletter, Post, SubstackAuth

auth = SubstackAuth(cookies_path="cookies_substack.json")

post = Post("https://newsletter.pragmaticengineer.com/p/steve-yegge-on-ai-agents-and-the", auth=auth)
html_content = post.get_content()  # includes paywalled content if you're subscribed
```

You can then convert `html_content` to Markdown and save it.

***

## 5. Converting HTML to Markdown and downloading images

If your chosen downloader already outputs Markdown and downloads images (many do; they advertise local image download and rewritten paths).  you may be done at this step.[^10][^11]

If you roll your own around `substack_api`, you can:

1. Use `markdownify` or similar to convert HTML → Markdown.
2. Parse the HTML for image tags and download them to a folder.

Install helpers:

```bash
pip install markdownify beautifulsoup4 lxml
```

shows a typical pattern for downloading images from a URL using `requests`.[^12]

Skeleton script:

```python
# save_post.py
import os
import re
import requests
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from substack_api import Post, SubstackAuth

OUTPUT_DIR = "archive"

def slug_from_url(url: str) -> str:
    # crude slug derivation from the Substack URL
    return url.rstrip("/").split("/")[-1] or "post"

def download_images(html, base_url, images_dir):
    os.makedirs(images_dir, exist_ok=True)
    soup = BeautifulSoup(html, "lxml")
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        img_url = urljoin(base_url, src)
        file_name = os.path.basename(urlparse(img_url).path) or "image.jpg"
        img_path = os.path.join(images_dir, file_name)
        resp = requests.get(img_url, timeout=30)
        resp.raise_for_status()
        with open(img_path, "wb") as f:
            f.write(resp.content)
        # rewrite src to local relative path
        img["src"] = os.path.join(os.path.basename(images_dir), file_name)
    return str(soup)

def save_substack_post(url: str, cookies_path: str = "cookies_substack.json"):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    slug = slug_from_url(url)

    auth = SubstackAuth(cookies_path=cookies_path)
    post = Post(url, auth=auth)
    html = post.get_content()

    # download images and rewrite HTML
    images_dir = os.path.join(OUTPUT_DIR, f"{slug}_images")
    html_with_local_images = download_images(html, url, images_dir)

    # convert to Markdown
    markdown = md(html_with_local_images, heading_style="ATX")

    md_path = os.path.join(OUTPUT_DIR, f"{slug}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    return md_path

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python save_post.py <substack_post_url>")
        raise SystemExit(1)
    url = sys.argv[^1]
    path = save_substack_post(url)
    print(f"Saved Markdown to {path}")
```

This gives you:

- `archive/<slug>.md` – Markdown with image references rewritten to local paths.
- `archive/<slug>_images/` – local image files.

The pattern for downloading images is similar to typical “download all images from URL” recipes.[^12]

***

## 6. Summary generation: pipeline design

At this point, for a given URL you have:

- A local Markdown file containing the full post (including paywalled content you’re entitled to).
- Local image files referenced by relative paths in the Markdown.

You want a command that:

1. Takes the URL.
2. Produces the Markdown file (as above).
3. Produces a **summary Markdown** with:
    - `#` top‑level title for the whole article.
    - `##` headings for major topics/subtopics you identify.
    - The images kept in‑place (referencing the same paths).

From your side, you’ll:

- Run `python save_post.py <url>` to generate the “source” Markdown.
- Then either:
    - Paste the Markdown into me directly, or
    - If your interface supports file upload, upload `archive/<slug>.md` (and optionally a zip with images).

From my side, when you provide that Markdown, you can instruct:

> “Please summarize this Markdown into a new Markdown document. Use a single `#` for the main title, `##` for major topics/subtopics, and keep all image references where they appear in the text.”

I’ll then return a structured summary Markdown that you can save as `archive/<slug>.summary.md`.

You can build a small wrapper script (`summarize_post.py`) to automate steps 1–2 and open the resulting `.md` in your editor, but the exact API for calling me depends on how you’re using this assistant (e.g., direct UI vs HTTP API vs other tooling).

***

## 7. Putting it together as a single command

In your project root (`C:\Users\YOUR_USER\substack_pipeline`), create a `run_post.bat` (or `.ps1`) that:

```bat
@echo off
setlocal

if "%~1"=="" (
    echo Usage: run_post.bat <substack_post_url>
    exit /b 1
)

set URL=%~1

REM Activate virtualenv
call .\.venv\Scripts\activate.bat

REM Save post as Markdown + images
python save_post.py %URL%

echo Now open the generated Markdown in archive\ and paste it into the assistant for summarization.

endlocal
```

You invoke it as:

```bash
run_post.bat https://newsletter.pragmaticengineer.com/p/steve-yegge-on-ai-agents-and-the
```

That gets you from URL → Markdown (with images) in one reproducible step.

***

## 8. Notes on ethics and limits

Tools like these are designed to download content you already have legal access to; their authors explicitly note they don’t bypass paywalls you’re not subscribed to.  Use them only on newsletters where you are a legitimate subscriber and for personal use/archival, not redistribution.[^1][^9]

***

If you’d like, I can next:

- Adjust the Python script to match whatever Substack2Markdown repo you end up choosing (e.g. wrap its CLI instead of using `substack_api`).
- Add a simple template for the summary Markdown layout you want, so we can keep that consistent.
<span style="display:none">[^13][^14][^15][^16][^17]</span>

<div align="center">⁂</div>

[^1]: https://github.com/timf34/Substack2Markdown

[^2]: https://github.com/avibathula/OrigSubstack2Markdown

[^3]: https://pypi.org/project/substack-api/1.1.1/

[^4]: https://github.com/NHagar/substack_api

[^5]: https://www.nickhagar.net/substack_api/

[^6]: https://k0nze.dev/posts/how-install-python-on-windows-11/

[^7]: https://www.reddit.com/r/Substack/comments/18zovty/substack2markdown_convert_substack_posts_to/

[^8]: https://blog.csdn.net/gitblog_00057/article/details/147346433

[^9]: https://github.com/carlvellotti/substack-downloader/blob/main/README.md

[^10]: https://github.com/alexferrari88/sbstck-dl

[^11]: https://github.com/alberba/SubstackDownloader

[^12]: https://dailypythonprojects.substack.com/p/download-all-images-from-a-url-with

[^13]: https://www.youtube.com/watch?v=8mO6QXOcpqU

[^14]: https://stackoverflow.com/questions/69862959/python-not-installing-on-windows-11

[^15]: https://www.youtube.com/watch?v=nDSJBdab_nE

[^16]: https://www.youtube.com/watch?v=LaUWoUneqiI

[^17]: https://github.com/chandandanjo/substack


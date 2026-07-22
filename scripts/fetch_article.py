#!/usr/bin/env python3
"""
Fetch any web article and save to Input/ directory with figures.

Usage:
    uv run python scripts/fetch_article.py <url>
    uv run python scripts/fetch_article.py <url> --cookies cookies_gmail.json

Called by:
    /fetch-article slash command (.claude/commands/fetch-article.md)

What it does:
    Uses Playwright (headless Chromium) to load a web article URL with full
    JavaScript rendering. Scrolls the page to trigger lazy-loaded images, then
    extracts the article body from the DOM. Supports multiple platform layouts
    including Substack, WordPress, Medium, and Ghost. Downloads all article
    figures to Input/{slug}_figs/ and converts the article HTML to Markdown.

Output files:
    Input/{slug}_RAW_ARTICLE.md   — article text as Markdown
    Input/{slug}_figs/fig_NN.ext  — downloaded article images

Dependencies:
    playwright, beautifulsoup4, markdownify, httpx

Cross-script references:
    - Imports fetch_substack.main_async() as a fallback when a Substack paywall
      is detected (scripts/fetch_substack.py)

Pipeline position:
    Stage 1 (fetch) → feeds into /format-transcript which reads *_RAW_ARTICLE.md
    from Input/ and produces Output/Formatted/*_FORMATTED_ARTICLE.md

Notes:
    - Includes a UTF-8 stdout fix for Windows (cp1252 encoding crashes on emoji
      in article titles). See the sys.stdout wrapper below.
    - The --cookies flag accepts a Netscape or JSON cookie file for paywalled sites.
"""

import sys
import io
# Force UTF-8 stdout on Windows to avoid cp1252 encode errors
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
import re
import os
import json
import argparse
import asyncio
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote, parse_qs
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


def resolve_image_url(src: str, base_url: str) -> str:
    """Resolve an image URL, unwrapping platform-specific wrappers.

    Handles Next.js, Substack CDN, WordPress, Medium, Cloudinary,
    Ghost, and Imgix image optimization wrappers.
    """
    if not src:
        return src

    # Make absolute first
    absolute = urljoin(base_url, src)
    parsed = urlparse(absolute)

    # Next.js: /_next/image?url=%2F_next%2Fstatic%2Fmedia%2Fname.hash.ext&w=N&q=N
    if "/_next/image" in parsed.path:
        qs = parse_qs(parsed.query)
        if "url" in qs:
            inner = unquote(qs["url"][0])
            # Inner path is relative to the same origin
            origin = f"{parsed.scheme}://{parsed.netloc}"
            return origin + inner if inner.startswith("/") else inner

    # Substack CDN: substackcdn.com/image/fetch/w_N,h_N,.../{original_url}
    if "substackcdn.com/image/fetch/" in absolute:
        match = re.search(r'/fetch/[^/]+/(https?://.+)$', absolute)
        if match:
            return match.group(1)

    # WordPress: i0.wp.com/{domain}/{path}?w=N
    if re.match(r'https?://i\d\.wp\.com/', absolute):
        return urlparse(absolute)._replace(query="").geturl()

    # Medium: miro.medium.com/v2/resize:fit:N/{id}
    if "miro.medium.com" in absolute and "resize:fit:" in absolute:
        return re.sub(r'resize:fit:\d+/', 'max/', absolute)

    # Cloudinary: res.cloudinary.com/.../w_N,h_N,.../{path}
    if "res.cloudinary.com" in absolute:
        return re.sub(r'/[a-z]_\d+[^/]*/(?=[^/]+$)', '/', absolute)

    # Ghost: {domain}/content/images/size/w_N/{path}
    if "/content/images/size/" in absolute:
        return re.sub(r'/size/w_\d+/', '/', absolute)

    # Imgix or generic: strip resize query params
    if any(p in parsed.query for p in ["w=", "width=", "resize="]):
        return parsed._replace(query="").geturl()

    return absolute


def extract_article_container(soup: BeautifulSoup) -> BeautifulSoup:
    """Find the main article content container using a priority cascade."""
    # Priority 1: <article> element
    article = soup.find("article")
    if article and len(article.get_text(strip=True)) > 500:
        return article

    # Priority 2: [role="main"] or <main>
    main = soup.find(attrs={"role": "main"}) or soup.find("main")
    if main and len(main.get_text(strip=True)) > 500:
        return main

    # Priority 3: Common content class names
    content_selectors = [
        ("div", {"class": re.compile(r"(post-content|article-content|entry-content|blog-content|prose)", re.I)}),
        ("div", {"class": re.compile(r"body.*markup", re.I)}),
        ("div", {"class": "body"}),
    ]
    for tag, attrs in content_selectors:
        elem = soup.find(tag, attrs)
        if elem and len(elem.get_text(strip=True)) > 500:
            return elem

    # Priority 4: Largest content block heuristic
    all_divs = soup.find_all("div")
    best_div = None
    best_len = 0
    skip_classes = {"nav", "header", "footer", "sidebar", "comment", "subscribe", "newsletter", "menu", "cookie"}
    for div in all_divs:
        classes = " ".join(div.get("class", [])).lower()
        if any(x in classes for x in skip_classes):
            continue
        text_len = len(div.get_text(strip=True))
        if text_len > best_len:
            best_len = text_len
            best_div = div
    if best_div and best_len > 500:
        return best_div

    raise ValueError("Could not locate article content in HTML")


def extract_title_and_meta(soup: BeautifulSoup) -> tuple[str, str | None]:
    """Extract article title and subtitle."""
    title_elem = (
        soup.find("h1", class_=re.compile(r"title", re.I))
        or soup.find("h1")
    )
    title = title_elem.get_text(strip=True) if title_elem else "Untitled"

    subtitle_elem = (
        soup.find("h2", class_=re.compile(r"subtitle", re.I))
        or soup.find("p", class_=re.compile(r"subtitle|description|excerpt", re.I))
    )
    subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else None

    return title, subtitle


def find_image_caption(img_tag) -> str | None:
    """Find caption for an image from figcaption, adjacent italic text, or alt."""
    # Check for figcaption
    parent = img_tag.parent
    if parent and parent.name == "figure":
        figcaption = parent.find("figcaption")
        if figcaption:
            return figcaption.get_text(strip=True)

    # Check for italic text immediately following
    next_sib = img_tag.find_next_sibling()
    if next_sib:
        if next_sib.name in ["em", "i"]:
            return next_sib.get_text(strip=True)
        if next_sib.name == "p":
            em = next_sib.find(["em", "i"])
            if em:
                text = em.get_text(strip=True)
                if text and len(text) < 300:
                    return text

    # Check parent's next sibling
    if parent:
        next_parent_sib = parent.find_next_sibling()
        if next_parent_sib:
            if next_parent_sib.name in ["em", "i"]:
                return next_parent_sib.get_text(strip=True)
            if next_parent_sib.name == "p":
                em = next_parent_sib.find(["em", "i"])
                if em:
                    text = em.get_text(strip=True)
                    if text and len(text) < 300:
                        return text

    # Fall back to alt text (if it's meaningful, not just "image")
    alt = img_tag.get("alt", "").strip()
    if alt and len(alt) > 5 and alt.lower() not in ("image", "photo", "picture", "img"):
        return alt

    return None


def guess_extension(url: str, content_type: str = "") -> str:
    """Guess file extension from URL or content-type."""
    url_lower = url.lower().split("?")[0]
    for ext in [".webp", ".png", ".gif", ".svg", ".jpeg", ".jpg"]:
        if url_lower.endswith(ext):
            return ext

    if "webp" in url_lower:
        return ".webp"
    if "png" in url_lower:
        return ".png"
    if "svg" in url_lower:
        return ".svg"
    if "gif" in url_lower:
        return ".gif"

    ct = content_type.lower()
    if "webp" in ct:
        return ".webp"
    if "png" in ct:
        return ".png"
    if "svg" in ct:
        return ".svg"
    if "gif" in ct:
        return ".gif"

    return ".jpg"


async def collect_and_download_images(
    content_soup: BeautifulSoup,
    base_url: str,
    figs_dir: Path,
    page,
) -> None:
    """Collect images from content, resolve URLs, download, and update soup in-place."""
    seen_urls = set()
    images = []

    for img in content_soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src or src.startswith("data:"):
            continue

        # Skip tiny images
        width = img.get("width")
        height = img.get("height")
        if width and height:
            try:
                if int(width) < 50 or int(height) < 50:
                    continue
            except (ValueError, TypeError):
                pass

        resolved = resolve_image_url(src, base_url)

        # Deduplicate
        # Normalize for dedup: strip query params
        dedup_key = urlparse(resolved)._replace(query="", fragment="").geturl()
        if dedup_key in seen_urls:
            continue
        seen_urls.add(dedup_key)

        images.append((img, resolved))

    if not images:
        print("  No article images found")
        return

    figs_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Found {len(images)} images to download")

    for idx, (img, img_url) in enumerate(images, start=1):
        try:
            response = await page.request.get(img_url, timeout=15000)
            if not response.ok:
                print(f"  Warning: HTTP {response.status} for {img_url[:80]}")
                continue

            body = await response.body()
            # Skip tiny files (icons, spacers)
            if len(body) < 5000:
                print(f"  Skipping tiny image ({len(body)} bytes): {img_url[:60]}")
                continue

            ct = response.headers.get("content-type", "")
            ext = guess_extension(img_url, ct)
            filename = f"fig_{idx:02d}{ext}"
            local_path = figs_dir / filename
            local_path.write_bytes(body)

            # Update soup
            img["src"] = f"{figs_dir.name}/{filename}"

            caption = find_image_caption(img)
            if caption:
                img["alt"] = f"Figure {idx}: {caption}"
            else:
                img["alt"] = f"Figure {idx}"

            size_kb = len(body) / 1024
            cap_display = f" — {caption[:50]}" if caption else ""
            print(f"  Downloaded: {filename} ({size_kb:.0f} KB){cap_display}")

        except Exception as e:
            print(f"  Warning: Failed to download {img_url[:80]}: {e}")


def html_to_markdown(html: str, title: str, subtitle: str | None = None) -> str:
    """Convert HTML to Markdown."""
    markdown = md(
        html,
        heading_style="ATX",
        bullets="-",
        strong_em_symbol="*",
        strip=["script", "style", "nav", "footer", "button"],
    )

    header = f"# {title}\n\n"
    if subtitle:
        header += f"*{subtitle}*\n\n"
    header += "---\n\n"

    markdown = header + markdown

    # Fix broken image syntax
    markdown = re.sub(r'\[!\]\(([^)]+)\)', r'![](\1)', markdown)

    # Clean up whitespace
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)

    # Remove empty links/images
    markdown = re.sub(r"\[\]\([^)]*\)", "", markdown)
    markdown = re.sub(r"!\[\]\(\)", "", markdown)

    # Remove duplicate captions
    markdown = re.sub(
        r'(!\[Figure \d+: ([^\]]+)\]\([^)]+\))\s*\n\n\*\2\*',
        r'\1',
        markdown,
    )

    return markdown.strip()


PAYWALL_MARKERS = [
    "This post is for paid subscribers",
    "This post is for paying subscribers",
    "Subscribe to continue reading",
    "Upgrade to paid",
    "Upgrade to read",
    "Already a paid subscriber",
    "Rest of this post is for paid",
]

SUBSTACK_COOKIE_PATHS = [
    Path("cookies_substack.json"),
    Path.home() / "cookies_substack.json",
]


def is_substack_url(url: str) -> bool:
    """Check if URL is a Substack article."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return "substack.com" in host or "/p/" in parsed.path


def find_substack_cookies() -> Path | None:
    """Find Substack cookies file in default locations."""
    for path in SUBSTACK_COOKIE_PATHS:
        if path.exists():
            return path
    return None


def detect_paywall(markdown: str) -> bool:
    """Check if fetched content appears to be paywalled (truncated)."""
    for marker in PAYWALL_MARKERS:
        if marker.lower() in markdown.lower():
            return True
    return False


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug for filenames."""
    safe = re.sub(r'[<>:"/\\|?*]', '', text)
    safe = re.sub(r'\s+', '-', safe.strip())
    # Remove trailing dashes/dots
    safe = safe.strip("-.")
    return safe[:80]


async def fetch_article(url: str, cookies_path: Path | None = None):
    """Main fetch function."""
    print(f"Fetching: {url}")
    print()

    # Auto-detect Substack URLs and load cookies if available
    if not cookies_path and is_substack_url(url):
        cookies_path = find_substack_cookies()
        if cookies_path:
            print(f"Substack URL detected — loading cookies from: {cookies_path}")

    # Load optional cookies
    cookies = []
    if cookies_path and cookies_path.exists():
        print(f"Loading cookies from: {cookies_path}")
        with open(cookies_path, encoding="utf-8") as f:
            raw = json.load(f)
        for c in raw:
            pc = {
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ""),
                "path": c.get("path", "/"),
            }
            if c.get("secure"):
                pc["secure"] = True
            same_site = c.get("sameSite", "Lax")
            if same_site in ("Strict", "Lax", "None"):
                pc["sameSite"] = same_site
            if "expirationDate" in c:
                pc["expires"] = c["expirationDate"]
            cookies.append(pc)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        if cookies:
            await context.add_cookies(cookies)
            print(f"Loaded {len(cookies)} cookies")

        page = await context.new_page()

        # Navigate
        print("Loading page...")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

        # Wait for common content selectors
        for sel in ["article", "main", "[role='main']", ".post-content", ".prose"]:
            try:
                await page.wait_for_selector(sel, timeout=5000)
                break
            except Exception:
                continue

        # Scroll to trigger lazy loading
        print("Scrolling to load lazy images...")
        scroll_steps = 5
        for i in range(scroll_steps):
            await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/scroll_steps})")
            await page.wait_for_timeout(800)
        # Scroll back to top
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)

        html = await page.content()
        final_url = page.url
        print(f"Final URL: {final_url}")

        # Parse
        soup = BeautifulSoup(html, "lxml")
        title, subtitle = extract_title_and_meta(soup)
        print(f"Title: {title}")
        if subtitle:
            print(f"Subtitle: {subtitle}")

        # Extract article container
        container = extract_article_container(soup)
        print(f"Content container: <{container.name}> ({len(container.get_text(strip=True))} chars)")

        # Build slug from title
        slug = slugify(title)
        figs_dir = Path("Input") / f"{slug}_figs"

        # Download images
        print("\nDownloading figures...")
        await collect_and_download_images(container, final_url, figs_dir, page)

        await browser.close()

    # Convert to markdown
    content_html = str(container)
    markdown = html_to_markdown(content_html, title, subtitle)

    # Add metadata header
    now = datetime.now(timezone.utc).isoformat()
    header = (
        f"# {title}\n\n"
        f"**Source:** {url}\n"
        f"**Saved:** {now}\n\n"
        f"---\n\n"
    )
    # Replace the auto-generated header with our metadata header
    # The html_to_markdown function adds its own header, so we replace it
    lines = markdown.split("\n")
    # Find where the content starts (after the --- separator)
    content_start = 0
    for i, line in enumerate(lines):
        if line.strip() == "---" and i > 0:
            content_start = i + 1
            break
    content_body = "\n".join(lines[content_start:]).strip()
    markdown = header + content_body

    # Check for paywall before saving
    if detect_paywall(markdown) and is_substack_url(url):
        print("\n*** Paywall detected — falling back to fetch_substack.py ***\n")
        cookie_file = cookies_path or find_substack_cookies()
        if cookie_file:
            # Import and delegate to fetch_substack
            try:
                from fetch_substack import main_async as substack_fetch
            except ImportError:
                # Handle running from project root vs scripts dir
                sys.path.insert(0, str(Path(__file__).parent))
                from fetch_substack import main_async as substack_fetch

            await substack_fetch(url, cookie_file)
            # find the output file fetch_substack created
            substack_files = sorted(Path("Input").glob("*_RAW_SUBSTACK.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            if substack_files:
                output_path = substack_files[0]
                slug_from_substack = output_path.stem.replace("_RAW_SUBSTACK", "")
                figs_dir_sub = Path("Input") / f"{slug_from_substack}_figs"
                fig_count = len(list(figs_dir_sub.glob("fig_*"))) if figs_dir_sub.exists() else 0
                return output_path, fig_count
        else:
            print("  No cookies_substack.json found — saving paywalled content as-is")

    # Save
    input_dir = Path("Input")
    input_dir.mkdir(exist_ok=True)
    output_path = input_dir / f"{slug}_RAW_ARTICLE.md"
    output_path.write_text(markdown, encoding="utf-8")

    # Report
    print(f"\nArticle saved to: {output_path}")

    fig_count = 0
    if figs_dir.exists():
        fig_count = len(list(figs_dir.glob("fig_*")))
        if fig_count > 0:
            print(f"Downloaded {fig_count} figures to {figs_dir}/")

    print(f"Total content: {len(markdown)} characters, {len(markdown.splitlines())} lines")
    print()

    # Preview first 15 lines
    print("Preview:")
    for line in markdown.split("\n")[:15]:
        print(f"  {line[:100]}")

    print(f"\nNext step: /format-transcript {output_path.name}")
    return output_path, fig_count


def main():
    parser = argparse.ArgumentParser(description="Fetch web article and save as Markdown with figures")
    parser.add_argument("url", help="Article URL")
    parser.add_argument("--cookies", "-c", type=Path, help="Path to cookies JSON file")
    args = parser.parse_args()

    asyncio.run(fetch_article(args.url, args.cookies))


if __name__ == "__main__":
    main()

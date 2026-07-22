#!/usr/bin/env python3
"""
Fetch Substack article and save to Input/ directory.
Usage: python fetch_substack.py <substack_url>

Uses Playwright browser automation to:
- Access paywalled content using exported cookies
- Handle JavaScript-rendered pages
- Download images
"""

import sys
import io
import re
import os
import json
import argparse
import asyncio
from pathlib import Path

# Fix Windows console encoding for emoji/unicode characters
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


DEFAULT_COOKIE_PATHS = [
    Path("cookies_substack.json"),
    Path.home() / "cookies_substack.json",
]


def find_cookie_file() -> Path | None:
    """Find cookie file in default locations."""
    for path in DEFAULT_COOKIE_PATHS:
        if path.exists():
            return path
    return None


def load_cookies_for_playwright(path: Path) -> list[dict]:
    """Load cookies from JSON file and convert to Playwright format."""
    with open(path, encoding="utf-8") as f:
        raw_cookies = json.load(f)

    playwright_cookies = []
    for cookie in raw_cookies:
        # Convert EditThisCookie format to Playwright format
        pc = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie.get("domain", ".substack.com"),
            "path": cookie.get("path", "/"),
        }

        # Handle secure flag
        if cookie.get("secure"):
            pc["secure"] = True

        # Handle sameSite
        same_site = cookie.get("sameSite", "Lax")
        if same_site in ["Strict", "Lax", "None"]:
            pc["sameSite"] = same_site

        # Handle expiry - Playwright uses expires (seconds since epoch)
        if "expirationDate" in cookie:
            pc["expires"] = cookie["expirationDate"]

        playwright_cookies.append(pc)

    return playwright_cookies


def is_inbox_url(url: str) -> bool:
    """Check if URL is a Substack inbox URL."""
    return "/inbox/post/" in url


def is_direct_article_url(url: str) -> bool:
    """Check if URL is a direct article URL (not inbox)."""
    parsed = urlparse(url)
    # Direct URLs have /p/ in the path and are NOT on substack.com/inbox
    return "/p/" in parsed.path and not is_inbox_url(url)


async def extract_post_id_from_page(page, url: str) -> str | None:
    """Extract post ID from article page metadata.

    Substack embeds the post ID in the Twitter card meta tag URL:
    <meta name="twitter:image" content=".../api/v1/post_preview/188532718/twitter.jpg">

    Note: The URL may be URL-encoded (e.g., %2F instead of /)
    """
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        # Get the raw HTML and extract with Python regex (more reliable than JS)
        html = await page.content()

        # Method 1: URL-encoded Twitter/OG image URL
        # Pattern: post_preview%2F188532718%2F (URL-encoded slashes)
        match = re.search(r'post_preview%2F(\d{9,})%2F', html)
        if match:
            return match.group(1)

        # Method 2: Non-encoded version
        # Pattern: post_preview/188532718/
        match = re.search(r'post_preview/(\d{9,})/', html)
        if match:
            return match.group(1)

        # Method 3: Any API URL with post ID
        match = re.search(r'substack\.com[^"\']*?/(\d{9,})', html)
        if match:
            return match.group(1)

        # Method 4: Check _preloadedData via JavaScript
        post_id = await page.evaluate(r'''
            () => {
                if (window._preloadedData?.post?.id) {
                    return String(window._preloadedData.post.id);
                }
                const article = document.querySelector('[data-post-id]');
                if (article) {
                    return article.getAttribute('data-post-id');
                }
                return null;
            }
        ''')
        if post_id:
            return post_id

        return None
    except Exception as e:
        print(f"  Warning: Could not extract post ID: {e}")
        return None


async def resolve_direct_url_to_inbox(url: str, cookies: list[dict]) -> tuple[str, bool]:
    """Try to convert a direct article URL to an inbox URL.

    Returns:
        tuple: (resolved_url, success)
        - If successful: (inbox_url, True)
        - If failed: (original_url, False)
    """
    print(f"Attempting to resolve direct URL to inbox URL...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        # Note: We don't need cookies for this - post ID is in public HTML
        page = await context.new_page()

        try:
            post_id = await extract_post_id_from_page(page, url)

            if post_id:
                inbox_url = f"https://substack.com/inbox/post/{post_id}"
                print(f"  Found post ID: {post_id}")
                print(f"  Inbox URL: {inbox_url}")
                return inbox_url, True
            else:
                return url, False
        finally:
            await browser.close()


def print_url_resolution_help(original_url: str):
    """Print detailed help when URL resolution fails."""
    print()
    print("=" * 70)
    print("AUTHENTICATION REQUIRED - Could not automatically resolve URL")
    print("=" * 70)
    print()
    print("The direct article URL cannot be used with your Substack cookies")
    print("because authentication is domain-specific.")
    print()
    print("To fetch this paywalled article, you need the INBOX URL:")
    print()
    print("OPTION 1: From your Substack inbox (easiest)")
    print("  1. Go to https://substack.com/inbox")
    print("  2. Find and click on the article")
    print("  3. Copy the URL from your browser's address bar")
    print("     It will look like: https://substack.com/inbox/post/123456789")
    print()
    print("OPTION 2: From email notification")
    print("  1. Find the Substack email notification for this article")
    print("  2. Click any link to open it in your browser")
    print("  3. Copy the URL (it should contain /inbox/post/)")
    print()
    print("OPTION 3: Search your inbox")
    print("  1. Go to https://substack.com/inbox")
    print("  2. Use browser search (Ctrl+F) to find the article title")
    print("  3. Click and copy the URL")
    print()
    print("Then run this command again with the inbox URL:")
    print(f'  /fetch-substack https://substack.com/inbox/post/XXXXXXX')
    print()
    print("=" * 70)


def extract_slug(url: str) -> tuple[str, str]:
    """Extract newsletter name and article slug from URL."""
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")

    match = re.search(r"/p/([^/?#]+)", parsed.path)
    if match:
        slug = match.group(1)
        newsletter = host.split(".")[0] if "substack.com" in host else host.split(".")[0]
        return newsletter, slug

    inbox_match = re.search(r"/inbox/post/(\d+)", parsed.path)
    if inbox_match:
        return "substack", inbox_match.group(1)

    raise ValueError(f"Could not extract article slug from: {url}")


async def resolve_inbox_url(page, url: str) -> str:
    """Resolve Substack inbox URL to the actual article URL."""
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(3000)

    # Wait for content to load
    try:
        await page.wait_for_selector("h1", timeout=10000)
    except Exception:
        pass

    # Get the page title to help match the article URL
    title = await page.title()
    title_slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')

    # Get page content and look for article URLs
    content = await page.content()

    # Find all Substack article URLs
    url_patterns = [
        r'(https://[a-z0-9.-]+\.substack\.com/p/[a-z0-9-]+)',
        r'(https://[a-z0-9.-]+\.[a-z]+/p/[a-z0-9-]+)',
    ]

    found_urls = []
    for pattern in url_patterns:
        found_urls.extend(re.findall(pattern, content, re.I))

    # Deduplicate and filter
    found_urls = list(set(found_urls))

    # Try to match with title
    for url in found_urls:
        slug = url.rstrip('/').split('/')[-1]
        if len(slug) > 10 and (slug in title_slug or title_slug[:20] in slug):
            return url

    # Return first substantial URL that isn't about/subscribe/etc
    for url in found_urls:
        slug = url.rstrip('/').split('/')[-1]
        if len(slug) > 15 and not any(x in slug for x in ['about', 'subscribe', 'archive']):
            return url

    # If still on inbox, try to find the "Open in app" or actual article link
    if found_urls:
        return found_urls[0]

    raise ValueError(f"Could not resolve inbox URL: {url}")


async def fetch_article_with_browser(url: str, cookies: list[dict]) -> tuple[str, str, str]:
    """Fetch article using Playwright browser with cookies."""
    async with async_playwright() as p:
        # Launch Chromium (not system Chrome - no profile lock issues)
        browser = await p.chromium.launch(
            headless=False,  # Show browser so user can see it working
            args=["--disable-blink-features=AutomationControlled"],
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # Add cookies
        if cookies:
            await context.add_cookies(cookies)
            print(f"Loaded {len(cookies)} cookies")

        try:
            page = await context.new_page()

            # Handle inbox URLs
            if is_inbox_url(url):
                print("Detected inbox URL, resolving to article...")
                url = await resolve_inbox_url(page, url)
                print(f"Resolved to: {url}")

            # Navigate to the article
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Wait for content to load
            print("Waiting for content to load...")
            await page.wait_for_timeout(5000)

            # Try to wait for article content
            try:
                await page.wait_for_selector(".body, article, .post-content", timeout=10000)
            except Exception:
                pass

            # Check for paywall and try to handle it
            try:
                # Look for "Read full story" or similar unlock buttons
                unlock_btn = await page.query_selector('a:has-text("Read full story")')
                if unlock_btn:
                    print("Found unlock button, clicking...")
                    await unlock_btn.click()
                    await page.wait_for_timeout(3000)
            except Exception:
                pass

            # Scroll down to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await page.wait_for_timeout(1000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            html = await page.content()
            title = await page.title()
            final_url = page.url

            return html, final_url, title

        finally:
            await browser.close()


def extract_article_content(html: str) -> tuple[str, str, str | None]:
    """Extract article title, subtitle, and main content from Substack HTML."""
    soup = BeautifulSoup(html, "lxml")

    # Extract title
    title_elem = (
        soup.find("h1", class_="post-title") or
        soup.find("h1", {"data-testid": "post-title"}) or
        soup.find("h1", class_=re.compile(r".*title.*", re.I)) or
        soup.find("h1")
    )
    title = title_elem.get_text(strip=True) if title_elem else "Untitled"

    # Extract subtitle
    subtitle_elem = (
        soup.find("h3", class_="subtitle") or
        soup.find("p", class_="subtitle") or
        soup.find("h2", class_="subtitle")
    )
    subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else None

    # Try multiple content selectors
    content = None
    selectors = [
        ("div", {"class": re.compile(r"body.*markup", re.I)}),
        ("div", {"class": "body markup"}),
        ("div", {"class": "body"}),
        ("div", {"class": "post-content"}),
        ("div", {"class": "available-content"}),
        ("article", {}),
    ]

    for tag, attrs in selectors:
        content = soup.find(tag, attrs)
        if content and len(str(content)) > 1000:
            break

    if not content or len(str(content)) < 500:
        # Fallback: find largest div with substantial text
        all_divs = soup.find_all("div")
        best_div = None
        best_len = 0
        for div in all_divs:
            classes = " ".join(div.get("class", []))
            if any(x in classes.lower() for x in ["nav", "header", "footer", "sidebar", "comment", "subscribe"]):
                continue
            text_len = len(div.get_text(strip=True))
            if text_len > best_len:
                best_len = text_len
                best_div = div
        if best_div and best_len > 500:
            content = best_div

    if not content:
        raise ValueError("Could not locate article content in HTML")

    return title, str(content), subtitle


def pick_best_image_url(img, base_url: str) -> str | None:
    """Return the highest-resolution URL available for this <img>.

    Substack typically wraps the displayed (downsampled) <img> in an <a>
    that links to the full-resolution image, and/or places a sibling
    "(enlarge)" link nearby. Prefer those over the embedded src so the
    saved figure is readable rather than the small lazy-loaded thumbnail.
    """
    src = img.get("src")
    fallback = urljoin(base_url, src) if src else None

    def looks_like_image_url(u: str) -> bool:
        if not u:
            return False
        ul = u.lower()
        return (
            "substackcdn.com/image" in ul
            or "substack-post-media" in ul
            or any(ul.split("?")[0].endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"))
        )

    # 1) Direct parent <a> wrapping this img — Substack's "click to enlarge"
    parent_a = img.find_parent("a")
    if parent_a and parent_a.get("href"):
        href = urljoin(base_url, parent_a["href"])
        if looks_like_image_url(href):
            return href

    # 2) Sibling "(enlarge)" link in the same figure / captioned-image container
    container = img.find_parent(["figure", "div"])
    hops = 0
    while container is not None and hops < 3:
        for a in container.find_all("a"):
            txt = (a.get_text() or "").strip().lower()
            if "enlarge" in txt and a.get("href"):
                href = urljoin(base_url, a["href"])
                if looks_like_image_url(href):
                    return href
        container = container.find_parent(["figure", "div"])
        hops += 1

    return fallback


async def download_images_async(content_html: str, base_url: str, figs_dir: Path, page) -> str:
    """Download images using browser context and add figure numbers.

    Downloads images to local figs/ directory with clean filenames (fig_01.jpg, etc.)
    and adds figure numbers as alt text for proper markdown conversion.
    Prefers high-resolution "enlarge" URLs over the displayed downsampled src.
    """
    soup = BeautifulSoup(content_html, "lxml")
    images_found = []

    for img in soup.find_all("img"):
        src = img.get("src")
        if not src or src.startswith("data:") or "pixel" in src.lower():
            continue

        # Skip tiny images (icons, tracking pixels)
        width = img.get("width")
        height = img.get("height")
        if width and height:
            try:
                if int(width) < 50 or int(height) < 50:
                    continue
            except ValueError:
                pass

        # Prefer the enlarged URL when one is available
        img_url = pick_best_image_url(img, base_url) or urljoin(base_url, src)
        images_found.append((img, img_url))

    if not images_found:
        return content_html

    figs_dir.mkdir(parents=True, exist_ok=True)

    for idx, (img, img_url) in enumerate(images_found, start=1):
        # Determine file extension
        ext = ".jpg"  # default
        if "png" in img_url.lower():
            ext = ".png"
        elif "gif" in img_url.lower():
            ext = ".gif"
        elif "webp" in img_url.lower():
            ext = ".webp"
        elif "jpeg" in img_url.lower():
            ext = ".jpeg"

        # Clean filename: fig_01.jpg, fig_02.png, etc.
        filename = f"fig_{idx:02d}{ext}"
        local_path = figs_dir / filename

        try:
            response = await page.request.get(img_url)
            if response.ok:
                local_path.write_bytes(await response.body())

                # Update image src to local path
                img["src"] = f"{figs_dir.name}/{filename}"

                # Try to find caption (italic text following the image)
                caption = find_image_caption(img)
                if caption:
                    img["alt"] = f"Figure {idx}: {caption}"
                else:
                    img["alt"] = f"Figure {idx}"

                print(f"  Downloaded: {filename}" + (f" ({caption[:40]}...)" if caption and len(caption) > 40 else f" ({caption})" if caption else ""))
            else:
                print(f"  Warning: Failed to download {img_url}: {response.status}")
        except Exception as e:
            print(f"  Warning: Failed to download {img_url}: {e}")

    return str(soup)


def find_image_caption(img_tag) -> str | None:
    """Find caption for an image (usually italic text following the image).

    Substack typically formats images with captions like:
    <img src="...">
    <em>Caption text</em>

    Or within a figure element:
    <figure>
      <img src="...">
      <figcaption>Caption text</figcaption>
    </figure>
    """
    # Check for figcaption (proper HTML5 figure)
    parent = img_tag.parent
    if parent and parent.name == "figure":
        figcaption = parent.find("figcaption")
        if figcaption:
            return figcaption.get_text(strip=True)

    # Check for italic text immediately following the image
    next_sibling = img_tag.find_next_sibling()
    if next_sibling:
        # Direct em/i sibling
        if next_sibling.name in ["em", "i"]:
            return next_sibling.get_text(strip=True)
        # Paragraph containing em/i
        if next_sibling.name == "p":
            em = next_sibling.find(["em", "i"])
            if em and em.get_text(strip=True):
                # Only use if the paragraph is mostly italic (caption-like)
                p_text = next_sibling.get_text(strip=True)
                em_text = em.get_text(strip=True)
                if len(em_text) > len(p_text) * 0.5:
                    return em_text

    # Check parent's next sibling (image might be wrapped in a div/p)
    if parent:
        next_parent_sibling = parent.find_next_sibling()
        if next_parent_sibling:
            if next_parent_sibling.name in ["em", "i"]:
                return next_parent_sibling.get_text(strip=True)
            if next_parent_sibling.name == "p":
                em = next_parent_sibling.find(["em", "i"])
                if em:
                    text = em.get_text(strip=True)
                    # Captions are usually short-ish
                    if text and len(text) < 300:
                        return text

    return None


def html_to_markdown(html: str, title: str, subtitle: str | None = None) -> str:
    """Convert HTML to Markdown with proper image handling."""
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

    # Fix broken image syntax: [!](url) -> ![](url)
    # markdownify sometimes produces [!] for images
    markdown = re.sub(r'\[!\]\(([^)]+)\)', r'![](\1)', markdown)

    # Clean up excessive whitespace
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)

    # Remove empty links and images
    markdown = re.sub(r"\[\]\([^)]*\)", "", markdown)
    markdown = re.sub(r"!\[\]\(\)", "", markdown)

    # Strip leftover Substack "(enlarge)" link text - we already saved the enlarged image.
    # Handles plain, bolded, and parenthesized variants:
    #   [enlarge](url)
    #   (**[enlarge](url)**)
    #   [(enlarge)](url)
    #   bare "(enlarge)" tokens left over after link stripping
    markdown = re.sub(r"\(\s*\*+\s*\[enlarge\]\([^)]*\)\s*\*+\s*\)", "", markdown, flags=re.IGNORECASE)
    markdown = re.sub(r"\*+\s*\[enlarge\]\([^)]*\)\s*\*+", "", markdown, flags=re.IGNORECASE)
    markdown = re.sub(r"\[\(?enlarge\)?\]\([^)]*\)", "", markdown, flags=re.IGNORECASE)
    markdown = re.sub(r"\(\s*enlarge\s*\)", "", markdown, flags=re.IGNORECASE)

    # Remove duplicate captions (caption might appear both in alt text and as following italic)
    # Pattern: ![Figure N: Caption](path)\n\n*Caption*
    markdown = re.sub(
        r'(!\[Figure \d+: ([^\]]+)\]\([^)]+\))\s*\n\n\*\2\*',
        r'\1',
        markdown
    )

    return markdown.strip()


def sanitize_filename(text: str) -> str:
    """Convert text to safe filename."""
    safe = re.sub(r'[<>:"/\\|?*]', '', text)
    safe = re.sub(r'\s+', '_', safe)
    return safe[:80]


def save_article(markdown: str, slug: str) -> Path:
    """Save article markdown to Input/ directory."""
    input_dir = Path("Input")
    input_dir.mkdir(exist_ok=True)
    output_path = input_dir / f"{sanitize_filename(slug)}_RAW_SUBSTACK.md"
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


async def main_async(url: str, cookie_path: Path | None):
    """Main async function."""
    print(f"Fetching: {url}")
    print()

    # Load cookies
    cookies = []
    if cookie_path:
        print(f"Loading cookies from: {cookie_path}")
        cookies = load_cookies_for_playwright(cookie_path)
    else:
        cookie_path = find_cookie_file()
        if cookie_path:
            print(f"Found cookies at: {cookie_path}")
            cookies = load_cookies_for_playwright(cookie_path)
        else:
            print("No cookies file found - proceeding without authentication")
            print("(Paywalled content may not be accessible)")

    # Direct article URLs (/p/slug) are fetched directly — inbox resolution via post ID
    # extraction is unreliable (grabs wrong IDs from page metadata/recommendations).
    # Cookies are still loaded into the browser context for authentication during fetch.
    if is_direct_article_url(url):
        # Strip utm/query params for cleaner fetch
        clean_url = url.split("?")[0]
        if clean_url != url:
            print(f"Stripping query params, fetching directly: {clean_url}")
            url = clean_url
        else:
            print("Direct article URL, fetching directly...")

    # Fetch with browser
    html, final_url, page_title = await fetch_article_with_browser(url, cookies)

    # Extract slug
    try:
        _, slug = extract_slug(final_url)
    except ValueError:
        slug = sanitize_filename(page_title)

    print(f"\nArticle URL: {final_url}")
    print(f"Slug: {slug}")

    # Extract content
    title, content_html, subtitle = extract_article_content(html)
    print(f"Title: {title}")
    if subtitle:
        print(f"Subtitle: {subtitle}")

    if slug.isdigit():
        slug = sanitize_filename(title)

    # Download figures to figs/ subdirectory
    figs_dir = Path("Input") / f"{slug}_figs"
    print("\nDownloading figures...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        if cookies:
            await context.add_cookies(cookies)
        page = await context.new_page()
        await page.goto(final_url, wait_until="domcontentloaded", timeout=30000)

        content_with_local_figs = await download_images_async(
            content_html, final_url, figs_dir, page
        )
        await browser.close()

    # Convert and save
    markdown = html_to_markdown(content_with_local_figs, title, subtitle)
    output_path = save_article(markdown, slug)

    print(f"\nArticle saved to: {output_path}")

    # Preview
    lines = markdown.split("\n")
    print(f"\nFirst 15 lines:")
    for line in lines[:15]:
        print(f"  {line[:100]}")

    # Report
    if figs_dir.exists():
        fig_count = len(list(figs_dir.glob("*")))
        if fig_count > 0:
            print(f"\nDownloaded {fig_count} figures to {figs_dir}")
    else:
        print("\nNo figures found in article")

    print(f"\nTotal content: {len(markdown)} characters")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Substack article and save as Markdown"
    )
    parser.add_argument("url", help="Substack article URL")
    parser.add_argument(
        "--cookies", "-c",
        type=Path,
        help="Path to cookies file (JSON format from EditThisCookie)"
    )
    args = parser.parse_args()

    asyncio.run(main_async(args.url, args.cookies))


if __name__ == "__main__":
    main()

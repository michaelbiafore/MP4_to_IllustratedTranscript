#!/usr/bin/env python3
"""
Fetch a Perplexity conversation thread and save as a single Markdown file.

Usage:
    uv run python scripts/fetch_perplexity.py <url>
    uv run python scripts/fetch_perplexity.py <url> --cookies cookies_perplexity.json

Called by:
    /perp-to-md slash command (.claude/commands/perp-to-md.md)

What it does:
    Uses Playwright (headless Chromium) with authentication cookies to load a
    Perplexity AI conversation thread. Extracts all user queries and Perplexity
    responses in order, converts answer HTML to proper Markdown (preserving code
    blocks, lists, headings), strips UI artifacts (source citation badges,
    follow-up buttons), and interleaves Q&A pairs into a structured document.

Output files:
    Input/{slug}_PERP.md  — the conversation thread as structured Markdown

Dependencies:
    playwright, beautifulsoup4, markdownify

Cross-script references:
    None — standalone script.

Pipeline position:
    Stage 1 (fetch) → the output *_PERP.md file can be processed by
    /format-transcript to produce a formatted markdown document, though the
    naming convention (_PERP) is distinct from _RAW_TRANSCRIPT or _RAW_ARTICLE.

Notes:
    - Requires valid Perplexity session cookies (the site requires login).
    - The --cookies flag defaults to looking for cookies_perplexity.json.
"""

import sys
import re
import json
import argparse
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from playwright.async_api import async_playwright


STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "its", "that", "this", "was",
    "are", "be", "been", "has", "have", "had", "do", "does", "did", "will",
    "can", "could", "would", "should", "may", "might", "i", "my", "me",
    "we", "you", "your", "he", "she", "they", "them", "how", "what",
    "which", "where", "when", "who", "why", "not", "no", "so", "if",
    "just", "about", "also", "now", "new", "some", "any", "all", "more",
    "very", "up", "out", "here", "there", "then", "than", "into",
}

PERPLEXITY_COOKIE_PATHS = [
    Path("cookies_perplexity.json"),
    Path.home() / "cookies_perplexity.json",
]


def find_perplexity_cookies() -> Path | None:
    """Find Perplexity cookies file in default locations."""
    for path in PERPLEXITY_COOKIE_PATHS:
        if path.exists():
            return path
    return None


def slugify_from_title(title: str, max_words: int = 6, max_len: int = 60) -> str:
    """Extract content words from Perplexity's thread title to build a filename slug.

    Removes stop words, keeps the first `max_words` content words,
    joins with underscores, and strips unsafe characters.
    """
    cleaned = re.sub(r'["""\'\u2018\u2019`]', '', title)
    words = re.findall(r'[A-Za-z0-9]+', cleaned)
    content_words = [w for w in words if w.lower() not in STOP_WORDS]
    if not content_words:
        content_words = words[:max_words]
    slug_words = content_words[:max_words]
    slug = "_".join(w.capitalize() for w in slug_words)
    slug = re.sub(r'[<>:"/\\|?*]', '', slug)
    return slug[:max_len]


def load_cookies(cookies_path: Path) -> list[dict]:
    """Load cookies from JSON file into Playwright format."""
    with open(cookies_path, encoding="utf-8") as f:
        raw = json.load(f)
    cookies = []
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
    return cookies


def extract_turns_from_html(html_content: str, page_title: str) -> list[dict]:
    """Parse Perplexity thread HTML and extract conversation turns.

    Uses DOM structure to find:
    - User queries: div elements with class containing 'group/query'
    - Perplexity answers: div.prose.inline with substantial content
    - First query: extracted from the page title (not in a group/query div)

    Returns a list of dicts: {"role": "user"|"assistant", "content": str}
    """
    soup = BeautifulSoup(html_content, "lxml")
    turns = []

    # --- Remove UI noise elements before extraction ---
    # Remove SVG icons, buttons, nav elements
    for tag in soup.find_all(["svg", "nav", "footer", "header"]):
        tag.decompose()
    # Remove source citation links (small inline refs like [stackoverflow])
    for a_tag in soup.find_all("a", class_=re.compile(r"citation|source", re.I)):
        a_tag.decompose()

    # --- Extract user queries ---
    # The first query is the page title / thread starter — it's NOT in a group/query div
    # Subsequent queries are in div.group/query containers
    query_divs = soup.find_all("div", class_=re.compile(r"group/query"))
    # Build list: first query from title, rest from query_divs
    user_queries = [page_title]
    for qd in query_divs:
        span = qd.find("span", class_=re.compile(r"font-sans.*text-foreground"))
        if span:
            text = span.get_text(separator="\n").strip()
        else:
            text = qd.get_text(separator="\n").strip()
        if text:
            user_queries.append(text)

    # --- Extract Perplexity answers ---
    # Answer content lives in div.prose.inline containers with substantial text
    prose_divs = soup.find_all("div", class_=re.compile(r"\bprose\b"))
    answer_divs = [
        d for d in prose_divs
        if d.name == "div"
        and "inline" in " ".join(d.get("class", []))
        and len(d.get_text(strip=True)) > 100
    ]

    # Convert each answer div to markdown using markdownify
    answer_markdowns = []
    for adiv in answer_divs:
        # Remove source reference badges inside the answer
        for badge in adiv.find_all("a", href=re.compile(r"^https?://")):
            # Keep links that are part of instructions (have meaningful text)
            link_text = badge.get_text(strip=True)
            # Remove bare domain-name citations like "stackoverflow", "docker-docs.uclv"
            if re.match(r'^[a-z0-9._-]+(\+\d+)?$', link_text, re.I):
                badge.decompose()

        raw_md = md(
            str(adiv),
            heading_style="ATX",
            bullets="-",
            strong_em_symbol="*",
            strip=["button", "svg", "nav"],
        )
        # Clean up the markdown
        cleaned = clean_answer_markdown(raw_md)
        answer_markdowns.append(cleaned)

    # --- Interleave queries and answers ---
    max_turns = max(len(user_queries), len(answer_markdowns))
    for i in range(max_turns):
        if i < len(user_queries):
            turns.append({"role": "user", "content": user_queries[i]})
        if i < len(answer_markdowns):
            turns.append({"role": "assistant", "content": answer_markdowns[i]})

    return turns


def clean_answer_markdown(text: str) -> str:
    """Clean up markdownified answer content."""
    # Fix code blocks: "```\nbash\n" -> "```bash\n"
    langs = (
        "bash|python|json|yaml|yml|sh|sql|go|rust|javascript|typescript|"
        "html|css|xml|toml|ini|dockerfile|makefile|ruby|java|c|cpp|csharp"
    )
    text = re.sub(rf'```\s*\n({langs})\s*\n', r'```\1\n', text)

    # Remove bare source-reference words on their own line (e.g., "stackoverflow")
    text = re.sub(r'\n[a-z0-9._-]+(?:\+\d+)?\s*\n', '\n', text)

    # Remove trailing "+N" source indicators after punctuation
    text = re.sub(r'(?<=[.!?])\s*[a-z0-9._-]*\+\d+', '', text)

    # Clean up multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def format_thread_markdown(turns: list[dict], title: str, url: str) -> str:
    """Format conversation turns into a single Markdown document."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# {title}",
        "",
        f"**Source:** {url}",
        f"**Saved:** {now}",
        "",
        "---",
        "",
    ]

    query_num = 0
    response_num = 0

    for turn in turns:
        if turn["role"] == "user":
            query_num += 1
            lines.append(f"## User Query {query_num}")
            lines.append("")
            lines.append(turn["content"])
            lines.append("")
        else:
            response_num += 1
            lines.append(f"## Perplexity Response {response_num}")
            lines.append("")
            lines.append(turn["content"])
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


async def fetch_perplexity(url: str, cookies_path: Path | None = None):
    """Main fetch function for Perplexity threads."""
    print(f"Fetching: {url}")
    print()

    # Find cookies
    if not cookies_path:
        cookies_path = find_perplexity_cookies()

    if not cookies_path or not cookies_path.exists():
        print("WARNING: No cookies_perplexity.json found.")
        print("  Perplexity requires authentication. The fetch may fail.")
        print("  Export your browser cookies and save as cookies_perplexity.json")
        print()

    cookies = []
    if cookies_path and cookies_path.exists():
        print(f"Loading cookies from: {cookies_path}")
        cookies = load_cookies(cookies_path)

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
        await page.wait_for_timeout(4000)

        # Check for auth redirect
        final_url = page.url
        if "auth/verify" in final_url or "login" in final_url:
            await browser.close()
            print(f"\nERROR: Redirected to login page: {final_url}")
            print("Your cookies may be expired. Re-export from your browser.")
            sys.exit(1)

        # Scroll through the entire thread to load all content
        print("Scrolling to load full thread...")
        prev_height = 0
        for _ in range(20):
            height = await page.evaluate("document.body.scrollHeight")
            if height == prev_height:
                break
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            prev_height = height
        # Scroll back to top
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)

        # Get page title and content
        title = await page.title()
        print(f"Title: {title}")

        html = await page.content()
        final_url = page.url
        print(f"Final URL: {final_url}")

        await browser.close()

    # Parse the thread
    print("\nParsing conversation thread...")
    turns = extract_turns_from_html(html, title)

    if not turns:
        print("ERROR: Could not extract any conversation turns from the page.")
        print("The page structure may have changed. Try copy-pasting manually.")
        sys.exit(1)

    user_count = sum(1 for t in turns if t["role"] == "user")
    asst_count = sum(1 for t in turns if t["role"] == "assistant")
    print(f"Found {user_count} user queries and {asst_count} assistant responses")

    # Build filename from title
    slug = slugify_from_title(title)
    filename = f"{slug}_PERP.md"

    # Format as markdown
    markdown = format_thread_markdown(turns, title, url)

    # Save
    input_dir = Path("Input")
    input_dir.mkdir(exist_ok=True)
    output_path = input_dir / filename
    output_path.write_text(markdown, encoding="utf-8")

    # Report
    print(f"\nSaved to: {output_path}")
    print(f"Total content: {len(markdown)} characters, {len(markdown.splitlines())} lines")
    print()

    # Preview first 15 lines
    print("Preview:")
    for line in markdown.split("\n")[:15]:
        print(f"  {line[:100]}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Perplexity conversation thread and save as Markdown"
    )
    parser.add_argument("url", help="Perplexity thread URL")
    parser.add_argument(
        "--cookies", "-c", type=Path,
        help="Path to cookies JSON file (default: cookies_perplexity.json)"
    )
    args = parser.parse_args()

    asyncio.run(fetch_perplexity(args.url, args.cookies))


if __name__ == "__main__":
    main()

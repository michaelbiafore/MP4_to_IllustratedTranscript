#!/usr/bin/env python3
"""Probe a Substack post for video sources, transcript availability, and image figures.

Diagnostic only — does not download. Used to decide whether the video can be
fetched server-side or if a local MP4 from the user is required.
"""
import sys, json, re, asyncio
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright


URL = sys.argv[1] if len(sys.argv) > 1 else None
if not URL:
    print("usage: inspect_substack_video.py <url>")
    sys.exit(2)


def load_cookies(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for c in raw:
        pc = {
            "name": c["name"], "value": c["value"],
            "domain": c.get("domain", ".substack.com"),
            "path": c.get("path", "/"),
        }
        if c.get("secure"): pc["secure"] = True
        ss = c.get("sameSite", "Lax")
        if ss in ("Strict", "Lax", "None"): pc["sameSite"] = ss
        if "expirationDate" in c: pc["expires"] = c["expirationDate"]
        out.append(pc)
    return out


async def main():
    cookies = load_cookies(Path("cookies_substack.json"))

    network_log = []  # (resource_type, url)
    media_urls = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        await ctx.add_cookies(cookies)

        page = await ctx.new_page()

        def log_request(req):
            u = req.url
            t = req.resource_type
            network_log.append((t, u))
            ul = u.lower()
            if any(x in ul for x in (".m3u8", ".mpd", ".mp4", ".m4s", ".ts?", "/video/", "video-cdn", "/hls/")):
                media_urls.append((t, u))
            if t in ("media", "xhr", "fetch") and any(x in ul for x in (".m3u8", ".mp4", ".m4s", "video")):
                media_urls.append((t, u))

        page.on("request", log_request)

        print(f"Navigating to: {URL}")
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        # scroll to trigger lazy load
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight/3)")
        await page.wait_for_timeout(1500)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight*2/3)")
        await page.wait_for_timeout(1500)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)

        title = await page.title()
        print(f"Title: {title}")
        print(f"Final URL: {page.url}")

        # Try to detect paywall
        paywall = await page.evaluate("""() => {
            const t = document.body.innerText;
            return /Subscribe to read|Upgrade to paid|This post is for paid|Read full story/.test(t);
        }""")
        print(f"Paywall indicator in body: {paywall}")

        # Find <video> elements
        video_info = await page.evaluate("""() => {
            const vids = Array.from(document.querySelectorAll('video'));
            return vids.map(v => ({
                src: v.src || null,
                currentSrc: v.currentSrc || null,
                poster: v.poster || null,
                sources: Array.from(v.querySelectorAll('source')).map(s => ({src:s.src, type:s.type})),
                duration: v.duration,
                outerHTMLHead: v.outerHTML.slice(0, 400),
            }));
        }""")
        print(f"\n<video> elements found: {len(video_info)}")
        for i, v in enumerate(video_info):
            print(f"  video[{i}] currentSrc={v['currentSrc']}")
            print(f"           src={v['src']}")
            print(f"           poster={v['poster']}")
            print(f"           sources={v['sources']}")
            print(f"           duration={v['duration']}")
            print(f"           html-head: {v['outerHTMLHead'][:200]}")

        # Find iframes (some Substack videos embed external players)
        iframes = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('iframe')).map(f => f.src);
        }""")
        print(f"\niframes: {len(iframes)}")
        for f in iframes[:10]:
            print(f"  {f}")

        # Look for "Transcript" toggle button
        transcript_button = await page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('button, a, [role=button]'));
            const hits = btns.filter(b => /transcript/i.test(b.innerText || ''));
            return hits.map(b => ({text:b.innerText.trim().slice(0,80), tag:b.tagName, classes: (b.className||'').slice(0,80)}));
        }""")
        print(f"\nTranscript-toggle candidates: {len(transcript_button)}")
        for b in transcript_button[:5]:
            print(f"  [{b['tag']}] '{b['text']}' classes={b['classes']}")

        # Try clicking it
        if transcript_button:
            clicked = await page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button, a, [role=button]'));
                const t = btns.find(b => /transcript/i.test(b.innerText || ''));
                if (t) { t.click(); return true; } return false;
            }""")
            if clicked:
                await page.wait_for_timeout(2500)
                # Look for transcript content
                tx = await page.evaluate("""() => {
                    // Look for elements with multiple timestamps like 0:23, 12:45
                    const all = Array.from(document.querySelectorAll('div, section, aside, ul'));
                    let best = null, bestCount = 0;
                    for (const el of all) {
                        const txt = el.innerText || '';
                        const m = txt.match(/\\b\\d{1,2}:\\d{2}\\b/g);
                        if (m && m.length > bestCount) {
                            bestCount = m.length;
                            best = txt.slice(0, 1500);
                        }
                    }
                    return {count: bestCount, snippet: best};
                }""")
                print(f"\nAfter clicking Transcript:")
                print(f"  Timestamps found in best block: {tx['count']}")
                if tx['snippet']:
                    print(f"  First 600 chars:\n    {tx['snippet'][:600].replace(chr(10), chr(10)+'    ')}")

        # Look for image-based figures in body
        imgs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('article img, [class*=body] img')).map(i => ({
                src: i.src, alt: i.alt, w: i.naturalWidth, h: i.naturalHeight,
            }));
        }""")
        substantive_imgs = [i for i in imgs if i['w'] > 100 and i['h'] > 100]
        print(f"\nBody images >100px: {len(substantive_imgs)}")
        for i in substantive_imgs[:10]:
            print(f"  {i['w']}x{i['h']}  alt='{i['alt'][:40]}'")
            print(f"    {i['src']}")

        await browser.close()

    print(f"\n=== media-suspect network requests: {len(media_urls)} ===")
    seen = set()
    for t, u in media_urls:
        key = u.split('?')[0]
        if key in seen: continue
        seen.add(key)
        print(f"  [{t}] {u[:200]}")

    print(f"\n=== total network requests: {len(network_log)} ===")


asyncio.run(main())

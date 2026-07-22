#!/usr/bin/env python3
"""
Fetch a Substack post's video transcript and metadata.

Substack's video player loads a `transcription.json` from substackcdn.com
that contains timestamped segments. This is much cleaner than scraping the
rendered DOM. Output is shaped like Whisper's JSON so the rest of the
fetch-mp4/format-mp4/slidefy-mp4 pipeline works unchanged.

Usage: python fetch_substack_video_transcript.py <substack_post_url>

Outputs:
  Input/{slug}_transcript.json        (Whisper-shape)
  Input/{slug}_video_meta.json        (video URL, duration, poster)
"""
import sys, json, re, asyncio
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright


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


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    s = re.sub(r"[\s_-]+", "_", s)
    return s[:80] or "video"


def to_whisper_shape(raw_transcript) -> dict:
    """Convert Substack transcription.json into Whisper's segment shape.

    Observed Substack shapes: a top-level list of segment dicts, or a dict
    wrapping {"segments": [...]} / {"chunks": [...]}. Times may be ms; detect.
    """
    if isinstance(raw_transcript, list):
        segments_raw = raw_transcript
        language = "en"
    else:
        segments_raw = raw_transcript.get("segments") or raw_transcript.get("chunks") or []
        language = raw_transcript.get("language", "en")

    # Heuristic: if any "end" > 50000, treat the times as milliseconds.
    sample_ends = [s.get("end", s.get("endTime", 0)) for s in segments_raw[:10]]
    in_ms = any(isinstance(e, (int, float)) and e > 50000 for e in sample_ends)
    div = 1000.0 if in_ms else 1.0

    out_segs = []
    full_text_parts = []
    for i, s in enumerate(segments_raw):
        start = float(s.get("start", s.get("startTime", 0))) / div
        end = float(s.get("end", s.get("endTime", start))) / div
        text = (s.get("text") or s.get("content") or "").strip()
        if not text:
            continue
        out_segs.append({
            "id": i,
            "seek": 0,
            "start": round(start, 3),
            "end": round(end, 3),
            "text": " " + text if not text.startswith(" ") else text,
        })
        full_text_parts.append(text)

    return {
        "text": " ".join(full_text_parts),
        "segments": out_segs,
        "language": language,
    }


async def main(url: str):
    cookies = load_cookies(Path("cookies_substack.json"))

    transcription_url = None  # captured from network
    video_meta = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        await ctx.add_cookies(cookies)

        page = await ctx.new_page()

        captured = {"url": None}
        def on_request(req):
            u = req.url
            if "transcription.json" in u and captured["url"] is None:
                captured["url"] = u
        page.on("request", on_request)

        print(f"Loading: {url}", flush=True)
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

        # Click the Transcript button to force the player to load the transcription file
        clicked = await page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('button, a, [role=button]'));
            const t = btns.find(b => /transcript/i.test((b.innerText || '').trim()));
            if (t) { t.click(); return true; }
            return false;
        }""")
        print(f"Transcript button clicked: {clicked}", flush=True)
        await page.wait_for_timeout(4000)

        # Capture video metadata from the player
        video_meta = await page.evaluate("""() => {
            const v = document.querySelector('video');
            if (!v) return null;
            return {
                video_id: v.getAttribute('data-video-id'),
                title: v.getAttribute('title'),
                duration_sec: v.duration,
                poster: v.poster,
                hls_src: (Array.from(v.querySelectorAll('source')).find(s => /hls/.test(s.src)) || {}).src,
                mp4_src: (Array.from(v.querySelectorAll('source')).find(s => s.type === 'video/mp4') || {}).src,
            };
        }""")
        page_title = await page.title()

        if not captured["url"]:
            # If the network capture missed it, try once more by toggling transcript closed/open
            print("Transcription URL not captured via network; trying second click", flush=True)
            await page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button, a, [role=button]'));
                const t = btns.find(b => /transcript/i.test((b.innerText || '').trim()));
                if (t) t.click();
            }""")
            await page.wait_for_timeout(1500)
            await page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button, a, [role=button]'));
                const t = btns.find(b => /transcript/i.test((b.innerText || '').trim()));
                if (t) t.click();
            }""")
            await page.wait_for_timeout(2500)

        transcription_url = captured["url"]
        print(f"Transcription URL: {transcription_url}", flush=True)

        if not transcription_url:
            print("ERROR: could not capture transcription.json URL from network", file=sys.stderr)
            await browser.close()
            sys.exit(2)

        # Fetch the transcription JSON via the same browser context (preserves auth + signed-URL params)
        r = await page.request.get(transcription_url)
        if not r.ok:
            print(f"ERROR: transcription fetch failed {r.status}", file=sys.stderr)
            await browser.close()
            sys.exit(3)
        transcription_raw = await r.json()

        await browser.close()

    print(f"Page title: {page_title}", flush=True)
    print(f"Video duration: {video_meta.get('duration_sec') if video_meta else '?'}s", flush=True)

    # Slug from URL path
    m = re.search(r"/p/([^/?#]+)", url)
    base_slug = m.group(1) if m else slugify(page_title)

    # Convert and write
    whisper = to_whisper_shape(transcription_raw)
    print(f"Segments: {len(whisper['segments'])}, total chars: {len(whisper['text'])}", flush=True)

    Path("Input").mkdir(exist_ok=True)
    transcript_path = Path("Input") / f"{base_slug}_transcript.json"
    transcript_path.write_text(json.dumps(whisper, indent=2, ensure_ascii=False), encoding="utf-8")

    raw_path = Path("Input") / f"{base_slug}_transcription_raw.json"
    raw_path.write_text(json.dumps(transcription_raw, indent=2, ensure_ascii=False), encoding="utf-8")

    meta_out = {
        "page_title": page_title,
        "page_url": url,
        "transcription_url": transcription_url,
        **(video_meta or {}),
    }
    meta_path = Path("Input") / f"{base_slug}_video_meta.json"
    meta_path.write_text(json.dumps(meta_out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"WROTE_TRANSCRIPT={transcript_path}", flush=True)
    print(f"WROTE_RAW={raw_path}", flush=True)
    print(f"WROTE_META={meta_path}", flush=True)
    print(f"SLUG={base_slug}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: fetch_substack_video_transcript.py <url>")
        sys.exit(2)
    asyncio.run(main(sys.argv[1]))

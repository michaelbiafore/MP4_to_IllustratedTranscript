#!/usr/bin/env python3
"""
Playwright fallback for fetching Udemy lecture transcripts when the api-2.0
caption path is blocked or returns nothing useful.

Used by fetch_udemy.py when --ui is passed or when the API path fails.
Reuses the same cookies file so no extra login is required.

This path produces plain text only — no timestamps. Callers that wanted SRT
should record `timestamps_available: false` in the manifest for these
lectures.
"""
from __future__ import annotations

import json
import re
from contextlib import contextmanager
from pathlib import Path

# Lazy import — Playwright is heavy.
def _import_pw():
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    return sync_playwright, PWTimeout


# Selector candidates, in priority order. We try each until one matches.
TRANSCRIPT_BUTTON_SELECTORS = [
    'button[data-purpose="transcript-toggle"]',
    'button[data-purpose*="transcript"]',
    '[data-purpose*="transcript-toggle"]',
    'button[aria-label*="Transcript" i]',
    'button:has-text("Transcript")',
]

TRANSCRIPT_PANEL_SELECTORS = [
    '[data-purpose="transcript-panel"]',
    '[data-purpose*="transcript-panel"]',
    '[class*="transcript--cue"]',
    '[data-purpose*="transcript"]',
]

CUE_ROW_SELECTORS = [
    '[data-purpose*="cue"]',
    '[class*="transcript--cue"]',
    'button[data-purpose*="transcript"]',
]


# ---------------------------------------------------------------------------
# Browser lifecycle
# ---------------------------------------------------------------------------

@contextmanager
def ui_context(cookie_path: Path, headless: bool = True):
    """
    Yield (browser, context, page) with cookies pre-loaded from cookie_path
    (Playwright storage_state shape OR EditThisCookie array — same coverage as
    udemy_auth._read_cookie_file).
    """
    sync_playwright, _ = _import_pw()

    storage_state = _load_storage_state(cookie_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            context = browser.new_context(
                storage_state=storage_state,
                viewport={"width": 1400, "height": 1000},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            try:
                yield browser, context, page
            finally:
                context.close()
        finally:
            browser.close()


def _load_storage_state(cookie_path: Path) -> dict:
    """Return a Playwright storage_state dict regardless of source format."""
    with open(cookie_path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "cookies" in data:
        return data
    if isinstance(data, list):
        # EditThisCookie array → storage_state shape
        out_cookies = []
        for c in data:
            domain = c.get("domain") or ""
            if not domain.lstrip(".").endswith("udemy.com"):
                continue
            entry = {
                "name": c["name"],
                "value": c["value"],
                "domain": domain if domain.startswith(".") else f".{domain}",
                "path": c.get("path") or "/",
                "expires": float(c.get("expirationDate", -1)),
                "httpOnly": bool(c.get("httpOnly", False)),
                "secure": bool(c.get("secure", False)),
                "sameSite": (c.get("sameSite") or "Lax").capitalize(),
            }
            if entry["sameSite"] not in ("Strict", "Lax", "None"):
                entry["sameSite"] = "Lax"
            out_cookies.append(entry)
        return {"cookies": out_cookies, "origins": []}
    raise ValueError(f"Unrecognized cookie file format: {cookie_path}")


# ---------------------------------------------------------------------------
# Transcript extraction
# ---------------------------------------------------------------------------

def lecture_url(course_url: str, lecture_id: int) -> str:
    """Build the player URL for a lecture given the course landing URL."""
    # Course URL: https://www.udemy.com/course/<slug>/
    base = course_url.rstrip("/")
    if base.endswith("/"):
        base = base[:-1]
    return f"{base}/learn/lecture/{lecture_id}"


def extract_transcript_via_player(page, lect_url: str, timeout_ms: int = 30_000) -> str:
    """
    Navigate to a lecture URL, click the Transcript button, scrape cue rows,
    and return joined plaintext.

    Returns "" if no transcript is visible (treat as no_captions).
    Raises RuntimeError on selector timeouts that suggest a structural change.
    """
    _, PWTimeout = _import_pw()

    page.goto(lect_url, wait_until="domcontentloaded", timeout=timeout_ms)

    # Wait for the player chrome to render — any of these signals will do.
    try:
        page.wait_for_selector(
            ", ".join([
                '[data-purpose="curriculum-item-title"]',
                '[data-purpose*="lecture-name"]',
                'video',
            ]),
            timeout=timeout_ms,
        )
    except PWTimeout as e:
        raise RuntimeError(f"Player did not render at {lect_url}: {e}")

    # Click the Transcript toggle. Try selectors in order.
    clicked = False
    for sel in TRANSCRIPT_BUTTON_SELECTORS:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=1500):
                loc.click()
                clicked = True
                break
        except PWTimeout:
            continue
        except Exception:
            continue

    if not clicked:
        # No transcript button means the lecture has no transcripts.
        return ""

    # Wait briefly for the panel to populate.
    panel_loc = None
    for sel in TRANSCRIPT_PANEL_SELECTORS:
        try:
            page.wait_for_selector(sel, timeout=8_000)
            panel_loc = page.locator(sel).first
            break
        except PWTimeout:
            continue

    if panel_loc is None:
        return ""

    # Pull cue rows from the first panel that has any.
    cues: list[str] = []
    for sel in CUE_ROW_SELECTORS:
        rows = panel_loc.locator(sel)
        try:
            count = rows.count()
        except Exception:
            count = 0
        if count > 0:
            for i in range(count):
                t = rows.nth(i).inner_text(timeout=2_000)
                if t and t.strip():
                    cues.append(t.strip())
            if cues:
                break

    if not cues:
        # Some Udemy versions render cues as plain text inside the panel; fall
        # back to grabbing the panel text wholesale.
        whole = panel_loc.inner_text(timeout=2_000)
        cues = [line.strip() for line in whole.split("\n") if line.strip()]

    return _reflow_ui_lines(cues)


# ---------------------------------------------------------------------------
# Reflow for UI-scraped lines (no timestamps to lean on)
# ---------------------------------------------------------------------------

_TERMINATORS = (".", "!", "?")


def _reflow_ui_lines(lines: list[str]) -> str:
    """
    UI-scraped lines have no timing — so paragraph breaks have to be inferred
    from sentence terminators only. Otherwise we mirror the API path's
    cross-cue word-merge fix.
    """
    seen: list[str] = []
    for ln in lines:
        ln = re.sub(r"\s+", " ", ln).strip()
        if not ln:
            continue
        if seen and ln == seen[-1]:
            continue
        seen.append(ln)

    if not seen:
        return ""

    out: list[str] = [seen[0]]
    for nxt in seen[1:]:
        prev = out[-1]
        if prev.rstrip().endswith(_TERMINATORS) and nxt[:1].isupper():
            out.append(nxt)
        else:
            if not prev.endswith(" ") and not nxt.startswith(" "):
                out[-1] = prev + " " + nxt
            else:
                out[-1] = prev + nxt

    return "\n\n".join(re.sub(r"[ \t]+", " ", p).strip() for p in out)

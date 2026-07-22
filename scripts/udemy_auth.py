#!/usr/bin/env python3
"""
Udemy authentication helpers for fetch_udemy.py.

Two paths:
  1. Cookies on disk  (cookies_udemy.json)  → primary
  2. Interactive login via Playwright       → fallback / refresh

The cookies file accepts either:
  - EditThisCookie / Cookie-Editor JSON array export
  - Playwright `storage_state` shape: {"cookies": [...], "origins": []}

After a successful interactive login, cookies are written in storage_state shape
so the same file feeds both `requests.Session` (Approach A) and
`browser.new_context(storage_state=...)` (Approach B).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests


COOKIE_PATH = Path("cookies_udemy.json")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Cookie file format detection + normalization
# ---------------------------------------------------------------------------

def _read_cookie_file(path: Path) -> list[dict]:
    """Return a list of cookie dicts, regardless of source format."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # storage_state shape from Playwright
    if isinstance(data, dict) and "cookies" in data:
        return list(data["cookies"])

    # EditThisCookie / Cookie-Editor — flat array
    if isinstance(data, list):
        return data

    raise ValueError(
        f"Unrecognized cookie file format in {path}. "
        "Expected a JSON array (EditThisCookie) or "
        "{cookies: [...]} (Playwright storage_state)."
    )


def _udemy_cookies_only(cookies: list[dict]) -> list[dict]:
    """Filter to udemy.com cookies (avoid leaking unrelated cookies into the session)."""
    out = []
    for c in cookies:
        domain = (c.get("domain") or "").lstrip(".")
        if domain.endswith("udemy.com"):
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# requests.Session for the API path
# ---------------------------------------------------------------------------

def make_session(cookie_path: Path = COOKIE_PATH) -> requests.Session:
    """
    Build a requests.Session pre-loaded with Udemy cookies and a real Chrome UA.

    Raises FileNotFoundError if the cookie file is absent — caller should
    suggest `--login`.
    """
    if not cookie_path.exists():
        raise FileNotFoundError(
            f"{cookie_path} not found. Run with --login to create it, "
            "or export from Cookie-Editor."
        )

    cookies = _udemy_cookies_only(_read_cookie_file(cookie_path))
    if not cookies:
        raise ValueError(
            f"{cookie_path} contains no udemy.com cookies. "
            "Re-export with Cookie-Editor while on a udemy.com tab."
        )

    sess = requests.Session()
    sess.headers.update({
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.udemy.com/",
        "X-Requested-With": "XMLHttpRequest",
    })

    for c in cookies:
        sess.cookies.set(
            name=c["name"],
            value=c["value"],
            domain=(c.get("domain") or ".udemy.com"),
            path=c.get("path") or "/",
        )

    return sess


def session_is_authenticated(sess: requests.Session) -> bool:
    """Quick liveness check: hit /users/me/ and confirm 200 + a real id."""
    try:
        r = sess.get(
            "https://www.udemy.com/api-2.0/users/me/",
            params={"fields[user]": "id,title,email"},
            timeout=15,
        )
    except requests.RequestException:
        return False
    if r.status_code != 200:
        return False
    try:
        body = r.json()
    except ValueError:
        return False
    return bool(body.get("id"))


# ---------------------------------------------------------------------------
# Interactive login (Playwright, headed)
# ---------------------------------------------------------------------------

LOGIN_URL = "https://www.udemy.com/join/login-popup/?locale=en_US"


def login_interactive(email: str, cookie_path: Path = COOKIE_PATH) -> Path:
    """
    Open Playwright in headed mode, type email, prompt the user for the
    6-digit verification code from their inbox, submit it, and dump
    storage_state to cookie_path.

    Returns the cookie_path on success. Raises RuntimeError on failure.
    """
    # Lazy import — Playwright is heavy and only needed in this path.
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    print(f"[login] Launching browser for {email} …")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=UA,
            viewport={"width": 1400, "height": 1000},
        )
        page = context.new_page()

        try:
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)

            # Email field — selectors vary; try a few.
            email_sel = (
                'input[type="email"], '
                'input[name="email"], '
                'input[autocomplete="username"]'
            )
            page.wait_for_selector(email_sel, timeout=30_000)
            page.fill(email_sel, email)

            # Continue button
            for btn_sel in (
                'button[type="submit"]',
                'button[data-purpose*="form-group-next"]',
                'button:has-text("Continue")',
                'button:has-text("Log in")',
            ):
                try:
                    if page.locator(btn_sel).first.is_visible(timeout=1500):
                        page.locator(btn_sel).first.click()
                        break
                except PWTimeout:
                    continue

            # Wait for the OTP screen — either a code-prompting input or the
            # phrase appears in the body.
            print("[login] Waiting for verification-code screen …")
            page.wait_for_function(
                """
                () => {
                    const t = (document.body.innerText || "").toLowerCase();
                    const phrasey = /6-digit|verification code|enter code|check your email/i.test(t);
                    const fieldy = !!document.querySelector(
                        'input[autocomplete="one-time-code"], '
                      + 'input[inputmode="numeric"], '
                      + 'input[name*="code" i]'
                    );
                    return phrasey || fieldy;
                }
                """,
                timeout=60_000,
            )

            # Prompt the user for the code from their inbox.
            print()
            print("=" * 60)
            print("Check your email for a 6-digit Udemy verification code.")
            print("Use the MOST RECENT code, in the SAME browser session.")
            print("=" * 60)
            code = input("Enter Udemy 6-digit code: ").strip()
            if not code or not code.isdigit():
                raise RuntimeError("No valid code entered. Aborting login.")

            # Type the code
            code_sel = (
                'input[autocomplete="one-time-code"], '
                'input[inputmode="numeric"], '
                'input[name*="code" i]'
            )
            page.wait_for_selector(code_sel, timeout=10_000)
            page.locator(code_sel).first.click(click_count=3)
            page.locator(code_sel).first.fill(code)

            # Submit
            for sub_sel in (
                'button[type="submit"]',
                'button[data-purpose*="submit"]',
                'button:has-text("Verify")',
                'button:has-text("Continue")',
            ):
                try:
                    if page.locator(sub_sel).first.is_visible(timeout=1500):
                        page.locator(sub_sel).first.click()
                        break
                except PWTimeout:
                    continue

            # Wait for navigation away from /login/
            try:
                page.wait_for_url(
                    lambda url: "login" not in url and "verify" not in url,
                    timeout=30_000,
                )
            except PWTimeout:
                # Some flows leave you on the same URL but flip session state.
                # Fall through and trust the cookie verification step below.
                pass

            # Save storage_state — this is the canonical format for reuse.
            cookie_path.parent.mkdir(parents=True, exist_ok=True)
            state = context.storage_state()
            with open(cookie_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            print(f"[login] Cookies written to {cookie_path}")

        finally:
            context.close()
            browser.close()

    # Verify by hitting /users/me/
    sess = make_session(cookie_path)
    if not session_is_authenticated(sess):
        raise RuntimeError(
            "Login finished but cookies don't authenticate against /users/me/. "
            "The code may have been invalid or expired — try again."
        )
    print("[login] Verified against /users/me/ — you are signed in.")
    return cookie_path


# ---------------------------------------------------------------------------
# CLI for standalone testing: `python udemy_auth.py --login me@example.com`
# ---------------------------------------------------------------------------

def _cli() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Udemy auth helper")
    ap.add_argument("--login", metavar="EMAIL", help="Run interactive login")
    ap.add_argument("--check", action="store_true", help="Verify existing cookies")
    args = ap.parse_args()

    if args.login:
        try:
            login_interactive(args.login)
        except Exception as e:
            print(f"[login] FAILED: {e}", file=sys.stderr)
            return 1
        return 0

    if args.check:
        try:
            sess = make_session()
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            return 2
        ok = session_is_authenticated(sess)
        print("authenticated" if ok else "NOT authenticated")
        return 0 if ok else 1

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(_cli())

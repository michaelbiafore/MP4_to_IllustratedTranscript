#!/usr/bin/env python3
"""
fetch_udemy.py — entry point for the /fetch-udemy slash command.

Downloads Udemy-provided captions for selected Sections (and Lectures within
those Sections) of a course the user owns, and writes per-lecture .txt /
.vtt / .srt plus per-section and combined `_RAW_TRANSCRIPT.md` bundles ready
for /format-transcript.

Auth: cookies_udemy.json at project root (Cookie-Editor JSON or Playwright
storage_state) — or run with `--login me@example.com` once to create it.

Usage examples:
    python scripts/fetch_udemy.py <course_url> --list
    python scripts/fetch_udemy.py <course_url> --sections 1,3-5
    python scripts/fetch_udemy.py <course_url> --sections 2 --lectures 1-3 --srt
    python scripts/fetch_udemy.py --login me@example.com

Companion plan: plans/PLAN_Udemy_FetchTranscript.md
"""
from __future__ import annotations

import argparse
import io
import json
import random
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Windows console: UTF-8 so course titles with accents/emoji don't crash.
if sys.platform == "win32":
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr.encoding != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Local modules
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import udemy_auth  # noqa: E402
import udemy_api   # noqa: E402
import vtt_to_text  # noqa: E402

PROJECT_ROOT = SCRIPTS_DIR.parent
INPUT_DIR = PROJECT_ROOT / "Input"


# ---------------------------------------------------------------------------
# Range parsing
# ---------------------------------------------------------------------------

def parse_ranges(spec: str | None) -> set[int] | None:
    """
    "1,3-5,8" → {1, 3, 4, 5, 8}.
    None / empty → None (meaning "all").
    """
    if spec is None:
        return None
    spec = spec.strip()
    if not spec:
        return None
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                lo, hi = int(a), int(b)
            except ValueError:
                raise SystemExit(f"Bad range component: {part!r}")
            if lo > hi:
                lo, hi = hi, lo
            out.update(range(lo, hi + 1))
        else:
            try:
                out.add(int(part))
            except ValueError:
                raise SystemExit(f"Bad range component: {part!r}")
    return out


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

_SAFE_RE = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
_WS_RE = re.compile(r"\s+")


def safe_filename(s: str, max_len: int = 80) -> str:
    """Make a string safe to use as a filename component."""
    s = _SAFE_RE.sub("_", s)
    s = _WS_RE.sub(" ", s).strip()
    if len(s) > max_len:
        s = s[:max_len].rstrip()
    return s or "untitled"


def kebab_slug(s: str, max_words: int = 8) -> str:
    """Lowercase kebab-case slug for directory/file naming."""
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s).lower().strip()
    parts = [p for p in re.split(r"[\s-]+", s) if p]
    return "-".join(parts[:max_words]) or "course"


# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------

def lecture_basename(section_idx: int, lecture_idx: int, title: str) -> str:
    return f"sec_{section_idx:02d}_lec_{lecture_idx:02d}_{safe_filename(title, 60)}"


# ---------------------------------------------------------------------------
# --list mode
# ---------------------------------------------------------------------------

def cmd_list(course: udemy_api.Course, course_dir_root: Path) -> int:
    print()
    print(f"Course: {course.title}")
    print(f"  id:    {course.id}")
    print(f"  slug:  {course.slug}")
    total_lectures = sum(len(s.lectures) for s in course.sections)
    print(f"  total: {len(course.sections)} sections, {total_lectures} lectures")
    print()
    for section in course.sections:
        print(f"Section {section.index}: {section.title}  ({len(section.lectures)} lectures)")
        for lec in section.lectures:
            mins = lec.length_sec // 60
            secs = lec.length_sec % 60
            dur = f"{mins:>3d}:{secs:02d}" if lec.length_sec else "  --:--"
            print(f"  Lecture {lec.index:>3d}: [{lec.asset_type:<8s}] {dur}  {lec.title}")
        print()

    # Save curriculum JSON for re-use.
    out = course_dir_root / f"{kebab_slug(course.title)}_udemy_curriculum.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "course_url": course.url,
        "course_id": course.id,
        "course_slug": course.slug,
        "title": course.title,
        "sections": [
            {
                "index": s.index,
                "title": s.title,
                "lectures": [
                    {
                        "index": l.index,
                        "id": l.id,
                        "title": l.title,
                        "asset_type": l.asset_type,
                        "length_sec": l.length_sec,
                    }
                    for l in s.lectures
                ],
            }
            for s in course.sections
        ],
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Curriculum saved → {out}")
    return 0


# ---------------------------------------------------------------------------
# --sections fetch
# ---------------------------------------------------------------------------

def fetch_one_lecture_via_api(
    sess,
    course: udemy_api.Course,
    section: udemy_api.Section,
    lecture: udemy_api.Lecture,
    out_dir: Path,
    write_srt: bool,
) -> dict:
    """
    Fetch one lecture's caption file via api-2.0 and write .vtt / .txt
    (and optionally .srt). Returns a manifest entry.
    """
    base = lecture_basename(section.index, lecture.index, lecture.title)
    txt_path = out_dir / f"{base}.txt"
    vtt_path = out_dir / f"{base}.vtt"
    srt_path = out_dir / f"{base}.srt" if write_srt else None

    entry: dict = {
        "section_index": section.index,
        "section_title": section.title,
        "lecture_index": lecture.index,
        "lecture_id": lecture.id,
        "title": lecture.title,
        "asset_type": lecture.asset_type,
        "duration_sec": lecture.length_sec,
        "status": "pending",
        "txt_path": None,
        "vtt_path": None,
        "srt_path": None,
        "chosen_locale": None,
        "timestamps_available": True,
    }

    if lecture.asset_type not in ("Video", "Article"):
        entry["status"] = "skipped"
        entry["kind"] = f"unsupported_asset_type:{lecture.asset_type}"
        return entry

    try:
        captions = udemy_api.fetch_lecture_captions(sess, course, lecture)
    except udemy_api.NoCaptionsError:
        entry["status"] = "no_captions"
        return entry
    except udemy_api.AuthError:
        entry["status"] = "error"
        entry["kind"] = "auth_failed"
        raise  # propagate so the orchestrator can stop
    except udemy_api.NotOwnedError:
        entry["status"] = "error"
        entry["kind"] = "not_enrolled"
        raise
    except Exception as e:
        entry["status"] = "error"
        entry["kind"] = "captions_lookup_failed"
        entry["message"] = str(e)
        return entry

    chosen = udemy_api.pick_english(captions)
    entry["chosen_locale"] = chosen.get("locale_id")

    try:
        vtt_text = udemy_api.download_caption(sess, chosen)
    except Exception as e:
        entry["status"] = "error"
        entry["kind"] = "caption_download_failed"
        entry["message"] = str(e)
        return entry

    out_dir.mkdir(parents=True, exist_ok=True)
    vtt_path.write_text(vtt_text, encoding="utf-8")
    entry["vtt_path"] = str(vtt_path.relative_to(PROJECT_ROOT))

    cues = vtt_to_text.parse_vtt(vtt_text)
    plaintext = vtt_to_text.cues_to_plaintext(cues)
    txt_path.write_text(plaintext, encoding="utf-8")
    entry["txt_path"] = str(txt_path.relative_to(PROJECT_ROOT))
    entry["status"] = "ok" if plaintext.strip() else "no_captions"

    if write_srt and cues:
        srt_text = vtt_to_text.cues_to_srt(cues)
        srt_path.write_text(srt_text, encoding="utf-8")
        entry["srt_path"] = str(srt_path.relative_to(PROJECT_ROOT))

    return entry


def fetch_one_lecture_via_ui(
    page,
    course: udemy_api.Course,
    section: udemy_api.Section,
    lecture: udemy_api.Lecture,
    out_dir: Path,
) -> dict:
    """UI fallback — plain text only, no timestamps."""
    import udemy_ui  # local import to avoid Playwright import on API-only runs

    base = lecture_basename(section.index, lecture.index, lecture.title)
    txt_path = out_dir / f"{base}.txt"

    entry: dict = {
        "section_index": section.index,
        "section_title": section.title,
        "lecture_index": lecture.index,
        "lecture_id": lecture.id,
        "title": lecture.title,
        "asset_type": lecture.asset_type,
        "duration_sec": lecture.length_sec,
        "status": "pending",
        "txt_path": None,
        "vtt_path": None,
        "srt_path": None,
        "chosen_locale": None,
        "timestamps_available": False,
    }

    if lecture.asset_type != "Video":
        entry["status"] = "skipped"
        entry["kind"] = f"unsupported_asset_type:{lecture.asset_type}"
        return entry

    lect_url = udemy_ui.lecture_url(course.url, lecture.id)
    try:
        text = udemy_ui.extract_transcript_via_player(page, lect_url)
    except Exception as e:
        entry["status"] = "error"
        entry["kind"] = "ui_extract_failed"
        entry["message"] = str(e)
        return entry

    if not text.strip():
        entry["status"] = "no_captions"
        return entry

    out_dir.mkdir(parents=True, exist_ok=True)
    txt_path.write_text(text, encoding="utf-8")
    entry["txt_path"] = str(txt_path.relative_to(PROJECT_ROOT))
    entry["status"] = "ok"
    return entry


# ---------------------------------------------------------------------------
# Aggregation: per-section + combined Markdown bundles
# ---------------------------------------------------------------------------

def _section_bundle_path(course_slug: str, section: udemy_api.Section) -> Path:
    return INPUT_DIR / (
        f"{course_slug}_section_{section.index:02d}_RAW_TRANSCRIPT.md"
    )


def _combined_bundle_path(course_slug: str) -> Path:
    return INPUT_DIR / f"{course_slug}_RAW_TRANSCRIPT.md"


def write_section_bundle(
    course: udemy_api.Course,
    section: udemy_api.Section,
    section_entries: list[dict],
    out_dir: Path,
    course_slug: str,
) -> Path:
    """Write Input/{slug}_section_NN_RAW_TRANSCRIPT.md for this section."""
    captured = datetime.now(timezone.utc).date().isoformat()
    fetched = [e for e in section_entries if e["status"] == "ok"]
    total_in_section = len(section.lectures)

    lines: list[str] = []
    lines.append(f"# {course.title} — Section {section.index}: {section.title}")
    lines.append("")
    lines.append(f"> Source: {course.url}")
    lines.append(f"> Section: {section.index} of {len(course.sections)}")
    lines.append(f"> Lectures: {len(fetched)}/{total_in_section}")
    lines.append(f"> Captured: {captured}")
    lines.append("")

    for entry in section_entries:
        title = entry["title"]
        idx = entry["lecture_index"]

        if entry["status"] == "ok":
            txt_rel = entry.get("txt_path")
            text = ""
            if txt_rel:
                text = (PROJECT_ROOT / txt_rel).read_text(encoding="utf-8")
            lines.append(f"## Lecture {section.index}.{idx} — {title}")
            lines.append("")
            lines.append(text.strip())
            lines.append("")
        elif entry["status"] == "no_captions":
            lines.append(f"## Lecture {section.index}.{idx} — {title}")
            lines.append("")
            lines.append("> _Lecture skipped: no captions available._")
            lines.append("")
        elif entry["status"] == "skipped":
            lines.append(f"## Lecture {section.index}.{idx} — {title}")
            lines.append("")
            lines.append(
                f"> _Lecture skipped: {entry.get('kind', 'unsupported asset')}._"
            )
            lines.append("")
        else:
            lines.append(f"## Lecture {section.index}.{idx} — {title}")
            lines.append("")
            kind = entry.get("kind", "error")
            msg = entry.get("message", "")
            lines.append(f"> _Lecture errored: {kind}. {msg}_")
            lines.append("")

    out_path = _section_bundle_path(course_slug, section)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out_path


def write_combined_bundle(
    course: udemy_api.Course,
    selected_sections: list[udemy_api.Section],
    entries_by_section: dict[int, list[dict]],
    course_slug: str,
) -> Path:
    """Write a single Input/{slug}_RAW_TRANSCRIPT.md with all selected sections."""
    captured = datetime.now(timezone.utc).date().isoformat()
    lines: list[str] = []
    lines.append(f"# {course.title}")
    lines.append("")
    lines.append(f"> Source: {course.url}")
    lines.append(
        f"> Sections fetched: {', '.join(str(s.index) for s in selected_sections)}"
    )
    lines.append(f"> Captured: {captured}")
    lines.append("")

    for section in selected_sections:
        lines.append("---")
        lines.append("")
        lines.append(f"## Section {section.index}: {section.title}")
        lines.append("")
        for entry in entries_by_section.get(section.index, []):
            title = entry["title"]
            idx = entry["lecture_index"]
            if entry["status"] == "ok":
                text = ""
                if entry.get("txt_path"):
                    text = (PROJECT_ROOT / entry["txt_path"]).read_text(encoding="utf-8")
                lines.append(f"### Lecture {section.index}.{idx} — {title}")
                lines.append("")
                lines.append(text.strip())
                lines.append("")
            elif entry["status"] == "no_captions":
                lines.append(f"### Lecture {section.index}.{idx} — {title}")
                lines.append("")
                lines.append("> _Lecture skipped: no captions available._")
                lines.append("")
            elif entry["status"] == "skipped":
                lines.append(f"### Lecture {section.index}.{idx} — {title}")
                lines.append("")
                lines.append(
                    f"> _Lecture skipped: {entry.get('kind', 'unsupported asset')}._"
                )
                lines.append("")
            else:
                lines.append(f"### Lecture {section.index}.{idx} — {title}")
                lines.append("")
                kind = entry.get("kind", "error")
                msg = entry.get("message", "")
                lines.append(f"> _Lecture errored: {kind}. {msg}_")
                lines.append("")

    out_path = _combined_bundle_path(course_slug)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------

def run_fetch(args) -> int:
    # 1. Auth
    cookie_path = Path(args.cookies) if args.cookies else udemy_auth.COOKIE_PATH

    if args.login:
        udemy_auth.login_interactive(args.login, cookie_path)
        if not args.course_url:
            print("[done] --login complete. Re-run with a course URL to fetch.")
            return 0

    if not args.course_url:
        print("error: course URL is required (unless using --login alone)", file=sys.stderr)
        return 2

    try:
        sess = udemy_auth.make_session(cookie_path)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        print(
            "Hint: run `python scripts/fetch_udemy.py --login you@example.com` first.",
            file=sys.stderr,
        )
        return 2

    if not udemy_auth.session_is_authenticated(sess):
        print(
            f"Cookies in {cookie_path} are not authenticated. "
            "Run with --login <email> to refresh.",
            file=sys.stderr,
        )
        return 2

    # 2. Resolve course + curriculum
    print(f"[course] resolving {args.course_url} …")
    try:
        course = udemy_api.resolve_course(sess, args.course_url)
    except udemy_api.NotFoundError:
        print(
            f"Course not found at {args.course_url}. "
            "Check the URL or whether the course is enrolled.",
            file=sys.stderr,
        )
        return 3
    print(f"[course] {course.title} (id={course.id}, slug={course.slug})")

    print("[curriculum] walking subscriber-curriculum-items …")
    course = udemy_api.fetch_curriculum(sess, course)
    course_slug = kebab_slug(course.title)

    # 3. --list short-circuits
    if args.list:
        return cmd_list(course, INPUT_DIR)

    if args.sections is None:
        print(
            "error: --sections is required (or use --list to see the curriculum)",
            file=sys.stderr,
        )
        return 2

    # 4. Build selectors
    section_set = parse_ranges(args.sections)
    lecture_set = parse_ranges(args.lectures)

    selected_sections = [
        s for s in course.sections if section_set is None or s.index in section_set
    ]
    if not selected_sections:
        print(
            f"error: no sections matched {args.sections!r}. "
            f"Course has {len(course.sections)} sections (1..{len(course.sections)}).",
            file=sys.stderr,
        )
        return 2

    pairs = list(udemy_api.iter_selected_lectures(course, section_set, lecture_set))
    if not pairs:
        print("error: no lectures matched the section/lecture selectors.", file=sys.stderr)
        return 2

    print(
        f"[plan] fetching {len(pairs)} lectures across "
        f"{len(selected_sections)} sections "
        f"(mode: {'ui' if args.ui else 'api'}{', srt' if args.srt else ''})"
    )

    # 5. Fetch
    out_dir = INPUT_DIR / f"{course_slug}_udemy"
    entries_by_section: dict[int, list[dict]] = {s.index: [] for s in selected_sections}

    pw_ctx = None
    page = None
    if args.ui:
        # Open one Playwright context for the whole run.
        import udemy_ui
        pw_ctx = udemy_ui.ui_context(cookie_path, headless=args.headless)
        browser, context, page = pw_ctx.__enter__()

    try:
        for i, (section, lecture) in enumerate(pairs, start=1):
            label = (
                f"S{section.index:02d}.L{lecture.index:02d}  "
                f"{lecture.title[:60]}"
            )
            print(f"[{i:>3d}/{len(pairs)}] {label}")

            try:
                if args.ui:
                    entry = fetch_one_lecture_via_ui(
                        page, course, section, lecture, out_dir
                    )
                else:
                    entry = fetch_one_lecture_via_api(
                        sess, course, section, lecture, out_dir, args.srt
                    )
            except udemy_api.AuthError:
                print(
                    "  AUTH ERROR — cookies expired mid-run. "
                    "Run with --login to refresh.",
                    file=sys.stderr,
                )
                return 4
            except udemy_api.NotOwnedError as e:
                print(f"  NOT ENROLLED: {e}", file=sys.stderr)
                return 5

            entries_by_section[section.index].append(entry)

            status = entry["status"]
            if status == "ok":
                print(f"      ok    → {entry['txt_path']}")
            elif status == "no_captions":
                print(f"      no_captions")
            elif status == "skipped":
                print(f"      skipped ({entry.get('kind')})")
            else:
                print(f"      ERROR ({entry.get('kind')}) {entry.get('message','')}")

            # Polite throttle between lectures
            time.sleep(random.uniform(0.5, 1.5))
    finally:
        if pw_ctx is not None:
            try:
                pw_ctx.__exit__(None, None, None)
            except Exception:
                pass

    # 6. Aggregation
    print()
    print("[bundle] writing per-section RAW_TRANSCRIPT files …")
    section_bundles: list[Path] = []
    for section in selected_sections:
        bundle = write_section_bundle(
            course, section, entries_by_section[section.index],
            out_dir, course_slug,
        )
        section_bundles.append(bundle)
        print(f"  → {bundle.relative_to(PROJECT_ROOT)}")

    combined_bundle: Path | None = None
    if args.out_mode in ("both", "per-section,combined", "combined") or args.out_mode == "both":
        combined_bundle = write_combined_bundle(
            course, selected_sections, entries_by_section, course_slug,
        )
        print(f"  → {combined_bundle.relative_to(PROJECT_ROOT)}")

    # 7. Manifest
    manifest_path = INPUT_DIR / f"{course_slug}_udemy_manifest.json"
    flat_entries: list[dict] = []
    for s in selected_sections:
        flat_entries.extend(entries_by_section[s.index])
    manifest = {
        "course_url": course.url,
        "course_id": course.id,
        "course_slug": course_slug,
        "title": course.title,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sections_requested": sorted(s.index for s in selected_sections),
        "lectures_requested_filter": args.lectures,
        "auth_method": "ui" if args.ui else "cookies",
        "out_mode": args.out_mode,
        "lectures": flat_entries,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  → {manifest_path.relative_to(PROJECT_ROOT)}")

    # 8. Summary
    by_status: dict[str, int] = {}
    for e in flat_entries:
        by_status[e["status"]] = by_status.get(e["status"], 0) + 1

    print()
    print("=" * 60)
    print(f"DONE — {course.title}")
    print("=" * 60)
    print(
        f"  ok:          {by_status.get('ok', 0)}\n"
        f"  no_captions: {by_status.get('no_captions', 0)}\n"
        f"  skipped:     {by_status.get('skipped', 0)}\n"
        f"  errors:      {by_status.get('error', 0)}"
    )
    print()
    print("Next steps:")
    for bundle in section_bundles:
        print(
            f"  /format-transcript {bundle.relative_to(PROJECT_ROOT)}"
        )
    if combined_bundle is not None:
        print(
            f"  # or, combined across sections:\n"
            f"  /format-transcript {combined_bundle.relative_to(PROJECT_ROOT)}"
        )
    print()
    print(
        "Reminder: cookies_udemy.json grants full Udemy account access. "
        "Delete it when you're done."
    )
    return 0


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Fetch Udemy course transcripts (you must own the course).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("course_url", nargs="?", help="https://www.udemy.com/course/<slug>/")
    p.add_argument(
        "--sections",
        help="1-based section ranges, e.g. '1,3-5,8'. Required unless --list/--login.",
    )
    p.add_argument(
        "--lectures",
        help="1-based lecture ranges within selected sections, e.g. '1-3'. Default: all.",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="Print the curriculum (numbered) and save curriculum JSON, then exit.",
    )
    p.add_argument(
        "--login",
        metavar="EMAIL",
        help="Run an interactive Playwright login (handles 6-digit email code), "
             "save cookies_udemy.json, then continue (or exit if no course given).",
    )
    p.add_argument(
        "--ui",
        action="store_true",
        help="Skip the api-2.0 path; scrape transcripts from the player UI via Playwright.",
    )
    p.add_argument(
        "--srt",
        action="store_true",
        help="Also write a .srt per lecture (only meaningful in API mode).",
    )
    p.add_argument(
        "--out-mode",
        choices=("per-section", "combined", "both"),
        default="both",
        help="Which Markdown bundles to produce. Default: both.",
    )
    p.add_argument(
        "--cookies",
        help="Path to cookies file. Default: cookies_udemy.json at project root.",
    )
    p.add_argument(
        "--headless",
        action="store_true",
        help="Run UI mode headless (default: show the browser).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run_fetch(args)
    except KeyboardInterrupt:
        print("\n[abort] interrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\nfatal: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Tiny WebVTT parser used by fetch_udemy.py.

Just enough to handle Udemy's caption files. We deliberately do NOT depend on
webvtt-py — the cue grammar Udemy emits is the simple WEBVTT subset:

    WEBVTT

    00:00:01.234 --> 00:00:04.567
    Some line of text
    sometimes wrapped over two lines

    00:00:04.700 --> 00:00:08.000
    Next cue

Public API:
    parse_vtt(text) -> list[Cue]
    cues_to_plaintext(cues) -> str
    cues_to_srt(cues) -> str
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass
class Cue:
    start: float          # seconds
    end: float            # seconds
    text: str             # cue text, newlines preserved within the cue


# HH:MM:SS.mmm OR MM:SS.mmm
_TS_RE = re.compile(r"(\d{1,3}):(\d{2})(?::(\d{2}))?\.(\d{3})")
_ARROW_RE = re.compile(
    r"\s*(?P<a>[^\s]+)\s+-->\s+(?P<b>[^\s]+)\b"
)


def _parse_ts(s: str) -> float:
    m = _TS_RE.fullmatch(s.strip())
    if not m:
        raise ValueError(f"Bad timestamp: {s!r}")
    a, b, c, ms = m.groups()
    if c is None:
        # MM:SS.mmm
        h, mn, sec = 0, int(a), int(b)
    else:
        h, mn, sec = int(a), int(b), int(c)
    return h * 3600 + mn * 60 + sec + int(ms) / 1000.0


def parse_vtt(text: str) -> list[Cue]:
    """
    Parse a WebVTT document into Cue objects.
    Strips the WEBVTT header and any NOTE / STYLE / REGION blocks.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Drop BOM if present
    if text.startswith("﻿"):
        text = text[1:]

    blocks = re.split(r"\n\s*\n", text.strip())
    cues: list[Cue] = []

    for blk in blocks:
        lines = blk.split("\n")
        if not lines:
            continue
        first = lines[0].strip()
        if first.upper().startswith("WEBVTT"):
            continue
        if first.upper().startswith(("NOTE", "STYLE", "REGION")):
            continue

        # Optional cue id line — skip if present
        idx = 0
        if "-->" not in lines[idx]:
            # could be a cue identifier
            if len(lines) > 1 and "-->" in lines[1]:
                idx = 1
            else:
                continue  # malformed block, skip

        m = _ARROW_RE.match(lines[idx])
        if not m:
            continue
        try:
            start = _parse_ts(m.group("a"))
            end = _parse_ts(m.group("b"))
        except ValueError:
            continue

        body = "\n".join(lines[idx + 1:]).strip()
        body = _strip_cue_tags(body)
        if not body:
            continue
        cues.append(Cue(start=start, end=end, text=body))

    return cues


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_cue_tags(text: str) -> str:
    """Remove cue payload tags (<v Speaker>, <c.classname>, &nbsp;, etc)."""
    text = _TAG_RE.sub("", text)
    text = (
        text
        .replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    return text


# ---------------------------------------------------------------------------
# Plaintext reflow
# ---------------------------------------------------------------------------

_TERMINATORS = (".", "!", "?")


def cues_to_plaintext(cues: Iterable[Cue]) -> str:
    """
    Stitch cues into readable paragraphs.

    Rules:
      - Within a cue, replace internal newlines with single spaces.
      - Deduplicate cues whose text equals the previous cue's text (Udemy
        sometimes emits rolling captions where successive cues repeat).
      - Insert a paragraph break ("\\n\\n") between cues when EITHER:
          (a) the gap between cue end and next cue start is > 2.0s, OR
          (b) the previous cue ended in . ! ? AND the next cue starts with
              a capital letter.
      - Otherwise join with a single space, fixing the cross-cue word-merge
        bug (insert a space when prev doesn't end in whitespace and next
        doesn't start with one).
    """
    cues = list(cues)
    if not cues:
        return ""

    out: list[str] = []
    prev_text: str | None = None
    prev_end: float | None = None

    for c in cues:
        body = re.sub(r"\s+", " ", c.text).strip()
        if not body:
            continue
        if body == prev_text:
            # Pure duplicate — Udemy rolling-caption artifact.
            prev_end = c.end
            continue

        if not out:
            out.append(body)
        else:
            gap = (c.start - (prev_end or c.start))
            prev_chunk = out[-1]
            paragraph_break = (
                gap > 2.0
                or (
                    prev_chunk.rstrip().endswith(_TERMINATORS)
                    and body[:1].isupper()
                )
            )
            if paragraph_break:
                out.append(body)
            else:
                # Fix cross-cue word merge: ensure exactly one space between.
                if not prev_chunk.endswith(" ") and not body.startswith(" "):
                    out[-1] = prev_chunk + " " + body
                else:
                    out[-1] = prev_chunk + body

        prev_text = body
        prev_end = c.end

    # Final whitespace squeeze on each paragraph
    paragraphs = [re.sub(r"[ \t]+", " ", p).strip() for p in out]
    return "\n\n".join(paragraphs)


# ---------------------------------------------------------------------------
# VTT → SRT (mechanical: replace `.` before millis with `,`, add seq numbers)
# ---------------------------------------------------------------------------

def _fmt_srt_ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:
        ms = 0
        s += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def cues_to_srt(cues: Iterable[Cue]) -> str:
    """Render cues as a SubRip (.srt) document."""
    out: list[str] = []
    for n, c in enumerate(cues, start=1):
        body = re.sub(r"\s+", " ", c.text).strip()
        if not body:
            continue
        out.append(str(n))
        out.append(f"{_fmt_srt_ts(c.start)} --> {_fmt_srt_ts(c.end)}")
        out.append(body)
        out.append("")
    return "\n".join(out).rstrip() + "\n"

#!/usr/bin/env python3
"""
Thin wrappers around Udemy's authenticated api-2.0 endpoints.

Endpoints used:
  - GET /api-2.0/courses/{slug}/                                 → resolve slug → id
  - GET /api-2.0/courses/{course_id}/subscriber-curriculum-items → curriculum
  - GET /api-2.0/users/me/subscribed-courses/{course_id}/lectures/{lecture_id}/
        ?fields[lecture]=asset&fields[asset]=captions             → caption metadata
  - GET <signed cdn url>                                         → caption file (VTT)

All functions take a `requests.Session` (built by udemy_auth.make_session())
and raise typed errors that the orchestrator can switch on.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Iterator
from urllib.parse import urlparse

import requests


API_ROOT = "https://www.udemy.com/api-2.0"


# ---------------------------------------------------------------------------
# Typed errors
# ---------------------------------------------------------------------------

class UdemyError(Exception):
    """Base for all errors raised by this module."""


class AuthError(UdemyError):
    """Cookies are missing/expired — caller should suggest --login."""


class NotOwnedError(UdemyError):
    """The course is reachable but the account is not enrolled."""


class NoCaptionsError(UdemyError):
    """The lecture exists but has no caption tracks."""


class NotFoundError(UdemyError):
    """404 from Udemy — wrong slug or wrong lecture id."""


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"/course/([^/?#]+)")


def slug_from_course_url(course_url: str) -> str:
    """Extract the course slug from any /course/<slug>/... URL form."""
    m = _SLUG_RE.search(course_url)
    if not m:
        raise ValueError(
            f"Could not extract course slug from {course_url!r}. "
            "Expected something like https://www.udemy.com/course/<slug>/"
        )
    return m.group(1)


# ---------------------------------------------------------------------------
# Low-level request with typed error mapping
# ---------------------------------------------------------------------------

def _get(sess: requests.Session, url: str, **kwargs) -> dict:
    """GET → JSON, with status code → typed error mapping."""
    r = sess.get(url, timeout=kwargs.pop("timeout", 30), **kwargs)
    if r.status_code == 401 or r.status_code == 403:
        # Distinguish "cookies dead" from "you don't own this course".
        # /users/me/ would 401; course endpoints will sometimes 403 for
        # not-enrolled. We treat 401 as auth, 403 as ownership.
        if r.status_code == 401:
            raise AuthError(
                f"401 from {url} — cookies appear expired. Run with --login."
            )
        raise NotOwnedError(
            f"403 from {url} — your account may not be enrolled in this course."
        )
    if r.status_code == 404:
        raise NotFoundError(f"404 from {url}")
    if r.status_code == 429:
        retry = int(r.headers.get("Retry-After", "5"))
        time.sleep(retry)
        return _get(sess, url, **kwargs)
    r.raise_for_status()
    try:
        return r.json()
    except ValueError as e:
        raise UdemyError(f"Non-JSON response from {url}: {e}")


# ---------------------------------------------------------------------------
# Curriculum data shapes
# ---------------------------------------------------------------------------

@dataclass
class Lecture:
    id: int
    index: int                # 1-based within section
    title: str
    asset_type: str           # Video, Article, Quiz, …
    length_sec: int = 0


@dataclass
class Section:
    index: int                # 1-based across the course
    title: str
    lectures: list[Lecture] = field(default_factory=list)


@dataclass
class Course:
    id: int
    slug: str
    title: str
    url: str
    sections: list[Section] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Endpoint wrappers
# ---------------------------------------------------------------------------

def resolve_course(sess: requests.Session, course_url: str) -> Course:
    """slug → numeric id + title, via /api-2.0/courses/{slug}/."""
    slug = slug_from_course_url(course_url)
    url = f"{API_ROOT}/courses/{slug}/"
    body = _get(
        sess,
        url,
        params={"fields[course]": "id,title,url"},
    )
    return Course(
        id=int(body["id"]),
        slug=slug,
        title=body.get("title") or slug,
        url=course_url,
    )


def fetch_curriculum(sess: requests.Session, course: Course) -> Course:
    """
    Walk subscriber-curriculum-items and group lectures under their chapters.
    Returns the same Course object with `sections` populated.
    """
    url = (
        f"{API_ROOT}/courses/{course.id}/subscriber-curriculum-items/"
    )
    params = {
        "page_size": "200",
        "fields[lecture]": "title,object_index,asset",
        "fields[chapter]": "title,object_index",
        "fields[asset]": "asset_type,length",
    }

    items: list[dict] = []
    next_url: str | None = url
    next_params: dict | None = params
    pages = 0
    while next_url:
        body = _get(sess, next_url, params=next_params)
        items.extend(body.get("results", []))
        next_url = body.get("next") or None
        # `next` from the API already includes the query string, so don't
        # re-pass params on subsequent calls.
        next_params = None
        pages += 1
        if pages > 50:
            raise UdemyError(
                "Curriculum pagination exceeded 50 pages — bailing out."
            )

    sections: list[Section] = []
    current: Section | None = None
    section_idx = 0
    lecture_idx = 0

    for it in items:
        cls = it.get("_class")
        if cls == "chapter":
            section_idx += 1
            current = Section(
                index=section_idx,
                title=it.get("title") or f"Section {section_idx}",
            )
            sections.append(current)
            lecture_idx = 0
            continue

        if cls == "lecture":
            if current is None:
                # Some courses start with a lecture before any chapter — invent
                # a synthetic Section 1.
                section_idx += 1
                current = Section(index=section_idx, title="Introduction")
                sections.append(current)
                lecture_idx = 0
            lecture_idx += 1
            asset = it.get("asset") or {}
            current.lectures.append(
                Lecture(
                    id=int(it["id"]),
                    index=lecture_idx,
                    title=it.get("title") or f"Lecture {lecture_idx}",
                    asset_type=asset.get("asset_type") or "Unknown",
                    length_sec=int(asset.get("length") or 0),
                )
            )
            continue

        # quiz / practice / coding-exercise — silently skipped for v1.

    course.sections = sections
    return course


def fetch_lecture_captions(
    sess: requests.Session,
    course: Course,
    lecture: Lecture,
) -> list[dict]:
    """
    Return the `captions` array for a lecture asset, e.g.:
      [{"id": ..., "url": ..., "locale_id": "en_US", "title": "English",
        "video_label": "English", "is_translation": false, ...}, ...]

    Raises NoCaptionsError if the array is empty / missing.
    """
    url = (
        f"{API_ROOT}/users/me/subscribed-courses/{course.id}"
        f"/lectures/{lecture.id}/"
    )
    body = _get(
        sess,
        url,
        params={
            "fields[lecture]": "asset",
            "fields[asset]": "captions,asset_type,time_estimation",
        },
    )
    asset = body.get("asset") or {}
    captions = asset.get("captions") or []
    if not captions:
        raise NoCaptionsError(
            f"Lecture {lecture.id} ({lecture.title!r}) has no captions."
        )
    return captions


def pick_english(captions: list[dict]) -> dict:
    """
    Pick the best English caption track:
      1. locale_id == 'en_US'
      2. any locale_id starting with 'en'
      3. is_translation == False (original language)
      4. first one
    """
    for c in captions:
        if c.get("locale_id") == "en_US":
            return c
    for c in captions:
        if (c.get("locale_id") or "").startswith("en"):
            return c
    for c in captions:
        if c.get("is_translation") is False:
            return c
    return captions[0]


def download_caption(sess: requests.Session, caption: dict) -> str:
    """Fetch the VTT (or SRT) file referenced by the caption record."""
    cap_url = caption.get("url") or caption.get("file_name")
    if not cap_url:
        raise UdemyError(f"Caption record has no url: {caption}")

    parsed = urlparse(cap_url)
    use_session = parsed.netloc.endswith("udemy.com")
    fetcher = sess if use_session else requests

    r = fetcher.get(cap_url, timeout=30)
    if r.status_code != 200:
        raise UdemyError(
            f"Caption download failed ({r.status_code}) for {cap_url}"
        )
    # Captions are usually UTF-8; trust requests' decoding.
    return r.text


# ---------------------------------------------------------------------------
# Convenience: walk lectures honoring section/lecture selectors
# ---------------------------------------------------------------------------

def iter_selected_lectures(
    course: Course,
    section_set: set[int] | None,
    lecture_set: set[int] | None,
) -> Iterator[tuple[Section, Lecture]]:
    """
    Yield (section, lecture) for every lecture matching the selectors.

    section_set=None means "all sections".
    lecture_set=None means "all lectures within each selected section".
    """
    for section in course.sections:
        if section_set is not None and section.index not in section_set:
            continue
        for lecture in section.lectures:
            if lecture_set is not None and lecture.index not in lecture_set:
                continue
            yield section, lecture

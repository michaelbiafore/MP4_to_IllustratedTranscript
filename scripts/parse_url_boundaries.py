#!/usr/bin/env python3
"""
parse_url_boundaries.py — extract Udemy lecture IDs from per-minute OCR
results, snap to known curriculum IDs (correcting OCR errors), and emit
lecture-boundary runs.

Usage:
  python scripts/parse_url_boundaries.py <ocr.json> <curriculum.json>
"""
import argparse
import json
import re
import sys


def candidate_ids(ocr_text: str) -> list[str]:
    """Find all plausible 8-digit lecture IDs in the OCR text."""
    # The URL pattern is "lecture/NNNNNNNN#overview" but OCR may garble it
    # so we just grep for any 8-digit number.
    return re.findall(r"\d{8}", ocr_text)


def snap_to_curriculum(candidate: str, known_ids: list[int]) -> int | None:
    """Snap a candidate 8-digit string to the nearest known ID
    by character-position equality (Hamming-like)."""
    best, best_match = 99, None
    for kid in known_ids:
        ks = str(kid)
        if len(ks) != len(candidate):
            continue
        diff = sum(a != b for a, b in zip(ks, candidate))
        if diff < best:
            best, best_match = diff, kid
    # Allow up to 2 mismatches (single-char OCR errors)
    return best_match if best <= 2 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ocr_json")
    ap.add_argument("curriculum_json")
    ap.add_argument("--section-title-prefix", default="Claude Cowork")
    args = ap.parse_args()

    rows = json.load(open(args.ocr_json))
    cur = json.load(open(args.curriculum_json))
    sec = [s for s in cur["sections"] if s["title"].startswith(args.section_title_prefix)][0]
    known = [lec["id"] for lec in sec["lectures"]]
    id_to_lec = {lec["id"]: lec for lec in sec["lectures"]}

    print(f"Section: {sec['title']}")
    print(f"Known IDs: {known[0]}…{known[-1]} ({len(known)} lectures)")
    print()

    # Per-minute: best-match lecture ID
    per_min = []
    for r in rows:
        cands = candidate_ids(r["title"])
        best = None
        for c in cands:
            m = snap_to_curriculum(c, known)
            if m is not None:
                best = m
                break
        per_min.append((r["t_sec"], r["t_str"], best, r["title"][:80]))

    # Print with snapped IDs
    for t_sec, t_str, lid, raw in per_min:
        idx = id_to_lec[lid]["index"] if lid else "?"
        title = (id_to_lec[lid]["title"][:40] if lid else "")
        print(f"  t={t_str:>6s}  lid={lid or '       --':>8}  L{idx:>2}  {title}")

    # Identify runs
    print("\n--- Lecture runs ---")
    last_lid, run_start = None, 0
    for i, (t_sec, _, lid, _) in enumerate(per_min):
        if lid != last_lid:
            if last_lid is not None:
                idx = id_to_lec[last_lid]["index"]
                print(f"  L{idx:02d}  {run_start//60}:{run_start%60:02d} – {(t_sec)//60}:{(t_sec)%60:02d}  ({(t_sec - run_start)//60} min)")
            run_start = t_sec
            last_lid = lid
    # Final run
    if last_lid is not None:
        end = per_min[-1][0] + 60
        idx = id_to_lec[last_lid]["index"]
        print(f"  L{idx:02d}  {run_start//60}:{run_start%60:02d} – {end//60}:{end%60:02d}  ({(end - run_start)//60} min)")


if __name__ == "__main__":
    main()

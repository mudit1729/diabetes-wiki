#!/usr/bin/env python3
"""Batch ingest diabetes trials through the OCR/LLM pipeline.

Reads trial URL list from TRIAL_URLS below, runs the pipeline for each,
and prints success/failure to stdout. Failures are logged but don't
stop the batch.

Usage:
    python batch_ingest.py                  # run all
    python batch_ingest.py --limit 3        # first 3 only
    python batch_ingest.py --slug sustain-6 # one specific trial
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Load .env so MISTRAL_KEY etc. are available
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())

from paper_ingest import ingest_pipeline


# (slug, url) — URLs prioritize PMC open-access > publisher full-text > PubMed page
TRIAL_URLS: list[tuple[str, str]] = [
    # Glycemic foundations
    ("dcct",          "https://pubmed.ncbi.nlm.nih.gov/8366922/"),
    ("ukpds-34",     "https://pubmed.ncbi.nlm.nih.gov/9742977/"),
    ("ukpds-80",     "https://pubmed.ncbi.nlm.nih.gov/18784090/"),
    ("accord",       "https://pubmed.ncbi.nlm.nih.gov/18539917/"),
    ("advance",      "https://pubmed.ncbi.nlm.nih.gov/18539916/"),
    ("vadt",         "https://pubmed.ncbi.nlm.nih.gov/19092145/"),
    # GLP-1 / incretin outcomes
    ("leader",        "https://pubmed.ncbi.nlm.nih.gov/27295427/"),
    ("sustain-6",     "https://pubmed.ncbi.nlm.nih.gov/27633186/"),
    ("rewind",        "https://pubmed.ncbi.nlm.nih.gov/31189511/"),
    ("flow",          "https://pubmed.ncbi.nlm.nih.gov/38785209/"),
    # SGLT2 outcomes
    ("empa-reg",      "https://pubmed.ncbi.nlm.nih.gov/26378978/"),
    ("canvas",        "https://pubmed.ncbi.nlm.nih.gov/28605608/"),
    ("declare-timi-58","https://pubmed.ncbi.nlm.nih.gov/30415602/"),
    ("credence",      "https://pubmed.ncbi.nlm.nih.gov/30990260/"),
    ("dapa-ckd",      "https://pubmed.ncbi.nlm.nih.gov/32970396/"),
    ("empa-kidney",   "https://pubmed.ncbi.nlm.nih.gov/36331190/"),
]


def run_one(slug: str, url: str) -> dict:
    print(f"\n{'='*80}")
    print(f"[{slug}]  {url}")
    print(f"{'='*80}")

    result = {"slug": slug, "url": url, "success": False, "error": None,
              "page_path": None, "citations": 0}
    try:
        for event_name, payload in ingest_pipeline(url=url, slug_hint=slug):
            if event_name == "status":
                stage = payload.get("stage", "?")
                msg = payload.get("message", "")
                print(f"  [{stage}] {msg}")
            elif event_name == "metadata":
                title = payload.get("title", "?")[:80]
                cits = payload.get("citations", 0)
                print(f"  [metadata] {title} · {cits} citations")
                result["citations"] = cits
            elif event_name == "done":
                print(f"  [done] {payload.get('page_path')}")
                result["success"] = True
                result["page_path"] = payload.get("page_path")
                result["citations"] = payload.get("citations", 0)
            elif event_name == "error":
                print(f"  [ERROR] {payload.get('message')}")
                result["error"] = payload.get("message")
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        print(f"  [PIPELINE ERROR] {result['error']}")

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Run only first N trials")
    parser.add_argument("--slug", help="Run a single trial by slug")
    parser.add_argument("--start", type=int, default=0, help="Start at index N")
    args = parser.parse_args()

    targets = TRIAL_URLS
    if args.slug:
        targets = [(s, u) for (s, u) in TRIAL_URLS if s == args.slug]
        if not targets:
            print(f"No trial with slug '{args.slug}'")
            sys.exit(1)
    elif args.limit:
        targets = TRIAL_URLS[args.start : args.start + args.limit]

    print(f"Running pipeline for {len(targets)} trials")

    results = []
    for slug, url in targets:
        results.append(run_one(slug, url))
        # gentle pause between calls to avoid rate limits
        time.sleep(2)

    # Summary
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    succ = [r for r in results if r["success"]]
    fail = [r for r in results if not r["success"]]
    print(f"Succeeded: {len(succ)}/{len(results)}")
    print(f"Failed:    {len(fail)}/{len(results)}")
    if succ:
        print("\nWritten:")
        for r in succ:
            print(f"  ✓ {r['slug']:20s}  {r['page_path']}  ({r['citations']} citations)")
    if fail:
        print("\nFailed (likely paywall / OCR block):")
        for r in fail:
            print(f"  ✗ {r['slug']:20s}  {r['error']}")


if __name__ == "__main__":
    main()

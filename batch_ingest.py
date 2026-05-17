#!/usr/bin/env python3
"""Batch ingest diabetes trials through the OCR/LLM pipeline.

Reads trial URL list from TRIAL_URLS below, runs the pipeline for each,
and prints success/failure to stdout. Failures are logged but don't
stop the batch.

Usage:
    python batch_ingest.py                  # run all, write locally only
    python batch_ingest.py --limit 3        # first 3 only
    python batch_ingest.py --slug sustain-6 # one specific trial
    python batch_ingest.py --autopush       # commit/push generated pages
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


# (slug, url, domain) — run `find_open_access.py` first when possible; if
# trial_urls.json has an OA PDF for a slug, batch_ingest will use that PDF URL.
TRIAL_URLS: list[tuple[str, str, str]] = [
    # Glycemic foundations
    ("dcct",          "https://pubmed.ncbi.nlm.nih.gov/8366922/", "insulin-technology"),
    ("edic-cvd",      "https://pubmed.ncbi.nlm.nih.gov/26861924/", "glycemic-targets"),
    ("ukpds-33",      "https://pubmed.ncbi.nlm.nih.gov/9742976/", "glycemic-targets"),
    ("ukpds-34",      "https://pubmed.ncbi.nlm.nih.gov/9742977/", "initial-therapy"),
    ("ukpds-80",      "https://pubmed.ncbi.nlm.nih.gov/18784090/", "glycemic-targets"),
    ("accord",        "https://pubmed.ncbi.nlm.nih.gov/18539917/", "glycemic-targets"),
    ("advance",       "https://pubmed.ncbi.nlm.nih.gov/18539916/", "glycemic-targets"),
    ("vadt",          "https://pubmed.ncbi.nlm.nih.gov/19092145/", "glycemic-targets"),
    ("dpp",           "https://pubmed.ncbi.nlm.nih.gov/11832527/", "diagnosis-classification"),
    ("grade",         "https://pubmed.ncbi.nlm.nih.gov/36129996/", "initial-therapy"),
    # GLP-1 / incretin outcomes
    ("leader",        "https://pubmed.ncbi.nlm.nih.gov/27295427/", "incretin-therapy"),
    ("sustain-1",     "https://pubmed.ncbi.nlm.nih.gov/?term=SUSTAIN+1+semaglutide+monotherapy", "incretin-therapy"),
    ("sustain-2",     "https://pubmed.ncbi.nlm.nih.gov/?term=SUSTAIN+2+semaglutide+sitagliptin", "incretin-therapy"),
    ("sustain-3",     "https://pubmed.ncbi.nlm.nih.gov/?term=SUSTAIN+3+semaglutide+exenatide", "incretin-therapy"),
    ("sustain-4",     "https://pubmed.ncbi.nlm.nih.gov/?term=SUSTAIN+4+semaglutide+insulin+glargine", "incretin-therapy"),
    ("sustain-5",     "https://pmc.ncbi.nlm.nih.gov/articles/PMC5991220/", "incretin-therapy"),
    ("sustain-6",     "https://pubmed.ncbi.nlm.nih.gov/27633186/", "incretin-therapy"),
    ("rewind",        "https://pubmed.ncbi.nlm.nih.gov/31189511/", "incretin-therapy"),
    ("surpass-cvot",  "https://pubmed.ncbi.nlm.nih.gov/?term=SURPASS-CVOT+tirzepatide+dulaglutide+cardiovascular+outcomes", "incretin-therapy"),
    ("flow",          "https://pubmed.ncbi.nlm.nih.gov/38785209/", "ckd"),
    # SGLT2 outcomes
    ("empa-reg",      "https://pubmed.ncbi.nlm.nih.gov/26378978/", "sglt2-therapy"),
    ("canvas",        "https://pubmed.ncbi.nlm.nih.gov/28605608/", "sglt2-therapy"),
    ("declare-timi-58","https://pubmed.ncbi.nlm.nih.gov/30415602/", "sglt2-therapy"),
    ("credence",      "https://pubmed.ncbi.nlm.nih.gov/30990260/", "ckd"),
    ("dapa-ckd",      "https://pubmed.ncbi.nlm.nih.gov/32970396/", "ckd"),
    ("empa-kidney",   "https://pubmed.ncbi.nlm.nih.gov/36331190/", "ckd"),
    # Mineralocorticoid receptor antagonist / residual kidney risk
    ("fidelio-dkd",   "https://pubmed.ncbi.nlm.nih.gov/33264825/", "ckd"),
    ("figaro-dkd",   "https://pubmed.ncbi.nlm.nih.gov/34449181/", "ckd"),
    # Insulin strategy and safety
    ("origin",        "https://pubmed.ncbi.nlm.nih.gov/22686416/", "insulin-technology"),
    ("devote",        "https://pubmed.ncbi.nlm.nih.gov/28605603/", "insulin-technology"),
    # Pregnancy, technology, inpatient
    ("hapo",          "https://pubmed.ncbi.nlm.nih.gov/18463375/", "pregnancy"),
    ("wisdm-cgm",     "https://pubmed.ncbi.nlm.nih.gov/?term=WISDM+continuous+glucose+monitoring+older+adults+type+1+diabetes", "insulin-technology"),
    ("nice-sugar",    "https://pubmed.ncbi.nlm.nih.gov/19318384/", "acute-inpatient"),
]

def _required_env_missing() -> list[str]:
    missing = [key for key in ("MISTRAL_KEY", "OPENAI_API_KEY") if not os.environ.get(key)]
    if not (os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")):
        missing.append("XAI_API_KEY or GROK_API_KEY")
    return missing


def _load_oa_overrides() -> dict[str, str]:
    import json
    path = BASE_DIR / "trial_urls.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    overrides: dict[str, str] = {}
    for slug, record in data.items():
        if isinstance(record, dict) and record.get("pdf_url"):
            overrides[slug] = record["pdf_url"]
    return overrides


def run_one(slug: str, url: str, group: str, *, do_autopush: bool) -> dict:
    print(f"\n{'='*80}")
    print(f"[{slug}]  {url}")
    print(f"{'='*80}")

    result = {"slug": slug, "url": url, "success": False, "error": None,
              "page_path": None, "citations": 0}
    try:
        for event_name, payload in ingest_pipeline(
            url=url,
            slug_hint=slug,
            group_hint=group,
            do_autopush=do_autopush,
        ):
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
    parser.add_argument("--ignore-missing-env", action="store_true",
                        help="Attempt the run even if required OCR/LLM keys are missing")
    parser.add_argument("--autopush", action="store_true",
                        help="Commit and push generated paper pages after each successful ingestion")
    args = parser.parse_args()

    missing = _required_env_missing()
    if missing and not args.ignore_missing_env:
        print("Missing required ingestion credentials:")
        for key in missing:
            print(f"  - {key}")
        print("\nSet them in .env, then rerun. The full pipeline requires Mistral OCR, GPT-5.5, and Grok/XAI.")
        sys.exit(2)

    targets = TRIAL_URLS
    if args.slug:
        targets = [(s, u, g) for (s, u, g) in TRIAL_URLS if s == args.slug]
        if not targets:
            print(f"No trial with slug '{args.slug}'")
            sys.exit(1)
    elif args.limit:
        targets = TRIAL_URLS[args.start : args.start + args.limit]

    oa_overrides = _load_oa_overrides()
    if oa_overrides:
        targets = [(s, oa_overrides.get(s, u), g) for (s, u, g) in targets]
        print(f"Loaded {len(oa_overrides)} OA PDF override(s) from trial_urls.json")

    blocked = [
        s for (s, u, _g) in targets
        if "pubmed.ncbi.nlm.nih.gov" in u and s not in oa_overrides
    ]
    if blocked:
        print("Refusing to OCR PubMed abstract/search URL(s) without OA PDF override:")
        for slug in blocked:
            print(f"  - {slug}")
        print("\nRun find_open_access.py first, use a PMC/direct PDF URL, or pass a single OCR-ready --slug with trial_urls.json.")
        sys.exit(3)

    print(f"Running pipeline for {len(targets)} trials")
    if not args.autopush:
        print("Autopush disabled; generated pages will remain local for review.")

    results = []
    for slug, url, group in targets:
        results.append(run_one(slug, url, group, do_autopush=args.autopush))
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

#!/usr/bin/env python3
"""For each diabetes trial, query PubMed → check PMC open-access → output verified PDF URLs.

Uses NCBI E-utilities (no API key required). Conservative: only outputs trials
where we can confirm the PMC paper is in the OA subset (real PDF download available).

Output: trial_urls.json with {slug: {pmid, doi, pmcid, pdf_url, title, year}}
        Trials without OA access are saved with pdf_url=null so we know to skip them.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

# Trial → PubMed search query (trial acronym + first author + year)
# Queries chosen to be specific enough to disambiguate
TRIAL_QUERIES = {
    # Glycemic foundations
    "dcct":                  '"effect of intensive treatment of diabetes on the development and progression" DCCT 1993',
    "edic-cvd":              '"Intensive Diabetes Treatment and Cardiovascular Disease in Patients with Type 1 Diabetes" Nathan 2005',
    "ukpds-33":              '"Intensive blood-glucose control with sulphonylureas or insulin" UKPDS 33',
    "ukpds-34":              '"intensive blood-glucose control with metformin" "UKPDS 34"',
    "ukpds-80":              '"10-year follow-up of intensive glucose control in type 2 diabetes" Holman 2008',
    "accord":                '"Effects of intensive glucose lowering in type 2 diabetes" ACCORD 2008',
    "advance":               '"Intensive blood glucose control and vascular outcomes in patients with type 2 diabetes" ADVANCE 2008',
    "vadt":                  '"Glucose control and vascular complications in veterans with type 2 diabetes" Duckworth 2009',
    # GLP-1 / incretin therapy
    "leader":                '"Liraglutide and Cardiovascular Outcomes in Type 2 Diabetes" Marso 2016',
    "sustain-1":             '"Efficacy and safety of once-weekly semaglutide monotherapy versus placebo" SUSTAIN 1',
    "sustain-2":             '"Semaglutide versus sitagliptin once-weekly" SUSTAIN 2',
    "sustain-3":             '"Semaglutide Versus Exenatide ER" SUSTAIN 3',
    "sustain-4":             '"Semaglutide versus once-daily insulin glargine" SUSTAIN 4',
    "sustain-5":             '"Semaglutide Added to Basal Insulin" SUSTAIN 5',
    "sustain-6":             '"Semaglutide and Cardiovascular Outcomes in Patients with Type 2 Diabetes"',
    "rewind":                '"Dulaglutide and cardiovascular outcomes in type 2 diabetes" REWIND',
    "flow":                  '"Effects of Semaglutide on Chronic Kidney Disease in Patients with Type 2 Diabetes"',
    # SGLT2 cardiorenal outcomes
    "empa-reg-outcome":      '"Empagliflozin, Cardiovascular Outcomes, and Mortality in Type 2 Diabetes"',
    "canvas":                '"Canagliflozin and Cardiovascular and Renal Events in Type 2 Diabetes"',
    "declare-timi-58":       '"Dapagliflozin and Cardiovascular Outcomes in Type 2 Diabetes"',
    "credence":              '"Canagliflozin and Renal Outcomes in Type 2 Diabetes and Nephropathy"',
    "dapa-ckd":              '"Dapagliflozin in Patients with Chronic Kidney Disease" Heerspink 2020',
    "empa-kidney":           '"Empagliflozin in Patients with Chronic Kidney Disease" Herrington 2023',
    # Comparative treatment strategy / technology
    "grade":                 '"Glycemia Reduction in Type 2 Diabetes" GRADE 2022',
    "devote":                '"Insulin Degludec versus Insulin Glargine in Type 2 Diabetes" DEVOTE',
    "origin":                '"Basal insulin and cardiovascular and other outcomes in dysglycemia" ORIGIN',
    "wisdm-cgm":             '"Continuous glucose monitoring in adults with type 1 diabetes" WISDM',
}

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OA_API = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"


def esearch_pmid(query: str) -> str | None:
    """Return the first PMID matching this query, or None."""
    r = requests.get(f"{EUTILS}/esearch.fcgi", params={
        "db": "pubmed", "term": query, "retmax": 1, "retmode": "json",
    }, timeout=30)
    r.raise_for_status()
    data = r.json()
    ids = data.get("esearchresult", {}).get("idlist", [])
    return ids[0] if ids else None


def efetch_summary(pmid: str) -> dict:
    """Return {title, year, doi} for a PMID. Uses XML to avoid JSON control-char issues."""
    import re as _re
    r = requests.get(f"{EUTILS}/esummary.fcgi", params={
        "db": "pubmed", "id": pmid, "version": "2.0",
    }, timeout=30)
    r.raise_for_status()
    xml = r.text
    title_m = _re.search(r"<Name>Title</Name>.*?<Item[^>]*>([^<]+)</Item>", xml, _re.S)
    if not title_m:
        title_m = _re.search(r"<Title>([^<]+)</Title>", xml)
    title = title_m.group(1) if title_m else ""
    pubdate_m = _re.search(r"<Name>PubDate</Name>.*?<Item[^>]*>([^<]+)</Item>", xml, _re.S)
    if not pubdate_m:
        pubdate_m = _re.search(r"<PubDate>([^<]+)</PubDate>", xml)
    year = (pubdate_m.group(1) if pubdate_m else "")[:4]
    doi = ""
    doi_m = _re.search(r"<ELocationID[^>]*EIdType=\"doi\"[^>]*>([^<]+)</ELocationID>", xml)
    if doi_m:
        doi = doi_m.group(1)
    else:
        doi_m = _re.search(r"<ArticleId IdType=\"doi\">([^<]+)</ArticleId>", xml)
        if doi_m:
            doi = doi_m.group(1)
    return {"title": title.strip(), "year": year, "doi": doi}


def elink_to_pmc(pmid: str) -> str | None:
    """Return PMC ID (e.g. 'PMC7220899') if the PubMed paper has a PMC version."""
    r = requests.get(f"{EUTILS}/elink.fcgi", params={
        "dbfrom": "pubmed", "db": "pmc", "id": pmid, "retmode": "json",
    }, timeout=30)
    r.raise_for_status()
    data = r.json()
    linksets = data.get("linksets", [])
    if not linksets:
        return None
    for link in linksets[0].get("linksetdbs", []):
        if link.get("dbto") == "pmc":
            ids = link.get("links", [])
            if ids:
                return f"PMC{ids[0]}"
    return None


def oa_pdf_url(pmcid: str) -> str | None:
    """Return the open-access PDF URL for a PMC paper, or None if not in OA subset."""
    # Strip 'PMC' prefix if present (oa.fcgi accepts either form)
    pmc_num = pmcid.replace("PMC", "")
    r = requests.get(OA_API, params={"id": f"PMC{pmc_num}"}, timeout=30)
    if r.status_code != 200:
        return None
    text = r.text
    # OA API returns XML; look for href in the link element
    if "idDoesNotExist" in text or "is not Open Access" in text:
        return None
    # Find <link href="..." format="pdf" ...>
    import re
    m = re.search(r'<link[^>]*format="pdf"[^>]*href="([^"]+)"', text)
    if not m:
        # Try alternative: href before format
        m = re.search(r'href="([^"]+)"[^>]*format="pdf"', text)
    if m:
        url = m.group(1)
        # OA returns ftp:// — switch to https
        url = url.replace("ftp://", "https://")
        return url
    return None


def resolve_trial(slug: str, query: str) -> dict:
    print(f"  [{slug}] searching: {query}")
    out = {"slug": slug, "query": query, "pmid": None, "title": None,
           "year": None, "doi": None, "pmcid": None, "pdf_url": None,
           "status": "pending"}
    try:
        pmid = esearch_pmid(query)
        if not pmid:
            out["status"] = "no_pubmed_match"
            print(f"    → no PubMed match")
            return out
        out["pmid"] = pmid
        time.sleep(0.4)  # NCBI rate limit ~3 req/sec without API key

        meta = efetch_summary(pmid)
        out.update(meta)
        print(f"    PMID {pmid} | {meta['title'][:70]}")
        time.sleep(0.4)

        pmcid = elink_to_pmc(pmid)
        if not pmcid:
            out["status"] = "not_in_pmc"
            print(f"    → not in PMC (paywalled)")
            return out
        out["pmcid"] = pmcid
        time.sleep(0.4)

        pdf_url = oa_pdf_url(pmcid)
        if not pdf_url:
            out["status"] = "in_pmc_not_oa"
            print(f"    → {pmcid} is in PMC but not OA subset")
            return out
        out["pdf_url"] = pdf_url
        out["status"] = "ok"
        print(f"    ✓ OA PDF: {pdf_url}")
    except Exception as e:
        out["status"] = f"error:{type(e).__name__}"
        print(f"    ERROR: {e}")
    return out


def main():
    results = {}
    for slug, query in TRIAL_QUERIES.items():
        results[slug] = resolve_trial(slug, query)
        time.sleep(0.5)

    out_path = Path(__file__).parent / "trial_urls.json"
    out_path.write_text(json.dumps(results, indent=2))

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    by_status = {}
    for slug, r in results.items():
        by_status.setdefault(r["status"], []).append(slug)
    for status, slugs in sorted(by_status.items()):
        print(f"\n{status}: {len(slugs)}")
        for s in slugs:
            print(f"  - {s}")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()

---
title: Overview
type: concept
status: active
tags:
  - overview
  - navigation
  - diabetes
updated: 2026-05-17
clinical_review: false
---

# Diabetes Wiki Overview

This wiki is an early ingestion workspace for source-grounded summaries of diabetes literature and practical decision domains for clinicians caring for people with diabetes. It is **not** a substitute for ADA, KDIGO, AACE, Endocrine Society, local formulary, or specialist guidance.

## Current State (2026-05-17)

The live seed content contains:

- **Domain taxonomy** under `wiki/taxonomies/research-map.md`.
- **Guideline anchor pages** under `wiki/guidelines/`.
- **Landmark trial/program pages** under `wiki/trials/`, including UKPDS and SUSTAIN 1-6.
- Empty `wiki/sources/papers/` remains available for full paper ingestion through `/add-paper`.

Hand-authored seed pages use authoritative public sources, PubMed, and society guideline pages, but they have **not** undergone local clinical review. Pages carry `clinical_review: false`.

## Evidence Priorities

Use this wiki to organize:

- Glycemic targets and why they differ by age, duration, comorbidity, hypoglycemia risk, and pregnancy status.
- Cardiorenal-metabolic drug selection, especially SGLT2 inhibitors, GLP-1 receptor agonists, tirzepatide, metformin, and insulin.
- Screening and prevention of kidney disease, retinopathy, neuropathy, diabetic foot disease, ASCVD, heart failure, and hypoglycemia.
- Diabetes technology evidence: CGM, pumps, automated insulin delivery, and time-in-range endpoints.
- India/South Asia practice considerations: cost, access, phenotype, diet, insurance coverage, and follow-up feasibility.

## How Pages Are Created

New paper summaries can be added through `/add-paper`. The pipeline:

1. Extracts text from a PDF
2. Fetches metadata and citation context
3. Drafts a structured summary
4. Integrates it into a Markdown wiki page
5. Adds tags from the diabetes keyword vocabulary

Each ingested page should preserve direct source identifiers such as `source_url`, `doi`, `pmid`, and `pmcid` where available.

## Views

- **Trials** — filterable grid of trial, guideline, procedure, conference, and paper pages
- **Graph** — network visualization of related pages
- **Timeline** — publications by year/research direction
- **Tags** — browse by topic tag
- **Chat** — RAG-powered Q&A using selected wiki pages as context
- **Search** — full-text search across the wiki

## Roadmap

- Ingest full open-access landmark papers where available.
- Add reviewed pages for ADA Standards of Care sections, KDIGO diabetes-CKD guidance, hypoglycemia management, insulin initiation, CGM/AID, and pregnancy diabetes.
- Add pragmatic treatment algorithms for primary care, endocrinology, nephrology, cardiovascular-risk, and hospital medicine users.

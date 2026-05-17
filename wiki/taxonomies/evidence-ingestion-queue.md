---
title: "Evidence Ingestion Queue"
type: taxonomy
status: active
updated: 2026-05-17
tags:
  - evidence-queue
  - ingestion
  - landmark
  - diabetes
clinical_review: false
---

# Evidence Ingestion Queue

Target corpus for full paper ingestion through Mistral OCR, GPT-5.5 summary/integration, and Grok/XAI metadata/citation support. Pages should be moved from this queue into `wiki/sources/papers/` only after the pipeline has created source-grounded summaries.

## Glycemic Foundations

| Slug | Paper / Program | Domain |
|------|-----------------|--------|
| `dcct` | DCCT intensive therapy in type 1 diabetes | Type 1 / technology |
| `edic-cvd` | EDIC cardiovascular follow-up | Glycemic targets |
| `ukpds-33` | UKPDS 33 intensive glucose control with sulfonylurea/insulin | Glycemic targets |
| `ukpds-34` | UKPDS 34 metformin | Initial therapy |
| `ukpds-80` | UKPDS 10-year follow-up | Glycemic targets |
| `accord` | ACCORD intensive glucose lowering | Glycemic targets |
| `advance` | ADVANCE intensive glucose control | Glycemic targets |
| `vadt` | Veterans Affairs Diabetes Trial | Glycemic targets |
| `dpp` | Diabetes Prevention Program | Diagnosis / prevention |
| `grade` | GRADE comparative effectiveness | Initial therapy |

## GLP-1 / Incretin Evidence

| Slug | Paper / Program | Domain |
|------|-----------------|--------|
| `leader` | LEADER liraglutide CVOT | Incretin therapy |
| `sustain-1` to `sustain-6` | Semaglutide SUSTAIN program | Incretin therapy |
| `rewind` | REWIND dulaglutide CVOT | Incretin therapy |
| `surpass-cvot` | Tirzepatide cardiovascular outcomes | Incretin therapy |
| `flow` | Semaglutide kidney outcomes in type 2 diabetes with CKD | CKD |

## SGLT2 / Kidney / Heart Failure Evidence

| Slug | Paper / Program | Domain |
|------|-----------------|--------|
| `empa-reg` | EMPA-REG OUTCOME | SGLT2 therapy |
| `canvas` | CANVAS Program | SGLT2 therapy |
| `declare-timi-58` | DECLARE-TIMI 58 | SGLT2 therapy |
| `credence` | CREDENCE | CKD |
| `dapa-ckd` | DAPA-CKD | CKD |
| `empa-kidney` | EMPA-KIDNEY | CKD |

## Residual Albuminuric CKD Risk

| Slug | Paper / Program | Domain |
|------|-----------------|--------|
| `fidelio-dkd` | FIDELIO-DKD finerenone | CKD |
| `figaro-dkd` | FIGARO-DKD finerenone | CKD |

## Insulin / Technology / Inpatient / Pregnancy

| Slug | Paper / Program | Domain |
|------|-----------------|--------|
| `origin` | ORIGIN basal insulin | Insulin / technology |
| `devote` | DEVOTE insulin degludec vs glargine | Insulin / technology |
| `wisdm-cgm` | WISDM CGM in older adults with type 1 diabetes | Insulin / technology |
| `hapo` | HAPO pregnancy outcomes | Pregnancy |
| `nice-sugar` | NICE-SUGAR inpatient critical care glucose targets | Acute / inpatient |

## Runbook

1. Copy `.env.example` to `.env` and set `MISTRAL_KEY`, `OPENAI_API_KEY`, and `XAI_API_KEY` or `GROK_API_KEY`.
2. Run `./venv/bin/python find_open_access.py` to discover open-access PDFs.
3. Run `./venv/bin/python batch_ingest.py --limit 3` for the first small batch.
4. Review generated pages for title, slug, PMID/DOI, clinical claims, and no tracked `.grounding/` files.
5. Continue with later batches once the first batch is clean.

## Current Blocker

The Diabetes Wiki checkout currently has Mistral/XAI credentials from the Neuro Wiki env file but no local `OPENAI_API_KEY`, so the GPT-5.5 summary/integration steps cannot run yet. Do not hand-write pages and label them as OCR/LLM-ingested.

## Interim Evidence Map

- [[wiki/taxonomies/landmark-evidence-map|Landmark Diabetes Evidence Map]] summarizes the multi-agent review pass and tracks source-verification leads.

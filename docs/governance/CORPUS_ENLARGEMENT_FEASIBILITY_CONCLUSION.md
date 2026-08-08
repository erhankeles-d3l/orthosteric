# Corpus-Enlargement Feasibility Analysis — Conclusion

**This is a feasibility finding, not Stage D.** No frozen Stage C artifact is touched. This document answers the question posed after `f0eaf3c`: *is obtaining ~500–875 primary-contrast-eligible compounds (≈24,000–42,000 total four-isoform-complete compounds) scientifically and operationally realistic from currently available public data?*

## What was checked, and why this order

Two questions, kept explicitly separate because they have very different cost profiles:

1. **Is there more already-published four-isoform data not yet captured in A4?** — a data-engineering question.
2. **Does the total public literature even contain enough such measurements, full stop?** — a fundamentally different question, since dedicated four-isoform PI3K-selectivity papers are a bounded, identifiable literature genre, not an open population.

Question 2 is answerable directly from data already in hand and was checked first, since a negative answer there makes question 1 moot.

## The direct evidence

Computed from A4 itself (`SNAP-05748f6627ea`), not estimated or searched externally:

| Metric | Value |
|---|---:|
| Distinct studies (papers) in A4 | 712 |
| Studies containing a four-isoform panel | **270** |
| Compounds per four-isoform study — median | 15 |
| Compounds per four-isoform study — largest | 521 |
| Total compound-mentions across those 270 studies (with cross-study overlap) | 6,207 |
| Distinct qualifying compounds (Stage C's own candidate pool) | 2,481 |
| A4's ChEMBL version and retrieval date | **ChEMBL_37, retrieved 2026-08-06** — two days before this analysis |

**A4 is not a stale or narrow extract.** It reflects essentially current ChEMBL. Re-querying ChEMBL more broadly would not meaningfully expand the candidate pool beyond what Stage C already used.

## The gap, quantified

Required primary-contrast-eligible compounds for adequate power at the policy-relevant effect size (ΔAUC = 0.20): **500–875** (§3 of `CORPUS_ENLARGEMENT_PLAN.md`). Translated to total four-isoform-complete corpus size via the observed yield rate: **≈24,000–42,000**.

**ChEMBL's entire currently-curated four-isoform PI3K literature contains ≈2,481 distinct qualifying compounds.** Reaching the required range would need **roughly 10–17× more distinct compounds than the entire relevant public-literature genre currently provides**, via ChEMBL.

## Would other sources close this gap?

- **BindingDB / PubChem BioAssay**: for a target family with PI3K's two-decade history of major pharma and academic investment, ChEMBL's literature-mining coverage is mature, not sparse. The realistic incremental yield from these sources, for a well-studied target, is on the order of **10–30%** — not the 1000–1700% needed.
- **Manual SI-table extraction** from papers not yet formally curated into ChEMBL/BindingDB: slower and more labor-intensive than database re-querying, and still bounded by the same underlying literature genre (the ≈270-paper four-isoform genre already identified). It does not change the order of magnitude, only how completely that existing genre is captured.
- **New experimental characterization**: the only path that could plausibly close a 10–17× gap. This is a sustained, multi-year experimental campaign at a scale matching a large pharmaceutical company's internal program — categorically different from, and vastly more expensive than, a public-data-mining effort.

## Computational-burden assessment (the GPU/hardware question)

**Not a constraint, at any stage considered here.** Every computational step in this entire campaign (Stage A through this feasibility check) has been CPU-bound: AutoDock Vina docking, RDKit cheminformatics, Biopython sequence alignment, numpy-based bootstrap simulation. No GPU has been used or needed anywhere in this pipeline.

A GPU would become relevant only as an *optional accelerant* for a large docking campaign, if a corpus enlargement at some smaller, more realistic scale were ever pursued (GPU-accelerated Vina/AutoDock-GPU forks exist). Even then, 16GB VRAM is comfortably sufficient — molecular docking has modest VRAM requirements relative to deep-learning workloads, which this pipeline does not currently involve at all. **This is a non-factor for the decision this document addresses.**

## Conclusion

> **The frozen confirmatory endpoint, as pre-registered under Rev. 5, is not practically supportable with currently available public data.** The gap between required and available four-isoform-complete compounds is approximately an order of magnitude, and no combination of realistically achievable public-data actions (broader ChEMBL querying, BindingDB/PubChem integration, SI-table mining) closes it. Closing it would require new experimental work at a scale beyond what a public-data-mining effort can deliver.

This is treated as a legitimate, decisive scientific finding in its own right — consistent with the outcome this campaign's own governance framework anticipated as possible from the outset (Rev. 5, and the corpus-enlargement plan that followed Stage C) — not a failure requiring further workaround.

## What this does and does not authorize

- Does not authorize Stage D/E under the current campaign.
- Does not authorize any modification of Stage C's frozen artifacts.
- Does not itself commission new experimental work — that is a separate resourcing decision, informed by this finding, not executed by it.
- Closes the corpus-enlargement line of inquiry opened after `f0eaf3c` with a stated, evidenced conclusion, rather than leaving it open pending a further, more elaborate feasibility study whose likely answer this data already shows.

## Reproducibility

Computed directly from A4 (`data/snapshots/activity_snapshot_A4/`), no new script artifact beyond the inline query reported here (re-run trivially against the same immutable snapshot). No sealed Stage C artifact was read, modified, or referenced by compound-level content — only aggregate study/isoform counts from the same underlying A4 snapshot Stage C itself drew from.

# Stage 0 Assessment — Activity Snapshot A4

**Date:** 2026-08-06
**Snapshot:** A4, `SNAP-05748f6627ea`
**Governance basis:** GDR-010 (accepted, Option A), GDR-011 (accepted, Option D + ATP covariate)

## Verdict

```
STAGE 0 GATE:  WARNING
ELIGIBLE FOR TRAINING: True
```

`CorpusQualityGatePolicy` (unmodified) returned `warning`, not `pass` or
`stop`, because two dimensions are non-fatal concerns rather than
structural degeneracy:

| Dimension | Status |
|---|---|
| connectivity | non_degenerate_unquantified |
| coverage | non_degenerate_unquantified |
| missingness | non_degenerate_unquantified |
| publication_concentration | non_degenerate_unquantified |
| scaffold_diversity | governed_threshold_met |
| confidence | insufficient_data (non-fatal; SCI0-031 review) |
| structural_coverage | not_yet_available (non-fatal; SCI0-031 review) |

The `confidence` and `structural_coverage` flags are **not** caused by
GDR-010/GDR-011 — `confidence_assay_quality_rule` and
`confidence_lit_tier_rule` were RULE_MISSING before this session, and
structural evidence discovery is a separate, not-yet-completed workstream
(Stage D, partial from a prior session).

## What GDR-010/GDR-011 changed

Before this session (A3, pre-GDR-010/011): `coverage` and `missingness`
were `structurally_degenerate` because the `(study_id, assay_id)` stratum
definition made `n_complete_compounds = 0` a structural certainty.

After (A4): `n_complete_compounds = 2,992` (`StratumReport`, C1_PRIMARY
strata only), all four isoforms individually populated
(β=3,641 · γ=6,896 · α=8,059 · δ=10,421), `scaffold_diversity` moved to
`governed_threshold_met`. Both dimensions cleared their degeneracy checks.

## Three different "complete compound" counts — not a bug

Three numbers appear across the artifacts produced this session, each a
correctly-scoped answer to a different question:

| Count | Value | Definition |
|---|---:|---|
| `GraphStats.compounds_all4_isoforms` | 2,500 | unique compounds with ≥1 record in all 4 isoforms **anywhere in the corpus** (global, not panel-scoped) |
| `characterize().c1_complete_compounds` | 2,427 | unique compounds complete within a **single C1 panel that itself covers all 4 isoforms** |
| `StratumReport.total_complete_compounds` | 2,992 | **sum over all 873 C1 panels** of (compounds complete in that panel) — a compound complete in 2 panels is counted twice |
| GGR-002a/002b `pact`-filtered index | 1,738 pairs / smaller | further restricted to records carrying a numeric `pchembl_value`, needed for any quantitative selectivity computation |

`n_complete_compounds` in the engineering-parameters / gate path is the
`StratumReport` figure (2,992), because that is what `CoverageEvaluator`
consumes (per GDR-002/GDR-003).

## GGR status (unresolved by design)

| GGR | Status | Reason |
|---|---|---|
| GGR-002a | `GDR_REQUIRED` | corpus-derived pair/sign-flip counts computed (6,469 pairs, 2,578 sign-flip candidates, 82 studies); no MMP transformation or switch-inclusion criterion is sealed |
| GGR-002b | `GDR_REQUIRED` | corpus-derived noise statistics computed (852 groups, median σ=0.260, ATP-confirmed subset 136 groups median σ=0.382); no S4b sharpness multiplier is sealed |
| GGR-010 | `CORPUS_INSUFFICIENT` | zero mTOR activity records in A4 (mTOR ChEMBL ID unverified/unacquired) |

None of these three statuses was changed to force a different outcome; all
three were already this way in the pre-A4 decision package and remain so.

## Explicit non-progression

Per governance instruction: Stage 0 reaching `WARNING`/`eligible_for_training=True`
does **not** authorize structural evidence discovery, SCI2-002 training,
Model Generation 1, or generative design in this session. Those require
separate authorization.

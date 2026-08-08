# Stage 0 Assessment — Activity Snapshot A4

**Date:** 2026-08-06 (updated after GDR-012/013/014)
**Snapshot:** A4, `SNAP-05748f6627ea` (unmodified throughout every update below —
verified via `md5sum` of `manifest.json`/`records.json.gz` before and after
each rerun in this session)
**Governance basis:** GDR-010 (Option A), GDR-011 (Option D + ATP covariate),
GDR-012 (exploratory scaffold-pair evidence classification), GDR-013
(deterministic aggregation + per-isoform-pair noise floor), GDR-014
(GGR-010 scope: evidence gap, non-blocking)

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
| GGR-002a | `GDR_REQUIRED` | GDR-012: 6,469 EXPLORATORY_BEMIS_MURCKO pairs (deterministic, GDR-013 aggregation), 3,256 sign-flip candidates, 82 studies, 1,254 compounds excluded (censored/unclassified required-isoform cell). No true-MMP definition or switch-magnitude multiplier is sealed — `switch_magnitude_multiplier_status() == "RULE_MISSING/GDR_REQUIRED"` unconditionally |
| GGR-002b | `GDR_REQUIRED` | GDR-013: per-isoform, per-replicate-type sigma computed and separated (TRUE_REPLICATE 420 cells / CROSS_ASSAY 432 cells); per-isoform-pair sigma_diff computed for (α,β)/(α,γ)/(α,δ). No single figure is sealed as a downstream multiplier for any specific consumer |
| GGR-010 | `CORPUS_INSUFFICIENT` | GDR-014: zero mTOR activity records in A4; explicitly re-scoped as a documented evidence gap, non-blocking for Model Generation 1 |

None of these three statuses was changed to force a different outcome.

## Effect of the GDR-012/013 aggregation fix (this update)

Replacing the prior last-write-wins panel index with GDR-013's
deterministic median aggregation changed two GGR-002a figures, as
expected — the pair *universe* is identical (6,469 pairs both before and
after, confirming no compounds were added or removed), but resolving
ambiguous multi-record cells to a principled median rather than an
arbitrary "whichever record iterated last" changed which specific pairs
register as sign-flips:

| Metric | Before (last-write-wins) | After (GDR-013 median) |
|---|---:|---:|
| Pairs examined | 6,469 | 6,469 (unchanged — same compound universe) |
| Sign-flip candidates | 2,578 | 3,256 |

This increase is the corrected figure, not a regression — it reflects
that some of the 473 previously-ambiguous cells (>0.3 pAct spread between
candidate values) were, by chance, resolved toward the non-flip value
under last-write-wins.

Per-isoform TRUE_REPLICATE vs CROSS_ASSAY sigma (GDR-013), on A4:

| Isoform | TRUE_REPLICATE (n, median σ) | CROSS_ASSAY (n, median σ) |
|---|---|---|
| PI3Kα | 80, 0.064 | 126, 0.272 |
| PI3Kβ | 32, 0.226 | 109, 0.191 |
| PI3Kγ | 52, 0.000¹ | 87, 0.849 |
| PI3Kδ | 256, 0.318 | 110, 0.424 |

¹ 27 of 52 PI3Kγ true-replicate cells have two source records reporting an
identical rounded pAct value (e.g. `6.57` from two distinct ChEMBL
activity IDs, same assay) — a real feature of the data (exact ties at
reporting precision), not a computation defect; verified by direct
inspection. This pulls the median toward zero and is a genuine reason a
single pooled isoform sigma would understate PI3Kγ's true measurement
noise for non-tied observations.

Per-isoform-pair σ_diff (independence assumed, GDR-013 §3.3):

| Pair | true_replicate | cross_assay | pooled (reference only) |
|---|---:|---:|---:|
| (α, β) | 0.235 | 0.333 | 0.254 |
| (α, γ) | 0.064 | 0.891 | 0.454 |
| (α, δ) | 0.324 | 0.504 | 0.407 |

The (α, γ) true_replicate figure is depressed by the same tied-value
effect noted above and should not be read as representative without that
caveat.

## Explicit non-progression

Per governance instruction: Stage 0 reaching `WARNING`/`eligible_for_training=True`
does **not** authorize structural evidence discovery, SCI2-002 training,
Model Generation 1, or generative design in this session. Those require
separate authorization.

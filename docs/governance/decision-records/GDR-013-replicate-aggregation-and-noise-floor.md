# Governance Decision Record GDR-013 — Replicate Aggregation and Per-Isoform-Pair Noise Floor (GGR-002b)

**Category:** Scientific-methodology — resolution of GGR-002b (within-study
noise floor).
**Status:** **ACCEPTED. Implemented.**
**Date raised:** 2026-08-06 (Project Owner Decision Package, GGR-002a/002b analysis).
**Date accepted:** 2026-08-06.
**Affects:** New `orthosteric.data.replicate_aggregation`, new
`orthosteric.data.noise_floor`; consumed by GDR-012 (`mmp_candidates.py`).
**Evidence base:** Activity Snapshot A4 (`SNAP-05748f6627ea`), via
`analysis/ggr002_decision_package_audit.py`.
**Note on implementation order:** the code and tests for this decision were
written before this record, in the same session, at the Project Owner's
explicit direction ("implement the approved governance decisions ...
create the required GDRs and tests"). This record documents the decision
already approved in the prior Decision Package turn and the exact scope of
what was implemented; it does not introduce any new scientific choice
beyond what was already presented and approved.

---

## 1. Decision (verbatim from the Project Owner)

> Replace last-write-wins aggregation with deterministic, provenance-
> preserving aggregation. Separate true assay replication from cross-assay
> heterogeneity. Implement the uncertainty representation required for
> per-isoform-pair selectivity rather than a single global sigma. Preserve
> censored observations explicitly, while keeping them out of exact-value
> MMP evidence until a censoring-aware method is governed.

## 2. Problem this resolves

The prior analysis-layer GGR-002b computation (`ggr_reassessment_a4.py`,
pre-GDR-013) reported a single pooled sigma = 0.260 pAct units across 852
replicate cells. The Decision Package audit
(`analysis/ggr002_decision_package_audit.py`) showed this pooling was not
defensible:

- **Per-isoform sigma varies ~3x**: PI3Kalpha median 0.140 vs PI3Kgamma
  median 0.431 (n=206 and n=139 groups respectively).
- **Replicate-type is conflated**: 852 replicate cells split into 420 with
  a single ChEMBL `assay_id` (a genuine repeat measurement, median sigma
  0.212) and 432 spanning multiple `assay_id`s under one GDR-011 C1
  protocol signature (cross-assay agreement, median sigma 0.343) — a
  63% gap between two populations reported previously as one number.
- **Cell-level aggregation was non-deterministic in intent**: 852 of 23,911
  (panel, compound, isoform) cells had >=2 exact observations, and the
  pair-generation code (a separate consumer, GGR-002a) took whichever
  record Python iterated last — reproducible given one fixed input file,
  but not a principled aggregate, and order-dependent under any upstream
  reordering. 473 of those 852 cells had >0.3 pAct spread between
  candidates.

## 3. What is governed

### 3.1 Deterministic aggregation (`replicate_aggregation.py`)

Within one (panel, compound, isoform) cell, exact (pchembl_value-bearing)
observations are combined by **median**, computed over values sorted
before aggregation. This mirrors the GDR-001 precedent
(`_deduplicator.py`, `RESOLVED_REPLICATE_MEDIAN`) at the coarser
GDR-011 C1 panel-level identity rather than `_deduplicator.py`'s finer
compound x isoform x construct x organism x assay x source identity.

Every result is invariant to input record order (verified,
`test_aggregate_cell_order_independent`, `test_deterministic_under_record_order_shuffle`
in `mmp_candidates.py`'s tests).

### 3.2 Replicate type: TRUE_REPLICATE vs CROSS_ASSAY

Every cell is classified `SINGLE` (1 exact obs), `TRUE_REPLICATE` (>=2
exact obs, one ChEMBL `assay_id`), `CROSS_ASSAY` (>=2 exact obs, multiple
`assay_id`s), or `NONE` (0 exact obs). Noise-floor statistics
(`noise_floor.compute_isoform_noise_floors`) are reported **separately**
for `TRUE_REPLICATE` and `CROSS_ASSAY`; a pooled figure is retained for
reference but is explicitly documented as not the recommended estimator.

### 3.3 Per-isoform-pair uncertainty, not a single global sigma

`noise_floor.compute_isoform_pair_noise_floors()` combines per-isoform
sigma into a per-isoform-pair `sigma_diff = sqrt(sigma_a^2 + sigma_b^2)`,
for each of (alpha, beta), (alpha, gamma), (alpha, delta) — the pairs that
matter to the project's S1 selectivity vector. This combination assumes
**independent measurement error** between the two isoforms; A4 contains no
paired-difference replicate structure to test that assumption directly,
and every `IsoformPairNoiseFloor` result carries an explicit
`independence_assumption_note` stating this. It is a documented
methodological choice, not an empirically validated covariance structure.

### 3.4 Censoring: preserved explicitly, excluded from exact-value evidence

A cell's `value` (the exact-observation median) is computed **only** from
pchembl_value-bearing records. Right/left-censored records never enter it,
but their `source_record_id`s and censoring kinds are retained on
`AggregatedCell` for audit (`censored_source_record_ids`,
`censoring_kinds`) — never silently discarded.

A previously-unaccounted edge case, found during implementation: 257 of
39,002 A4 accepted records carry `censoring == "exact"` with no
`pchembl_value` (a ChEMBL data-quality gap — e.g. non-standard reporting
units that block automatic pChEMBL computation — not true right/left
censoring). These are tracked in a third bucket,
`unclassified_source_record_ids`, distinct from both exact and censored
evidence, so they are neither miscounted as censored nor silently dropped.

A censoring-aware combination method (e.g. treating a right-censored bound
as directional evidence of a lower bound on selectivity) is **not**
implemented here and remains open — see GDR-012 §4.

## 4. What is NOT decided by this record

- No global "the" noise floor is selected. Per-isoform, per-replicate-type
  sigma values are reported; a downstream consumer choosing one figure for
  a specific purpose (e.g. a loss-function scale) is a separate decision.
- No switch-magnitude multiplier is chosen — see GDR-012.
- No censoring-aware statistical method (e.g. Tobit-style combination of
  exact and censored evidence within a cell) is implemented — the current
  policy is strict separation, not synthesis.

## 5. Empirical result on Activity Snapshot A4

| Isoform | n TRUE_REPLICATE | sigma (median) | n CROSS_ASSAY | sigma (median) |
|---|---:|---:|---:|---:|
| PI3Kalpha | (see `ggr_reassessment_a4.py` rerun) | | | |
| PI3Kbeta | | | | |
| PI3Kgamma | | | | |
| PI3Kdelta | | | | |

(Populated by the post-acceptance rerun; see
`data/snapshots/activity_snapshot_A4/ggr_reassessment.json`, produced
without modifying A4 itself.)

## 6. Tests

`tests/data/test_replicate_aggregation.py` (14 tests): determinism under
record-order shuffling, `ReplicateType` classification, censored-value
exclusion and retention, the `censoring="exact"`-with-no-pchembl edge
case, LEGACY_FALLBACK exclusion.

`tests/data/test_noise_floor.py` (9 tests): TRUE_REPLICATE/CROSS_ASSAY
separation, no cross-isoform pooling, sqrt-sum-of-squares combination,
`None` (never fabricated) when data is missing, and that the
switch-magnitude sentinel is returned unconditionally regardless of input.

## 7. Review trigger

A future GDR is required before: (a) any single noise-floor figure is
adopted for a specific downstream use (e.g. GDR-008's Tobit likelihood
scale); (b) a censoring-aware combination method is introduced.

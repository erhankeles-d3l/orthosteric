# Governance Decision Record GDR-012 — Exploratory Scaffold-Pair Evidence Classification (GGR-002a)

**Category:** Scientific-methodology — resolution of GGR-002a (comparative
selectivity / MMP switch evidence).
**Status:** **ACCEPTED. Implemented.**
**Date raised:** 2026-08-06 (Project Owner Decision Package, GGR-002a/002b analysis).
**Date accepted:** 2026-08-06.
**Affects:** New `orthosteric.data.mmp_candidates`. Depends on GDR-011
(comparability unit), GDR-013 (aggregation and noise floor).
**Evidence base:** Activity Snapshot A4 (`SNAP-05748f6627ea`), via
`analysis/ggr002_decision_package_audit.py`.
**Note on implementation order:** see the identical note in GDR-013 — code
and tests were written in the same session as this record, at the Project
Owner's explicit direction, implementing a decision already presented and
approved in the prior Decision Package turn.

---

## 1. Decision (verbatim from the Project Owner)

> Treat current Bemis–Murcko switch counts as exploratory only and do not
> call them MMP evidence. ... Do not invent the final magnitude
> multiplier; surface it as an explicit remaining Project Owner decision
> if the evidence does not determine it.

## 2. Problem this resolves

The prior analysis (`ggr_reassessment_a4.py`, pre-GDR-012) generated 6,469
"same-scaffold complete pairs" and reported 2,578 "sign-flip candidates"
without any evidentiary qualifier. The Decision Package audit established:

- "Same scaffold family" (Bemis–Murcko ring/linker identity, SCI0-012) is
  **not** a matched molecular pair (MMP) relationship. Two compounds can
  share a scaffold family while differing at multiple positions
  simultaneously; no single-point-transformation check exists anywhere in
  this repository.
- Sign-flip magnitude showed some real separation from non-flip pairs
  (median ~0.5–0.6 vs 0.19 pAct units) but **34% of sign-flip candidates
  fell below 2x the (pre-GDR-013, pooled) replicate noise floor** — a
  substantial fraction indistinguishable from measurement noise under a
  conservative criterion.
- The underlying per-cell values inherited the GDR-013 last-write-wins
  defect (see GDR-013 §2).

## 3. What is governed

### 3.1 Evidence classification: EXPLORATORY_BEMIS_MURCKO, never MMP

`mmp_candidates.ScaffoldPairEvidenceClass` has two members:

- `EXPLORATORY_BEMIS_MURCKO` — Bemis–Murcko scaffold-family identity only.
  **The only value any code path in this repository produces.** Every
  `ScaffoldPairCandidate` carries this tag and `ScaffoldPairReport` carries
  an explicit `evidence_class_note` stating the pairs are NOT MMP evidence.
- `MMP_CONFIRMED` — reserved for a future module implementing a genuine
  single-point-transformation MMP definition. Not implemented; no code
  path produces it. Its presence in the enum is a placeholder for future
  work, not a claim that such work exists.

No downstream report, document, or claim may describe
`EXPLORATORY_BEMIS_MURCKO` output as "MMP evidence" or a "confirmed
switch."

### 3.2 Candidate generation uses GDR-013's deterministic aggregation

`generate_exploratory_scaffold_pairs()` calls
`replicate_aggregation.aggregate_records_by_cell()`, replacing the
last-write-wins defect. Verified deterministic under record-order
shuffling (`test_deterministic_under_record_order_shuffle`,
`test_multi_record_cell_uses_median_not_last_writer`).

### 3.3 Censoring: excluded from candidate generation, counted, never discarded

A compound is eligible for candidate-pair generation in a panel only if
every required isoform's aggregated cell has an exact value
(`AggregatedCell.value is not None`). A compound measured in all four
isoforms but with a censored-only (or unclassified-only, per GDR-013 §3.4)
cell for at least one required isoform is excluded from exact-value
candidate generation. The exclusion is counted
(`n_compounds_excluded_censored_required_isoform`) and reported on every
`ScaffoldPairReport`; the underlying censored/unclassified evidence remains
visible via the `AggregatedCell` it came from. This is a strict-exclusion
policy, not a censoring-aware combination method (see GDR-013 §4) — that
remains open.

### 3.4 Magnitude: reported descriptively, no multiplier chosen

Each candidate carries `magnitude` (raw |delta_a - delta_b|),
`sigma_diff_reference` (best-available per-isoform-pair sigma from
GDR-013, with an explicit `sigma_diff_basis` documenting which of
true_replicate / cross_assay / pooled / unavailable was used, following a
stated fallback order — never silently substituted), and
`magnitude_over_sigma` (their ratio). **No pass/fail threshold is applied
anywhere in this module.** `noise_floor.switch_magnitude_multiplier_status()`
remains the fixed sentinel `"RULE_MISSING/GDR_REQUIRED"`, verified to
return the same value regardless of any input
(`test_switch_magnitude_multiplier_is_constant_regardless_of_input`).

Structurally verified: no `ScaffoldPairCandidate` field named
`passes_threshold` or `is_confirmed_switch` (or equivalent) exists.

## 4. What is NOT decided by this record — explicit remaining Project Owner decisions

1. **Is Bemis–Murcko scaffold-family sharing an acceptable long-term proxy
   for a matched pair, or must a true single-transformation MMP module be
   built?** (Decision Package §Decision 1, Option D.)
2. **Should a magnitude threshold gate "candidate switch" status, and on
   what sigma basis (true-replicate, cross-assay, or pooled) and what
   multiplier k?** This record explicitly declines to choose k.
3. **How should a censored required-isoform cell eventually be used**
   (currently: excluded and counted) — e.g. as directional evidence that
   the true selectivity is at least as large as the exact-value estimate
   would suggest, once a censoring-aware method is governed?

## 5. Empirical result on Activity Snapshot A4

Populated by the post-acceptance rerun (this session); see
`data/snapshots/activity_snapshot_A4/ggr_reassessment.json`. A4 itself was
not modified.

## 6. Tests

`tests/data/test_mmp_candidates.py` (9 tests): evidence-class tagging,
sign-flip detection correctness, scaffold-family isolation, determinism
under shuffling, the exact multi-record-cell regression this module fixes,
censored-required-isoform exclusion and counting, and the structural
absence of any threshold-decision field.

## 7. Review trigger

Required before: (a) any claim of "confirmed MMP evidence" is made from
this corpus; (b) a switch-magnitude multiplier is adopted; (c) censored
evidence is combined with exact evidence for candidate generation.

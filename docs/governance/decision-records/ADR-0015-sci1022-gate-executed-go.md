# ADR-0015 — SCI1-022 Gate Executed on Real Data; SI3 Satisfied (GO)

**Date:** 2026-08-06
**Category:** Bounded operational decision (Category B per Project Owner
mandate — reversible, documented, empirically testable, compatible with
existing governance).
**Status:** Accepted, executed.

## Decision

Executed the previously-unrun SCI1-021 (baseline evaluation) / SCI1-022
(gate procedure) on real Activity Snapshot A4, closing the actual SI3
blocker: "no `model/`/`train/` code may exist until SCI1-022 is Done."

The backlog listed SCI1-022 as "Done" meaning the *code* existed
(`eval/_gate.py`, `eval/_baselines.py`), but the gate had never been
*executed* against real data — no gate record existed anywhere in the
repository, and `docs/SCIENTIFIC_STATE.md` (where
`docs/IMPLEMENTATION_PROTOCOL_SCIENTIFIC.md` requires baseline results to
be recorded before the first `model/` commit) did not exist. This was
verified by direct grep across the repository before proceeding.

## Why this is a bounded decision, not a Project Owner escalation

- Reversible: re-running the gate with different data or a different seed
  produces a new, independently checkable record; nothing is destroyed.
- Documented: full inputs (A4 snapshot SHA, scaffold split SHA, per-baseline
  RMSE) are recorded in `docs/governance/SCI1022_GATE_RECORD_A4.json`.
- Empirically testable: every number is reproducible from A4 plus the new
  `orthosteric.eval._target_construction` module (7 tests).
- Compatible with existing governance: uses only already-governed code
  (`s1_gate_evaluation`, the three SCI1-018/019/020 baselines,
  `scaffold_split`) plus a new glue module connecting them to A4 via the
  already-governed GDR-011/GDR-013 aggregation. No new scientific rule,
  threshold, or evidence class was introduced.
- Does not change what the platform claims to know: the gate's own
  threshold (0.3 log units, Constitution §1.4) was not touched.

## New code

`src/orthosteric/eval/_target_construction.py`: builds `SelectivityTarget`
objects from snapshot records via `orthosteric.data.replicate_aggregation`
(GDR-013) and the C1_PRIMARY comparability unit (GDR-011). Selectivity
differences are computed strictly within one panel; a compound complete in
multiple C1_PRIMARY panels contributes the median of its per-panel
differences (documented, bounded aggregation choice, consistent with the
GDR-001/GDR-013 replicate-median precedent). 7 tests.

## Result (real, on Activity Snapshot A4)

```
SelectivityTargets:     1,267 compounds
Scaffold split (seed=42, SCI1-017):
  train: 822 compounds / 407 scaffolds
  val:   191 compounds / 57 scaffolds
  test:  254 compounds / 115 scaffolds
  scaffold_overlap: 0

Baseline RMSE (held-out test, log units):
                          alpha_vs_beta  alpha_vs_gamma  alpha_vs_delta
  ligand_only_mean              1.174          0.817          1.106
  nearest_neighbor_tanimoto     0.560          0.707          0.570
  proteochemometric_linear      0.675          0.760          0.714

SCI1-022 GATE RECORD:
  vote: GO
  any_baseline_meets_s2: False  (min ligand-only RMSE 0.817 > 0.3 threshold)
  n_within_study: 254
```

**GO** — the ligand-only null baseline does not solve the task
(RMSE 0.817–1.174 ≫ 0.3 log units). A learned comparative model may add
value. SI3 is satisfied; `model/`/`train/` (here, `orthosteric.learning`)
code is authorized to proceed.

## Observation (reported honestly, not a gate criterion)

The nearest-neighbour and proteochemometric baselines already substantially
outperform ligand-only (RMSE ~0.56–0.76 vs ~0.82–1.17), meaning ligand
structure alone carries real predictive signal for isoform selectivity —
consistent with Constitution §1.2's characterization of orthosteric α
selectivity as "a solved medicinal chemistry problem." The GO decision is
about the null (ligand-*ignoring*) baseline, not about how hard the task
is in absolute terms; this project's contribution, if any, would need to
be evaluated against the NN/PCM baselines, not just the mean predictor.

## Review trigger

None — this is an executed record, not an open decision. A future model
generation's evaluation must be compared against these exact baseline
figures (same snapshot, same split) or a documented successor gate.

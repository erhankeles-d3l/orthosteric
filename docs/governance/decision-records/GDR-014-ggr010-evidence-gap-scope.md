# Governance Decision Record GDR-014 — GGR-010 Scope: Evidence Gap, Not a Model Generation 1 Hard Gate

**Category:** Scientific-architecture — scope of the dual PI3K/mTOR census
relative to Model Generation 1 eligibility.
**Status:** **ACCEPTED. Documented (no code enforces GGR-010 as a gate
today, so no code change was required).**
**Date raised:** 2026-08-06 (Project Owner Decision Package, §Decision 4).
**Date accepted:** 2026-08-06.
**Affects:** Project process documentation (`docs/governance/STAGE_0_ASSESSMENT_A4.md`,
the Stage-0-to-SCI2-002 checklist). Does not affect any governed source code:
`CorpusQualityGatePolicy` never referenced GGR-010, so there is no gate
behavior to change.

---

## 1. Decision (verbatim from the Project Owner)

> Treat GGR-010 as a documented evidence gap/out-of-scope for Model
> Generation 1 rather than a hard training gate.

## 2. Background

GGR-010 (dual PI3K/mTOR census) status is `CORPUS_INSUFFICIENT`: Activity
Snapshot A4 contains zero mTOR activity records (the mTOR ChEMBL target ID,
candidate CHEMBL2842, was never verified or acquired against ChEMBL 37).
This is data absence, not a missing governance rule — confirmed in the
prior Decision Package turn (§Decision 4) and unchanged by this record.

## 3. What this decision changes

Prior project-process documentation implicitly listed GGR-010 resolution as
one of several items required before "SCI2-002 unblocked" (Decision
Package §Decision 3 checklist). This record formally re-scopes it:

- GGR-010 identifies compounds whose apparent PI3K selectivity might be
  confounded by dual mTOR inhibition — a **safety/interpretation-layer**
  concern, not a prerequisite for the core comparative
  PI3Kalpha/beta/gamma/delta representation Model Generation 1 requires.
- Blocking Model Generation 1 on GGR-010 would conflate "we cannot yet flag
  mTOR-confounded compounds" with "we cannot yet train the comparative
  model" — these are separable. The comparative task (pAct_alpha,
  pAct_alpha-beta, pAct_alpha-gamma, pAct_alpha-delta) does not reference
  mTOR at all.
- GGR-010 remains open and is carried forward as a **documented evidence
  gap** to be addressed at the model-interpretation / candidate-review
  layer (e.g. flagging predictions for compounds later found to have mTOR
  activity), not as a blocker on reaching that layer.

## 4. What this decision does NOT change

- GGR-010's status remains `CORPUS_INSUFFICIENT`. This record does not
  resolve it, does not acquire mTOR data, and does not infer mTOR activity
  by any indirect means (pathway, structural similarity, docking, or model
  output) — all of which remain explicitly prohibited per the governing
  instructions.
- No code enforced GGR-010 as a gate before this record, so no code
  changes it. `CorpusQualityGatePolicy`'s dimension evaluators
  (`ConnectivityEvaluator`, `CoverageEvaluator`, `MissingnessEvaluator`,
  `PublicationConcentrationEvaluator`, `ScaffoldDiversityEvaluator`,
  `StructuralCoverageEvaluator`, `ConfidenceEvaluator`) contain no
  reference to mTOR or GGR-010 — verified by inspection during the Decision
  Package audit.
- If mTOR data is later acquired, GGR-010 may be resolved on its own
  timeline, independent of Model Generation 1's schedule.

## 5. Stage-0-to-SCI2-002 checklist (revised)

Superseding the checklist in the prior Decision Package turn:

```
[x] Stage 0 gate: no STRUCTURALLY_DEGENERATE dimension           (A4: satisfied)
[ ] GGR-002a: status other than GDR_REQUIRED                     (see GDR-012)
[ ] GGR-002b: status other than GDR_REQUIRED                     (see GDR-013)
[ ] confidence dimension: resolved or explicitly waived at SCI0-031 (open, pre-existing, unrelated)
[ ] structural_coverage: resolved or explicitly waived at SCI0-031  (open, pre-existing, unrelated)
[removed] GGR-010 resolution — no longer a listed precondition (this record)
```

GGR-010 is tracked separately as an evidence gap in project documentation,
not on this checklist.

## 6. Review trigger

Revisit if mTOR activity data is later acquired and a Project Owner
decision is made about how (if at all) it should feed back into model
training, evaluation, or candidate interpretation.

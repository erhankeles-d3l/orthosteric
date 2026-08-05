# ADR-0008 [Architectural] — Decision Policy Layer (`policy/`)

**Status:** Accepted
**Decision:** Add a new architectural layer, `src/orthosteric/policy/`, that
classifies model predictions against configurable, versioned project
objectives, and amend `ENGINEERING_STANDARDS.md` §2's package table and the
`.importlinter` layer order to admit it.
**Date:** 2026-08-05
**Reversibility:** costly — a new package appears in the authoritative ENG §2
responsibility table and in the enforced import graph.
**Review trigger:** first `SCI-2` model generation producing real predictions;
or any request to make policy thresholds sealed artefacts.

---

## Context

The Project Owner requested a decision-policy layer that evaluates predictions
against configurable scientific objectives (potency, selectivity, confidence,
uncertainty, and future project-specific rules), strictly separated from
evidence generation, harmonization, featurization, training, and prediction.
The architectural intent — keeping *project prioritization criteria* out of the
*evidence and modelling path* — is consistent with the separation discipline
ENG §2 already enforces, and nothing in the Constitution, ADR-0001…ADR-0007, or
`GDR-001` conflicts with it.

Two naming/structural conflicts were found during review, and are resolved by
this ADR rather than papered over.

### Conflict 1 — `SCI-4` is already allocated, and load-bearing

The request labelled this layer `SCI-4`, "immediately after the prediction
stage." In this repository:

| Requested | Actual (`docs/IMPLEMENTATION_BACKLOG.md`) |
|---|---|
| `SCI-3` = Prediction | `SCI-3` = Knowledge extraction and first Tier 2 query |
| `SCI-4` = Decision Policy | `SCI-4` = **Cross-family transfer** |

`SCI-4` maps to Constitution §9.6, "Stage 4 — Cross-family transfer (Phase 3;
**a gate, not an option**)," which carries criterion **S7**. Per §9.6's binding
honesty clause, S7 carries the project's *entire generality claim*: "Because
Stage 4 carries the entire generality claim, its absence changes what the
project is. Without S7, the deliverable is a case study on Class I PI3K, and
the title, abstract and conclusions must say so." Re-using the `SCI-4` label
for a decision-policy layer would shadow the stage carrying that claim, and
silently renumbering stages would break the Constitution's §9.x stage mapping
and every backlog cross-reference to it. Neither is acceptable, and neither was
the intent of the request.

**Resolution.** The requested capability is implemented in full, as an
*unnumbered architectural layer* rather than a numbered stage. This is not a
downgrade — it is the correct category. The repository already distinguishes
the two:

- **`SCI-N` are temporal stages**: sequenced work with gate records, phase
  commitments, and Constitution §9.x mappings.
- **Package names are architectural layers**: `data/`, `pocket/`, `features/`,
  `model/`, `train/`, `eval/`, `explain/`, `kg/` — code responsibilities, not
  scheduled stages, and none of them is numbered.

The request itself called this an "architectural layer" operating on model
outputs. `policy/` is therefore the consistent home. No stage is renumbered, no
stage is created, and `SCI-4`/S7 is untouched.

If the Project Owner does additionally want a numbered *stage* for policy work
(e.g. a scheduled candidate-prioritization stage), that is a separate
governance decision affecting the Constitution's stage mapping, and is not
taken here.

### Conflict 2 — ENG §2's package table is authoritative and exhaustive

ENG §2 states: "Each package under `src/<pkg>/` has exactly one [responsibility],
and they are mutually exclusive," followed by a closed table. `policy/` is
absent from it, and none of the eight existing responsibilities covers
"classify predictions against project objectives" — `eval/` is the nearest, but
its responsibility is "evaluation, calibration, degeneracy battery, seal
reading," i.e. scoring the project's own falsifiable criteria, which is
explicitly *not* what a prioritization layer does (see "Criterion firewall"
below). Adding the package therefore requires amending the table, which per
ENG §1 requires an Accepted ADR before implementation. That is this ADR.

---

## Decision detail

### Placement in the import graph

`policy/` is added as the **highest** layer in the `.importlinter` layers
contract, above `eval/`. Consequence, which is the point: `policy/` may import
lower layers, and **no lower layer may import `policy/`**. Mechanically, this
makes it impossible for a policy threshold to influence featurization,
training, prediction, evaluation, or the evidence corpus — the separation the
request asked for is enforced by the import linter, not by convention.

Amended layer order (highest → lowest):

```
orthosteric.policy      <- new
orthosteric.eval
orthosteric.explain
orthosteric.train
orthosteric.model
orthosteric.features
orthosteric.pocket
orthosteric.data
orthosteric.runtime
```

### Criterion firewall (Constitution §1.4)

Constitution §1.4 fixes the S-criteria thresholds before any model is trained,
and `SCI0-029` seals them. Policy thresholds are a different kind of object:
they express *what the project currently wants to prioritize*, are expected to
change between projects, and are explicitly **not** scientific claims about
PI3K. Allowing them to be confused would create a route to post-hoc threshold
selection — precisely the failure `R23` and §1.4 exist to prevent.

Three mechanisms keep them apart:

1. **Import direction** — `eval/` cannot import `policy/` (above).
2. **Explicit non-eligibility marker** — every `PolicyOutcome` and
   `DecisionRecord` carries `criterion_eligible = False`, a field whose only
   purpose is to make misuse loud in any artefact that serializes it.
3. **Documentation** — `policy/README.md` and this ADR state that no policy
   output may be reported as, or used to compute, S1–S10.

Policy thresholds are consequently **not** sealed artefacts and are **not**
added to `sealed/MANIFEST.md`.

### Governed constraints the layer must honour

The layer is new, but it operates on quantities the Constitution already
governs. These are implemented as governed rules, not as invented policy:

| Rule | Source | Implementation |
|---|---|---|
| Selectivity is **undefined** below `pAct_α ≥ 7.0` | §2.3(6) potency floor | `SelectivityPolicy` returns `UNDEFINED_POTENCY_FLOOR`, not a low tier — "undefined" is not "Tier below A" |
| `Indeterminate` contributes **zero** to selectivity claims and is not evidence of sparing | §2.2 | Any `Indeterminate` among the isoforms a claim needs → `UNDEFINED_INDETERMINATE`; never silently read as spared |
| Primary target is expressed as log differences `pAct_α − pAct_x` | §2.3(4) | Computed in log space; fold-change exposed as a derived view (`10 ** Δ`), mathematically identical to the requested ratio |
| Biochemical and cellular selectivity are separate targets, never pooled | §2.3(3) | Heterogeneous `measurement_class` within one prediction → `UNDEFINED_MIXED_CLASS` |
| Joint confidence is a **product** over correlated events, lower than the weakest component; the min-rule is wrong | §2.4 | `ConfidencePolicy` composes by product, never `min` |
| No model may claim precision below its label noise floor | §2.4 | `UncertaintyPolicy` compares interval width against a caller-supplied floor and abstains when none is supplied, rather than assuming one |

### Interaction with the blocked Cheng–Prusoff normalization (AUDITOR-5)

The request specified computing selectivity from "the harmonized potency metric
adopted elsewhere in the pipeline." **No such cross-isoform-harmonized metric
currently exists.** Constitution §2.3's own preamble states the reason: "All
targets in Tiers 1 and 2 are engaged ATP-competitively and **differ in ATP
Km**. IC50 depends on assay ATP concentration." Conversion to `Ki` via
Cheng–Prusoff is the normalization that would make cross-isoform ratios
comparable, and it is blocked — `AUDITOR-5` is `INSUFFICIENT_EVIDENCE`
(no authoritative per-isoform ATP Km source; see
`docs/governance/SCI0-028-GOVERNANCE-GAP-REPORT.md` §7).

This ADR does **not** unblock it and does not infer any Km. Instead the layer
makes the gap explicit and auditable rather than silently producing a
scientifically invalid ratio:

- `PredictionInput` carries a required `normalization: NormalizationStatus`
  field (`CHENG_PRUSOFF_APPLIED` / `NOT_NORMALIZED` /
  `NORMALIZATION_NOT_REQUIRED`).
- When a cross-isoform selectivity tier is computed from `NOT_NORMALIZED`
  inputs, the outcome is still produced (the arithmetic is well defined) but
  carries `governance_flags` containing an `AUDITOR-5` advisory, propagated
  into `DecisionRecord`. The tier is usable for *internal prioritization* —
  which is all this layer is for — and is marked as not comparable across
  assays with differing `[ATP]`.
- `criterion_eligible` remains `False` regardless, so no such number can reach
  a gated criterion.

### Provenance and determinism

`DecisionProvenance` records: policy identifier, policy version, the full
threshold configuration, software version (`SoftwareProvenance`, reused from
`SCI0-011` rather than redefined), model version, evidence snapshot SHA-256,
prediction identifier, and decision timestamp.

Following the `SCI0-011` precedent exactly: the **timestamp is provenance
metadata and is excluded from the decision content hash**, so two evaluations
of the same prediction under the same configuration and software produce an
identical `decision_content_sha256`. Determinism is a property of the decision;
the timestamp records when it was taken.

`evidence_snapshot_sha256` is the `SCI0-011` snapshot hash, which is what makes
a decision reproducible from the immutable corpus as required.

---

## Alternatives considered

| Alternative | Why not |
|---|---|
| Label it `SCI-4` as requested | Collides with Cross-family transfer / S7 / Constitution §9.6 binding honesty clause (Conflict 1) |
| Renumber existing `SCI-4`/`SCI-5` to free the label | Breaks Constitution §9.x stage mapping and all backlog cross-references; a Scientific-category change to the project's gate structure, far beyond the request's intent |
| Put policy logic in `eval/` | ENG §2 responsibilities are mutually exclusive; `eval/` scores the project's falsifiable criteria, and merging prioritization into it destroys the §1.4 firewall this ADR exists to build |
| Put policy logic in `model/` | ENG §2: `model/` is prediction only, "must not contain evaluation metrics"; and it would let thresholds sit upstream of predictions |
| Hard-code the selectivity cutoffs | Explicitly rejected by the request, and correctly: they are project objectives, not scientific truths |
| Make policy thresholds sealed artefacts | Would wrongly imply they gate scientific claims, and would force a corpus/threshold re-seal every time a prioritization preference changed — the opposite of the requested property that "changing these thresholds must never require rebuilding the curated evidence corpus" |

## Consequences

- ENG §2 gains a ninth package row; `.importlinter` gains a ninth layer.
- `policy/` may be built and tested now, before `SCI-1`/`SCI-2` exist, because
  it depends only on an input contract it defines itself
  (`PredictionInput`), not on a trained model. No prediction is fabricated: the
  layer is exercised in tests against explicitly synthetic inputs, and produces
  no scientific claim.
- Default selectivity tiers (10× / 30× / 100× / 300× / 1000×) ship as
  configuration with no sealed status and no scientific authority. They are
  project prioritization bands.
- `SCI-4` (Cross-family transfer), S7, and Constitution §9.6 are unchanged.
- `AUDITOR-5` remains `INSUFFICIENT_EVIDENCE`; no ATP Km value is introduced.

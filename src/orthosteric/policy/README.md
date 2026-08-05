# `policy/` — Decision Policy Layer

**Authority:** `ADR-0008` [Architectural].
**Constitution sections served:** §2.2 (Indeterminate), §2.3(3) (biochemical /
cellular never pooled), §2.3(4) (log-difference target), §2.3(6) (potency
floor), §2.4 (uncertainty composition), §1.4 (criterion firewall — by
exclusion).

## Purpose

Classify model predictions against configurable, versioned **project
objectives**: potency, selectivity, confidence, uncertainty, and future
project-specific prioritization rules.

## What this layer is not

It is **not** an evidence-processing layer. It never modifies evidence,
harmonized data, feature representations, or learned models. That is enforced
mechanically, not by convention: `policy/` is the **highest** layer in the
`.importlinter` layers contract, so no lower layer may import it.

It is **not** a numbered stage. `SCI-4` is *Cross-family transfer*
(Constitution §9.6, criterion S7 — the criterion carrying the project's entire
generality claim). `ADR-0008` records why this capability is an unnumbered
architectural layer, consistent with `data/`, `features/`, `model/`, `eval/`,
`explain/`, rather than a stage.

It is **not** criterion-scoring. Every `PolicyOutcome` and `DecisionRecord`
carries `criterion_eligible = False`. Policy thresholds express what the
project currently wants to prioritize; the Constitution's S-criteria thresholds
are fixed before training (§1.4) and sealed by `SCI0-029`. Conflating them
would open a route to post-hoc threshold selection (risk `R23`).

## Corpus quality gate (`ADR-0009`)

`CorpusQualityGatePolicy` is a small sibling construct alongside the
prediction-level policies above: it consumes a `CorpusQualityAssessment`
(`quality/`) — never raw corpus statistics — and applies the `GDR-003` §4
aggregation rule to produce a `GateDecision` (`PROCEED` / `WARNING` /
`REDESIGN` / `STOP`). It does not implement the `Policy` ABC, because its
input/output shape genuinely differs from a per-compound prediction
decision; see `ADR-0009` §5 for why forcing one interface onto both was
rejected. `criterion_eligible` remains `False`, matching the firewall above.

## Public API

| Name | Purpose |
|---|---|
| `PolicyEngine` | Runs registered policies, emits a `DecisionRecord` with provenance |
| `Policy` | ABC every policy implements; add a policy without changing existing code |
| `PolicyConfig` | Versioned configuration shared by one engine's policies |
| `SelectivityTierTable`, `SelectivityTier` | Configurable prioritization bands |
| `DEFAULT_SELECTIVITY_TIERS` | 10x / 30x / 100x / 300x / 1000x — project objectives, not scientific claims |
| `SelectivityPolicy` | Fold-selectivity → tier, with §2.2/§2.3 gates |
| `PotencyPolicy` | Reference-isoform potency floor (§2.3(6)) |
| `ConfidencePolicy` | Joint confidence as a **product** (§2.4) |
| `UncertaintyPolicy` | Interval width vs label-noise floor (§2.4); abstains when no floor is configured |
| `PredictionInput`, `IsoformPrediction` | Input contract `SCI-2`/`SCI-3` must satisfy |
| `DecisionRecord`, `DecisionProvenance` | Immutable decision + reproducibility anchor |

## Selectivity

Computed in log space, per Constitution §2.3(4):

```
log_difference(x) = pAct_reference - pAct_x
fold(x)           = 10 ** log_difference(x)      # == Activity_x / Activity_reference
Smin              = min over off-target isoforms of fold(x)
```

`Smin` determines the tier. The full `SelectivityVector` — every per-isoform
log difference and fold value, plus which isoform was limiting — is retained
for downstream analysis, so nothing is lost to the scalar.

Worked example (α = 0.5 nM, β = 85 nM, γ = 170 nM, δ = 120 nM):
fold β ≈ 170, γ ≈ 340, δ ≈ 240 → `Smin` ≈ 170 → **`TIER_C`** (≥ 100×, < 300×),
limiting isoform β.

## Governed gates applied before any tier is assigned

| Gate | Rule | Result |
|---|---|---|
| Potency floor | §2.3(6): selectivity is *undefined* below `pAct_α ≥ 7.0` | `UNDEFINED_POTENCY_FLOOR` — not a low tier |
| Indeterminate | §2.2: contributes zero to selectivity claims; not evidence of sparing | `UNDEFINED_INDETERMINATE` |
| Mixed class | §2.3(3): biochemical and cellular never pooled | `UNDEFINED_MIXED_CLASS` |
| Missing prediction | Missing is not inactive | `UNDEFINED_MISSING_PREDICTION` |

## Known limitation: the potency metric is not cross-isoform harmonized

The Class I isoforms differ in ATP Km and IC50 depends on assay `[ATP]`
(Constitution §2.3 preamble). Cheng–Prusoff conversion to `Ki` is the
normalization that would make cross-isoform ratios comparable, and it is
**blocked**: `AUDITOR-5` is `INSUFFICIENT_EVIDENCE` (no authoritative
per-isoform ATP Km source — see
`docs/governance/SCI0-028-GOVERNANCE-GAP-REPORT.md` §7).

This layer does not unblock it and infers no Km. Instead every
`PredictionInput` carries a required `NormalizationStatus`, and a tier computed
from `NOT_NORMALIZED` inputs still carries the `AUDITOR5_ADVISORY` governance
flag into the `DecisionRecord`. Such tiers are usable for internal
prioritization only.

## Determinism

`decision_content_sha256` covers the prediction, configuration, participating
policies, and software provenance — **not** the timestamp, following the
`SCI0-011` precedent. Identical inputs and configuration therefore yield an
identical content hash; the timestamp records when the decision was taken.

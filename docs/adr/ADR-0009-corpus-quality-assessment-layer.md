# ADR-0009 [Architectural] — Corpus Quality Assessment Layer (`quality/`)

**Status:** Accepted
**Decision:** Add a new architectural layer, `src/orthosteric/quality/`, that
interprets a `SCI0-011`/`GDR-002` `CorpusProfile` into a per-dimension,
transparent adequacy assessment, strictly separated from both the descriptive
profile beneath it and the decision policy above it. Amend `ENGINEERING_
STANDARDS.md` §2's package table and the `.importlinter` layer order to admit
it.
**Date:** 2026-08-05.
**Reversibility:** costly — a new package appears in the authoritative ENG §2
responsibility table and in the enforced import graph.
**Review trigger:** `SCI0-018` (structural inventory) landing, which is the
first point at which the prepared structural-coverage extension point (§4)
has real data to consume; or any request to add a quality dimension.

---

## Context

`GDR-002` reclassified `N_c`, `N_b`, and `N_w` as corpus-derived engineering
parameters and, in doing so, retired R1's automatic numeric kill-switch for
them, routing the resulting adequacy judgment to the `SCI0-031` human gate.
That left the judgment correctly de-fanged but architecturally informal: the
human at `SCI0-031` was pointed at a raw `CorpusProfile` with no structured
interpretation layer between "here are forty numbers" and "proceed, redesign,
or stop." The Project Owner's instruction asks for exactly that missing
layer, with three responsibilities kept architecturally separate and none
merged into another:

```
SCI0-011 Immutable Snapshot
        |
SCI0-014b Dataset Characterization
        |
Corpus Profile                    (GDR-002; data/snapshots/_profile.py)
        |
Corpus Quality Assessment         (this ADR; quality/)
        |
ADR-0008 Decision Policy Layer    (policy/)
        |
Proceed / Warning / Redesign / Stop
```

Two package-boundary questions had to be resolved before implementation, per
`ENGINEERING_STANDARDS.md` §2 ("each package... has exactly one
[responsibility]... mutually exclusive"):

## 1. Why a new package, not an extension of `data/` or `policy/`

`data/`'s ENG §2 responsibility is "loading, provenance, censoring, tier
gating." Interpreting a profile's *adequacy* is not measurement — it is a
judgment about what the measurements mean, which is a categorically different
responsibility, and the Project Owner's instruction is explicit that "these
are three distinct architectural layers" and "do not merge these
responsibilities." Folding assessment logic into `data/snapshots/_profile.py`
would violate ENG §2's mutual-exclusivity rule the same way folding it into
`policy/` would violate the instruction's explicit requirement that "the
policy layer must not compute statistics itself" and must "consume only
`CorpusQualityAssessment` rather than raw corpus statistics." A third package
is therefore required, exactly as `ADR-0008` required a new package rather
than extending `eval/` or `model/` for the same category of reason.

## 2. Layer placement in the import graph

`quality/` is inserted directly above `data/` and below every other layer:

```
orthosteric.policy      (ADR-0008; highest — nothing may import it)
orthosteric.eval
orthosteric.explain
orthosteric.train
orthosteric.model
orthosteric.features
orthosteric.pocket
orthosteric.quality     <- new (this ADR)
orthosteric.data
orthosteric.runtime
```

Consequences, mechanical and load-bearing:

- `data/` **cannot** import `quality/`. `CorpusProfile` remains descriptive
  only by construction, not merely by convention: it is architecturally
  impossible for the profile-building code to reach up into interpretation
  logic, matching the instruction's "CorpusProfile must remain descriptive
  only. No decisions. No pass/fail."
- `policy/` (unaffected — still the highest layer) can import `quality/`,
  satisfying "ADR-0008 should consume only `CorpusQualityAssessment`."
- `pocket/`, `features/`, `model/`, `train/`, `explain/`, `eval/` are
  unaffected and do not need to import `quality/`; none of the `SCI-1`/`SCI-2`
  work described elsewhere in the backlog depends on this layer, and this ADR
  does not create a dependency where none was requested.

**Design-contract boundary, stated honestly (not mechanically enforced).**
Import-linter enforces the package boundary, not which functions within an
allowed package get called. "Never access raw records directly"
(the Project Owner's instruction) is enforced here as an *interface contract*:
every `QualityDimensionEvaluator.evaluate()` (§3) takes a `CorpusProfile` as
its only input and nothing else is passed a record list anywhere in this
package. This is the same enforcement strategy `ADR-0008` already used for
`policy/`'s `Policy.evaluate(prediction)` — the mechanism is precedent, not
novel.

## 3. Extensibility mechanism — reused, not reinvented

`quality/` uses the identical extensibility pattern `ADR-0008` established
for `policy/`: an abstract `QualityDimensionEvaluator` interface plus an
engine (`CorpusQualityAssessor`) that iterates whatever evaluators it was
given. Adding a dimension — structural diversity, MD-state diversity,
pocket-state diversity, mutation coverage, assay diversity, experimental
modality diversity, all named in the Project Owner's instruction as future
extensions — means adding a class and registering an instance; no existing
evaluator or the assessor itself changes. This is deliberate reuse of a
proven pattern rather than a new one, for the same reason `ADR-0008` gave for
choosing it originally: determinism and non-interference are properties of
the interface, not of any one implementation.

## 4. The structural-coverage extension point — prepared, not implemented

Per the explicit instruction "prepare explicit extension points for
`SCI0-007`-derived structural information... do not implement `SCI-1`
structural features here," this ADR adds:

- A registered `StructuralCoverageEvaluator` that always returns
  `DimensionStatus.NOT_YET_AVAILABLE`, with a rationale naming exactly what it
  will check once data exists (experimental PDB coverage, AlphaFold-fallback
  coverage, construct diversity, conformational-state diversity, ligand-bound
  structural coverage) — demonstrating the extension mechanism end-to-end
  without inventing the computation.
- A reserved, always-`None`-defaulted field on `CorpusProfile`,
  `structural_coverage: StructuralCoverageStats | None`, and an empty
  `StructuralCoverageStats` placeholder dataclass naming the fields a future
  `SCI0-018` computation would populate. No PDB or AlphaFold record is read
  anywhere in this change.

This is an additive, backward-compatible change to `_profile.py`
(`GDR-002`'s already-merged module): every existing caller that does not pass
`structural_coverage` gets `None`, and every existing test's relative-hash
comparisons remain valid, since none asserted a literal hash value. The
profile schema and algorithm version constants are bumped (`_gdr002` →
`_adr0009`) because the profile's *shape* changed, per the same "changing
[X] must produce a new version" principle `GDR-002` already established for
the profile itself.

## 5. `PROCEED` / `WARNING` / `REDESIGN` / `STOP` — where each label is decided

Per the instruction, dimension-level status and the overall recommendation
are computed by different layers:

| Layer | Output | Vocabulary |
|---|---|---|
| `quality/` (`CorpusQualityAssessment`) | Per-dimension interpretation | `DimensionStatus` — see `GDR-003` for exactly which non-arbitrary rule produces each value |
| `policy/` (`CorpusQualityGatePolicy`, new in this change) | Overall recommendation | `GateStatus.PROCEED` / `WARNING` / `REDESIGN` / `STOP` |

`CorpusQualityGatePolicy` is a small sibling construct within `policy/`,
distinct from the existing `Policy` ABC (`ADR-0008`): its input is a
`CorpusQualityAssessment`, not a `PredictionInput`, because the two are
genuinely different kinds of decisions (a prediction-level classification vs.
a corpus-adequacy gate), and forcing one interface onto both would be
architecturally dishonest rather than reused discipline. `GateDecision`
carries `criterion_eligible = False`, matching `ADR-0008`'s firewall
convention: a corpus-adequacy gate decision is not a Constitution `S1`–`S10`
criterion either.

**How the aggregation avoids opaque scoring.** `GateStatus` is computed by
simple, stated set-membership rules over the *categorical* per-dimension
statuses (e.g., "`STOP` if any dimension is `STRUCTURALLY_DEGENERATE`"), never
by a weighted sum or any numeric combination — see `GDR-003` §2 for the exact
rule table. This satisfies "avoid collapsing everything into one number
unless governance already specifies how" by not collapsing anything into a
number at all.

## 6. What this ADR does not do

- It does not set, or remove the need to eventually set, any Constitution
  §1.4-sealed threshold. `GDR-003` documents which specific rules are used and
  why none of them is an invented magnitude (§7 below).
- It does not touch AUDITOR-5 / ATP Km / Cheng–Prusoff. Scientific parameters
  remain under scientific governance, unaffected by this architectural layer.
- It does not compute structural-coverage statistics from real `SCI0-007`
  data (§4).
- It does not implement `SCI-1` features of any kind.

## 7. Non-arbitrary rules: pointer

The specific rule used per dimension — and the argument that each is a
structural/definitional fact rather than an invented magnitude — is a
scientific-methodology decision, documented in `GDR-003`, not repeated here.
This ADR fixes the architecture; `GDR-003` fixes the content.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Extend `data/snapshots/_profile.py` with a `quality_status` field | Violates ENG §2 mutual exclusivity and the instruction's explicit "do not merge these responsibilities"; would also let `data/` produce pass/fail judgments, which the instruction forbids |
| Extend `policy/` to compute the assessment itself | Violates "the policy layer must not compute statistics itself" and "should consume only `CorpusQualityAssessment` rather than raw corpus statistics" |
| Force `CorpusQualityGatePolicy` to implement the existing `Policy(PredictionInput)` ABC | The input/output shapes are genuinely different (corpus-level gate vs. per-compound prediction); forcing one interface onto both hides that difference rather than expressing it |
| Collapse per-dimension statuses into a single weighted score | Explicitly rejected by the instruction ("avoid collapsing everything into one number unless governance already specifies how"; "do not introduce opaque scoring") |
| Implement real structural-coverage computation now | Explicitly out of scope ("do not implement `SCI-1` structural features here") and no `SCI0-018` data exists yet to compute it from |

## Consequences

- ENG §2 gains a tenth package row; `.importlinter` gains a tenth layer,
  positioned so `data/` cannot import it and `policy/` can.
- `_profile.py`'s schema and algorithm version constants bump; the change is
  additive and backward-compatible.
- `policy/`'s public API gains `CorpusQualityGatePolicy`, `GateDecision`,
  `GateStatus`, alongside the existing prediction-level policies — the two
  families coexist in the same package because both are, architecturally,
  "things above `eval/` that classify something and must not be imported
  from below," which is exactly `policy/`'s ENG §2 responsibility as already
  amended by `ADR-0008`.
- No Constitution threshold, ADR-0003 item, or `SCI0-028` open item changes
  status because of this ADR; see `GDR-003` for the one item this change set
  does close out.

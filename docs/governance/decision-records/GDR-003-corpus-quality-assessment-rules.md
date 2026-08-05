# Governance Decision Record GDR-003 — Corpus Quality Assessment Rules; Closing the Remaining R1 Threshold Dependency

**Category:** Scientific (methodology — which specific rules a quality
dimension may use without inventing a threshold; and the final disposition
of R1's numeric interpretation for `N_c`/`N_b`/`N_w`).
**Status:** Accepted.
**Date:** 2026-08-05.
**Decided by:** Project Owner, direct instruction (2026-08-05), implemented
by the computational pipeline. Companion to `ADR-0009`, which fixes the
architecture this record's rules run inside.
**Amends:** `docs/specifications/CONSTITUTION_AMENDMENT_SET_v4.7.md`
Amendment A10 (further revision note, additive); `GDR-002` (extends, does
not contradict, its §4).

---

## Decision

Every rule a `quality/` dimension evaluator applies is one of exactly two
kinds. No third kind is used anywhere in this change set, and none may be
added without a further Governance Decision Record:

1. **Structural/definitional facts** — statements true or false by the
   definition of the quantity itself, independent of any magnitude choice.
   Example: "does at least one four-isoform-complete stratum exist" is true
   or false by the definition of `n_w`; there is no number to invent, only a
   zero/non-zero check.
2. **Already-governed magnitudes** — a number the Constitution or a prior
   Governance Decision Record has already sealed, cited by reference rather
   than re-derived or re-chosen. Exactly one such number exists in this
   record's scope: the "< 8 scaffold families" disjunct of R1, fixed at the
   Constitution's original authorship (v4.6), not one of `SCI0-028`'s
   outstanding placeholders (`GDR-002` §3, "the scaffold-diversity gap").

**No rule in this record introduces a new magnitude threshold.** Where no
structural fact and no already-governed number exists for a dimension, the
evaluator reports the descriptive metric and a status meaning "present;
adequacy not governed; refer to the `SCI0-031` human gate" — never a
manufactured `PASS`/`WARNING` split.

## 1. Rationale

`docs/governance/SCI0-028-GOVERNANCE-GAP-REPORT.md` §3–4 and `GDR-002`
already established, independently, that no literature source and no
first-principles derivation can supply a defensible magnitude for `N_c`,
`N_b`, or `N_w`. Any dimension-evaluator rule that quietly picked a
percentage, a ratio, or a count (however reasonable-sounding) to split
`PASS`/`WARNING` would be exactly the invented threshold the project has
twice already found unsupportable — merely relocated from "seal a number
before the audit" to "invent a number inside the assessment code." This
record exists to make that discipline explicit and auditable per dimension,
so a future contributor extending `quality/` has a standard to hold new
evaluators to.

## 2. Per-dimension rules

Each rule below states which of the two permitted kinds it is, and why.

### Connectivity
- `STRUCTURALLY_DEGENERATE` if `n_c == 0` (no compounds in any component —
  the evidence graph is empty) — structural fact.
- `STRUCTURALLY_DEGENERATE` if `n_connected_components == total_compounds`
  and `total_compounds > 0` (every compound is its own isolated component;
  zero co-assay relationships exist anywhere) — structural fact: this is the
  definitional boundary of "no connectivity at all," not a chosen ratio.
- `STRUCTURALLY_DEGENERATE` if `n_b == 0` and `n_connected_components > 1`
  (more than one component exists, and nothing bridges any of them — no
  cross-study comparison is possible for any pair of studies) — structural
  fact about the graph's topology, not a magnitude.
- `NON_DEGENERATE_UNQUANTIFIED` otherwise — present; whether the observed
  `N_c`/`N_b` is "enough" is exactly the judgment `GDR-002` routed to
  `SCI0-031`, and this record does not attempt it.

### Coverage
- `STRUCTURALLY_DEGENERATE` if any Tier 1 isoform has zero measured compounds
  (`per_isoform_compounds[iso] == 0`) — structural fact: the Constitution's
  comparative framework requires evidence for all four isoforms to exist at
  all (§2.3(4)'s `S1` vector has one term per isoform).
- `STRUCTURALLY_DEGENERATE` if `n_w == 0` (zero compounds measured across all
  four isoforms within one qualifying stratum) — structural fact: `S1`,
  `S2`, `S4a`, `S4b` are literally undefined without at least one such
  compound; this is not a chosen minimum, it is the point below which the
  quantity the criteria are defined on does not exist.
- `NON_DEGENERATE_UNQUANTIFIED` otherwise.

### Scaffold diversity
- `GOVERNED_THRESHOLD_NOT_MET` if the corpus-global scaffold-family count
  (`characterization.scaffold_stats.n_ring_system_families`) is below 8 —
  citing R1's own unchanged fourth disjunct, an already-governed magnitude,
  not invented here.
- `GOVERNED_THRESHOLD_MET` otherwise, **with an explicit caveat carried into
  the rationale string**: R1's actual criterion restricts the count to the
  largest connected component specifically, which `GDR-002` recorded as not
  yet computable (`scaffold_families_in_largest_component: None`). The
  corpus-global count is always >= the true restricted count, so a
  corpus-global `GOVERNED_THRESHOLD_MET` does **not** guarantee the true,
  narrower criterion is met — this is stated in every such outcome's
  rationale, never silently elided.

### Publication concentration
- `INSUFFICIENT_DATA` if `n_publications == 0` — no publication-linked
  evidence exists to assess independence from at all.
- `WARNING` if `n_publications == 1` — structural fact, not a chosen
  percentage: "independent replication" is definitionally impossible with
  fewer than two independent sources, matching Constitution §2.4's own
  emphasis on inter-lab reproducibility requiring more than one lab.
- `NON_DEGENERATE_UNQUANTIFIED` otherwise (>= 2 publications — independent
  replication is at least possible; how well-distributed the evidence is
  across them is not assessed here).

### Confidence
- `INSUFFICIENT_DATA` if `mean_confidence is None` (no confidence scores
  attached to any record in the corpus) — structural fact.
- `NON_DEGENERATE_UNQUANTIFIED` otherwise — the distribution (tier counts,
  mean, median) is reported in full as supporting metrics; no cutoff is
  applied to it.

### Missingness
- `STRUCTURALLY_DEGENERATE` if every isoform-pair overlap entry in the
  missingness matrix is zero (no two Tier 1 isoforms are ever co-measured
  for any compound) — the same underlying condition as the connectivity
  degenerate cases, reported from `CharacterizationReport.missingness`
  specifically so the instruction's "no information may be hidden" is honored
  even where the signal is redundant with another dimension.
- `NON_DEGENERATE_UNQUANTIFIED` otherwise.

### Structural coverage (extension point; `ADR-0009` §4)
- `NOT_YET_AVAILABLE`, always, until `SCI0-018` exists. This is not a rule
  about the corpus; it is an honest statement that the evaluator has no data
  source yet. See `ADR-0009` §4 for the reserved field this will eventually
  read.

## 3. `DimensionStatus` vocabulary (binding on future evaluators)

| Value | Meaning | Kind of rule that may produce it |
|---|---|---|
| `STRUCTURALLY_DEGENERATE` | A governed Constitution criterion is definitionally uncomputable | Structural fact only |
| `GOVERNED_THRESHOLD_MET` / `GOVERNED_THRESHOLD_NOT_MET` | An already-sealed Constitution or GDR number was checked | Already-governed magnitude only — the evaluator must cite exactly which sealed value it used |
| `INSUFFICIENT_DATA` | Zero underlying observations for this dimension | Structural fact (count == 0) |
| `WARNING` | A structural boundary condition short of full degeneracy was met | Structural fact only (e.g., "exactly one independent source," never a percentage) |
| `NON_DEGENERATE_UNQUANTIFIED` | Present; magnitude adequacy is not governed and is not assessed here | Default when no rule of either permitted kind applies |
| `NOT_YET_AVAILABLE` | No data source exists yet for this dimension | Extension-point placeholder only |

A future evaluator introducing a new `WARNING` or a new `GOVERNED_THRESHOLD_*`
value must be able to state, in its own module docstring, which of the two
permitted kinds justifies it, in the same form as §2 above. This is the
standard `ADR-0009` §3's extensibility mechanism is built to be held to.

## 4. `GateStatus` aggregation rule (`policy/_corpus_gate.py`)

Deterministic, categorical, stated in full (no part of this rule is
implicit):

```
STOP      if any dimension is STRUCTURALLY_DEGENERATE
REDESIGN  else if any dimension is GOVERNED_THRESHOLD_NOT_MET
WARNING   else if any dimension is WARNING, or INSUFFICIENT_DATA,
               or NOT_YET_AVAILABLE
PROCEED   otherwise (every dimension is NON_DEGENERATE_UNQUANTIFIED or
               GOVERNED_THRESHOLD_MET)
```

`INSUFFICIENT_DATA` and `NOT_YET_AVAILABLE` are folded into `WARNING` rather
than `PROCEED`, per "preserve fail-closed behavior throughout" — an assessed
dimension with no data is not silently treated as adequate.

This is boolean set-membership logic over categorical labels, not a weighted
score, satisfying the instruction's "avoid opaque scoring" and "transparent
governed rules" requirements simultaneously.

## 5. Effect on R1 and `GDR-002` — the remaining dependency is now closed

`GDR-002` §4 already retired R1's automatic kill-switch for `N_c`/`N_b`/`N_w`
and routed the judgment to `SCI0-031`, but left open exactly how that human
judgment would be informed. This record closes that: the `SCI0-031` decision
is now informed by a `GateDecision`, itself informed by a
`CorpusQualityAssessment` containing zero magnitude comparisons against
`N_c`, `N_b`, or `N_w` directly — every rule touching those three quantities
in §2 above is a structural zero/non-zero check, never a "greater than X"
comparison. **No fixed-threshold dependency on `N_c`, `N_b`, or `N_w`
remains anywhere in the interpretation pipeline**, satisfying the
instruction's explicit closing requirement.

The one magnitude comparison that does remain in this record's scope (the
"< 8 scaffold families" check) is not one of `N_c`/`N_b`/`N_w` and was never
part of `GDR-002`'s reclassification — it is R1's separate, already-governed
fourth disjunct, cited rather than invented, exactly as `GDR-002` §3 and §4
already stated it would remain.

## 6. What this record does not do

- It does not set any new numeric threshold for `N_c`, `N_b`, or `N_w`.
- It does not touch AUDITOR-5, ATP Km, or Cheng–Prusoff normalization.
- It does not introduce machine-learning-based quality estimation, and no
  parameter in this record is tuned against model performance — every rule
  in §2 is fixed by definition or by prior governance, before any model
  exists to tune against.
- It does not compute the true largest-component-restricted scaffold-family
  count; the caveat in §2 ("Scaffold diversity") is carried forward, not
  resolved.

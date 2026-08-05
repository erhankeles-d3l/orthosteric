# `quality/` — Corpus Quality Assessment Layer

**Authority:** `ADR-0009` [Architectural]; `GDR-003` [Scientific] (which
specific rules each dimension may use, and why none is an invented threshold).

## Purpose

Interpret an already-frozen `CorpusProfile` (`GDR-002`,
`data/snapshots/_profile.py`) into a transparent, per-dimension adequacy
assessment — the middle of three architecturally distinct layers:

```
CorpusProfile              descriptive only (data/snapshots, GDR-002)
        |
CorpusQualityAssessment    interpretive (this package)
        |
Decision Policy            policy/ (ADR-0008) -- consumes the assessment,
                            never raw statistics
```

## What this layer is not

It is **not** a statistics-computation layer. Every `QualityDimensionEvaluator
.evaluate()` takes only a `CorpusProfile`; none reads a raw record or
recomputes anything `data/snapshots`, `data/graph.py`, or `data/audit.py`
already computed.

It is **not** a decision layer. It produces per-dimension `DimensionStatus`
values, never `PROCEED`/`WARNING`/`REDESIGN`/`STOP` — that synthesis happens
in `policy/`'s `CorpusQualityGatePolicy` (`ADR-0009` §5), which consumes this
package's output and nothing else.

It does **not** invent numeric thresholds. Every rule a dimension evaluator
applies is either a structural/definitional fact (true or false by the
quantity's own definition — e.g. "does at least one four-isoform-complete
compound exist") or an already-governed magnitude cited by reference (the
one example in this package: R1's "< 8 scaffold families," fixed at the
Constitution's original authorship). See `GDR-003` §2 for the exact rule
used by every evaluator, and the standard any future evaluator must meet.

## Public API

| Name | Purpose |
|---|---|
| `CorpusQualityAssessor` | Runs registered evaluators, produces a `CorpusQualityAssessment` |
| `QualityDimensionEvaluator` | ABC every dimension implements; add one without changing existing code |
| `default_evaluators()` | The standard evaluator set (connectivity, coverage, scaffold diversity, publication concentration, confidence, missingness, structural coverage) |
| `DimensionStatus` | Closed vocabulary — see `GDR-003` §3 for the binding definition of each value |
| `DimensionAssessment` | One dimension's status, rationale, supporting metrics, and provenance — "no information may be hidden" |
| `CorpusQualityAssessment` | Immutable, content-hashed, snapshot-specific result |

## Dimensions implemented today

| Dimension | Rule kind | Possible statuses |
|---|---|---|
| Connectivity | Structural facts (zero/near-zero checks on `N_c`/`N_b`) | `STRUCTURALLY_DEGENERATE`, `NON_DEGENERATE_UNQUANTIFIED` |
| Coverage | Structural facts (zero-isoform, `n_w == 0`) | `STRUCTURALLY_DEGENERATE`, `NON_DEGENERATE_UNQUANTIFIED` |
| Scaffold diversity | Already-governed magnitude (R1's "< 8 families") | `GOVERNED_THRESHOLD_MET` (with a stated caveat), `GOVERNED_THRESHOLD_NOT_MET` |
| Publication concentration | Structural fact ("exactly one source") | `INSUFFICIENT_DATA`, `WARNING`, `NON_DEGENERATE_UNQUANTIFIED` |
| Confidence | Structural fact (no scores at all) | `INSUFFICIENT_DATA`, `NON_DEGENERATE_UNQUANTIFIED` |
| Missingness | Structural fact (zero co-measurement anywhere) | `STRUCTURALLY_DEGENERATE`, `NON_DEGENERATE_UNQUANTIFIED` |
| Structural coverage | Extension-point stub — no data source yet | `NOT_YET_AVAILABLE`, always, until `SCI0-018` |

## Extending this package

Future dimensions named in `ADR-0009` §3 (structural diversity, MD-state
diversity, pocket-state diversity, mutation coverage, assay diversity,
experimental modality diversity) are added by writing a new
`QualityDimensionEvaluator` and passing an instance to
`CorpusQualityAssessor(evaluators=[...])`. No existing evaluator or the
assessor itself needs to change. A new evaluator using `WARNING` or a
`GOVERNED_THRESHOLD_*` status must state, in its own docstring, which of
`GDR-003` §2's two permitted rule kinds justifies it.

## Determinism

`assessment_content_sha256` covers every dimension's output and the source
`profile_sha256` — **not** the assessment timestamp, following the same
convention `SCI0-011` and `GDR-002`'s `CorpusProfile` already established.

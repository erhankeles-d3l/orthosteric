# Governance Gap Report — `SCI0-028`

**Objective under review:** `SCI0-028` — seal `N_c`, `N_b`, `N_w`, the S4b sharpness
factor, the duplicate-resolution policy, and the per-isoform ATP Km source.
**Prepared:** 2026-08-05, autonomously, by the computational pipeline (no human
scientific adjudication performed in producing this report).
**Outcome:** `SCI0-028` **cannot be implemented at this time.** Every required
seal is classified `RULE_MISSING` below. No numeric threshold, similarity
measure, or scientific policy is proposed anywhere in this document
(`CLAUDE.md` §1).
**Ordering consequence:** `SCI0-015` remains blocked. The backlog's own ordering
constraint — "`SCI0-028` must be `Done` before `SCI0-015` begins" — is
unsatisfied, so no work on `SCI0-015` is authorized.

---

## 0. Terminology note

Per Project Owner direction (2026-08-05), this report and all documents
produced from this point forward use **Governance Decision Record** or
**Governance Amendment** for the human action that resolves an item below,
rather than "Independent Scientific Auditor sign-off." The reasoning, as
stated by the Project Owner: the computational pipeline remains autonomous;
no human scientifically adjudicates routine cases; humans only change the
governing methodology. A Governance Decision Record is exactly that —
a change to governing methodology, not a case-by-case scientific ruling.

This is a **going-forward labeling convention**, not a retroactive edit.
Existing frozen documents — `ADR-0003`, `docs/reports/audit_reports/*.md`,
`docs/PROJECT_CONSTITUTION_v4.6.md` §1.6/§7.7 — are quoted verbatim below
using their original "Auditor" / "AUDITOR-N" language, because that is what
they say and ADRs are immutable except for their Status line (`ENGINEERING_
STANDARDS.md` §1). No existing governance file is edited by this report.

Formally renaming the Constitution §1.6 role, or the `AUDITOR-1`…`AUDITOR-5`
item labels in `docs/reports/audit_reports/ADR-0003_INDEPENDENT_AUDITOR_
BRIEF.md`, would itself be a governance change and is not performed here
without separate authorization; §9 below records this as a recommendation
only.

---

## 1. Scope of `SCI0-028`, as governed

Two sources define what `SCI0-028` must produce, and they list slightly
different item sets. Both are reproduced so nothing is silently narrowed:

**`docs/IMPLEMENTATION_BACKLOG.md`** (row for `SCI0-028`):
> Seal: **`N_c`, `N_b`, `N_w`, S4b sharpness factor**, duplicate-resolution
> policy — sealed before `SCI0-015` runs (§1.4)

**`sealed/MANIFEST.md`** ("Expected artefacts"):
> `SCI0-028` | `N_c`, `N_b`, `N_w`, S4b sharpness factor, duplicate-resolution
> policy, per-isoform ATP Km source

`sealed/MANIFEST.md` includes a sixth item — the per-isoform ATP Km source —
that the backlog row text omits. This report treats the union of both lists
(six items) as the authoritative scope, since `sealed/MANIFEST.md` is the
artefact registry against which `scripts/checks/seal_timestamp.py` validates,
and omitting an item it expects would be a silent narrowing of scope.

`sealed/MANIFEST.md` itself currently reads, in full:

> **Nothing is sealed yet.** Seals are produced by `SCI0-023` … `SCI0-029`,
> all of which are `Scientific` category and require the Independent
> Scientific Auditor (Constitution §7.7, ENG §1).
>
> | Artefact | SHA-256 file | Sealing commit | Objective | Date |
> |---|---|---|---|---|
> | *(none)* | — | — | — | — |

This is dispositive on its own: as of this report, the manifest records zero
sealed artefacts of any kind, for any objective, including `SCI0-028`.

---

## 2. Per-item classification

| # | Item | Classification | Governing citation |
|---|---|---|---|
| 1 | `N_c` — min. size of largest connected component | `RULE_MISSING` | §3 below |
| 2 | `N_b` — min. bridging-compound count | `RULE_MISSING` | §3 below |
| 3 | `N_w` — min. within-study four-isoform compound count | `RULE_MISSING` | §4 below |
| 4 | S4b sharpness factor (interval-width multiplier `k`) | `RULE_MISSING` | §5 below |
| 5 | Duplicate-resolution policy | `RULE_MISSING` | §6 below |
| 6 | Per-isoform ATP Km source, construct scope, version policy, conflict rule | `RULE_MISSING` | §7 below |

**Zero of six items are `RULE_AVAILABLE`.** No implementation or Decision
Record is prepared in this report, per the instruction that `RULE_AVAILABLE`
items alone receive implementation.

---

## 3. `N_c` and `N_b` — connected-component and bridging thresholds

**What the governing text requires.** `docs/reports/audit_reports/ADR-0003_
INDEPENDENT_AUDITOR_BRIEF.md` (AUDITOR-2 row):

> No candidate numerical value for any of the four exists anywhere in the
> repository — confirmed by full-text search... Determine `N_c`, `N_b`, `N_w`,
> sharpness factor from first principles / the connectivity structure — no
> existing authoritative source contains these values; this task does not
> propose any.

**What evidence has been prepared.** `docs/reports/audit_reports/ADR-0003_
AUDITOR_2_THRESHOLD_EVIDENCE.md` ran a three-model Monte Carlo sensitivity
analysis (uniform-random, clustered/hub-study, correlated-coverage) to test
whether a defensible candidate range could be derived analytically before
seeing the real corpus. Result, quoted:

> Model B — arguably the more realistic assumption for a real literature
> corpus... produces a mean Lcc nearly 4× larger than Models A and C, with an
> order-of-magnitude wider confidence interval. The conclusion "Lcc grows much
> more slowly than compound count" is not a property of the ADR-0003 problem;
> it is an artifact of assuming uniform random study structure...
>
> UNRESOLVED — evidence insufficient... No numeric range for `N_c` or `N_b`
> is proposed in this corrected document.

**Why this is `RULE_MISSING`, not merely undecided-but-simple.** The evidence
document does not just lack a number; it demonstrates that the number is
sensitive by roughly 4× to an assumption about literature structure that
cannot be verified without running the real `SCI0-015` connectivity audit —
i.e., the threshold's correct value plausibly depends on the very data the
threshold is meant to gate, which is the exact hazard `Constitution §1.4`
("thresholds fixed before results are seen") exists to prevent. Setting a
number now, even a conservative one, would either (a) be arbitrary with no
principled basis, or (b) implicitly assume one of three disclosed,
mutually-inconsistent graph models is correct.

**Unresolved definitional ambiguity (blocks both items even before a number
exists).** The same evidence document flags, unchanged across drafts:

> Ambiguity flagged (unchanged): none of the governing documents states
> whether these are measured on raw records or scaffold-deduplicated
> compounds.

This is itself a `RULE_MISSING` sub-item: whether `N_c` and `N_b` are counted
over raw activity records or over `SCI0-012` scaffold-deduplicated compound
identities is not stated in the Constitution, `ADR-0003`, or the backlog, and
changes the counting unit for `SCI0-014`'s `build_graph_stats_from_records()`
output.

**Downstream dependency.** `docs/IMPLEMENTATION_BACKLOG.md` Part VIII (Amendment
A10 of `CONSTITUTION_AMENDMENT_SET_v4.7.md`) makes `N_c` and `N_b` load-bearing
in the R1 kill criterion:

> `R1` | Largest connected component < `N_c` compounds, or bridging compounds
> < `N_b`, or within-study four-isoform compounds < `N_w`, or < 8 scaffold
> families in the connected component. All four sealed before the audit runs.

Without `N_c`/`N_b`, `SCI0-015`'s R1 evaluation has no pass/fail line, and
`SCI0-014`'s already-computed `largest_connected_component` and
`bridging_compounds` fields (merged, `commit b53d76a`) have no threshold to
be compared against.

---

## 4. `N_w` — within-study four-isoform compound count

**Classification:** `RULE_MISSING`, though evidence is comparatively more
developed than `N_c`/`N_b`.

`ADR-0003_AUDITOR_2_THRESHOLD_EVIDENCE.md`, §6:

> Power to detect a 0.5 log effect at σ=0.3 (Constitution floor) is ≈1.0
> already at `N_w`=8 (4 families × 2 compounds/family). Statistical power is
> not the binding constraint for `N_w`... CANDIDATE RANGE (unchanged):
> representativeness-based `N_w` in 24–40, contingent on Auditor's own choice
> of minimum compounds/family — offered as a starting point, not a derived
> result.

The document explicitly labels this a "CANDIDATE RANGE," not a decision, and
states plainly that a range offered as "a starting point" still requires the
human decision-maker's own choice of a minimum-compounds-per-family parameter
that no governing document states. A candidate range prepared for a human to
choose from is not the same as a chosen value; adopting the midpoint or any
other point in `[24, 40]` here would be exactly the invention `CLAUDE.md` §1
prohibits ("do not fill a table... with plausible-looking values").

Same downstream dependency as §3 (R1 kill criterion; also feeds
`within_study_four_isoform` in `SCI0-014`'s `GraphStats`, already computed and
awaiting a threshold).

---

## 5. S4b sharpness factor

**Classification:** `RULE_MISSING`.

`Amendment A1` of `CONSTITUTION_AMENDMENT_SET_v4.7.md` defines the criterion
structurally but leaves the multiplier unsealed by design:

> S4b | Per-target sharpness | Tier 1 | Mean predictive interval width per
> target ≤ the within-study label noise floor (§3.1 Q4) × `[SEALED AT STAGE
> 0]`. Calibration achieved by uniformly wide intervals fails.

`ADR-0003_AUDITOR_2_THRESHOLD_EVIDENCE.md`, §6:

> S4b: null-model calibration showing a constant-width predictor's apparent
> coverage depends on the assumed true-effect spread; `k` in [1.5, 2.0] denies
> the null model plausible-looking coverage across the tested range. This
> finding is also independent of the graph-connectivity question and is
> retained unchanged.

As with `N_w`, this is a candidate range from null-model calibration, not a
sealed value — the document's own closing line states, without qualification
by criterion: **"Independent Auditor decision still required: YES."**

**Additional blocking dependency, not merely a missing number.** S4b's formula
is "within-study label noise floor × `k`." The within-study label noise floor
itself is the output of `SCI0-016` ("Q4 audit — both noise floors, within-study
and cross-study," per `docs/IMPLEMENTATION_BACKLOG.md`), which has not run.
Even if `k` were sealed today, S4b could not be evaluated until `SCI0-016`
produces the floor it multiplies. `SCI0-028`'s ordering constraint ("sealed
before `SCI0-015` runs") does not by itself establish that `SCI0-016` has run
first; this report flags the dependency rather than assuming an order not
stated in the backlog.

---

## 6. Duplicate-resolution policy

**Classification:** `RULE_MISSING`, with an internal documentation
inconsistency that itself needs reconciliation.

`ADR-0003_INDEPENDENT_AUDITOR_BRIEF.md` (AUDITOR-3 row):

> No default or candidate policy text exists anywhere; ADR-0003 §7.8 is
> referenced by number but the referenced content is the open item itself,
> not a resolution.

The brief's decision checklist (§ "Decision Record," near the end of the
document) lists AUDITOR-3 with an unchecked box: `☐ Accepted ☐ Rejected
☐ Modified — details: __________`.

**Inconsistency requiring reconciliation, not resolution by this report.**
`src/orthosteric/data/adjudication.py` implements an `AdjudicationStatus.
RESOLVED` outcome for AUDITOR-3 (procedure v1.0, log-median aggregation
stratified by isoform × construct × species). The current
`src/orthosteric/data/harmonization/_deduplicator.py` module — merged more
recently — states the opposite in its module docstring:

> A prior draft of this module implemented log-median aggregation under a
> mislabeled "(RESOLVED)" comment; that draft is superseded by this one and
> must not be resurrected without an actual Auditor sign-off changing
> ADR-0003's Status line.

These two files currently disagree about whether AUDITOR-3 is resolved.
`adjudication.py` was not edited by this report; `_deduplicator.py`'s stricter,
fail-closed reading governs the corpus today (`SCI0-009`, merged as
`commit 92c013e`) and is the behavior actually running. This report does not
adjudicate which file is right — that is exactly the kind of scientific
call this task explicitly excludes — but records the discrepancy as a
concrete item for a Governance Decision Record to settle: either (a) accept
that `adjudication.py`'s procedure v1.0 output for AUDITOR-3 was premature and
formally supersede it, or (b) accept it and correct `_deduplicator.py`'s
docstring and fail-closed behavior to match. Leaving both files in the
repository asserting contradictory statuses for the same open item is itself
a defect (`ENGINEERING_STANDARDS.md` §1: ADR Status changes require a
recorded decision, not silent drift between two source files).

**Downstream dependency.** `SCI0-009`'s current behavior (correct, pending
resolution) fails closed on any group with ≥2 non-identical exact values,
emitting `GroupConflictStatus.RULE_MISSING`. This is expected and by design;
it is not a defect to fix, and no aggregation logic should be added to
`_deduplicator.py` until this item is sealed.

---

## 7. Per-isoform ATP Km source, construct scope, version policy, conflict rule

**Classification:** `RULE_MISSING`. Listed in `sealed/MANIFEST.md`'s
`SCI0-028` row but omitted from the `docs/IMPLEMENTATION_BACKLOG.md` backlog
row text (§1 above records this discrepancy).

`ADR-0003_INDEPENDENT_AUDITOR_BRIEF.md` (AUDITOR-5 row, "Update" note):

> One primary source is now verified — Somoza et al. 2015, J. Biol. Chem.
> 290(13):8439–8446, DOI 10.1074/jbc.M114.634683 — with quoted, tool-retrieved
> Km(ATP) values for all four Class I isoforms (PI3Kα 48 μM, PI3Kβ 279 μM,
> PI3Kγ 37 μM, PI3Kδ 118 μM, all TR-FRET/Table 1) plus a second, internally
> conflicting PI3Kδ value (37 ± 3 μM, ATP-competition global fit) that the
> source itself does not reconcile. Three isoforms were measured with human
> protein; PI3Kδ with murine protein — a construct/species mismatch. Still no
> independent second source, no construct-scope decision, no version/date
> policy, and no conflict-resolution rule — evidence improved, nothing
> resolved.

This is the clearest case in the report of evidence progress without
resolution: a candidate primary source exists and is cited, but (a) it
contains an internal conflict for PI3Kδ the source itself does not settle,
(b) the PI3Kδ measurement's species (murine) does not match the human
constructs used for the other three isoforms, and (c) no second independent
source has been sought or found to cross-validate. None of these three gaps
can be closed by re-reading the same source more carefully; each requires
either a Governance Decision Record accepting a specific resolution
(e.g., "use the TR-FRET value for PI3Kδ despite the species mismatch, flagged
as lower-confidence") or further literature search this report does not
perform, since selecting among the two conflicting PI3Kδ values or accepting
the species mismatch is itself the kind of judgment call `RULE_MISSING`
exists to prevent this pipeline from making unilaterally.

**Downstream dependency.** This is the same item AUDITOR-5 governs, already
recorded as `INSUFFICIENT_EVIDENCE` in `adjudication.py` and correctly
blocking `SCI0-008` (Cheng-Prusoff normalization). No change to that status is
made or implied here.

---

## 8. Non-invention statement

No numeric value, similarity threshold, aggregation formula, or ATP Km value
is proposed, implied, defaulted, or silently adopted anywhere in this report.
Every quoted number above (the candidate ranges for `N_w` and S4b's `k`, and
the Somoza et al. Km values) is reproduced verbatim from an existing,
previously-prepared evidence document — none is computed, estimated, or
selected by this report. Where a range or midpoint might appear to invite a
choice (e.g., `N_w` ∈ [24, 40]), no midpoint, mean, or "reasonable default" is
offered.

---

## 9. Recommendations (not decisions)

These are offered as the pipeline's summary of what a Governance Decision
Record would need to address per item; none is a proposed answer.

| Item | What a Governance Decision Record must specify |
|---|---|
| `N_c`, `N_b` | Counting basis (raw records vs. `SCI0-012` scaffold-deduplicated compounds); the numeric floor itself, informed by — but not derived from — the three-model sensitivity range in `ADR-0003_AUDITOR_2_THRESHOLD_EVIDENCE.md` §4 |
| `N_w` | Minimum compounds-per-family parameter; the resulting floor (candidate range `[24, 40]` exists as a starting point only) |
| S4b sharpness factor | The multiplier `k` (candidate range `[1.5, 2.0]` exists as a starting point only); sequencing relative to `SCI0-016`'s noise-floor output |
| Duplicate-resolution policy | Reconciliation of the `adjudication.py` / `_deduplicator.py` status discrepancy (§6); if AUDITOR-3 is to be treated as resolved, formal supersession of the current fail-closed `SCI0-009` behavior; if not, formal correction of `adjudication.py`'s `RESOLVED` status |
| ATP Km source | Resolution of the PI3Kδ internal conflict (37 μM vs. 118 μM) and the human/murine construct mismatch; whether a second independent source is required before sealing; version/date policy for future Km updates |

**Terminology recommendation (process, not scientific).** Should the Project
Owner wish to formalize the terminology change described in §0 beyond this
report — e.g., retitling the Constitution §1.6 "Independent Scientific
Auditor" role, or relabeling `AUDITOR-1`…`AUDITOR-5` in future documents —
that would itself constitute a Process-category (or, if it touches Constitution
role definitions, Scientific-category) governance change under `ENGINEERING_
STANDARDS.md` §1, and is not performed by this report. This pipeline will
apply the new terminology in documents it authors going forward (as done
throughout this report) without altering the historical record.

---

## 10. What remains correctly implemented pending these seals

No corrective action is needed on the data pipeline itself. The following
already defer correctly and require no change until the items above are
sealed:

- `SCI0-009` (`_deduplicator.py`) fails closed on non-identical duplicate
  groups (`GroupConflictStatus.RULE_MISSING`) rather than aggregating.
- `SCI0-011` (`_manifest.py`) records `within_group_conflict_threshold =
  "RULE_MISSING/SCI0-016_required"` and equivalent markers for the SCI0-010
  confidence rules in every snapshot's `PolicyManifest`.
- `SCI0-014` (`graph.py`) computes `largest_connected_component`,
  `bridging_compounds`, and `within_study_four_isoform` but performs no
  pass/fail comparison against any threshold — the fields exist and are
  reproducible; only the gating comparison is missing, exactly as it should
  be until `N_c`/`N_b`/`N_w` are sealed.
- `SCI0-014b` (`audit.py`) is explicitly descriptive and does not feed any
  split, stratum, or threshold decision (its own binding invariant).
- `AUDITOR-5`'s `INSUFFICIENT_EVIDENCE` status in `adjudication.py` for ATP Km
  is unchanged by this report.

---

## 11. Effect on `SCI0-015`

`SCI0-015` ("Public comparative evidence audit — Q1 as amended, all nine
sub-questions") remains **not authorized to begin.** The backlog's explicit
ordering constraint stands: running the connectivity audit before its
thresholds are sealed would let the kill criterion be chosen after seeing the
data (`Constitution §1.4`; risk `R23`).

**No branch, commit, or PR for `SCI0-015` or `SCI0-028` implementation
follows from this report.** This report is the complete deliverable for the
`SCI0-028` review requested.

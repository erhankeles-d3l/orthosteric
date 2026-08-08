# Governance Decision Record GDR-011 — ChEMBL Stratum Unit and ATP-Concentration Extraction

**Category:** Scientific — definition of the within-study evaluation stratum
(Constitution §2.3(1)) and of assay-comparability admissibility (§2.3(2)).
**Status:** **ACCEPTED — Issue 1: Option D. Issue 2: ATP as non-mandatory covariate. Implemented.**
**Date raised:** 2026-08-06.
**Date accepted:** 2026-08-06 (Project Owner decision).
**Raised by:** Computational pipeline during Stage H QA of Activity Snapshot A3.
**Affects:** SCI0-013 (`strata.py`), SCI0-014 (`graph.py`), new
`orthosteric.data.comparability`, new
`orthosteric.data.harmonization._atp_extraction`, `quality/_dimensions.py`
`CoverageEvaluator`, Constitution §2.3(1) and §2.3(2), engineering parameter
`n_complete_compounds`.
**Blocking:** Stage 0 sealing; corpus quality gate; Model Generation 1. RESOLVED.
**Evidence snapshot:** Activity Snapshot A3, `SNAP-5e5e54cb5590`
(`5e5e54cb5590da829aaccbd7e121d4197d38f1de9923799b8eec8a0296b171da`).
**Implementation snapshot:** Activity Snapshot A4, `SNAP-05748f6627ea`.

---

## Issue 1 — The `(study_id, assay_id)` stratum is unsatisfiable on ChEMBL data

### Constitution and current implementation

Constitution §2.3(1): *"Selectivity computed only from within-study, within-assay
panels."*

`strata.py` (SCI0-013) implements the stratum as a `(study_id, assay_id)` pair.
`CoverageEvaluator` derives `n_complete_compounds` = compounds individually
measured across all four Tier 1 isoforms **within one such stratum**, and marks
coverage `STRUCTURALLY_DEGENERATE` when that count is zero.

### Empirical finding (A3, 39,002 accepted records)

| Isoforms covered by one `assay_id` | Number of assays |
|---|---|
| 1 | **2,308** |
| 2 | 0 |
| 3 | 0 |
| 4 | 0 |

**Every ChEMBL assay covers exactly one target.** This is structural: in ChEMBL's
data model an assay is defined per `(document × target × protocol)`. A document
reporting a four-isoform panel therefore emits four distinct `assay_chembl_id`s.

Worked example — `CHEMBL1138050`, a document covering all four isoforms:

```
CHEMBL871582  PI3Kgamma   type=B   n=33
CHEMBL871583  PI3Kalpha   type=B   n=23
CHEMBL871586  PI3Kbeta    type=B   n=4
CHEMBL871588  PI3Kdelta   type=B   n=4
```

### Consequence

`n_complete_compounds == 0` is **structurally guaranteed** for any
ChEMBL-sourced corpus, at any size, forever. The coverage gate can never pass.
This is not a data-sufficiency problem and cannot be resolved by acquiring more
ChEMBL data.

### What the corpus does contain

| Grouping unit | Documents covering all 4 isoforms | Compounds measured in all 4 within that unit |
|---|---|---|
| `(study_id, assay_id)` — current | 0 | **0** |
| `study_id` (ChEMBL document) | 270 | **2,481** |

Also: 2,500 compounds are measured across all four isoforms somewhere in the
corpus (`compounds_all4_isoforms`), and 6,821 compounds bridge ≥2 isoforms.

### Options

**Option A — Stratum = `study_id` (ChEMBL document).**
Treats one publication as the comparability unit. Yields 2,481 complete
compounds across 270 documents.
*For:* Recovers a usable evaluation ground truth. Within a single medicinal-chemistry
paper, the isoform panel is normally run in parallel by one group under one
protocol, which is the confounding that §2.3(1) exists to prevent.
*Against:* Weakens the literal "within-assay" guarantee. A document may contain
assays run at different ATP concentrations or in different formats (see Issue 2).

**Option B — Stratum = `(study_id, protocol_signature)`.**
Group assays within a document by a derived protocol signature (assay_type,
BAO format, extracted ATP concentration, description similarity).
*For:* Preserves the intent of "within-assay" while matching ChEMBL's data model.
*Against:* Requires a governed definition of `protocol_signature` — itself a
scientific decision, and dependent on Issue 2 being resolved first.

**Option C — Retain `(study_id, assay_id)`; source panels elsewhere.**
Accept that ChEMBL cannot supply the stratum and obtain four-isoform panels from
a source that preserves panel structure (e.g. curated per-paper extraction, or
a vendor panel dataset).
*For:* No weakening of the Constitution.
*Against:* No such source is currently identified or budgeted; blocks the project
indefinitely.

### Recommendation

None offered. This is a scientific judgement about what constitutes a comparable
panel, and it changes `n_complete_compounds`, a governed engineering parameter
feeding the corpus quality gate. Per Constitution §36 the pipeline has not
selected an option.

---

## Issue 2 — ATP concentration is present in ChEMBL only as free text

### Constitution

§2.3(2): *"Every record carries assay ATP concentration, format, substrate,
construct. Records lacking ATP concentration are flagged and excluded from
primary targets."*

§0.5 and §2.3 preamble: all Tier 1/Tier 2 targets are engaged ATP-competitively
and differ in ATP Km, so IC50 depends on assay ATP concentration and
cross-assay ratios are not comparable without it.

### Empirical finding

`atp_concentration_um` is populated in **0 of 39,002** accepted A3 records.

Cause: the ChEMBL activity API exposes no structured ATP-concentration field.
The information is present in the free-text `assay_description`:

| Measure | Count | % of 39,508 raw |
|---|---:|---:|
| `assay_description` mentions ATP | 23,941 | 60.6% |
| Numeric `N uM ATP` extractable by regex | 13,327 | 33.7% |
| Structured field available | 0 | 0% |

Per isoform, ATP mention rate: PI3Kalpha 42.3%, PI3Kbeta 53.1%,
PI3Kgamma 60.8%, PI3Kdelta 75.0% — **the missingness is isoform-dependent**,
which is itself a confounder for comparative selectivity work.

Distinct extracted concentrations (µM): 10.0 (n=6,210), 2.0 (3,359),
20.0 (2,620), 1.0 (303), 50.0 (302), 125.0 (206), 60.0 (162), 25.0 (143),
plus 4 further values — 12 distinct values in total.

Example descriptions:
- `Inhibition of PI3Kalpha in presence of 25 uM ATP`
- `Inhibition of recombinant PI3Kalpha by radioactive phosphotransfer assay in presence of 10 uM ATP`

### Consequence

Under a literal reading of §2.3(2), **every record in A3 must be excluded from
primary targets**, because none carries an ATP concentration. The corpus would
be empty for the primary learning task.

### What is required

A governed **ATP-concentration extraction rule**, specifying at minimum:

1. the accepted textual patterns (and whether regex extraction is admissible
   evidence at all, versus manual curation);
2. handling of ranges, "approximately", and Km-referenced phrasings
   (`at ATP Km`, `at 1 mM ATP`);
3. unit normalisation (µM / mM / nM);
4. the confidence class assigned to a text-derived value versus a curated one;
5. the disposition of the ~39–66% of records where no concentration is stated —
   exclude from primary targets (§2.3(2) literal), or admit at reduced
   confidence with the missingness recorded;
6. whether isoform-dependent missingness requires stratified handling.

Each of these is a scientific decision with direct effect on which records are
admissible and on the comparability of every selectivity ratio computed.

**Status: RULE_MISSING.** The pipeline has not implemented any extraction and
has not assigned any ATP value.

---

## Interaction between the two issues

Option B for Issue 1 depends on Issue 2: a `protocol_signature` that ignores ATP
concentration would group non-comparable assays, defeating its purpose. If
Option B is chosen, Issue 2 must be resolved first.

Option A is decidable independently, but its principal weakness — that one
document may mix protocols — can only be quantified once ATP concentrations are
extractable.

---

## What was NOT done

Per Constitution §36 and §25 of the execution instructions, the pipeline did not:

- redefine the stratum unit or modify `strata.py`;
- alter `CoverageEvaluator` or any gate threshold;
- implement ATP-concentration text extraction;
- assign, impute, or default any ATP concentration;
- exclude or admit records on ATP grounds;
- mark the corpus eligible for training.

The corpus quality gate result stands as **STOP**, which is the correct and
honest outcome given the above.

---

## Interim consequence

- Stage 0 cannot be sealed (compounded with GDR-010, still open).
- `n_complete_compounds` remains 0 and coverage remains
  `STRUCTURALLY_DEGENERATE`.
- Model Generation 1 remains blocked.
- Acquisition, harmonization, scaffold assignment, connectivity and scaffold
  diversity are unaffected and are complete.

## Review trigger

Project Owner decision required before Stage 0 sealing. Issue 2 should be
decided before or together with Issue 1 Option B.

---

## ACCEPTANCE ADDENDUM (2026-08-06)

**Decision (verbatim from the Project Owner):**

> GDR-011 Issue 1: Approve Option D. The primary within-study comparability
> unit shall be `(study_id, bao_format, assay_type)`, i.e. C1. Retain a
> hierarchical ATP-confirmed subset as a flagged/secondary stratum rather
> than making it the primary comparability requirement. The previous
> `(study_id, assay_id)` definition is rejected because it is structurally
> incapable of producing four-isoform panels in ChEMBL.
>
> GDR-011 Issue 2: Approve ATP as a non-mandatory covariate/stratifier.
> Preserve ATP status as `KNOWN` or `UNKNOWN`; never treat two unknown ATP
> conditions as equivalent. Do not discard records solely because ATP is
> unknown. Regex-derived ATP concentrations remain provisional until the
> multi-value extraction ambiguity has been governed. In particular, do not
> silently apply a first-match rule to the 2,089 ambiguous descriptions.

Status is tracked as three values, not two: `KNOWN` / `AMBIGUOUS` / `UNKNOWN`
— `AMBIGUOUS` is not folded into either `KNOWN` (no first-match rule) or a
bare `UNKNOWN` (candidates are retained for future adjudication), matching
the decision's explicit "do not silently apply a first-match rule."

### Implementation

**Comparability (Issue 1):** `src/orthosteric/data/comparability.py`.
`resolve_panel_key(record)` returns `(key, tier)`; `tier` is
`PanelKeyTier.C1_PRIMARY` when `bao_format`/`assay_type` are present, else
`PanelKeyTier.LEGACY_FALLBACK` (preserved only for pre-GDR-011
generic-algorithm test fixtures; never scientific evidence —
`is_scientific_evidence` is `False`). `panel_key()` is the tier-blind bare
key used by the union-find/stratum grouping mechanics in `graph.py` and
`strata.py`; both were rewired onto it. `atp_confirmed_panel_key()`
implements the secondary, flagged ATP-confirmed stratum (Option D
"hierarchical"): it returns `None` whenever the panel itself is
`LEGACY_FALLBACK`, or `atp_status` is not `"known"` — including
`AMBIGUOUS` — so the secondary stratum is strictly narrower than
`C1_PRIMARY`, never broader, and never fabricates a match between two
`UNKNOWN`/`AMBIGUOUS` records.

`graph.py`'s `GraphStats` gained `legacy_fallback_records` (audit-only
counter). `strata.py`'s `WithinStudyStratum` gained `panel_tier`;
`StratumReport.c1_primary_strata()` filters to scientific-evidence strata.
A conservative rule was added: if ANY record contributing to a panel
resolves to `LEGACY_FALLBACK` (by coincidental key collision), the whole
panel is downgraded to `LEGACY_FALLBACK` — ambiguity never upgrades to
`C1_PRIMARY`.

**ATP (Issue 2):** `src/orthosteric/data/harmonization/_atp_extraction.py`.
`extract_atp_status(description)` returns `AtpStatus.KNOWN` (exactly one
numeric candidate), `AMBIGUOUS` (≥2 distinct numeric candidates — order of
appearance in the text is irrelevant; verified by
`test_ambiguous_candidates_order_independent`), or `UNKNOWN` (no numeric
candidate, including radiolabel references such as `[gamma-33P]ATP` and
Km-referenced text with no number). `AtpExtractionResult.concentration_um`
is populated only for `KNOWN`; `candidate_values_um` retains every
candidate for `AMBIGUOUS`, for future adjudication.

**Harmonization pipeline:** `scripts/stage_bc_freeze_activity_snapshot.py`
now reads `bao_format` directly from the raw ChEMBL payload (previously
unparsed) and calls `extract_atp_status()` on `assay_description` for
every record, before any admissibility filtering, so the field is present
and auditable regardless of exclusion status.

### Empirical result on Activity Snapshot A4

| Metric | Value |
|---|---:|
| C1_PRIMARY panels | 873 |
| LEGACY_FALLBACK records | 0 (all real ChEMBL records carry bao_format/assay_type) |
| C1_PRIMARY complete four-isoform (panel, compound) pairs | 2,992 (`StratumReport`) |
| ATP `KNOWN` | 11,464 (29.4%) |
| ATP `AMBIGUOUS` | 2,089 (5.4%) — unchanged from the pre-acceptance evidence; none resolved |
| ATP `UNKNOWN` | 25,449 (65.3%) |

Stage 0 gate on A4 (`CorpusQualityGatePolicy`, unmodified):
`coverage: non_degenerate_unquantified`, `missingness:
non_degenerate_unquantified`, `connectivity: non_degenerate_unquantified`,
`scaffold_diversity: governed_threshold_met`. Overall gate: **WARNING**
(non-fatal: `confidence`, `structural_coverage` — both pre-existing,
unrelated to this GDR). `eligible_for_training = True`.

### Tests

`tests/data/test_comparability.py` (17), `tests/data/harmonization/test_atp_extraction.py`
(17), `tests/data/test_strata.py` (+5 for `panel_tier`/`c1_primary_strata()`,
including the coincidental-collision downgrade case). All pre-existing
`graph.py`/`strata.py` tests pass unchanged via the `LEGACY_FALLBACK`
fallback.

### What was explicitly NOT done

No MMP transformation rule, switch-inclusion threshold, or S4b sharpness
multiplier was frozen — GGR-002a and GGR-002b remain `GDR_REQUIRED` (see
`data/snapshots/activity_snapshot_A4/ggr_reassessment.json`). This GDR
resolves what a comparable panel and an ATP condition *are*; it does not
resolve what counts as a valid MMP or a governed noise-floor multiplier.

# Governance Decision Record GDR-011 (DRAFT — NOT ACCEPTED) — ChEMBL Stratum Unit and ATP-Concentration Extraction

**Category:** Scientific — definition of the within-study evaluation stratum
(Constitution §2.3(1)) and of assay-comparability admissibility (§2.3(2)).
**Status:** **DRAFT — awaiting Project Owner decision. NOT accepted. NOT implemented.**
**Date raised:** 2026-08-06.
**Raised by:** Computational pipeline during Stage H QA of Activity Snapshot A3.
**Affects:** SCI0-013 (`strata.py`), `quality/_dimensions.py` `CoverageEvaluator`,
Constitution §2.3(1) and §2.3(2), engineering parameter `n_complete_compounds`.
**Blocking:** Stage 0 sealing; corpus quality gate; Model Generation 1.
**Evidence snapshot:** Activity Snapshot A3, `SNAP-5e5e54cb5590`
(`5e5e54cb5590da829aaccbd7e121d4197d38f1de9923799b8eec8a0296b171da`).

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

# Governance Decision Record GDR-001 — Duplicate-Resolution Policy (AUDITOR-3)

**Category:** Scientific (methodology; no numeric threshold, tier, or evidence-
class definition is altered).
**Status:** Accepted.
**Date:** 2026-08-05.
**Decided by:** Computational pipeline, under explicit Project Owner
authorization (2026-08-05) to resolve scientific-methodology questions not
already settled by the Constitution, ADRs, or prior Governance Decision
Records, where a comprehensive literature review identifies a single,
well-supported methodological choice.
**Supersedes (in effect, not in text):** The `RULE_MISSING` treatment of
AUDITOR-3 in `src/orthosteric/data/harmonization/_deduplicator.py` (module as
of commit `92c013e`). That module's own docstring is not edited retroactively
beyond what is required to reflect this record; its historical account of why
the question was previously unresolved remains accurate and is left in place,
annotated with a pointer to this record.
**Question addressed (`ADR-0003_INDEPENDENT_AUDITOR_BRIEF.md`, AUDITOR-3):**
"Duplicate-resolution policy for conflicting measurements of the same
compound/isoform: median / most-recent / highest-confidence / other."

---

## Decision

Within a fully-specified evidence-identity group — same compound
(`HarmonizedCompound.internal_id`), isoform, **construct**, **organism**,
measurement type, measurement class, assay identifier, and source (source
type + accession) — two or more non-identical **exact** (non-censored)
activity values are combined by taking the **median** of the reported
values. Censored records in the same group are retained unchanged and are
never included in the median; they continue to be checked for logical
contradiction against the resolved value exactly as they were against
individual exact values before this record.

This decision is **narrowly scoped**. It resolves only how to combine
multiple measurements that already share an identical identity — i.e.,
records that a domain scientist would recognize as replicate determinations
of the same physical quantity, reported by the same source under the same
assay. It does **not**:

- authorize combining values across different studies, sources, or accessions
  (Constitution §2.3(1) as amended; `SCI0-013`'s within-study stratum
  architecture is unaffected and remains the sole basis for any evaluation
  criterion);
- resolve Cheng-Prusoff normalization or the ATP Km source question
  (AUDITOR-5 remains `INSUFFICIENT_EVIDENCE`, unchanged);
- set any numeric noise-floor or conflict threshold (`SCI0-016`'s within-
  study and cross-study noise floors remain unseal, `SCI0-028`'s
  duplicate-resolution *numeric policy*, if any further numeric parameter is
  ever found necessary, remains open — see "What remains open" below); or
- change `SCI0-010`'s confidence scoring, which continues to operate across
  identity groups rather than within one.

## Accompanying schema correction

`_deduplicator.py`'s evidence-identity key, as merged (commit `92c013e`), was
`(compound_id, isoform, measurement_type, measurement_class, assay_id,
source_key)`. It omitted two fields the schema already carries on
`AssayMetadata` — `construct` and `organism` — creating a latent risk that a
wild-type and a mutant construct (or a human and a non-human ortholog)
measured under the same nominal `assay_id` could be placed in the same
identity group and, after this record, incorrectly median-combined. This
record adopts the corrected key — `(compound_id, isoform, construct,
organism, measurement_type, measurement_class, assay_id, source_key)` — as a
prerequisite. This correction is schema bookkeeping using fields the module
already carries, consistent with the same authority `_deduplicator.py`'s own
docstring already claims for its identity-grouping step (point 1, "built
entirely from fields the schema already carries... not a scientific
judgement"), and is adopted regardless of the aggregation decision above: it
strictly narrows existing groups and cannot introduce a new failure mode.

---

## Rationale

**Why median, not mean.** Public bioactivity measurements (IC50, Ki) are
well documented to carry occasional large outliers from technical assay
failure, transcription error, or unit confusion, against a background of
inter-lab noise on the order of 0.3–0.5 log units even under strict curation.
Two independent quantitative studies of ChEMBL-derived data — Kramer,
Kalliokoski, Gedeck & Vulpetti, *J. Med. Chem.* 2012, 55, 5165–5173 ("The
Experimental Uncertainty of Heterogeneous Public Ki Data") and Landrum &
Riniker, *J. Chem. Inf. Model.* 2024, 64, 1560–1567 ("Combining IC50 or Ki
Values From Different Sources Is a Source of Significant Noise") — quantify
this directly; the latter reports median absolute deviations of 0.50 log
units (IC50) and 0.52 log units (Ki) under minimal curation, falling to 0.27
and 0.45 under stringent curation (as summarized in Schiebroek, Landrum &
Riniker, *J. Chem. Inf. Model.* 2025, "Balancing Data Quantity and Quality:
Evaluating Curation Strategies for Bioactivity Prediction in Lead
Optimization," DOI `10.1021/acs.jcim.6c01018`). Robust-statistics literature
(Huber, *Robust Statistics*, 1981/2004) establishes the median as the
standard robust estimator of central tendency precisely for this failure
pattern — an occasional large outlier in an otherwise well-behaved
measurement set — because its influence function is bounded, unlike the
mean's.

**Important scope caveat on the Landrum & Riniker (2024) finding.** That
paper's warning is specifically about combining values **across different
sources** — exactly the cross-study pooling this project's Constitution
§2.3(1) (as amended) already forbids for any gating criterion, and which
`SCI0-013`'s within-study stratum extraction already structurally prevents.
It is not a warning against combining true replicate measurements reported
by the *same* source under the *same* assay, which is the only case this
record's identity key admits. If anything, the paper's finding reinforces
the existing within-study architecture rather than bearing on the narrower
question this record resolves.

**Why median, not the log-transformation question.** `ActivityRecord.value`
is stored as a bare `Decimal` (no explicit unit field on the record itself;
see "Assumptions" below). Median is invariant under any strictly monotonic
transform — `median(f(x)) = f(median(x))` for monotonic `f`, which includes
`log`. Whatever unit convention the stored value follows, taking the median
of the as-stored values is equivalent to taking the median in log space and
back-transforming. This decision therefore does not depend on resolving the
storage-unit question, and does not need to.

**Domain-specific precedent for median over duplicates specifically (not
just general robustness).** Multiple independent bioactivity-curation
pipelines documented in the literature use median explicitly for this exact
step (combining multiple potency values for the same compound-target pair
before modeling), including:
- Yang et al., "Rep3Net: An Approach Exploiting Multimodal Representation for
  Molecular Bioactivity Prediction" (arXiv:2512.00521): "Multiple entries
  representing the same compound were identified and instead of discarding
  duplicates, we aggregated them using the median IC50 value to minimize the
  effect of experimental variation."
- An uncertainty-aware reinforcement-learning chemical-language-model study
  (arXiv:2606.24990) resolving ChEMBL duplicates in two passes, both times
  "retaining... the median pChEMBL Value," explicitly "to end up with one
  potency value per unique canonical compound."
- Zhang et al., "Bioactivity-explorer" (*J. Cheminformatics*, 2019,
  DOI `10.1186/s13321-019-0370-7`), computing median (alongside mean/max/min,
  reported together) for molecules with multiple reported potency
  measurements from ChEMBL.

**Why not "most-recent."** No literature source located in this review uses
recency as a duplicate-resolution criterion for bioactivity measurements, and
none was expected to: a compound's true Ki or IC50 against a fixed protein
target is a physical constant, not a time-varying quantity, so a more recent
measurement carries no presumption of being more correct absent an explicit,
separate quality argument (which is exactly what confidence scoring,
`SCI0-010`, already exists to make — orthogonally to this decision). This
option is rejected as unsupported.

**Why not "highest-confidence" as the sole resolution.** Selecting one record
and discarding the others sacrifices the variance reduction that combining
multiple independent replicate readings provides, and is a materially weaker
use of the available evidence than a robust combination — particularly
because, within the identity groups this record's key defines, all
contributing records already share the same source and assay, so within-group
confidence variation is expected to be small; the primary place confidence
should influence outcomes is in weighting or filtering *across* different
identity groups/strata (already `SCI0-010`'s role), not in picking a winner
*within* one. This option is not adopted as the primary rule but is not
foreclosed as a secondary consideration if a future record narrows further.

---

## Alternatives considered

| Alternative | Why not adopted |
|---|---|
| Arithmetic mean (in stored units) | Not robust to the outlier pattern the cited literature documents in exactly this kind of data; median dominates it for this failure mode |
| Geometric mean | Mathematically appropriate for log-normal data but adds no benefit over median here — median already commutes with the log transform, and does not require assuming which specific transform the stored values follow (see rationale above) |
| Trimmed / Winsorized mean | A reasonable alternative for larger replicate counts; not adopted because it requires choosing a trim percentage, which is itself an unsealed numeric parameter this record avoids introducing, and replicate counts in bioactivity duplicate groups are typically small (2–4), where trimming and median converge or trimming is undefined |
| Most-recent | No literature support found for bioactivity duplicates; no principled basis (see rationale) |
| Highest-confidence only | Discards corroborating replicate information within an already-tightly-scoped group; confidence's better role is cross-group weighting (`SCI0-010`), not intra-group selection |
| Leave `RULE_MISSING` (no change) | Was the status quo; not adopted because the Project Owner's 2026-08-05 authorization specifically directs adoption of a well-supported rule where the literature clearly supports one, and it does here |

## Confidence level

**High**, for the specific, narrowly-scoped question this record resolves
(combining literal replicate measurements sharing source, assay, construct,
organism, isoform, and measurement type). The supporting literature is
domain-specific (bioactivity data, not a generic statistics analogy alone),
converges from multiple independent groups, and the rejected alternatives
have no comparable support. **Not** claimed as high confidence for anything
beyond this scope — in particular, this record makes no claim about
combining values across sources or studies, and defers entirely to
`SCI0-013`'s existing within-study architecture for that question.

## Assumptions made explicit

- `ActivityRecord.value` is assumed to already be unit-consistent within a
  single `measurement_type` (i.e., no records mixing nM and μM under the
  same `MeasurementType.IC50` reach this module). This module does not
  independently verify unit consistency; if such a defect exists upstream
  (`SCI0-003`/`SCI0-004`), it is a data-quality issue this record does not
  claim to detect or correct.
- "Construct" as recorded in `AssayMetadata.construct` is assumed to
  distinguish wild-type from mutant reports when both exist (e.g., a paper
  reporting both WT and H1047R activity would report them under different
  `construct` strings). This module does not independently verify that
  source connectors populate `construct` consistently; a source that leaves
  `construct` uniformly `None` across WT and mutant records would not be
  caught by this correction. No evidence of that specific failure mode was
  found in this review, and none is asserted.

## What remains open

This record does **not** resolve:
- `N_c`, `N_b`, `N_w`, or the S4b sharpness factor (see
  `docs/governance/SCI0-028-GOVERNANCE-GAP-REPORT.md`, unchanged by this
  record except for the compound-counting-basis clarification recorded
  separately in that document's revision accompanying this GDR).
- AUDITOR-5 (ATP Km source, construct scope, version policy, conflict rule).
  A further literature search was performed as part of the same review that
  produced this record (see the gap-report revision) and did not locate an
  independent second source for PI3K isoform ATP Km; a related search
  surfaced a paper reporting PI3Kα/β **Km for phosphatidylinositol** (the
  lipid substrate, not ATP) — a different kinetic parameter entirely, noted
  here so it is not mistaken for progress on the ATP Km question by a future
  reader skimming this record for "PI3K Km" citations.
- Whether an additional numeric noise-vs-conflict threshold will eventually
  be needed for cases this record's key does not fully disambiguate. None
  was needed for the resolution adopted here, because the identity key
  already narrows every group this record acts on to same-source,
  same-assay, same-construct, same-organism replicates before the median is
  taken — there is no remaining "is this noise or a real conflict"
  judgment call inside that scope for the median to require calibrating
  against.

## Effect on existing artefacts

- `src/orthosteric/data/harmonization/_deduplicator.py` — identity key
  extended with `construct`, `organism`; `GroupConflictStatus.RULE_MISSING`
  is no longer produced by the "≥2 distinct exact values" path (replaced by
  a new resolved status); `Deduplicator.POLICY_ID` bumped, which propagates
  a new snapshot hash for any corpus rebuilt after this change (`SCI0-011`,
  `PolicyManifest.deduplication_policy`).
- `docs/governance/SCI0-028-GOVERNANCE-GAP-REPORT.md` — revised in the same
  change set to record this item as resolved and to add the ATP Km search
  finding above.
- `sealed/MANIFEST.md` — not modified. This record is a methodology decision,
  not a sealed numeric artefact of the kind `SCI0-023`…`SCI0-029` produce;
  no entry is added there.

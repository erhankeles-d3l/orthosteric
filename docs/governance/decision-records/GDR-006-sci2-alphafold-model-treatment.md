# Governance Decision Record GDR-006 — SCI-2 AlphaFold Model-Level Treatment

**Category:** Scientific (methodology — how AlphaFold-derived structural
evidence enters the SCI-2 model; resolution of GGR-005 from SCI2-001).  
**Status:** Accepted.  
**Date:** 2026-08-06.  
**Decided by:** Project Owner, direct instruction (2026-08-06).  
**Resolves:** SCI2-001 GGR-005 and GDR-004 disposition table row GGR-005.  
**Companion documents:** SCI0-007 amendment, SCI2-001-specification.md §10.

---

## Decision

**AlphaFold treatment = Option B: include AlphaFold-derived features in
training with an explicit boolean is_alphafold source indicator feature.**

Algorithm identifier (canonical): `alphafold_include_source_indicator_v1`

---

## Rationale

### Why Option A (exclude from training) was rejected

Option A (treat AlphaFold-sourced isoforms as UNAVAILABLE) is overly
restrictive and sacrifices information without scientific necessity. SCI0-007
already governs which AlphaFold models are admissible (mean pLDDT >= 70;
source confirmed by UniProt accession match; only when no admissible PDB
exists). Admissible AlphaFold models provide geometrically reasonable structural
context even if they are not experimental.

Furthermore, Option A would make the model unable to predict for any compound
where one or more isoforms have only AlphaFold structural evidence, reducing
effective coverage during Extension (Tier 2 evaluation).

### Why Option B was chosen

1. The model can learn to weight structural features differently for AlphaFold
   vs experimental sources. The is_alphafold indicator provides the signal
   without inventing a downweighting factor.
2. The model's uncertainty (GDR-007 heteroscedastic Gaussian output) can
   empirically reflect the lower structural quality of AlphaFold models by
   assigning wider predictive intervals.
3. This approach is testable: we can check whether predictions from
   AlphaFold-sourced isoforms have systematically wider intervals than
   experimental-sourced predictions (a form of internal calibration).
4. The is_alphafold source label is already preserved in IsoformEvidence
   (learning/_interfaces.py), making this a zero-additional-schema change.

### Why Option C (downweighting) was rejected

Option C requires a weighting factor alpha_AF in (0, 1) to discount
AlphaFold features. No governing document specifies this factor, and no
principled derivation exists without empirical evidence. GDR-004 prohibits
inventing it.

---

## Implementation specification

### is_alphafold indicator feature

A single boolean feature `is_alphafold` is appended to the pocket feature
vector for each isoform. This is a binary indicator: 0 = experimental PDB
source, 1 = AlphaFold source.

The indicator is a direct serialization of `IsoformEvidence.is_alphafold`
from learning/_interfaces.py (already defined in SCI2-001).

### Provenance preservation

SCI0-007 requirement: AlphaFold source is always labeled `StructureSource.ALPHAFOLD`
in `IsoformEvidence.structure_record_id` and `ComparativePrediction.*_structure_source`.
The is_alphafold feature is derived from this label; the label itself survives
independently.

### Training behavior

During training, AlphaFold-sourced training examples (rare in Tier 1 given
existing PDB coverage) are treated identically to experimental examples except
that the is_alphafold indicator is set to 1. The model may learn lower
confidence for AlphaFold inputs, or may learn that the structural features are
equally informative. Both outcomes are valid; neither is enforced.

### Evaluation and reporting

Every evaluation report that includes AlphaFold-sourced predictions MUST
stratify results by source type (experimental vs AlphaFold). Aggregate metrics
that pool the two are reported as secondary; stratified metrics are primary.

---

## What this record resolves

**Resolved:**
- AlphaFold model-level treatment: Option B (include with source indicator).
- The is_alphafold feature definition and its position in the feature vector.
- The reporting requirement (stratified by source type).

**Not resolved by this record:**
- AlphaFold structures for Tier 2 targets (Class II PI3Ks, Vps34, mTOR, DNA-PK)
  are handled identically -- the is_alphafold indicator applies regardless of tier.
- The AlphaFold admissibility rules themselves (SCI0-007, rules AF-1 through AF-5)
  are unchanged by this record.

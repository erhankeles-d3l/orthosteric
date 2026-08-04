# Amendment: SCI0-007 AlphaFold Fallback

**Type:** Specification Amendment — Decision Record  
**Supersedes:** SCI0-007 AlphaFold exclusion language (defect 7)  
**Date:** 2026-08-02  
**Authorized by:** Project Owner  
**Status:** Adopted  

---

## Decision

SCI0-007 is amended to permit a narrowly constrained AlphaFold fallback, subject
to the deterministic admissibility rules below.

**Experimental PDB remains mandatory whenever an admissible experimental human PDB
structure satisfying the current §2.1 criteria exists.**

AlphaFold is permitted only as a fallback when no admissible experimental human PDB
exists for the required isoform/structural context.

---

## Rationale

Defect 7 excluded AlphaFold on the grounds that predicted structures cannot support
§2.1(1) (pocket definition requires a bound ligand).  That rationale is correct
for the purpose of **pocket definition and interaction-fingerprint derivation**.

However, AlphaFold provides useful structural context for:
  * sequence-to-structure correspondence validation;
  * construct completeness analysis;
  * isoform-identity verification;

where the absence of a bound ligand is not a disqualifying limitation, because
these use cases do not require a ligand-bound pocket.

The amendment therefore permits AlphaFold strictly as a **fallback for structural
context**, never as a replacement for experimental evidence in pocket-definition or
interaction-fingerprint contexts.

---

## Deterministic admissibility rules — AlphaFold fallback

These rules are frozen at version 1.0.  They may only be changed by a subsequent
gate-level Decision Record.

### Rule AF-1 — Fallback trigger (mandatory prerequisite)

AlphaFold may be used if and only if:
```
_search_pdb_by_uniprot(uniprot_ac) returns zero records
OR
all PDB records for the uniprot_ac are INADMISSIBLE under §2.1 rules
```

If any PDB structure is admissible, AlphaFold **must not** be used.

### Rule AF-2 — Source

AlphaFold DB (https://alphafold.ebi.ac.uk/) via the public REST API.
Source must be retrieved by UniProt accession; isoform identity must be confirmed
by exact UniProt accession match before use.

### Rule AF-3 — Isoform-identity confirmation

The AlphaFold model must be retrieved by the canonical human UniProt accession
from `PI3K_UNIPROT_MAP`.  Any mismatch between the model accession and the target
accession triggers `GOVERNANCE_EXCEPTION`.

### Rule AF-4 — Confidence threshold

The mean pLDDT score of the full model must be ≥ 70.0 (AlphaFold's own threshold
for "confident" predictions).  Models below this threshold are
`INADMISSIBLE_LOW_CONFIDENCE`.

**Note — RULE_MISSING for per-residue threshold:** A per-residue pLDDT threshold
for ATP-site-relevant residues is not specified in the current governance.  If a
use case requires per-residue confidence filtering, classify as
`RULE_MISSING / GOVERNANCE_DECISION_REQUIRED` until a subsequent amendment
specifies the threshold.

### Rule AF-5 — Provenance requirements

Every AlphaFold-derived StructureRecord must carry:
  * `structure_source = StructureSource.ALPHAFOLD_FALLBACK`
  * `alphafold_model_id`: the AlphaFold DB identifier (e.g. `AF-P42336-F1-model_v4`)
  * `alphafold_version`: model version string (e.g. `v4`)
  * `mean_plddt`: mean pLDDT score of the retrieved model
  * `fallback_reason`: "NO_ADMISSIBLE_EXPERIMENTAL_PDB_FOR_{ISOFORM}"
  * `inadmissibility_reason = None` (it is admissible)
  * NO `resolution_angstrom` (predicted, not experimental)
  * NO `experimental_method` (not experimental)
  * NO `has_bound_ligand = True` (predicted structures carry no bound ligand)
  * NO `ligand_ids` (empty list)

### Rule AF-6 — Prohibition on experimental metadata fabrication

AlphaFold StructureRecords must never carry:
  * `resolution_angstrom` (any non-None value)
  * `experimental_method` (any value)
  * `has_bound_ligand = True`
  * `ligand_ids` (any non-empty value)
  * `deposition_date` as a PDB deposition date
  * `release_date` as a PDB release date

Fabricating experimental metadata for a predicted structure is prohibited;
violation triggers immediate `GOVERNANCE_EXCEPTION`.

### Rule AF-7 — Pocket definition exclusion

AlphaFold structures must never be used as the source for the §2.1 pocket
definition or for interaction-fingerprint feature derivation.  Those operations
require experimental structures with a bound ligand.  This restriction preserves
the scientific intent of defect 7.

### Rule AF-8 — Downstream distinguishability

Phase C analysis code must be able to condition on `structure_source` to
exclude AlphaFold fallback records from operations that require experimental
structures.  The `structure_source` field must never be dropped or converted.

### Rule AF-9 — Fail-closed behavior

If the AlphaFold API returns no model for the required accession, or if the
model fails Rule AF-4, the operation returns
`StructureAdmissibility.INADMISSIBLE_LOW_CONFIDENCE` or
`StructureAdmissibility.INADMISSIBLE_NO_EXPERIMENTAL_STRUCTURE` and continues
with other isoforms.  The failure is recorded in `inadmissibility_reason`.

---

## Artifacts that must be updated

1. `SCI0-001-refinement-data-acquisition.md` — SCI0-007 spec (remove blanket exclusion,
   add fallback rules)
2. `src/orthosteric/data/sources/structural/_pdb.py` — add `AlphaFoldConnector`
3. `src/orthosteric/data/sources/structural/_structure_record.py` — add AlphaFold fields
4. `src/orthosteric/data/sources/structural/__init__.py` — export new classes
5. Tests for all nine rules

---

## Scientific integrity preservation

This amendment does not change:
  * the §2.1 pocket definition (experimental + bound ligand);
  * the R4 risk mitigation for the induced specificity pocket;
  * ADR-0003 or any adjudication rule;
  * AUDITOR-5 ATP Km policy;
  * any other frozen methodology.

The amendment extends SCI0-007 by adding a fallback path, not by weakening
the primary experimental-evidence requirements.

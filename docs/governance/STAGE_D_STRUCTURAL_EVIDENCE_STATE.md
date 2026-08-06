# Stage D — Structural Evidence Discovery State Report

**Date:** 2026-08-06  
**Activity Snapshot:** A0 (SHA: 2b8f5ce6f236344b6e7d5ca67729a7fae77d3cb47a9fca2f9e36d4f3a9599493)

## Status: PARTIAL

Structural evidence discovery was initiated but is not complete.

---

## What Was Accomplished

### StructuralEvidenceRecord Implemented

`src/orthosteric/data/sources/structural/_evidence_record.py`  
First-class immutable record implementing the evidence hierarchy with explicit
UNAVAILABLE ≠ ABSENT enforcement (§18 of Stage D instructions).

Evidence classes supported:
- `EXPERIMENTAL_COMPLEX` (Level 1) — exact compound + isoform, observed pose
- `ANALOGUE_REFERENCE` (Level 2) — related compound; reference only
- `EXPERIMENTAL_RECEPTOR` (Level 3) — experimental receptor for docking
- `LITERATURE_BINDING_MODE` (Level 4)
- `ALPHAFOLD_RECEPTOR` (Level 5) — GDR-006
- `UNAVAILABLE` (Level 6) — explicit, never silent

### PDB Structural Coverage Discovered

| Isoform | UniProt | PDB Entries (RCSB) | Note |
|---------|---------|-------------------|------|
| PIK3CA (α) | P42336 | NOT YET SEARCHED | awaiting PIK3CA acquisition |
| PIK3CB (β) | P42338 | 0 (RCSB cross-ref gap) | known RCSB issue; alternative query needed |
| PIK3CG (γ) | P48736 | **107** | confirmed via RCSB search 2026-08-06 |
| PIK3CD (δ) | O00329 | NOT YET SEARCHED | awaiting PIK3CD acquisition |

### PIK3CG Receptor Quality (Sample — 15 of 107 structures)

All 15 sampled structures have resolution 2.0–3.2Å. Ligand cross-referencing
requires the RCSB CCD → InChIKey mapping endpoint (not yet run due to rate
and timeout constraints).

---

## What Is Blocked

### Compound-Level EXPERIMENTAL_COMPLEX Matching
- Requires: for each of 7,667 corpus InChIKeys, query PDB for a co-crystal
  with the corresponding PI3K isoform
- Requires: CCD ligand code → InChIKey mapping (via `data.rcsb.org/rest/v1/core/chemcomp/`)
- Status: NOT RUN — would require ~7,667 RCSB API calls

### PIK3CB RCSB Search Returns 0
- P42338 (PIK3CB) returns 204 No Content from RCSB `exact_match` on
  `database_accession`. Known RCSB cross-ref inconsistency.
- PIK3CB structures DO exist in PDB (e.g. 2Y3A, 4BFR); alternative
  query (by gene name or polymer entity name) is needed.
- Status: RULE_MISSING — alternative search strategy to be specified.

### Docking Architecture
- All docking parameters are RULE_MISSING (see DOCKING_RULE_MISSING_LOG.md)

---

## Missingness Audit

Per §18 of acquisition instructions — these distinctions are enforced in
StructuralEvidenceRecord.is_experimental, is_alphafold, is_docked flags:

```
UNAVAILABLE ≠ ABSENT
no PDB structure ≠ no binding
RCSB search returns 0 ≠ compound does not bind
no docking run ≠ non-productive engagement
```

Default evidence class for all 7,667 corpus compounds: `UNAVAILABLE`
(explicitly instantiated via `StructuralEvidenceRecord.unavailable()`)
until full cross-reference runs.

---

## Next Steps Required

1. Fix PIK3CB PDB search (gene-name or full-text query fallback)
2. Acquire PIK3CA (CHEMBL4005) and PIK3CD (CHEMBL3130) activity data
3. Run full CCD → InChIKey ligand mapping for PIK3CG 107 structures
4. For matched ligands: populate `EXPERIMENTAL_COMPLEX` evidence records
5. For unmatched compounds with PIK3CG: populate `EXPERIMENTAL_RECEPTOR` evidence
6. For compounds with no PDB receptor: initiate AlphaFold fallback (GDR-006)
7. File GDRs for all docking RULE_MISSING items before any docking proceeds

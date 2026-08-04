# RULE_CONFLICT — SCI0-007 AlphaFold Fallback

**Classification:** `RULE_CONFLICT / GOVERNANCE_DECISION_REQUIRED`  
**Date:** 2026-08-02  
**Raised by:** implementation agent  
**Affects:** SCI0-007 structural-source selection  

---

## Conflict statement

The implementation instruction requests an AlphaFold fallback when no eligible
experimental PDB structure exists.  This conflicts with two authoritative
governing documents.

## Governing documents that explicitly exclude AlphaFold

### 1. SCI0-001-refinement defect correction table, defect 7

> "AlphaFold as a structure source | **Excluded** — no resolution, no bound
> ligand, cannot support §2.1(1); R4 risk."

This was introduced as a *defect correction* — meaning the prior design
contained AlphaFold and it was deliberately removed because it cannot satisfy
the pocket-definition requirement.

### 2. SCI0-007 specification

> "PDB: metadata and coordinates for human structures with a **bound ATP-site
> ligand**.  UniProt: sequence and isoform identity only.  **AlphaFold excluded**
> (defect 7)."

Explicit exclusion with a direct reference to the defect.

### 3. Constitution §2.1(1) — pocket definition

> "The pocket is the union, across the reference ensemble per target, of
> residues with any heavy atom within 5.0 Å of any heavy atom of **a bound
> ATP-site ligand**."
> "**Apo-derived definitions are prohibited**"

AlphaFold provides no bound ligand and no experimental resolution.  It cannot
produce a pocket satisfying §2.1(1).

### 4. Risk register R4

> "Apo-pocket definition deletes induced specificity pocket (C6) | Fatal to
> determinant claims | §2.1(1); apo-ablation"

An AlphaFold structure has the same failure mode as an apo structure: the
induced specificity pocket between Trp780 and Met772 does not exist in the
predicted/apo state.  Using it would trigger R4.

---

## What is blocked

The AlphaFold fallback as described in the implementation instruction cannot
be implemented without overriding at least SCI0-007 specification and the
SCI0-001-refinement defect correction, both of which are ADR-level or
specification-level governance artifacts.

The blocked operation: selecting an AlphaFold model when no eligible
experimental PDB exists.

---

## What is not blocked

All experimental-PDB acquisition, UniProt acquisition, construct descriptor,
admissibility filtering, and provenance tracking proceed independently.
The four Class I PI3K isoforms all have experimental human structures with
bound ligands in the PDB; this fallback would only be needed for an isoform
with no qualifying experimental structure, which is not the current case.

---

## Resolution options (for Project Owner / governance decision)

A. **Accept existing exclusion** — AlphaFold remains excluded.  When no
   eligible experimental structure exists for a target, the pipeline returns
   `INADMISSIBLE_NO_EXPERIMENTAL_STRUCTURE` and continues with other isoforms.
   This is the current governance position and requires no amendment.

B. **Amend SCI0-007 via a gate-level Decision Record** — explicitly permit
   AlphaFold as a fallback with a documented scientific justification for why
   the §2.1(1) pocket-definition requirement can be relaxed in the fallback
   case.  This would require at minimum: a Decision Record that identifies
   how an AlphaFold structure is used (sequence identity only? fold scaffold
   only?) without violating the R4 risk; and a record of why the fallback
   case is expected to arise.

---

## Current implementation decision

**SCI0-007 proceeds with experimental-PDB-only acquisition.** The
`StructureSource` enum includes `ALPHAFOLD_FALLBACK` as a value (so the
downstream data model can accommodate it if a governance amendment authorizes
it), but no AlphaFold retrieval code is executed under the current rules.
An isoform with no qualifying experimental structure returns
`AdmissibilityDecision.INADMISSIBLE_NO_EXPERIMENTAL_STRUCTURE`.

This is the fail-closed, governance-consistent position.

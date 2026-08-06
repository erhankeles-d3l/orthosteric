# Stage 0 — Governance Closure Report

**Date:** 2026-08-06  
**Branch:** feature/stage0-corpus-acquisition  
**Snapshot 0:** NOT BUILT (see §3)  
**Corpus status:** NO VALID PI3K RECORDS ACQUIRED

---

## §1. Acquisition Summary

**Source:** ChEMBL 37 (version confirmed from API status endpoint)  
**Retrieval window:** 2026-08-06  
**Acquisition script:** `scripts/stage0_acquire.py`  
**Raw data directory:** `data/raw/chembl/`

### §1.1 Records Downloaded

| ChEMBL ID (old tier map) | Assumed target | Actual ChEMBL 37 target | Records downloaded | Admissibility |
|---|---|---|---|---|
| CHEMBL4523 | PIK3CA (p110α) | PIM2 (Serine/threonine-protein kinase pim-2) | 200 | **INADMISSIBLE** — wrong target |
| CHEMBL5319 | PIK3CB (p110β) | DDR1 (Epithelial discoidin domain-containing receptor 1) | 400 | **INADMISSIBLE** — wrong target |
| CHEMBL3629 | PIK3CD (p110δ) | CK2α (Casein kinase II subunit alpha) | 1,200 | **INADMISSIBLE** — wrong target |
| CHEMBL5541 | PIK3CG (p110γ) | (not reached — 0 IC50 records) | 0 | INADMISSIBLE — wrong target per ADR-0011 |
| CHEMBL2842 | MTOR | Not verified (API unavailable) | 0 | PENDING_VERIFICATION |

**Total valid PI3K records acquired: 0.**

### §1.2 Root Cause

The ChEMBL target IDs in `_tier_map.py` were originally verified against ChEMBL 34.
In ChEMBL 37, these IDs now resolve to different proteins (PIM2, DDR1, CK2α).
This was detected by reading `target_pref_name` from the downloaded activity records.

Governance response: ADR-0011 (accepted), tier map corrected.  
Correct ChEMBL 37 IDs identified (PIK3CB: CHEMBL3145, PIK3CG: CHEMBL3267).  
PIK3CA and PIK3CD ChEMBL 37 IDs remain PENDING_API_VERIFICATION.

### §1.3 ChEMBL API Stability

The ChEMBL 37 REST API was intermittently unavailable during the acquisition session,
returning HTTP 500 errors for many endpoints including the target search and individual
target lookup endpoints. This prevented verification of PIK3CA and PIK3CD ChEMBL 37 IDs.
Activity queries using the correct IDs (CHEMBL3145, CHEMBL3267) were not attempted since
the API was returning errors.

**This is an external constraint, not an implementation gap.**

---

## §2. Governance Item Status

### §2.1 GGR-002a — MMP Switch Set

**Status: UNRESOLVED / INSUFFICIENT_REAL_EVIDENCE**

**Evidence examined:** 0 valid PI3K records.  
**Reason:** No valid PI3K data acquired (wrong ChEMBL IDs; API unavailability).  
**Required to resolve:** Within-study matched molecular pairs from PI3K α/β/γ/δ panels.  
**Path to resolution:** Re-run acquisition using CHEMBL3145 (PIK3CB) and CHEMBL3267 (PIK3CG) 
once the API is stable. Confirm PIK3CA and PIK3CD ChEMBL 37 IDs. Then extract 
within-study multi-isoform compound sets and identify MMP pairs.

### §2.2 GGR-002b — S4b Sharpness Multiplier / Within-Study Noise Floor

**Status: UNRESOLVED / INSUFFICIENT_REAL_EVIDENCE**

**Evidence examined:** 0 valid PI3K records.  
**Reason:** Same as GGR-002a.  
**Required to resolve:** Within-study replicate measurements (same compound, same assay, 
same isoform) across at least one PI3K isoform. Even 20-50 replicate pairs would provide 
an initial noise floor estimate.  
**Path to resolution:** As GGR-002a; additionally collect assay records where 
`assay_chembl_id` is repeated for the same `molecule_chembl_id`.

### §2.3 GGR-010 — Dual PI3K/mTOR Inhibitor Census

**Status: UNRESOLVED / INSUFFICIENT_REAL_EVIDENCE**

**Evidence examined:** 0 valid PI3K records; 0 mTOR records.  
**Reason:** No valid PI3K data; mTOR ChEMBL 37 ID not verified; API unavailable.  
**Required to resolve:** (1) Confirm MTOR ChEMBL 37 ID (CHEMBL2842 — was verified in 
ChEMBL 34; re-verification required). (2) Download PI3K and mTOR activity tables. 
(3) Cross-reference by `molecule_chembl_id` to identify dual actives.  
**Path to resolution:** Verify MTOR ID. Download activity tables. Build census.

---

## §3. Snapshot 0 Status

**Snapshot 0 has NOT been built.** No valid PI3K activity records are available to freeze.

Building an empty or inadmissible-record-only Snapshot 0 would create a governance artifact 
that could be confused with a real scientific corpus. The correct procedure is:

1. Wait for ChEMBL API stability (or retry at a later time).
2. Acquire PI3K data using the correct ChEMBL 37 IDs (CHEMBL3145, CHEMBL3267 confirmed;
   PIK3CA and PIK3CD pending ID verification).
3. Freeze Snapshot 0 once at least 4-isoform panels are available for some compounds.

**Snapshot 0 will be built in a follow-up session when valid data is available.**

---

## §4. Inadmissible Data Disposition

The following raw data directories contain inadmissible records (wrong targets, not PI3K):

```
data/raw/chembl/CHEMBL4523/   -- PIM2 data, 200 records, inadmissible
data/raw/chembl/CHEMBL5319/   -- DDR1 data, 400 records, inadmissible  
data/raw/chembl/CHEMBL3629/   -- CK2α data, 1200 records, inadmissible
```

These directories are being deleted from the working tree. The acquisition manifest 
records the fact that they were downloaded and why they are inadmissible.

---

## §5. Infrastructure Status

Despite the corpus acquisition failure, the following infrastructure is **complete and ready**:

| Component | Status |
|---|---|
| ChEMBL connector (`_chembl.py`) | Ready |
| Tier map (`_tier_map.py`) | Updated (ADR-0011) |
| Harmonization pipeline (`harmonization/`) | Ready |
| Snapshot builder (`snapshots/_builder.py`) | Ready |
| `CurrentCorpus` / `CorpusSnapshotV2` lifecycle | Ready |
| `CorpusLifecyclePipeline` | Ready |
| `SnapshotDiff` / `CorpusSnapshotRegistry` | Ready |
| Quality assessment pipeline | Ready |
| `ModelGenerationRecord` interface | Ready |
| SCI2-002 machine implementation | **PENDING — see §6** |

---

## §6. Next Steps

1. **Retry corpus acquisition** when ChEMBL API is stable.
   Targets to use: CHEMBL3145 (PIK3CB), CHEMBL3267 (PIK3CG).
   Before PIK3CA/PIK3CD: run ADR-0011 verification commands.

2. **Implement SCI2-002** (model infrastructure) — does not depend on corpus.
   This session will proceed to SCI2-002 implementation using synthetic fixtures
   for engineering validation, per Constitution §19 of the mission.

3. **Build Snapshot 0** — once valid PI3K records are acquired.

4. **Resolve GGR-002a/b/010** — once Snapshot 0 is built and characterized.

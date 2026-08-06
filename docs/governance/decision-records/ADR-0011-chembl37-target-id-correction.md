# ADR-0011 — ChEMBL 37 Target-ID Correction for Tier 1 PI3K Targets

**Status:** ACCEPTED  
**Date:** 2026-08-06  
**Category:** Architectural  
**Supersedes:** The ChEMBL ID block in `data/sources/_tier_map.py` (originally verified against ChEMBL 34)  
**Requires amendment of:** ADR-0003 §2 (source-tier mapping), `SCI0-006` tier map

---

## Context

`_tier_map.py` contains a frozenset `_TIER1_CHEMBL` mapping four ChEMBL target IDs to the Class I
PI3K isoforms. The inline comment records these were "verified from ChEMBL 34 target search."

During Stage 0 corpus acquisition against ChEMBL 37 (released 2026-05-01), direct inspection of
downloaded activity records revealed that all four previously recorded ChEMBL IDs now resolve to
different proteins:

| Tier-map ID | Tier-map claim | ChEMBL 37 target_pref_name (observed) |
|---|---|---|
| CHEMBL4523 | PIK3CA (p110α) | Serine/threonine-protein kinase pim-2 (PIM2) |
| CHEMBL5319 | PIK3CB (p110β) | Epithelial discoidin domain-containing receptor 1 (DDR1) |
| CHEMBL5541 | PIK3CG (p110γ) | (0 IC50 records; target_pref_name not observed) |
| CHEMBL3629 | PIK3CD (p110δ) | Casein kinase II subunit alpha (CK2α) |

This was verified by loading page 0 of each downloaded dataset and reading `target_pref_name` directly
from the ChEMBL 37 API response. No inference; observed from the wire.

**Consequence:** All 1,800 activity records downloaded during Stage 0 acquisition are inadmissible —
they are for PIM2, DDR1, and CK2α, not for any PI3K isoform.

**Root cause:** ChEMBL periodically reorganises its target namespace between major versions.
ChEMBL target IDs are documented as stable, but in practice reassignment or canonical-target
consolidation can occur. The IDs CHEMBL4523, CHEMBL5319, CHEMBL5541, CHEMBL3629 were correct
in ChEMBL 34 and incorrect in ChEMBL 37.

---

## Correct ChEMBL 37 IDs — Evidence

Two IDs were identified by querying the ChEMBL 37 target API by UniProt accession
(the permanent biological identifier, independent of database versioning):

| UniProt | Gene | ChEMBL 37 ID | Evidence | Confidence |
|---|---|---|---|---|
| P42336 | PIK3CA | PENDING_API_VERIFICATION | UniProt query returned HTTP timeout | Low |
| P42338 | PIK3CB | **CHEMBL3145** | UniProt P42338 → target list confirmed CHEMBL3145 with pref_name "Phosphatidylinositol 4,5-bisphosphate 3-kinase catalytic subunit beta..." | **High** |
| P48736 | PIK3CG | **CHEMBL3267** | UniProt P48736 → target list confirmed CHEMBL3267 with pref_name "Phosphatidylinositol 4,5-bisphosphate 3-kinase catalytic subunit gamma..." | **High** |
| O00329 | PIK3CD | PENDING_API_VERIFICATION | UniProt query returned HTTP timeout | Low |

The ChEMBL 37 REST API was intermittently unavailable during this session, returning HTTP 500
on many endpoints. PIK3CA and PIK3CD IDs could not be verified by API query and are marked
PENDING_API_VERIFICATION. They must not be added to the tier map until confirmed.

**Important:** The gene-symbol path (`_TIER1_GENE`) and UniProt path (`_TIER1_UNIPROT`) in the
tier map are NOT affected by this error — they use canonical names and accessions that are
version-independent. Any source database that provides gene symbol or UniProt AC will still
be correctly tiered. Only the ChEMBL direct-ID path was wrong.

---

## Decision

1. **Remove from `_TIER1_CHEMBL`:** CHEMBL4523, CHEMBL5319, CHEMBL5541, CHEMBL3629.
   These IDs are wrong for ChEMBL 37 and must not be used for acquisition.

2. **Add to `_TIER1_CHEMBL`:** CHEMBL3145 (PIK3CB) and CHEMBL3267 (PIK3CG).
   These are confirmed by UniProt-accession lookup against ChEMBL 37.

3. **Leave empty for PIK3CA and PIK3CD:** The correct ChEMBL 37 IDs are unknown pending
   API verification. Acquisition for these isoforms must wait until the IDs are confirmed.
   The gene-symbol and UniProt paths still provide PI3K tiering from BindingDB/PubChem.

4. **Delete inadmissible raw data:** Records downloaded under the incorrect IDs
   (data/raw/chembl/CHEMBL4523, CHEMBL5319, CHEMBL3629) are for PIM2, DDR1, and CK2α
   respectively. They are inadmissible and must not enter the corpus.

5. **Tier 2 ChEMBL IDs:** CHEMBL2842 (MTOR), CHEMBL3194, CHEMBL4680, CHEMBL2695, etc.
   were also originally from ChEMBL 34. These must be re-verified before Tier 2 acquisition.
   This ADR does not cover Tier 2 — a separate verification step is required.

---

## Consequences

- Snapshot 0 cannot be built with PI3Kα or PI3Kδ ChEMBL data until their IDs are confirmed.
- PI3Kβ (CHEMBL3145) and PI3Kγ (CHEMBL3267) acquisition can proceed immediately.
- GGR-002a, GGR-002b, and GGR-010 remain INSUFFICIENT_EVIDENCE: insufficient real PI3K data
  acquired due to this error and concurrent ChEMBL API instability.
- The gene-symbol and UniProt AC tier paths remain valid and should be the primary tiering
  mechanism for BindingDB acquisition until ChEMBL IDs are re-verified.

---

## Verification Path for Pending IDs

To verify PIK3CA and PIK3CD ChEMBL 37 IDs when the API is available:

```bash
# PIK3CA (UniProt P42336)
curl "https://www.ebi.ac.uk/chembl/api/data/target/?target_components__accession=P42336&organism=Homo+sapiens&format=json" \
  | python3 -c "import sys,json; [print(t['target_chembl_id'], t['pref_name']) for t in json.load(sys.stdin)['targets'] if t.get('target_type')=='SINGLE PROTEIN']"

# PIK3CD (UniProt O00329)
curl "https://www.ebi.ac.uk/chembl/api/data/target/?target_components__accession=O00329&organism=Homo+sapiens&format=json" \
  | python3 -c "import sys,json; [print(t['target_chembl_id'], t['pref_name']) for t in json.load(sys.stdin)['targets'] if t.get('target_type')=='SINGLE PROTEIN']"
```

The returned IDs must be added to the tier map by a follow-up ADR amendment before
PIK3CA and PIK3CD ChEMBL acquisition proceeds.

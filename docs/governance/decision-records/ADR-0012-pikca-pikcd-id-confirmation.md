# ADR-0012 — PIK3CA and PIK3CD ChEMBL 37 Target ID Confirmation

**Date:** 2026-08-06
**Status:** Accepted
**Supersedes:** The PENDING_API_VERIFICATION entries in ADR-0011

## Decision

PIK3CA (p110α) and PIK3CD (p110δ) ChEMBL 37 target IDs have been confirmed by
direct UniProt accession lookup against the ChEMBL 37 REST API.

| Gene | UniProt AC | ChEMBL 37 ID | pref_name |
|------|-----------|--------------|-----------|
| PIK3CA (p110α) | P42336 | **CHEMBL4005** | Phosphatidylinositol 4,5-bisphosphate 3-kinase catalytic subunit alpha isoform |
| PIK3CD (p110δ) | O00329 | **CHEMBL3130** | Phosphatidylinositol 4,5-bisphosphate 3-kinase catalytic subunit delta isoform |

Both are `SINGLE PROTEIN`, `Homo sapiens`.

## Verification

```
GET https://www.ebi.ac.uk/chembl/api/data/target/?target_components__accession=P42336&format=json
→ CHEMBL4005, Homo sapiens, SINGLE PROTEIN, PIK3CA

GET https://www.ebi.ac.uk/chembl/api/data/target/?target_components__accession=O00329&format=json
→ CHEMBL3130, Homo sapiens, SINGLE PROTEIN, PIK3CD
```

## Effect

`src/orthosteric/data/sources/_tier_map.py` `_TIER1_CHEMBL` now contains all four
Tier 1 IDs: CHEMBL4005 (α), CHEMBL3145 (β), CHEMBL3267 (γ), CHEMBL3130 (δ).

Activity data for PIK3CA and PIK3CD has not yet been acquired.  The next
acquisition script run will fetch these targets and produce Activity Snapshot A1.

## Alternatives

None — direct API verification is the only acceptable method per ADR-0011.

## Reversibility

Reversible with a new Decision Record if ChEMBL 37 is found to have changed
these IDs, which would be a database inconsistency.

## Review trigger

At next Activity Snapshot creation.

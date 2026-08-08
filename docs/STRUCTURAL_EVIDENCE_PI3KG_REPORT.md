# Structural Evidence for PIK3Kgamma: First Compound-Level Match

**Date:** 2026-08-06
**Snapshot:** A4, `SNAP-05748f6627ea` (unmodified — verified before/after)
**Purpose:** completes the first item in the prior session's Stage D
"next steps" list ("run full CCD → InChIKey ligand mapping for PIK3Kgamma
107 structures") and honestly assesses whether the result supports a
structural-augmented training experiment.

## Real data acquired (RCSB PDB REST API)

| Step | Result |
|---|---|
| PIK3Kgamma PDB entries (search, UniProt P48736) | 107 |
| Distinct co-crystallized ligand CCD codes (non-additive) | 102 |
| InChIKeys resolved (RCSB `pdbx_chem_comp_descriptor`, type=InChIKey — exact RCSB values, not RDKit-recomputed) | 102/102 |

Two fetch-path bugs from the prior session were found and fixed in the
process: `nonpolymer_entities` is not embedded in the RCSB `entry` core
endpoint response (must fetch `rcsb_entry_container_identifiers.
non_polymer_entity_ids` then the `nonpolymer_entity/{pdb_id}/{entity_id}`
endpoint per entity); and `rcsb_chem_comp_descriptor.smiles` does not
exist on the `chemcomp` endpoint (SMILES/InChI/InChIKey are entries in the
`pdbx_chem_comp_descriptor` list, keyed by `type`). Both traced against a
known reference structure (1E7V / LY294002) before trusting the bulk fetch.

## Compound-level matching against Activity Snapshot A4

| Match tier | Count |
|---|---:|
| EXACT InChIKey (full, incl. stereo) | 66 |
| SKELETON InChIKey (connectivity only, stereo layer differs) | 2 |
| **Total distinct matched corpus compounds** | **68** |
| Real `EXPERIMENTAL_COMPLEX` records (one per PDB entry per matched compound) | 69 |
| Corpus compounds explicitly `UNAVAILABLE` | 16,167 |

The two SKELETON matches (BWY, BYM) are tagged distinctly from the 66
EXACT matches — never conflated, per the tested tier-separation invariant
(`test_skeleton_match_tagged_separately_from_exact`).

Full record set: `data/structural_evidence/pi3kg_experimental_complex_A4.json`
(69 records). Summary: `docs/governance/STAGE_D_PI3KG_MATCHING_A4.json`.

## Overlap with the actual modeling set

```
SelectivityTargets (complete 4-isoform C1_PRIMARY compounds): 1,267
Overlap with structurally-matched compounds:                     28  (2.2%)
```

## Honest feasibility assessment: INSUFFICIENT for a training run

28 compounds is below the documented (not governed) 50-compound floor for
a trustworthy scaffold-aware train/val/test split, and — more
fundamentally — the existing `ComparativeSelectivityModelV1.fit()`/
`predict()` anti-fabrication rule (tested last session,
`test_compound_missing_from_structural_features_is_skipped_not_fabricated`)
**skips** any example missing from a supplied `structural_features`
mapping rather than zero-filling it. Passing a 28-entry mapping while
fitting on the 1,267-compound corpus would silently collapse the
effective training set to ~28 compounds — not a meaningful structural-
vs-ligand-only comparison, and **not run here for that reason**.

## Architectural implication surfaced, not resolved

Two designs exist for incorporating sparse structural evidence, and this
session's finding makes the tradeoff concrete rather than abstract:

1. **Skip-on-missing** (current, tested): correct and honest, but at 2.2%
   coverage it cannot produce a usable experiment — the model would train
   on 28 compounds and tell us almost nothing.
2. **Presence-indicator + zero-fill-when-absent**: a common ML pattern
   (binary "evidence available" flag alongside a real feature value, zero
   only when explicitly flagged as missing) that would let all 1,267
   compounds remain in training while still giving the ~28 structurally-
   matched compounds a real, non-fabricated signal others lack. This is a
   genuinely different, defensible design — but it changes a *tested
   invariant* from the prior session, so it is **not implemented here**;
   it is surfaced as an explicit design decision for a future session,
   not silently substituted.

No structural-augmented model was trained. No claim of "structural
evidence improves the model" (or the reverse) is made — there was no
statistically meaningful experiment to run.

## Reproducibility

`analysis/run_pi3kg_structural_evidence_matching.py` (deterministic given
the cached RCSB fetch, provenance documented in the module docstring).
New governed module: `orthosteric.data.sources.structural.
_pi3kg_complex_matching` (8 tests, `tests/data/sources/structural/
test_pi3kg_complex_matching.py`).

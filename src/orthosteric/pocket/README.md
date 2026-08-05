# `pocket/` — Structural Preprocessing and Pocket Extraction

**Authority:** ADR-0010 [Architectural]. Phase C SCI-1.
**Constitution sections served:** §2.1, §0.3, §A.1(4), §A.6.

## Purpose

Transform raw PDB/AlphaFold structures into governed ATP-site pocket
representations ready for the `features/` layer.

## Scientific principles implemented

**No apo pocket definitions.** The induced specificity pocket (Trp780/Met772
cleft) is absent in apo structures. Constitution §2.1 Rule 1 prohibits apo-
derived pocket boundaries; every `PocketResidueSet` is built from the
ligand-ensemble union across ligand-bound structures only.

**Rotamer states are part of the pocket.** Selectivity derives substantially
from side-chain conformational accessibility (§2.1 Rule 2). The
`PocketResidue` type records which rotamer states are accessible in each
contributing structure, not just sequence identity.

**Governed distance cutoff.** The 5.0 Å heavy-atom threshold is exposed as
`GOVERNED_DISTANCE_CUTOFF_ANGSTROM` — a named constant modifiable only via a
Governance Decision Record, not via an undocumented keyword argument.

**Correspondence stability.** A residue observed in < 2 independent structures
is flagged `correspondence_stable = False` (§A.1(4) stability requirement).

**Experimental priority.** `StructureSource` explicitly distinguishes
experimental PDB structures from governed AlphaFold fallbacks; no code may
silently treat a predicted structure as experimental.

## Phase C SCI-1 modules

| Module | Status | Description |
|---|---|---|
| `_structure_record.py` | Done (Milestone 2) | Typed frozen data models: `StructureRecord`, `StructureProvenance`, `ConstructDescriptor`, `LigandRecord`, `ChainRecord`, `ResidueRecord` |
| `_pocket_definition.py` | Done (Milestone 2) | Governed pocket definition: `PocketDefinitionPolicy`, `PocketResidueSet`, `SubRegion` |
| `_residue_mapping.py` | SCI1-003 | Cross-isoform residue correspondence (structure-based, not sequence-only) |
| `_rotamer_state.py` | SCI1-002 | Rotamer state representation for selectivity-relevant residues |
| `_pocket_geometry.py` | SCI1-002 | Volume, depth, enclosure, shape descriptors |
| `_solvent_accessibility.py` | SCI1-002 | Per-residue SASA; ordered/displaceable water annotation |

"""pocket package — Structural preprocessing and pocket extraction (Phase C SCI-1).

Authority: ADR-0010 [Architectural].
Responsibility (ENG §2): structural preprocessing and pocket extraction --
structure cleaning, chain selection, ligand extraction, binding-site
extraction, residue numbering harmonisation, pocket definition (Constitution
§2.1 §A.6), rotamer-state representation, pocket geometry. The ATP-site
representation that features/ and learning/ consume.

Constitution sections served: §2.1, §0.3, §A.1(4), §A.6.

Must NOT contain: feature selection, prediction, model training,
interpretation.
"""

from orthosteric.pocket._pocket_definition import (
    GOVERNED_DISTANCE_CUTOFF_ANGSTROM,
    GOVERNED_MIN_STRUCTURES_FOR_STABILITY,
    POCKET_DEFINITION_ALGORITHM_VERSION,
    PocketDefinitionPolicy,
    PocketResidue,
    PocketResidueSet,
    SubRegion,
    default_pocket_definition_policy,
)
from orthosteric.pocket._structure_record import (
    ChainRecord,
    ConformationalState,
    ConstructClass,
    ConstructDescriptor,
    DataTier,
    LigandRecord,
    LigandShapeClass,
    ResidueRecord,
    StructureProvenance,
    StructureRecord,
    StructureSource,
    make_record_id,
)

__all__ = [
    "GOVERNED_DISTANCE_CUTOFF_ANGSTROM",
    "GOVERNED_MIN_STRUCTURES_FOR_STABILITY",
    "POCKET_DEFINITION_ALGORITHM_VERSION",
    "ChainRecord",
    "ConformationalState",
    "ConstructClass",
    "ConstructDescriptor",
    "DataTier",
    "LigandRecord",
    "LigandShapeClass",
    "PocketDefinitionPolicy",
    "PocketResidue",
    "PocketResidueSet",
    "ResidueRecord",
    "StructureProvenance",
    "StructureRecord",
    "StructureSource",
    "SubRegion",
    "default_pocket_definition_policy",
    "make_record_id",
]

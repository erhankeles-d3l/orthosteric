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
from orthosteric.pocket._pocket_geometry import (
    GEOMETRY_ALGORITHM_VERSION,
    VOLUME_RULE_MISSING_NOTE,
    AtomCoordinate,
    GeometryConfig,
    PocketGeometry,
    compute_pocket_geometry,
)
from orthosteric.pocket._rotamer_state import (
    CHI_ATOM_NAMES,
    ROTAMER_ALGORITHM_VERSION,
    ROTAMER_CLASSIFICATION_RULE_MISSING_NOTE,
    ChiAngle,
    PocketRotamerStates,
    ResidueRotamerState,
    RotamerAvailability,
    compute_pocket_rotamer_states,
)
from orthosteric.pocket._solvent_accessibility import (
    GOVERNED_PROBE_RADIUS_ANGSTROM,
    SASA_ALGORITHM_VERSION,
    TIEN_2013_MAX_ASA,
    PocketSASA,
    ResidueSASA,
    SASAAvailability,
    SASAConfig,
    compute_pocket_sasa,
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
    "CHI_ATOM_NAMES",
    "GEOMETRY_ALGORITHM_VERSION",
    "GOVERNED_DISTANCE_CUTOFF_ANGSTROM",
    "GOVERNED_MIN_STRUCTURES_FOR_STABILITY",
    "GOVERNED_PROBE_RADIUS_ANGSTROM",
    "POCKET_DEFINITION_ALGORITHM_VERSION",
    "ROTAMER_ALGORITHM_VERSION",
    "ROTAMER_CLASSIFICATION_RULE_MISSING_NOTE",
    "SASA_ALGORITHM_VERSION",
    "TIEN_2013_MAX_ASA",
    "VOLUME_RULE_MISSING_NOTE",
    "AtomCoordinate",
    "ChainRecord",
    "ChiAngle",
    "ConformationalState",
    "ConstructClass",
    "ConstructDescriptor",
    "DataTier",
    "GeometryConfig",
    "LigandRecord",
    "LigandShapeClass",
    "PocketDefinitionPolicy",
    "PocketGeometry",
    "PocketResidue",
    "PocketResidueSet",
    "PocketRotamerStates",
    "PocketSASA",
    "ResidueRecord",
    "ResidueRotamerState",
    "ResidueSASA",
    "RotamerAvailability",
    "SASAAvailability",
    "SASAConfig",
    "StructureProvenance",
    "StructureRecord",
    "StructureSource",
    "SubRegion",
    "compute_pocket_geometry",
    "compute_pocket_rotamer_states",
    "compute_pocket_sasa",
    "default_pocket_definition_policy",
    "make_record_id",
]

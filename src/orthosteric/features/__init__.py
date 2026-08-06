"""features package -- Structural representation construction (Phase C SCI-1).

Authority: ADR-0010 [Architectural].
Provides: interaction fingerprints (SCI1-004), contact maps and structural
graphs (SCI1-005), pocket descriptors and comparative feature sets (SCI1-006).
Consumes pocket/ representations; produces ML-ready tensors.
Must NOT contain: structure I/O, training loops, prediction, policy decisions.
"""

from orthosteric.features._comparative_feature import (
    COMPARATIVE_FEATURE_ALGORITHM_VERSION,
    ComparativeFeatureSet,
    DifferentialFlag,
    InteractionPresence,
    PositionProfile,
    build_comparative_feature_set,
)
from orthosteric.features._contact_map import (
    CONTACT_MAP_ALGORITHM_VERSION,
    ContactMapConfig,
    ContactStatus,
    LigandResidueContactMap,
    PocketContactMap,
    ResidueResidueContactMap,
    compute_contact_map,
)
from orthosteric.features._interaction_fingerprint import (
    FINGERPRINT_ALGORITHM_VERSION,
    ComparativeFingerprint,
    FingerprintConfig,
    InteractionEvidence,
    InteractionFingerprint,
    InteractionStatus,
    InteractionType,
    build_comparative_fingerprint,
    compute_interaction_fingerprint,
)
from orthosteric.features._pocket_descriptor import (
    POCKET_DESCRIPTOR_ALGORITHM_VERSION,
    PocketDescriptor,
    build_pocket_descriptor,
)
from orthosteric.features._structural_graph import (
    STRUCTURAL_GRAPH_ALGORITHM_VERSION,
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeType,
    PocketGraph,
    StructuralGraphConfig,
    compute_structural_graph,
)

__all__ = [
    "COMPARATIVE_FEATURE_ALGORITHM_VERSION",
    "CONTACT_MAP_ALGORITHM_VERSION",
    "FINGERPRINT_ALGORITHM_VERSION",
    "POCKET_DESCRIPTOR_ALGORITHM_VERSION",
    "STRUCTURAL_GRAPH_ALGORITHM_VERSION",
    "ComparativeFeatureSet",
    "ComparativeFingerprint",
    "ContactMapConfig",
    "ContactStatus",
    "DifferentialFlag",
    "EdgeType",
    "FingerprintConfig",
    "GraphEdge",
    "GraphNode",
    "InteractionEvidence",
    "InteractionFingerprint",
    "InteractionPresence",
    "InteractionStatus",
    "InteractionType",
    "LigandResidueContactMap",
    "NodeType",
    "PocketContactMap",
    "PocketDescriptor",
    "PocketGraph",
    "PositionProfile",
    "ResidueResidueContactMap",
    "StructuralGraphConfig",
    "build_comparative_feature_set",
    "build_comparative_fingerprint",
    "build_pocket_descriptor",
    "compute_contact_map",
    "compute_interaction_fingerprint",
    "compute_structural_graph",
]

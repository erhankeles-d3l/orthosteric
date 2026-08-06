"""features package -- Structural representation construction (Phase C SCI-1).

Authority: ADR-0010 [Architectural].
Responsibility: interaction fingerprints, contact maps, structural graphs,
pocket descriptors, comparative multi-isoform feature sets, MD-ready stubs.
Consumes pocket/ representations; produces ML-ready tensors.

Must NOT contain: structure I/O, training loops, prediction, policy decisions.
"""

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
    "CONTACT_MAP_ALGORITHM_VERSION",
    "FINGERPRINT_ALGORITHM_VERSION",
    "STRUCTURAL_GRAPH_ALGORITHM_VERSION",
    "ComparativeFingerprint",
    "ContactMapConfig",
    "ContactStatus",
    "EdgeType",
    "FingerprintConfig",
    "GraphEdge",
    "GraphNode",
    "InteractionEvidence",
    "InteractionFingerprint",
    "InteractionStatus",
    "InteractionType",
    "LigandResidueContactMap",
    "NodeType",
    "PocketContactMap",
    "PocketGraph",
    "ResidueResidueContactMap",
    "StructuralGraphConfig",
    "build_comparative_fingerprint",
    "compute_contact_map",
    "compute_interaction_fingerprint",
    "compute_structural_graph",
]

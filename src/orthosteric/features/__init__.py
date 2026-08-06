"""features package -- Structural representation construction (Phase C SCI-1).

Authority: ADR-0010 [Architectural].
Modules:
  SCI1-004: interaction fingerprints (_interaction_fingerprint)
  SCI1-005: contact maps + structural graph (_contact_map, _structural_graph)
  SCI1-006: pocket descriptors + comparative features (_pocket_descriptor,
            _comparative_feature)
  SCI1-007: MD interface stubs (_md_interface)
  SCI1-008: governed feature config (_feature_config)
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
from orthosteric.features._feature_config import (
    FEATURE_CONFIG_ALGORITHM_VERSION,
    FeatureConfig,
    default_feature_config,
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
from orthosteric.features._md_interface import (
    MD_INTERFACE_ALGORITHM_VERSION,
    ConformationalStateLabel,
    EnsembleMetadata,
    InteractionPersistence,
    MDFeaturePlaceholder,
    MDStatus,
    WaterOccupancy,
)
from orthosteric.features._pipeline import (
    PIPELINE_ALGORITHM_VERSION,
    FeaturePipelineResult,
    build_comparative_features,
    compute_features,
    is_path_a_compliant,
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
    "FEATURE_CONFIG_ALGORITHM_VERSION",
    "FINGERPRINT_ALGORITHM_VERSION",
    "MD_INTERFACE_ALGORITHM_VERSION",
    "PIPELINE_ALGORITHM_VERSION",
    "POCKET_DESCRIPTOR_ALGORITHM_VERSION",
    "STRUCTURAL_GRAPH_ALGORITHM_VERSION",
    "ComparativeFeatureSet",
    "ComparativeFingerprint",
    "ConformationalStateLabel",
    "ContactMapConfig",
    "ContactStatus",
    "DifferentialFlag",
    "EdgeType",
    "EnsembleMetadata",
    "FeatureConfig",
    "FeaturePipelineResult",
    "FingerprintConfig",
    "GraphEdge",
    "GraphNode",
    "InteractionEvidence",
    "InteractionFingerprint",
    "InteractionPersistence",
    "InteractionPresence",
    "InteractionStatus",
    "InteractionType",
    "LigandResidueContactMap",
    "MDFeaturePlaceholder",
    "MDStatus",
    "NodeType",
    "PocketContactMap",
    "PocketDescriptor",
    "PocketGraph",
    "PositionProfile",
    "ResidueResidueContactMap",
    "StructuralGraphConfig",
    "WaterOccupancy",
    "build_comparative_feature_set",
    "build_comparative_features",
    "build_comparative_fingerprint",
    "build_pocket_descriptor",
    "compute_contact_map",
    "compute_features",
    "compute_interaction_fingerprint",
    "compute_structural_graph",
    "default_feature_config",
    "is_path_a_compliant",
]

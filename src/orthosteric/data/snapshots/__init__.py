"""orthosteric.data.snapshots — immutable content-hashed corpus snapshots.

Objective: SCI0-011.
Specification: SCI0-001-refinement §SCI0-011 + ENG §13 + Constitution §3.3.

Public API
----------
Builder            :class:`SnapshotBuilder`
Snapshot           :class:`CorpusSnapshot`
Manifest           :class:`SnapshotManifest`
Software provenance:class:`SoftwareProvenance`
Policy manifest    :class:`PolicyManifest`
Corpus profile      :class:`CorpusProfile`, :func:`freeze_corpus_profile` (GDR-002)
"""

from orthosteric.data.snapshots._builder import (
    CorpusSnapshotV2,
    SnapshotBuilder,
    SnapshotManifestV2,
)
from orthosteric.data.snapshots._manifest import (
    PolicyManifest,
    SoftwareProvenance,
)
from orthosteric.data.snapshots._profile import (
    CORPUS_PROFILE_SCHEMA_VERSION,
    PROFILE_ALGORITHM_VERSION,
    CorpusProfile,
    EngineeringParameters,
    StructuralCoverageStats,
    freeze_corpus_profile,
)

__all__ = [
    "CORPUS_PROFILE_SCHEMA_VERSION",
    "PROFILE_ALGORITHM_VERSION",
    "CorpusProfile",
    "CorpusSnapshotV2",
    "EngineeringParameters",
    "PolicyManifest",
    "SnapshotBuilder",
    "SnapshotManifestV2",
    "SoftwareProvenance",
    "StructuralCoverageStats",
    "freeze_corpus_profile",
]

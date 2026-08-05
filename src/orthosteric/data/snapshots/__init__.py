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

__all__ = [
    "CorpusSnapshotV2",
    "PolicyManifest",
    "SnapshotBuilder",
    "SnapshotManifestV2",
    "SoftwareProvenance",
]

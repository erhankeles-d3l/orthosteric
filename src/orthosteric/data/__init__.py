"""orthosteric.data — public data acquisition and adjudication API.

Objective: SCI0-002 (package scaffold); extended by SCI0-003 onwards.

Constitution sections served: §0.1 (tier architecture), §0.4 (Tier 2
information barrier), §2.3 (selectivity definition), §3.3 (provenance).

See README.md in this directory for the full section mapping.
"""

from orthosteric.data.adjudication import (
    AdjudicationResult,
    AdjudicationStatus,
    run_adr0003_adjudication,
)
from orthosteric.data.corpus import (
    CorpusSnapshot,
    EvidenceRecord,
    SnapshotManifest,
)
from orthosteric.data.exceptions import (
    ConfigurationError,
    GovernanceException,
    NormalizationError,
    OrthoDataError,
    ProvenanceError,
    SnapshotIntegrityError,
    TierViolationError,
)
from orthosteric.data.models import (
    CensoringKind,
    DataTier,
    MeasurementKind,
    RecordStatus,
    SourceDB,
)

__all__ = [
    "AdjudicationResult",
    "AdjudicationStatus",
    "CensoringKind",
    "ConfigurationError",
    "CorpusSnapshot",
    "DataTier",
    "EvidenceRecord",
    "GovernanceException",
    "MeasurementKind",
    "NormalizationError",
    "OrthoDataError",
    "ProvenanceError",
    "RecordStatus",
    "SnapshotIntegrityError",
    "SnapshotManifest",
    "SourceDB",
    "TierViolationError",
    "run_adr0003_adjudication",
]

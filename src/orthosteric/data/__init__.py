"""orthosteric.data — public data acquisition and adjudication API.

Objective: SCI0-002 (package scaffold); extended by SCI0-003 onwards.

Constitution sections served: §0.1 (tier architecture), §0.4 (Tier 2
information barrier), §2.3 (selectivity definition), §3.3 (provenance).

See README.md in this directory for the full section mapping.
"""

from orthosteric.data.activity import (
    AnyActivityRecord,
    BiochemicalRecord,
    CellularRecord,
    CensoredValue,
    RelationalOperator,
    censored_fraction,
    is_censored,
)
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
    ActivityRecord,
    CensoringKind,
    DataTier,
    MeasurementClass,
    MeasurementType,
    RecordStatus,
    SourceDB,
)

__all__ = [
    "ActivityRecord",
    "AdjudicationResult",
    "AdjudicationStatus",
    "AnyActivityRecord",
    "BiochemicalRecord",
    "CellularRecord",
    "CensoredValue",
    "CensoringKind",
    "ConfigurationError",
    "CorpusSnapshot",
    "DataTier",
    "EvidenceRecord",
    "GovernanceException",
    "MeasurementClass",
    "MeasurementType",
    "NormalizationError",
    "OrthoDataError",
    "ProvenanceError",
    "RecordStatus",
    "RelationalOperator",
    "SnapshotIntegrityError",
    "SnapshotManifest",
    "SourceDB",
    "TierViolationError",
    "censored_fraction",
    "is_censored",
    "run_adr0003_adjudication",
]

# Lifecycle types (corpus_lifecycle)
from orthosteric.data.corpus_lifecycle import (
    CorpusDataMode as CorpusDataMode,
)
from orthosteric.data.corpus_lifecycle import (
    CorpusLifecycleStage as CorpusLifecycleStage,
)
from orthosteric.data.corpus_lifecycle import (
    CurrentCorpus as CurrentCorpus,
)
from orthosteric.data.corpus_lifecycle import (
    DataModeViolation as DataModeViolation,
)

"""orthosteric.data.provenance — immutable provenance schema and writer.

Objective: SCI0-003.
Constitution §3.3: every record carries source, study or accession, assay,
[ATP], construct, date, curator, extraction version, tier, and curation
confidence.  A record missing any field is rejected at construction.
"""

from orthosteric.data.provenance.enums import (
    ExtractionTier,
    LicenseType,
    LocatorType,
    MeasurementClass,
    MeasurementType,
    SourceConfidence,
    SourceType,
    Tier,
    Unit,
)
from orthosteric.data.provenance.models import (
    SCHEMA_VERSION,
    AssayMetadata,
    ExtractionMetadata,
    ProvenanceRecord,
    PublicationMetadata,
    Quantity,
    SourceMetadata,
    SpanAnchor,
)
from orthosteric.data.provenance.validator import (
    ProvenanceValidationError,
    validate_provenance,
)
from orthosteric.data.provenance.writer import (
    ProvenanceSerializationError,
    deserialize,
    serialize,
    to_json_bytes,
)

__all__ = [
    "SCHEMA_VERSION",
    "AssayMetadata",
    "ExtractionMetadata",
    "ExtractionTier",
    "LicenseType",
    "LocatorType",
    "MeasurementClass",
    "MeasurementType",
    "ProvenanceRecord",
    "ProvenanceSerializationError",
    "ProvenanceValidationError",
    "PublicationMetadata",
    "Quantity",
    "SourceConfidence",
    "SourceMetadata",
    "SourceType",
    "SpanAnchor",
    "Tier",
    "Unit",
    "deserialize",
    "serialize",
    "to_json_bytes",
    "validate_provenance",
]

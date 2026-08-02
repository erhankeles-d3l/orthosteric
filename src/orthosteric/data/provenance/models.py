"""Immutable provenance models.

Objective: SCI0-003.
Owner: Constitution §3.3 (provenance mandatory per record), §0.4 (tier), §2.3(2).

Scientific rationale:
    No scientific record may exist without complete provenance. Every dataclass here
    is frozen: provenance is never modified in place, and a correction is a new record
    (CLAUDE.md §8, SI9). Composition is preferred to a single wide class so that each
    metadata group can be validated and evolved independently.

Design constraints carried from the protocol:
    * ``tier`` is mandatory and non-defaultable — a default would silently mark Tier 2
      data as Tier 1 and defeat the Constitution §0.4 barrier at its origin.
    * There is no ``snapshot_id``. A snapshot hash is computed over its records, so a
      record cannot reference the snapshot containing it. Direction is manifest → record.
    * Concentrations are ``Quantity``, never bare floats.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from .enums import (
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

__all__ = [
    "AssayMetadata",
    "ExtractionMetadata",
    "ProvenanceRecord",
    "PublicationMetadata",
    "Quantity",
    "SourceMetadata",
    "SpanAnchor",
]

SCHEMA_VERSION = "1.0.0"
"""Provenance schema version.

A schema change produces a new version; records are never edited in place (SI9).
The version is serialized with every record so that a snapshot remains interpretable
after the schema evolves.
"""


@dataclass(frozen=True, slots=True)
class Quantity:
    """A physical quantity with an explicit unit.

    Attributes:
        value: Magnitude as :class:`~decimal.Decimal`. Decimal rather than float so
            that serialization is byte-reproducible; float repr varies across
            platforms and would make snapshot hashes non-deterministic.
        unit: The unit the magnitude is expressed in.
    """

    value: Decimal
    unit: Unit


@dataclass(frozen=True, slots=True)
class SpanAnchor:
    """Locator identifying where in a source a value appears.

    Required for literature-derived records. The SCI0-006b verification gate treats an
    unanchored or unverified extraction as discardable rather than low-confidence: a
    fabricated value carrying a genuine DOI is harder to detect than a missing one.

    Attributes:
        locator_type: Kind of location (table, assay section, free text).
        locator_id: Identifier of the table, figure or section within the source.
        row_or_line: Row or line within the locator, where applicable.
        verified: Whether the value was confirmed against the source span.
    """

    locator_type: LocatorType
    locator_id: str
    row_or_line: str | None
    verified: bool


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    """Origin of a record in the public scientific record.

    Attributes:
        source_type: Public source (ADR-0003 §2 accepted list).
        accession: Source-native identifier for the record.
        source_version: Version or release of the source consulted.
        downloaded_utc: Timezone-aware UTC retrieval timestamp.
        license: Licence under which the content is available.
        tdm_permission: Whether text-and-data-mining permission applies. ``None``
            where not applicable (database sources).
        tier: Scope tier of the target. Mandatory and non-defaultable
            (Constitution §0.1, §0.4).
    """

    source_type: SourceType
    accession: str
    source_version: str
    downloaded_utc: datetime
    license: LicenseType
    tdm_permission: bool | None
    tier: Tier


@dataclass(frozen=True, slots=True)
class PublicationMetadata:
    """Bibliographic identity of the primary publication, where one exists.

    All fields are nullable: database records may lack a primary citation, and an
    absent identifier is recorded as ``None`` rather than inferred (CLAUDE.md §1).
    """

    doi: str | None
    pmid: str | None
    pmcid: str | None
    journal: str | None
    publication_year: int | None


@dataclass(frozen=True, slots=True)
class AssayMetadata:
    """Experimental context of a measurement.

    Attributes:
        assay_id: Source-native assay identifier.
        assay_description: Free-text assay description as reported.
        organism: Source organism of the protein construct.
        target: Target protein name as reported.
        isoform: Isoform designation (for example ``p110alpha``).
        construct: Construct description as reported. Structured normalization is
            SCI0-007; this field records what the source stated.
        atp_concentration: Assay ATP concentration. ``None`` where unreported, in
            which case the record cannot be normalized by Cheng-Prusoff (SCI0-008)
            and is excluded from primary targets (Constitution §2.3(2)).
        measurement_type: Quantity reported.
        measurement_class: Biochemical or cellular. Carried structurally so
            Constitution §2.3(3) is enforceable at the type level.
    """

    assay_id: str | None
    assay_description: str | None
    organism: str | None
    target: str
    isoform: str | None
    construct: str | None
    atp_concentration: Quantity | None
    measurement_type: MeasurementType
    measurement_class: MeasurementClass


@dataclass(frozen=True, slots=True)
class ExtractionMetadata:
    """How the record entered this platform.

    Attributes:
        curator_version: Version of the curation ruleset applied.
        pipeline_version: Version of the extraction pipeline that produced the record.
        extraction_tier: Where in the publication the value was found. ``None`` for
            database-sourced records.
        span_anchor: Locator for literature-derived values. ``None`` for database
            sources; required and verified for literature sources.
        source_confidence: The source's own curation annotation, not a computed score.
    """

    curator_version: str
    pipeline_version: str
    extraction_tier: ExtractionTier | None
    span_anchor: SpanAnchor | None
    source_confidence: SourceConfidence


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    """Complete provenance for one scientific record.

    Every activity measurement references exactly one of these. A record without
    complete provenance may not exist in the platform (Constitution §3.3), and an
    output lacking provenance is deleted rather than archived (ENG §7).

    Attributes:
        provenance_id: Globally unique identifier for this provenance record.
        source: Where the record came from.
        publication: Primary citation, where one exists.
        assay: Experimental context of the measurement.
        extraction: How the record entered the platform.
    """

    provenance_id: UUID
    source: SourceMetadata
    publication: PublicationMetadata | None
    assay: AssayMetadata
    extraction: ExtractionMetadata

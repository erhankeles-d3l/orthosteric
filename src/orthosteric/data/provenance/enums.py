"""Typed enumerations for the provenance schema.

Objective: SCI0-003.
Owner: Constitution §3.3 (provenance), §0.4 (tier), §2.3(2) (assay metadata).

Scientific rationale:
    Every value in the provenance record is drawn from a closed vocabulary so that
    unknown data is represented explicitly rather than guessed. No member of any
    enumeration here may be inferred from context (CLAUDE.md §1).

Downstream dependencies:
    SCI0-004 (activity schema) consumes ``MeasurementType`` and ``MeasurementClass``.
    SCI0-006 (connectors) assigns ``Tier`` at ingestion.
    SCI0-006b (literature mining) assigns ``ExtractionTier`` and ``LocatorType``.
    SCI0-010 (confidence scoring) consumes ``SourceConfidence`` and ``ExtractionTier``.
"""

from __future__ import annotations

from enum import StrEnum, unique

__all__ = [
    "ExtractionTier",
    "LicenseType",
    "LocatorType",
    "MeasurementClass",
    "MeasurementType",
    "SourceConfidence",
    "SourceType",
    "Tier",
    "Unit",
]


@unique
class SourceType(StrEnum):
    """Public source from which a record originates (ADR-0003 §2)."""

    CHEMBL = "ChEMBL"
    BINDINGDB = "BindingDB"
    PUBCHEM = "PubChem"
    PDB = "PDB"
    UNIPROT = "UniProt"
    LITERATURE = "Literature"


@unique
class Tier(StrEnum):
    """Scope tier of the target a record concerns (Constitution §0.1).

    Assigned at ingestion, never defaulted. ``TIER_2`` records are subject to the
    information barrier of Constitution §0.4 and must never reach a training path.
    """

    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


@unique
class MeasurementType(StrEnum):
    """Quantity a measurement reports."""

    IC50 = "IC50"
    KI = "Ki"
    KD = "Kd"
    EC50 = "EC50"


@unique
class MeasurementClass(StrEnum):
    """Assay class of a measurement.

    Carried structurally so that Constitution §2.3(3) — biochemical and cellular
    selectivity are separate targets, never pooled — is enforceable by the schema
    rather than by convention.
    """

    BIOCHEMICAL = "biochemical"
    CELLULAR = "cellular"


@unique
class ExtractionTier(StrEnum):
    """Location within a publication from which a value was extracted.

    Ordered by descending reliability. Recorded per record because table-derived and
    free-text-derived values have materially different error rates, which SCI0-010
    weights.
    """

    SUPPLEMENTARY_TABLE = "supplementary_table"
    MANUSCRIPT_TABLE = "manuscript_table"
    ASSAY_SECTION = "assay_section"
    FREE_TEXT = "free_text"


@unique
class LocatorType(StrEnum):
    """Kind of anchor identifying where in a source a value appears."""

    SUPPLEMENTARY_TABLE = "supplementary_table"
    MANUSCRIPT_TABLE = "manuscript_table"
    ASSAY_SECTION = "assay_section"
    FREE_TEXT = "free_text"


@unique
class SourceConfidence(StrEnum):
    """The source's own curation annotation.

    This is a provenance *fact* about what the source asserted. It is distinct from
    the decomposed confidence score computed at SCI0-010, which is derived rather
    than recorded.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNANNOTATED = "unannotated"


@unique
class LicenseType(StrEnum):
    """Licence under which the source content is made available."""

    CC_BY = "CC-BY"
    CC_BY_SA = "CC-BY-SA"
    CC0 = "CC0"
    PUBLIC_DOMAIN = "public-domain"
    DATABASE_LICENSE = "database-license"
    UNKNOWN = "unknown"


@unique
class Unit(StrEnum):
    """Concentration unit.

    A bare float is prohibited for concentrations: 10 uM and 10 mM differ by three
    orders of magnitude and both occur in the literature.
    """

    MOLAR = "M"
    MILLIMOLAR = "mM"
    MICROMOLAR = "uM"
    NANOMOLAR = "nM"
    PICOMOLAR = "pM"

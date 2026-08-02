"""Shared fixtures for provenance tests (SCI0-003)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from orthosteric.data.provenance import (
    AssayMetadata,
    ExtractionMetadata,
    ExtractionTier,
    LicenseType,
    LocatorType,
    MeasurementClass,
    MeasurementType,
    ProvenanceRecord,
    PublicationMetadata,
    Quantity,
    SourceConfidence,
    SourceMetadata,
    SourceType,
    SpanAnchor,
    Tier,
    Unit,
)

FIXED_UUID = UUID("12345678-1234-5678-1234-567812345678")
FIXED_TS = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def source() -> SourceMetadata:
    """A Tier 1 ChEMBL source record."""
    return SourceMetadata(
        source_type=SourceType.CHEMBL,
        accession="CHEMBL123456",
        source_version="35",
        downloaded_utc=FIXED_TS,
        license=LicenseType.CC_BY_SA,
        tdm_permission=None,
        tier=Tier.TIER_1,
    )


@pytest.fixture
def publication() -> PublicationMetadata:
    """A fully populated publication record."""
    return PublicationMetadata(
        doi="10.1000/example",
        pmid="12345678",
        pmcid=None,
        journal="J. Med. Chem.",
        publication_year=2013,
    )


@pytest.fixture
def assay() -> AssayMetadata:
    """A biochemical assay with recorded ATP concentration."""
    return AssayMetadata(
        assay_id="CHEMBL_ASSAY_1",
        assay_description="radiometric kinase assay",
        organism="Homo sapiens",
        target="PI3K p110alpha",
        isoform="p110alpha",
        construct="p110alpha/p85alpha heterodimer",
        atp_concentration=Quantity(value=Decimal("10"), unit=Unit.MICROMOLAR),
        measurement_type=MeasurementType.IC50,
        measurement_class=MeasurementClass.BIOCHEMICAL,
    )


@pytest.fixture
def extraction() -> ExtractionMetadata:
    """Database-sourced extraction metadata (no span anchor)."""
    return ExtractionMetadata(
        curator_version="curation-1.0.0",
        pipeline_version="pipeline-1.0.0",
        extraction_tier=None,
        span_anchor=None,
        source_confidence=SourceConfidence.HIGH,
    )


@pytest.fixture
def record(
    source: SourceMetadata,
    publication: PublicationMetadata,
    assay: AssayMetadata,
    extraction: ExtractionMetadata,
) -> ProvenanceRecord:
    """A complete, valid database-sourced provenance record."""
    return ProvenanceRecord(
        provenance_id=FIXED_UUID,
        source=source,
        publication=publication,
        assay=assay,
        extraction=extraction,
    )


@pytest.fixture
def verified_anchor() -> SpanAnchor:
    """A verified supplementary-table anchor."""
    return SpanAnchor(
        locator_type=LocatorType.SUPPLEMENTARY_TABLE,
        locator_id="Table S3",
        row_or_line="14",
        verified=True,
    )


@pytest.fixture
def literature_source() -> SourceMetadata:
    """A literature source record."""
    return SourceMetadata(
        source_type=SourceType.LITERATURE,
        accession="10.1000/example",
        source_version="pmc-oa-2026-07",
        downloaded_utc=FIXED_TS,
        license=LicenseType.CC_BY,
        tdm_permission=True,
        tier=Tier.TIER_1,
    )


@pytest.fixture
def literature_extraction(verified_anchor: SpanAnchor) -> ExtractionMetadata:
    """Literature extraction metadata with a verified anchor."""
    return ExtractionMetadata(
        curator_version="curation-1.0.0",
        pipeline_version="pipeline-1.0.0",
        extraction_tier=ExtractionTier.SUPPLEMENTARY_TABLE,
        span_anchor=verified_anchor,
        source_confidence=SourceConfidence.UNANNOTATED,
    )

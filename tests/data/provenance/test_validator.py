"""Structural validation tests (SCI0-003)."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from orthosteric.data.provenance import (
    ExtractionMetadata,
    ProvenanceRecord,
    ProvenanceValidationError,
    Quantity,
    SourceMetadata,
    SpanAnchor,
    Unit,
    validate_provenance,
)


def test_valid_record_passes(record: ProvenanceRecord) -> None:
    """A well-formed record validates silently."""
    validate_provenance(record)


def test_naive_timestamp_rejected(record: ProvenanceRecord) -> None:
    """Timestamps must be timezone-aware."""
    bad = dataclasses.replace(record.source, downloaded_utc=datetime(2026, 1, 1))  # noqa: DTZ001
    with pytest.raises(ProvenanceValidationError, match="timezone-aware"):
        validate_provenance(dataclasses.replace(record, source=bad))


def test_non_utc_timestamp_rejected(record: ProvenanceRecord) -> None:
    """Timestamps must carry a +00:00 offset, not a local one."""
    tz = timezone(timedelta(hours=3))
    bad = dataclasses.replace(record.source, downloaded_utc=datetime(2026, 1, 1, tzinfo=tz))
    with pytest.raises(ProvenanceValidationError, match="UTC"):
        validate_provenance(dataclasses.replace(record, source=bad))


def test_empty_accession_rejected(record: ProvenanceRecord) -> None:
    """An accession must identify something."""
    bad = dataclasses.replace(record.source, accession="   ")
    with pytest.raises(ProvenanceValidationError, match="accession"):
        validate_provenance(dataclasses.replace(record, source=bad))


def test_negative_atp_rejected(record: ProvenanceRecord) -> None:
    """A concentration cannot be negative."""
    bad = dataclasses.replace(
        record.assay, atp_concentration=Quantity(Decimal("-1"), Unit.MICROMOLAR)
    )
    with pytest.raises(ProvenanceValidationError, match="non-negative"):
        validate_provenance(dataclasses.replace(record, assay=bad))


def test_absent_atp_is_permitted(record: ProvenanceRecord) -> None:
    """Missing ATP concentration is valid but excludes the record from primary targets.

    Constitution §2.3(2): unreported [ATP] means the record cannot be normalized by
    Cheng-Prusoff. That is a downstream admissibility question, not a structural defect.
    """
    validate_provenance(
        dataclasses.replace(record, assay=dataclasses.replace(record.assay, atp_concentration=None))
    )


def test_literature_requires_span_anchor(
    record: ProvenanceRecord,
    literature_source: SourceMetadata,
    extraction: ExtractionMetadata,
) -> None:
    """A literature record without an anchor is rejected (SCI0-006b gate)."""
    bad = dataclasses.replace(record, source=literature_source, extraction=extraction)
    with pytest.raises(ProvenanceValidationError, match="span_anchor"):
        validate_provenance(bad)


def test_unverified_span_anchor_rejected(
    record: ProvenanceRecord,
    literature_source: SourceMetadata,
    literature_extraction: ExtractionMetadata,
) -> None:
    """Unverified extractions are discarded, not retained at low confidence.

    A fabricated value carrying a genuine DOI is harder to detect than a missing one.
    """
    anchor: SpanAnchor = literature_extraction.span_anchor  # type: ignore[assignment]
    unverified = dataclasses.replace(
        literature_extraction, span_anchor=dataclasses.replace(anchor, verified=False)
    )
    bad = dataclasses.replace(record, source=literature_source, extraction=unverified)
    with pytest.raises(ProvenanceValidationError, match="span-verified"):
        validate_provenance(bad)


def test_valid_literature_record_passes(
    record: ProvenanceRecord,
    literature_source: SourceMetadata,
    literature_extraction: ExtractionMetadata,
) -> None:
    """A verified literature record validates."""
    validate_provenance(
        dataclasses.replace(record, source=literature_source, extraction=literature_extraction)
    )


def test_all_problems_reported(record: ProvenanceRecord) -> None:
    """Validation reports every problem, not only the first."""
    bad_source = dataclasses.replace(record.source, accession="", source_version="")
    with pytest.raises(ProvenanceValidationError) as exc:
        validate_provenance(dataclasses.replace(record, source=bad_source))
    expected_problems = 2
    assert len(exc.value.problems) == expected_problems

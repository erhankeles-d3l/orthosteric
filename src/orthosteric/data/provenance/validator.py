"""Structural validation of provenance records.

Objective: SCI0-003.
Owner: Constitution §3.3.

Scientific rationale:
    Validation here is *structural only*. It confirms that a record is well formed —
    identifiers parse, timestamps carry an explicit UTC offset, enumerations are
    members, mandatory fields are present. It does not confirm that a DOI resolves,
    that an accession exists, or that a value is scientifically plausible. Asserting
    scientific correctness at ingestion would be inference, which CLAUDE.md §1 forbids.

Downstream dependencies:
    SCI0-006 connectors call :func:`validate_provenance` before a record is admitted.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from .enums import SourceType
from .models import (
    AssayMetadata,
    ExtractionMetadata,
    ProvenanceRecord,
    Quantity,
    SourceMetadata,
    SpanAnchor,
)

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

__all__ = ["ProvenanceValidationError", "validate_provenance"]

_ZERO = timedelta(0)


class ProvenanceValidationError(ValueError):
    """Raised when a provenance record is structurally invalid.

    Attributes:
        problems: Every problem found, so that a caller sees the complete set rather
            than only the first.
    """

    def __init__(self, problems: Sequence[str]) -> None:
        """Initialise with the collected problems."""
        self.problems: tuple[str, ...] = tuple(problems)
        super().__init__("; ".join(problems))


def _check_quantity(q: Quantity | None, label: str, problems: list[str]) -> None:
    if q is None:
        return
    if not q.value.is_finite():
        problems.append(f"{label}: value must be finite")
    if q.value < 0:
        problems.append(f"{label}: value must be non-negative")


def _check_source(source: SourceMetadata, problems: list[str]) -> None:
    if not source.accession.strip():
        problems.append("source.accession: must be non-empty")
    if not source.source_version.strip():
        problems.append("source.source_version: must be non-empty")
    ts = source.downloaded_utc
    if ts.tzinfo is None or ts.utcoffset() is None:
        problems.append("source.downloaded_utc: must be timezone-aware")
    elif ts.utcoffset() != _ZERO:
        problems.append("source.downloaded_utc: must be UTC (offset +00:00)")


def _check_assay(assay: AssayMetadata, problems: list[str]) -> None:
    if not assay.target.strip():
        problems.append("assay.target: must be non-empty")
    _check_quantity(assay.atp_concentration, "assay.atp_concentration", problems)


def _check_extraction(
    extraction: ExtractionMetadata, source: SourceMetadata, problems: list[str]
) -> None:
    if not extraction.curator_version.strip():
        problems.append("extraction.curator_version: must be non-empty")
    if not extraction.pipeline_version.strip():
        problems.append("extraction.pipeline_version: must be non-empty")

    is_literature = source.source_type is SourceType.LITERATURE
    anchor: SpanAnchor | None = extraction.span_anchor

    if is_literature:
        if extraction.extraction_tier is None:
            problems.append("extraction.extraction_tier: required for literature sources")
        if anchor is None:
            problems.append("extraction.span_anchor: required for literature sources")
        elif not anchor.verified:
            problems.append(
                "extraction.span_anchor: literature values must be span-verified "
                "(SCI0-006b gate); unanchored extractions are discarded, not down-weighted"
            )
        elif not anchor.locator_id.strip():
            problems.append("extraction.span_anchor.locator_id: must be non-empty")


def validate_provenance(record: ProvenanceRecord) -> None:
    """Validate a provenance record structurally.

    Args:
        record: The record to validate.

    Raises:
        ProvenanceValidationError: If any structural problem is found. All problems
            are reported together.
    """
    problems: list[str] = []
    _check_source(record.source, problems)
    _check_assay(record.assay, problems)
    _check_extraction(record.extraction, record.source, problems)
    if problems:
        raise ProvenanceValidationError(problems)

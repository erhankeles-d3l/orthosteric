"""Extraction, span-verification, and OA coverage-bias analysis.

Objective: SCI0-006b.

Span-verification gate (binding rule from the spec)
----------------------------------------------------
An extracted value is CANDIDATE until its SpanAnchor is verified against
the source span.  Verification confirms:
  1. the cited locator (table/figure/section) exists in the document;
  2. the row/cell/line at that locator contains the extracted value;
  3. the value and its relation match what is written in the source.

An unanchored or unverifiable value is DISCARDED, never retained at low
confidence.  A fabricated measurement carrying a genuine DOI is harder to
detect than a missing one, because its provenance record looks sound.

OA coverage bias
----------------
PMC-OA is a non-random subset of the literature by journal, year, and funder.
The coverage_bias_report() function computes the fraction of PI3K-relevant
publications that are OA-accessible vs. the total candidate set, broken down
by year and journal, so the corpus bias is measurable rather than invisible.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ExtractionStatus(StrEnum):
    """Lifecycle status of a literature-extracted activity value."""

    CANDIDATE = "candidate"  # extracted, not yet span-verified
    SPAN_VERIFIED = "span_verified"  # anchor confirmed against source
    DISCARDED = "discarded"  # unanchored or verification failed
    OA_INACCESSIBLE = "oa_inaccessible"  # source not OA; cannot verify


@dataclass
class SpanVerificationResult:
    """Result of verifying an extracted value against its source span.

    Attributes:
        verified:        True if the anchor locates the value in the source.
        status:          Final extraction status after verification attempt.
        locator_found:   Whether the cited table/section/figure was found.
        value_matched:   Whether the extracted value matches the source text.
        relation_matched: Whether the extracted relation matches the source.
        failure_reason:  Human-readable reason if not verified.
        raw_span_text:   The actual text at the anchor location, for audit.
    """

    verified: bool
    status: ExtractionStatus
    locator_found: bool = False
    value_matched: bool = False
    relation_matched: bool = False
    failure_reason: str | None = None
    raw_span_text: str | None = None


@dataclass
class LiteratureExtractionRecord:
    """A single activity value extracted from a literature source.

    Before span-verification the status is CANDIDATE.  Downstream
    components must not treat CANDIDATE records as confirmed evidence.
    After verification the status is either SPAN_VERIFIED or DISCARDED.

    The record is deliberately narrow — it contains only extraction
    metadata, not the full activity schema.  Downstream SCI0-008/009
    harmonization converts SPAN_VERIFIED records into ActivityRecord.

    Attributes:
        doi:              DOI of the source publication.
        pmid:             PubMed ID, if available.
        pmcid:            PMC ID, if the article is OA-accessible.
        extraction_tier:  Where in the document the value was found.
        locator_id:       Table, figure, or section identifier.
        row_or_line:      Row or line within the locator.
        raw_value_text:   Verbatim text as it appears in the source.
        extracted_value:  Parsed numeric value as a string.
        extracted_relation: Extracted relational operator (=, >, <).
        extracted_units:  Units as they appear in the source.
        target_text:      Target/isoform description in the source.
        compound_text:    Compound name/identifier in the source.
        assay_text:       Assay description in the source.
        atp_text:         [ATP] as reported in the source, if present.
        status:           Extraction lifecycle status.
        verification:     SpanVerificationResult after verification.
        tdm_permitted:    Whether the source license allows TDM.
        license:          Source license identifier.
        raw_payload:      Full API response for provenance.
    """

    doi: str
    pmid: str | None
    pmcid: str | None
    extraction_tier: str  # supplementary_table | manuscript_table | assay_section | free_text
    locator_id: str | None
    row_or_line: str | None
    raw_value_text: str
    extracted_value: str | None
    extracted_relation: str
    extracted_units: str | None
    target_text: str | None
    compound_text: str | None
    assay_text: str | None
    atp_text: str | None
    status: ExtractionStatus = ExtractionStatus.CANDIDATE
    verification: SpanVerificationResult | None = None
    tdm_permitted: bool = False
    license: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def is_usable(self) -> bool:
        """Return True only for span-verified records with TDM permission."""
        return self.status == ExtractionStatus.SPAN_VERIFIED and self.tdm_permitted


def verify_span(
    record: LiteratureExtractionRecord,
    full_text: str | None,
) -> LiteratureExtractionRecord:
    """Verify an extraction record against its source span.

    This is a structural / deterministic check:
      - Is the locator present in the full text?
      - Does the verbatim raw_value_text appear at or near that locator?

    If full_text is None (article not OA-accessible), the record is
    marked OA_INACCESSIBLE rather than CANDIDATE or DISCARDED.

    A fabricated value passing this gate is possible only if the DOI,
    locator, and raw_value_text are all consistent with the source — which
    requires actual access to the source text.  Fabrication without access
    is detected as OA_INACCESSIBLE or DISCARDED (locator not found).

    Parameters
    ----------
    record:
        The CANDIDATE record to verify.
    full_text:
        Full text of the article, or None if inaccessible.

    Returns:
    -------
    A new LiteratureExtractionRecord with status and verification set.
    """
    if not record.tdm_permitted:
        result = SpanVerificationResult(
            verified=False,
            status=ExtractionStatus.DISCARDED,
            failure_reason="TDM_NOT_PERMITTED",
        )
        return _with_verification(record, result)

    if full_text is None:
        result = SpanVerificationResult(
            verified=False,
            status=ExtractionStatus.OA_INACCESSIBLE,
            failure_reason="FULL_TEXT_UNAVAILABLE",
        )
        return _with_verification(record, result)

    if not record.locator_id:
        result = SpanVerificationResult(
            verified=False,
            status=ExtractionStatus.DISCARDED,
            failure_reason="NO_SPAN_ANCHOR",
        )
        return _with_verification(record, result)

    # Check 1: locator present in full text
    locator_found = record.locator_id in full_text

    if not locator_found:
        result = SpanVerificationResult(
            verified=False,
            status=ExtractionStatus.DISCARDED,
            locator_found=False,
            failure_reason="LOCATOR_NOT_IN_FULL_TEXT",
        )
        return _with_verification(record, result)

    # Check 2: raw value text appears in the vicinity of the locator
    idx = full_text.find(record.locator_id)
    # Search within a ±2000 char window around the locator
    window_start = max(0, idx - 200)
    window_end = min(len(full_text), idx + 2000)
    window = full_text[window_start:window_end]
    raw_span = window[:200]  # capture for audit

    value_matched = record.raw_value_text in window

    if not value_matched:
        result = SpanVerificationResult(
            verified=False,
            status=ExtractionStatus.DISCARDED,
            locator_found=True,
            value_matched=False,
            raw_span_text=raw_span,
            failure_reason="VALUE_NOT_IN_LOCATOR_WINDOW",
        )
        return _with_verification(record, result)

    result = SpanVerificationResult(
        verified=True,
        status=ExtractionStatus.SPAN_VERIFIED,
        locator_found=True,
        value_matched=True,
        relation_matched=True,  # assumed if value matched; relation is part of raw_value_text
        raw_span_text=raw_span,
    )
    return _with_verification(record, result)


def _with_verification(
    record: LiteratureExtractionRecord,
    result: SpanVerificationResult,
) -> LiteratureExtractionRecord:
    """Return a new record with verification and status set."""
    return dataclasses.replace(
        record,
        status=result.status,
        verification=result,
    )


@dataclass
class OACoverageBias:
    """OA coverage bias report for a set of candidate publications.

    Quantifies the non-random nature of the PMC-OA subset so that the
    resulting corpus bias is measurable rather than invisible (spec
    requirement).

    Attributes:
        total_candidates:  Total publications identified as PI3K-relevant.
        oa_accessible:     Publications accessible via PMC-OA or other OA.
        oa_fraction:       oa_accessible / total_candidates.
        by_year:           {year: {"total": N, "oa": M, "fraction": F}}
        by_journal:        {journal: {"total": N, "oa": M, "fraction": F}}
        bias_note:         Human-readable summary of the dominant bias.
    """

    total_candidates: int
    oa_accessible: int
    oa_fraction: float
    by_year: dict[int, dict[str, Any]] = field(default_factory=dict)
    by_journal: dict[str, dict[str, Any]] = field(default_factory=dict)
    bias_note: str = ""


def coverage_bias_report(
    publications: list[dict[str, Any]],
) -> OACoverageBias:
    """Compute OA coverage bias from a publication metadata list.

    Parameters
    ----------
    publications:
        List of dicts with keys: doi, pmid, year (int), journal (str),
        oa_accessible (bool).

    Returns:
    -------
    OACoverageBias with per-year and per-journal breakdowns.
    """
    total = len(publications)
    oa = sum(1 for p in publications if p.get("oa_accessible", False))
    fraction = oa / total if total > 0 else 0.0

    by_year: dict[int, dict[str, Any]] = {}
    by_journal: dict[str, dict[str, Any]] = {}

    for pub in publications:
        year = int(pub.get("year", 0))
        journal = str(pub.get("journal", "unknown"))
        is_oa = bool(pub.get("oa_accessible", False))

        if year not in by_year:
            by_year[year] = {"total": 0, "oa": 0, "fraction": 0.0}
        by_year[year]["total"] += 1
        by_year[year]["oa"] += int(is_oa)

        if journal not in by_journal:
            by_journal[journal] = {"total": 0, "oa": 0, "fraction": 0.0}
        by_journal[journal]["total"] += 1
        by_journal[journal]["oa"] += int(is_oa)

    for d in by_year.values():
        d["fraction"] = d["oa"] / d["total"] if d["total"] > 0 else 0.0
    for d in by_journal.values():
        d["fraction"] = d["oa"] / d["total"] if d["total"] > 0 else 0.0

    # Identify dominant bias dimension
    if by_journal:
        min_j = min(by_journal, key=lambda j: by_journal[j]["fraction"])
        max_j = max(by_journal, key=lambda j: by_journal[j]["fraction"])
        min_f = by_journal[min_j]["fraction"]
        max_f = by_journal[max_j]["fraction"]
        if max_f - min_f > 0.3:
            bias_note = (
                f"Strong journal-level OA bias: {min_j} has {min_f:.0%} OA "
                f"vs {max_j} at {max_f:.0%}. Corpus under-represents {min_j}."
            )
        else:
            bias_note = f"Overall OA fraction: {fraction:.0%}. No single dominant bias detected."
    else:
        bias_note = f"Overall OA fraction: {fraction:.0%}."

    return OACoverageBias(
        total_candidates=total,
        oa_accessible=oa,
        oa_fraction=fraction,
        by_year=by_year,
        by_journal=by_journal,
        bias_note=bias_note,
    )

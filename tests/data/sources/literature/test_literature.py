"""SCI0-006b exit-criterion tests.

Exit criteria (spec):
1. Every extracted value resolves to a source span.
2. Unanchored extractions are rejected (not retained at low confidence).
3. OA coverage fraction and audit error rate reported.
4. TDM-not-permitted sources are not processed.
5. Span-verification is deterministic.
"""

from __future__ import annotations

from typing import Any

from orthosteric.data.sources.literature._crossref import (
    _TDM_PERMITTED_LICENSES,
    CrossRefConnector,
    _parse_crossref_work,
)
from orthosteric.data.sources.literature._extractor import (
    ExtractionStatus,
    LiteratureExtractionRecord,
    OACoverageBias,
    coverage_bias_report,
    verify_span,
)

# ── Span-verification gate (exit criteria 1 & 2) ─────────────────────────────


def _candidate(
    raw_value_text: str = "100 nM",
    locator_id: str | None = "Table1",
    tdm_permitted: bool = True,
    doi: str = "10.1234/test",
) -> LiteratureExtractionRecord:
    return LiteratureExtractionRecord(
        doi=doi,
        pmid=None,
        pmcid="PMC1234567",
        extraction_tier="manuscript_table",
        locator_id=locator_id,
        row_or_line="3",
        raw_value_text=raw_value_text,
        extracted_value="100",
        extracted_relation="=",
        extracted_units="nM",
        target_text=None,
        compound_text=None,
        assay_text=None,
        atp_text=None,
        status=ExtractionStatus.CANDIDATE,
        tdm_permitted=tdm_permitted,
    )


def test_verified_extraction_with_matching_span() -> None:
    """Exit criterion 1: a valid extraction with locatable span is SPAN_VERIFIED."""
    full_text = "...Table1 contains IC50 values: 100 nM for compound A..."
    rec = _candidate()
    result = verify_span(rec, full_text)
    assert result.status == ExtractionStatus.SPAN_VERIFIED
    assert result.verification is not None
    assert result.verification.verified


def test_unanchored_extraction_is_discarded() -> None:
    """Exit criterion 2: no locator_id → DISCARDED, not retained at low confidence."""
    full_text = "some text with 100 nM but no table reference"
    rec = _candidate(locator_id=None)
    result = verify_span(rec, full_text)
    assert result.status == ExtractionStatus.DISCARDED
    assert result.verification is not None
    assert not result.verification.verified
    assert result.verification.failure_reason == "NO_SPAN_ANCHOR"


def test_value_not_in_locator_window_is_discarded() -> None:
    """Value exists in doc but not near the cited locator → DISCARDED."""
    full_text = "Table1 has some data here. Later in the paper: 100 nM IC50."
    rec = _candidate(raw_value_text="50 nM")  # 50 nM not near Table1
    result = verify_span(rec, full_text)
    assert result.status == ExtractionStatus.DISCARDED
    assert result.verification is not None
    assert not result.verification.value_matched


def test_full_text_unavailable_is_oa_inaccessible() -> None:
    """If full text is None (not OA), record is OA_INACCESSIBLE, not DISCARDED."""
    rec = _candidate()
    result = verify_span(rec, full_text=None)
    assert result.status == ExtractionStatus.OA_INACCESSIBLE
    assert result.verification is not None
    assert result.verification.failure_reason == "FULL_TEXT_UNAVAILABLE"


def test_tdm_not_permitted_is_discarded() -> None:
    """TDM not permitted → DISCARDED immediately, no text search attempted."""
    full_text = "Table1 IC50 = 100 nM compound A"
    rec = _candidate(tdm_permitted=False)
    result = verify_span(rec, full_text)
    assert result.status == ExtractionStatus.DISCARDED
    assert result.verification is not None
    assert result.verification.failure_reason == "TDM_NOT_PERMITTED"


def test_candidate_status_before_verification() -> None:
    rec = _candidate()
    assert rec.status == ExtractionStatus.CANDIDATE
    assert not rec.is_usable()  # CANDIDATE is not usable


def test_span_verified_with_tdm_is_usable() -> None:
    full_text = "Table1: 100 nM IC50 data"
    rec = _candidate()
    verified = verify_span(rec, full_text)
    assert verified.is_usable()


def test_verification_is_deterministic() -> None:
    """Exit criterion 5: same inputs produce identical outputs."""
    full_text = "Table1 shows IC50 = 100 nM"
    rec = _candidate()
    r1 = verify_span(rec, full_text)
    r2 = verify_span(rec, full_text)
    assert r1.status == r2.status
    assert r1.verification is not None
    assert r2.verification is not None
    assert r1.verification.verified == r2.verification.verified


# ── OA coverage bias (exit criterion 3) ──────────────────────────────────────


def test_oa_coverage_bias_basic() -> None:
    """Exit criterion 3: OA fraction and per-journal breakdown computed."""
    publications: list[dict[str, Any]] = [
        {"doi": "10.1/a", "year": 2020, "journal": "JMedChem", "oa_accessible": True},
        {"doi": "10.1/b", "year": 2020, "journal": "JMedChem", "oa_accessible": False},
        {"doi": "10.1/c", "year": 2021, "journal": "ChemBiol", "oa_accessible": True},
        {"doi": "10.1/d", "year": 2021, "journal": "ChemBiol", "oa_accessible": True},
    ]
    report = coverage_bias_report(publications)
    assert isinstance(report, OACoverageBias)
    assert report.total_candidates == 4
    assert report.oa_accessible == 3
    assert abs(report.oa_fraction - 0.75) < 1e-9
    assert 2020 in report.by_year
    assert report.by_year[2020]["total"] == 2
    assert report.by_year[2020]["oa"] == 1
    assert abs(report.by_year[2020]["fraction"] - 0.5) < 1e-9
    assert "JMedChem" in report.by_journal


def test_oa_coverage_bias_empty() -> None:
    report = coverage_bias_report([])
    assert report.total_candidates == 0
    assert report.oa_fraction == 0.0


def test_strong_journal_bias_detected() -> None:
    publications: list[dict[str, Any]] = [
        {"doi": f"10.1/a{i}", "year": 2022, "journal": "OpenJournal", "oa_accessible": True}
        for i in range(10)
    ] + [
        {"doi": f"10.1/b{i}", "year": 2022, "journal": "ClosedJournal", "oa_accessible": False}
        for i in range(10)
    ]
    report = coverage_bias_report(publications)
    assert "bias" in report.bias_note.lower() or "ClosedJournal" in report.bias_note


# ── CrossRef TDM detection ────────────────────────────────────────────────────


def test_cc_by_license_is_tdm_permitted() -> None:
    work: dict[str, Any] = {
        "title": ["PI3K selectivity"],
        "container-title": ["Journal of Med Chem"],
        "published-print": {"date-parts": [[2023]]},
        "author": [],
        "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
    }
    result = _parse_crossref_work("10.1234/test", work)
    assert result.tdm_permitted
    assert result.license_url is not None


def test_restricted_license_is_not_tdm_permitted() -> None:
    work: dict[str, Any] = {
        "title": ["PI3K paper"],
        "container-title": ["Restricted Journal"],
        "published-print": {"date-parts": [[2022]]},
        "author": [],
        "license": [{"URL": "https://www.elsevier.com/restricted-license"}],
    }
    result = _parse_crossref_work("10.5678/test", work)
    assert not result.tdm_permitted


def test_all_tdm_permitted_licenses_recognized() -> None:
    for lic_url in _TDM_PERMITTED_LICENSES:
        work: dict[str, Any] = {
            "title": ["Test"],
            "license": [{"URL": lic_url}],
        }
        result = _parse_crossref_work("10.0/test", work)
        assert result.tdm_permitted, f"License not recognized: {lic_url}"


def test_crossref_connector_implements_interface() -> None:
    conn = CrossRefConnector()
    assert hasattr(conn, "version")
    assert hasattr(conn, "metadata")
    assert hasattr(conn, "lookup_doi")
    assert conn.version() == "crossref-api-v1"
    m = conn.metadata()
    assert "name" in m
    assert m["name"] == "CrossRef"


# ── Extraction tier priority ──────────────────────────────────────────────────


def test_extraction_tier_values() -> None:
    """Extraction tiers follow spec-binding priority order."""
    expected = {
        "supplementary_table",
        "manuscript_table",
        "assay_section",
        "free_text",
    }
    # All four tiers are representable
    for tier in expected:
        rec = _candidate()
        import dataclasses

        r = dataclasses.replace(rec, extraction_tier=tier)
        assert r.extraction_tier == tier


# ── PMC extractor unit tests (no network) ────────────────────────────────────


def test_pmc_extractor_verifies_table_candidates() -> None:
    """Table-extracted candidates are verified inline by extract_activity_candidates."""
    from orthosteric.data.sources.literature._pmc import PMCConnector, PMCFullText

    xml = """<article>
<table-wrap id="Table1">
<tr><td>Compound A</td><td>IC50 = 45 nM</td></tr>
</table-wrap>
</article>"""
    ft = PMCFullText(
        pmcid="PMC9999",
        doi="10.1/test",
        full_text=xml,
        has_supplementary=False,
        license_url="https://creativecommons.org/licenses/by/4.0/",
        tdm_permitted=True,
        raw_payload={},
    )
    connector = PMCConnector()
    records = connector.extract_activity_candidates(ft, doi="10.1/test", pmid="99999")
    # All records should be verified or discarded — none should remain CANDIDATE
    for rec in records:
        assert rec.status != ExtractionStatus.CANDIDATE, (
            f"Record still CANDIDATE after extract_activity_candidates: {rec}"
        )
    # At least one extraction found
    assert len(records) > 0


def test_pmc_no_tdm_returns_empty() -> None:
    """No extraction attempted when TDM is not permitted."""
    from orthosteric.data.sources.literature._pmc import PMCConnector, PMCFullText

    ft = PMCFullText(
        pmcid="PMC9998",
        doi="10.1/restricted",
        full_text="<article><table-wrap id='T1'><tr><td>100 nM</td></tr></table-wrap></article>",
        has_supplementary=False,
        license_url="https://elsevier.com/restricted",
        tdm_permitted=False,
        raw_payload={},
    )
    connector = PMCConnector()
    records = connector.extract_activity_candidates(ft)
    assert len(records) == 0

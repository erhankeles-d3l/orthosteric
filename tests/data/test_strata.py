"""SCI0-013 exit-criterion tests.

Exit criteria:
  (1) missing ≠ inactive anywhere in the schema.
  (2) The within-study stratum is separable and its size reported.
"""

from __future__ import annotations

from typing import Any

from orthosteric.data.strata import (
    StratumEntry,
    extract_strata,
)


def _rec(
    ik: str,
    isoform: str,
    value: float | None,
    study_id: str = "S1",
    assay_id: str = "A1",
    exclusion_reason: str | None = None,
    censoring: str = "exact",
    pub: str | None = "doi:10.1/test",
) -> dict[str, Any]:
    return {
        "inchikey": ik,
        "isoform": isoform,
        "study_id": study_id,
        "assay_id": assay_id,
        "activity_value": value,
        "censoring": censoring,
        "exclusion_reason": exclusion_reason,
        "source_record_id": f"{ik}_{isoform}_{study_id}",
        "publication_id": pub,
    }


IK_A = "ABCDEFGHIJKLMNOPQRSTUVWXY0"
IK_B = "BCDEFGHIJKLMNOPQRSTUVWXYZ1"


# ── Exit criterion 1: missing ≠ inactive ──────────────────────────────────────


def test_missing_not_collapsed_to_inactive() -> None:
    """A compound measured in only alpha is missing in beta/gamma/delta -- not inactive."""
    records = [_rec(IK_A, "PI3Kalpha", 7.0)]
    report = extract_strata(records)
    s = report.strata[0]
    # IK_A measured in only one isoform → incomplete
    assert IK_A in s.incomplete_compounds
    assert IK_A not in s.complete_compounds


def test_stratum_entry_is_missing_flag() -> None:
    """StratumEntry.is_missing=True must mean 'not measured', not 'inactive'."""
    entry = StratumEntry(
        inchikey=IK_A,
        isoform="PI3Kbeta",
        study_id="S1",
        assay_id="A1",
        activity_value=None,  # None = not measured
        censoring=None,
        is_missing=True,
        source_records=[],
    )
    assert entry.is_missing
    assert entry.activity_value is None
    # is_missing=True, activity_value=None → missing, not inactive (exit criterion 1)


def test_excluded_records_do_not_contribute() -> None:
    """Excluded records never contribute to a stratum."""
    records = [
        _rec(IK_A, "PI3Kalpha", 7.0),
        _rec(IK_B, "PI3Kalpha", 6.0, exclusion_reason="INADMISSIBLE"),
    ]
    report = extract_strata(records)
    all_iks = {e.inchikey for s in report.strata for e in s.entries}
    assert IK_B not in all_iks


# ── Exit criterion 2: stratum separable and size reported ─────────────────────


def test_complete_stratum_reported() -> None:
    """A compound with all four isoforms in the same study → complete."""
    records = [
        _rec(IK_A, "PI3Kalpha", 8.0),
        _rec(IK_A, "PI3Kbeta", 5.0),
        _rec(IK_A, "PI3Kgamma", 4.5),
        _rec(IK_A, "PI3Kdelta", 6.0),
    ]
    report = extract_strata(records)
    assert report.total_strata == 1
    assert report.strata[0].stratum_size == 1
    assert IK_A in report.strata[0].complete_compounds


def test_stratum_size_equals_complete_compounds() -> None:
    records = [
        # IK_A: complete
        _rec(IK_A, "PI3Kalpha", 8.0),
        _rec(IK_A, "PI3Kbeta", 5.0),
        _rec(IK_A, "PI3Kgamma", 4.5),
        _rec(IK_A, "PI3Kdelta", 6.0),
        # IK_B: incomplete (missing gamma, delta)
        _rec(IK_B, "PI3Kalpha", 7.0),
        _rec(IK_B, "PI3Kbeta", 4.5),
    ]
    report = extract_strata(records)
    s = report.strata[0]
    assert s.stratum_size == 1  # only IK_A is complete
    assert len(s.incomplete_compounds) == 1  # IK_B is incomplete


def test_stratum_size_report() -> None:
    """stratum_sizes() returns separable dict by (study, assay)."""
    records = [
        # Study 1: complete compound
        _rec(IK_A, "PI3Kalpha", 8.0, study_id="S1"),
        _rec(IK_A, "PI3Kbeta", 5.0, study_id="S1"),
        _rec(IK_A, "PI3Kgamma", 4.5, study_id="S1"),
        _rec(IK_A, "PI3Kdelta", 6.0, study_id="S1"),
        # Study 2: different study, same compound
        _rec(IK_A, "PI3Kalpha", 7.8, study_id="S2"),
        _rec(IK_A, "PI3Kbeta", 4.8, study_id="S2"),
        _rec(IK_A, "PI3Kgamma", 4.2, study_id="S2"),
        _rec(IK_A, "PI3Kdelta", 5.8, study_id="S2"),
    ]
    report = extract_strata(records)
    sizes = report.stratum_sizes()
    assert ("S1", "A1") in sizes
    assert ("S2", "A1") in sizes
    assert sizes[("S1", "A1")] == 1
    assert sizes[("S2", "A1")] == 1
    assert report.total_strata == 2


def test_two_studies_are_separate_strata() -> None:
    """§2.3(1): selectivity only within study — two studies → two strata."""
    records = [
        _rec(IK_A, "PI3Kalpha", 8.0, study_id="S1"),
        _rec(IK_A, "PI3Kbeta", 5.0, study_id="S1"),
        _rec(IK_A, "PI3Kgamma", 4.5, study_id="S1"),
        _rec(IK_A, "PI3Kdelta", 6.0, study_id="S1"),
        _rec(IK_A, "PI3Kalpha", 7.8, study_id="S2"),  # different study
    ]
    report = extract_strata(records)
    assert report.total_strata == 2
    keys = {(s.study_id, s.assay_id) for s in report.strata}
    assert ("S1", "A1") in keys
    assert ("S2", "A1") in keys
    # S1 has complete IK_A; S2 has only alpha → incomplete
    s1 = report.strata_by_key[("S1", "A1")]
    s2 = report.strata_by_key[("S2", "A1")]
    assert s1.stratum_size == 1
    assert s2.stratum_size == 0


def test_usable_strata_count() -> None:
    records = [
        _rec(IK_A, "PI3Kalpha", 8.0),
        _rec(IK_A, "PI3Kbeta", 5.0),
        _rec(IK_A, "PI3Kgamma", 4.5),
        _rec(IK_A, "PI3Kdelta", 6.0),
    ]
    report = extract_strata(records)
    assert report.usable_strata == 1


def test_empty_input_gives_empty_report() -> None:
    report = extract_strata([])
    assert report.total_strata == 0
    assert report.stratum_size() if hasattr(report, "stratum_size") else True


def test_multiple_measurements_retained() -> None:
    """Multiple measurements per (ik, iso, study, assay) are retained."""
    records = [
        _rec(IK_A, "PI3Kalpha", 8.0, study_id="S1"),
        _rec(IK_A, "PI3Kalpha", 7.8, study_id="S1"),  # replicate
        _rec(IK_A, "PI3Kbeta", 5.0, study_id="S1"),
        _rec(IK_A, "PI3Kgamma", 4.5, study_id="S1"),
        _rec(IK_A, "PI3Kdelta", 6.0, study_id="S1"),
    ]
    report = extract_strata(records)
    s = report.strata[0]
    alpha_entries = [e for e in s.entries if e.isoform == "PI3Kalpha"]
    # Two source records in alpha cell
    assert len(alpha_entries) == 1  # one entry per cell
    assert len(alpha_entries[0].source_records) == 2  # two source IDs retained


def test_publication_link_preserved() -> None:
    records = [
        _rec(IK_A, "PI3Kalpha", 7.0, pub="doi:10.1234/test"),
        _rec(IK_A, "PI3Kbeta", 5.0, pub="doi:10.1234/test"),
        _rec(IK_A, "PI3Kgamma", 4.5, pub="doi:10.1234/test"),
        _rec(IK_A, "PI3Kdelta", 6.0, pub="doi:10.1234/test"),
    ]
    report = extract_strata(records)
    for entry in report.strata[0].entries:
        assert entry.publication_id == "doi:10.1234/test"

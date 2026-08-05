"""SCI0-014b exit-criterion tests.

Exit criteria:
  (1) characterize() never modifies records.
  (2) Output is deterministic (same input → same report).
  (3) Outputs cover all required dimensions: isoform stats, scaffold stats,
      connectivity, confidence, publication, missingness, temporal.
  (4) Accepted vs excluded records counted correctly.
  (5) Report is attached to snapshot_sha256.
"""

from __future__ import annotations

from typing import Any

from orthosteric.data.audit import characterize


def _rec(
    ik: str = "IK1",
    iso: str = "PI3Kalpha",
    value: float | None = 7.0,
    excl: str | None = None,
    study: str = "S1",
    assay: str = "A1",
    censoring: str = "exact",
    pub: str | None = "doi:10.1/test",
    scaffold_fid: str | None = "SCAF_AAAA0000001",
    qty: str = "IC50",
    conf_score: float | None = 0.8,
    prov_tier: str = "T1",
    ts: str = "2024-03-01T00:00:00Z",
) -> dict[str, Any]:
    return {
        "inchikey": ik,
        "isoform": iso,
        "activity_value": value,
        "exclusion_reason": excl,
        "study_id": study,
        "assay_id": assay,
        "censoring": censoring,
        "publication_id": pub,
        "scaffold_family_id": scaffold_fid,
        "activity_type": qty,
        "confidence_score": conf_score,
        "provenance_tier": prov_tier,
        "retrieval_timestamp": ts,
    }


# ── Exit criterion 1: never modifies records ──────────────────────────────────


def test_characterize_does_not_modify_records() -> None:
    records = [_rec()]
    original = [dict(r) for r in records]
    characterize(records)
    assert records[0] == original[0]


# ── Exit criterion 2: determinism ─────────────────────────────────────────────


def test_characterize_is_deterministic() -> None:
    records = [
        _rec("IK1", "PI3Kalpha", 8.0),
        _rec("IK1", "PI3Kbeta", 5.0),
        _rec("IK2", "PI3Kalpha", 7.0),
    ]
    r1 = characterize(records, "SHA1")
    r2 = characterize(records, "SHA1")
    assert r1.total_records == r2.total_records
    assert (
        r1.connectivity.largest_connected_component == r2.connectivity.largest_connected_component
    )


# ── Exit criterion 4: accepted / excluded counts ──────────────────────────────


def test_accepted_excluded_counted_correctly() -> None:
    records = [
        _rec("IK1", "PI3Kalpha"),
        _rec("IK2", "PI3Kalpha", excl="INADMISSIBLE"),
    ]
    report = characterize(records)
    assert report.total_records == 2
    assert report.accepted_records == 1
    assert report.excluded_records == 1


def test_empty_records_returns_zero_report() -> None:
    report = characterize([])
    assert report.total_records == 0
    assert report.accepted_records == 0


# ── Exit criterion 5: snapshot SHA attached ───────────────────────────────────


def test_snapshot_sha256_attached() -> None:
    report = characterize([_rec()], snapshot_sha256="abc123")
    assert report.snapshot_sha256 == "abc123"


# ── Isoform stats ─────────────────────────────────────────────────────────────


def test_isoform_stats_all_four_present() -> None:
    records = [
        _rec("IK1", "PI3Kalpha", 8.0),
        _rec("IK1", "PI3Kbeta", 5.0),
    ]
    report = characterize(records)
    isos = {s.isoform for s in report.isoform_stats}
    assert {"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}.issubset(isos)


def test_isoform_stats_median_pactivity() -> None:
    records = [
        _rec("IK1", "PI3Kalpha", 7.0),
        _rec("IK2", "PI3Kalpha", 9.0),
    ]
    report = characterize(records)
    alpha = next(s for s in report.isoform_stats if s.isoform == "PI3Kalpha")
    assert alpha.median_pactivity == 8.0
    assert alpha.n_compounds == 2


def test_censored_records_counted_in_isoform_stats() -> None:
    records = [
        _rec("IK1", "PI3Kalpha", 5.0, censoring="right_censored"),
        _rec("IK2", "PI3Kalpha", 7.0),
    ]
    report = characterize(records)
    assert report.censored_records == 1
    alpha = next(s for s in report.isoform_stats if s.isoform == "PI3Kalpha")
    assert alpha.n_censored == 1
    assert alpha.n_exact == 1


# ── Scaffold stats ────────────────────────────────────────────────────────────


def test_scaffold_stats_families_counted() -> None:
    records = [
        _rec("IK1", scaffold_fid="FAM1"),
        _rec("IK2", scaffold_fid="FAM1"),
        _rec("IK3", scaffold_fid="FAM2"),
        _rec("IK4", scaffold_fid="ACYCLIC"),
    ]
    report = characterize(records)
    assert report.scaffold_stats.n_ring_system_families == 2
    assert report.scaffold_stats.n_acyclic_compounds == 1
    assert report.scaffold_stats.largest_family_size == 2


# ── Connectivity stats ────────────────────────────────────────────────────────


def test_connectivity_delegated_to_graph() -> None:
    records = [
        _rec("IK1", "PI3Kalpha"),
        _rec("IK1", "PI3Kbeta"),
        _rec("IK1", "PI3Kgamma"),
        _rec("IK1", "PI3Kdelta"),
    ]
    report = characterize(records)
    assert report.connectivity.total_compounds == 1
    assert report.connectivity.compounds_all4_isoforms == 1


# ── Publication stats ─────────────────────────────────────────────────────────


def test_publication_stats_counted() -> None:
    records = [
        _rec("IK1", pub="doi:10.1/A"),
        _rec("IK2", pub="doi:10.1/A"),  # same publication
        _rec("IK3", pub="doi:10.1/B"),
        _rec("IK4", pub=None),
    ]
    report = characterize(records)
    assert report.publication_stats.n_publications == 2
    assert report.publication_stats.n_records_with_pub == 3
    assert report.publication_stats.n_records_without_pub == 1
    assert report.publication_stats.largest_publication_record_count == 2


# ── Missingness matrix ────────────────────────────────────────────────────────


def test_missingness_matrix_overlap() -> None:
    records = [
        _rec("IK1", "PI3Kalpha"),
        _rec("IK1", "PI3Kbeta"),
        _rec("IK2", "PI3Kalpha"),
    ]
    report = characterize(records)
    m = report.missingness
    # IK1 has both alpha and beta → overlap[alpha][beta] == 1
    assert m.overlap["PI3Kalpha"]["PI3Kbeta"] == 1
    # IK2 has alpha but not beta → missing[alpha][beta] includes IK2
    assert m.missing_directional["PI3Kalpha"]["PI3Kbeta"] == 1


# ── Temporal counts ───────────────────────────────────────────────────────────


def test_temporal_counts_by_year() -> None:
    records = [
        _rec(ts="2023-01-01T00:00:00Z"),
        _rec(ts="2023-06-01T00:00:00Z"),
        _rec(ts="2024-01-01T00:00:00Z"),
    ]
    report = characterize(records)
    assert report.temporal_counts.get("2023", 0) == 2
    assert report.temporal_counts.get("2024", 0) == 1

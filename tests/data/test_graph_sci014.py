"""SCI0-014 exit-criterion tests for build_graph_stats_from_records().

Exit criteria:
  (1) Largest connected component computed and reproducible.
  (2) Bridging compound count computed and reproducible.
  (3) Study-cluster structure computed and reportable.
  All three must be reproducible (same input → same output on every call).
"""

from __future__ import annotations

from typing import Any

from orthosteric.data.graph import build_graph_stats_from_records


def _r(
    ik: str,
    iso: str,
    study: str = "S1",
    assay: str = "A1",
    excl: str | None = None,
    scaffold: str | None = None,
) -> dict[str, Any]:
    return {
        "inchikey": ik,
        "isoform": iso,
        "study_id": study,
        "assay_id": assay,
        "exclusion_reason": excl,
        "scaffold_family_id": scaffold,
    }


# ── Exit criterion 1: largest connected component ────────────────────────────


def test_empty_records_returns_zero_lcc() -> None:
    stats = build_graph_stats_from_records([])
    assert stats.largest_connected_component == 0


def test_single_compound_lcc_is_1() -> None:
    stats = build_graph_stats_from_records([_r("IK1", "PI3Kalpha")])
    assert stats.largest_connected_component == 1
    assert stats.n_connected_components == 1


def test_two_coassayed_compounds_same_component() -> None:
    """Compounds in the same panel → same component → LCC = 2."""
    records = [
        _r("IK1", "PI3Kalpha", study="S1", assay="A1"),
        _r("IK2", "PI3Kalpha", study="S1", assay="A1"),
    ]
    stats = build_graph_stats_from_records(records)
    assert stats.n_connected_components == 1
    assert stats.largest_connected_component == 2


def test_two_isolated_compounds_two_components() -> None:
    """Compounds in different panels → different components."""
    records = [
        _r("IK1", "PI3Kalpha", study="S1", assay="A1"),
        _r("IK2", "PI3Kalpha", study="S2", assay="A1"),
    ]
    stats = build_graph_stats_from_records(records)
    assert stats.n_connected_components == 2
    assert stats.largest_connected_component == 1


def test_lcc_reproducible() -> None:
    """Exit criterion 1: same input → same LCC every call."""
    records = [
        _r("IK1", "PI3Kalpha", "S1", "A1"),
        _r("IK2", "PI3Kalpha", "S1", "A1"),
        _r("IK3", "PI3Kbeta", "S2", "A1"),
    ]
    s1 = build_graph_stats_from_records(records)
    s2 = build_graph_stats_from_records(records)
    assert s1.largest_connected_component == s2.largest_connected_component
    assert s1.n_connected_components == s2.n_connected_components


def test_bridging_connects_components() -> None:
    """IK1 in both S1 and S2 links them into one component."""
    records = [
        _r("IK1", "PI3Kalpha", "S1", "A1"),
        _r("IK1", "PI3Kbeta", "S2", "A1"),
        _r("IK2", "PI3Kalpha", "S1", "A1"),
        _r("IK3", "PI3Kalpha", "S2", "A1"),
    ]
    stats = build_graph_stats_from_records(records)
    # IK1 bridges S1 and S2 → all three compounds in one component
    assert stats.n_connected_components == 1
    assert stats.largest_connected_component == 3


# ── Exit criterion 2: bridging compounds ─────────────────────────────────────


def test_no_bridging_compounds_when_all_single_study() -> None:
    records = [
        _r("IK1", "PI3Kalpha", "S1"),
        _r("IK2", "PI3Kbeta", "S1"),
    ]
    stats = build_graph_stats_from_records(records)
    assert stats.bridging_compounds == 0


def test_bridging_compound_detected() -> None:
    """IK1 in two panels with 2 distinct isoforms → bridging."""
    records = [
        _r("IK1", "PI3Kalpha", "S1"),
        _r("IK1", "PI3Kbeta", "S2"),  # different study, different isoform
    ]
    stats = build_graph_stats_from_records(records)
    assert stats.bridging_compounds == 1


def test_same_isoform_two_studies_not_bridging() -> None:
    """IK1 in two panels but only 1 isoform total → not a bridging compound."""
    records = [
        _r("IK1", "PI3Kalpha", "S1"),
        _r("IK1", "PI3Kalpha", "S2"),  # same isoform, different study
    ]
    stats = build_graph_stats_from_records(records)
    assert stats.bridging_compounds == 0


def test_bridging_count_reproducible() -> None:
    """Exit criterion 2: same input → same bridging count every call."""
    records = [
        _r("IK1", "PI3Kalpha", "S1"),
        _r("IK1", "PI3Kbeta", "S2"),
        _r("IK2", "PI3Kgamma", "S1"),
    ]
    s1 = build_graph_stats_from_records(records)
    s2 = build_graph_stats_from_records(records)
    assert s1.bridging_compounds == s2.bridging_compounds


# ── Exit criterion 3: study-cluster structure ─────────────────────────────────


def test_cluster_count_equals_distinct_panels() -> None:
    records = [
        _r("IK1", "PI3Kalpha", "S1", "A1"),
        _r("IK1", "PI3Kbeta", "S1", "A2"),  # same study, different assay
        _r("IK2", "PI3Kalpha", "S2", "A1"),
    ]
    stats = build_graph_stats_from_records(records)
    assert stats.n_study_clusters == 3


def test_largest_cluster_size() -> None:
    records = [
        _r("IK1", "PI3Kalpha", "S1"),
        _r("IK2", "PI3Kbeta", "S1"),  # two compounds in S1
        _r("IK3", "PI3Kalpha", "S2"),  # one compound in S2
    ]
    stats = build_graph_stats_from_records(records)
    assert stats.largest_study_cluster == 2


def test_four_isoform_cluster_counted() -> None:
    """Cluster covering all 4 Tier 1 isoforms counted in n_four_isoform_clusters."""
    records = [
        _r("IK1", "PI3Kalpha"),
        _r("IK1", "PI3Kbeta"),
        _r("IK1", "PI3Kgamma"),
        _r("IK1", "PI3Kdelta"),
    ]
    stats = build_graph_stats_from_records(records)
    assert stats.n_four_isoform_clusters == 1
    assert stats.within_study_four_isoform == 1


def test_cluster_structure_reproducible() -> None:
    """Exit criterion 3: same input → same cluster structure every call."""
    records = [
        _r("IK1", "PI3Kalpha", "S1"),
        _r("IK2", "PI3Kalpha", "S1"),
        _r("IK3", "PI3Kbeta", "S2"),
    ]
    s1 = build_graph_stats_from_records(records)
    s2 = build_graph_stats_from_records(records)
    assert s1.n_study_clusters == s2.n_study_clusters
    assert s1.largest_study_cluster == s2.largest_study_cluster
    assert s1.median_study_cluster_size == s2.median_study_cluster_size


# ── Correctness: excluded records ────────────────────────────────────────────


def test_excluded_records_not_counted() -> None:
    records = [
        _r("IK1", "PI3Kalpha"),
        _r("IK2", "PI3Kalpha", excl="INADMISSIBLE"),
    ]
    stats = build_graph_stats_from_records(records)
    assert stats.total_compounds == 1


def test_per_isoform_counts() -> None:
    records = [
        _r("IK1", "PI3Kalpha"),
        _r("IK1", "PI3Kbeta"),
        _r("IK2", "PI3Kalpha"),
    ]
    stats = build_graph_stats_from_records(records)
    assert stats.per_isoform_compounds["PI3Kalpha"] == 2
    assert stats.per_isoform_compounds["PI3Kbeta"] == 1
    assert stats.per_isoform_compounds["PI3Kgamma"] == 0


def test_compounds_all4_isoforms() -> None:
    records = [
        _r("IK1", "PI3Kalpha"),
        _r("IK1", "PI3Kbeta"),
        _r("IK1", "PI3Kgamma"),
        _r("IK1", "PI3Kdelta"),
        _r("IK2", "PI3Kalpha"),
        _r("IK2", "PI3Kbeta"),
    ]
    stats = build_graph_stats_from_records(records)
    assert stats.compounds_all4_isoforms == 1
    assert stats.compounds_ge2_isoforms == 2


def test_scaffold_families_counted() -> None:
    records = [
        _r("IK1", "PI3Kalpha", scaffold="SCAF_AAAA000000001"),
        _r("IK2", "PI3Kalpha", scaffold="SCAF_AAAA000000002"),
        _r("IK3", "PI3Kalpha", scaffold="SCAF_AAAA000000001"),  # same family
    ]
    stats = build_graph_stats_from_records(records)
    assert stats.scaffold_families == 2

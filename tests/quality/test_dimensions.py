"""Per-dimension evaluator tests (GDR-003 §2 rules)."""

from __future__ import annotations

from orthosteric.data.audit import characterize
from orthosteric.data.graph import build_graph_stats_from_records
from orthosteric.data.snapshots import StructuralCoverageStats, freeze_corpus_profile
from orthosteric.quality import (
    GOVERNED_SCAFFOLD_FAMILY_FLOOR,
    ConfidenceEvaluator,
    ConnectivityEvaluator,
    CoverageEvaluator,
    DimensionStatus,
    MissingnessEvaluator,
    PublicationConcentrationEvaluator,
    ScaffoldDiversityEvaluator,
    StructuralCoverageEvaluator,
)
from tests.quality._fixtures import (
    SNAPSHOT_SHA,
    build_profile,
    degenerate_records,
    healthy_records,
    policy,
    sw,
)

# ── Connectivity ──────────────────────────────────────────────────────────────


def test_connectivity_non_degenerate_on_healthy_corpus() -> None:
    profile = build_profile(healthy_records())
    result = ConnectivityEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.NON_DEGENERATE_UNQUANTIFIED
    assert result.dimension == "connectivity"


def test_connectivity_degenerate_when_every_compound_isolated() -> None:
    profile = build_profile(degenerate_records())
    result = ConnectivityEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.STRUCTURALLY_DEGENERATE
    assert "isolated" in result.rationale


def test_connectivity_rationale_never_empty() -> None:
    for records in (healthy_records(), degenerate_records()):
        result = ConnectivityEvaluator().evaluate(build_profile(records))
        assert result.rationale != ""
        assert result.supporting_metrics


# ── Coverage ──────────────────────────────────────────────────────────────────


def test_coverage_non_degenerate_on_healthy_corpus() -> None:
    profile = build_profile(healthy_records())
    result = CoverageEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.NON_DEGENERATE_UNQUANTIFIED


def test_coverage_degenerate_when_isoform_entirely_missing() -> None:
    records = [
        r
        for r in healthy_records()
        if r["isoform"] != "PI3Kdelta"  # remove one isoform entirely
    ]
    profile = build_profile(records)
    result = CoverageEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.STRUCTURALLY_DEGENERATE
    assert "PI3Kdelta" in result.rationale


def test_coverage_degenerate_when_n_w_zero() -> None:
    """No compound complete across all four isoforms -> degenerate, even if
    every isoform individually has some coverage."""
    records: list[dict[str, object]] = [
        {
            "inchikey": f"IK{i}",
            "isoform": iso,
            "study_id": "S1",
            "assay_id": "A1",
            "activity_value": 7.0,
            "censoring": "exact",
            "exclusion_reason": None,
        }
        for i, iso in enumerate(("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"))
    ]  # each isoform measured, but on a DIFFERENT compound -> n_w == 0
    profile = build_profile(records)
    result = CoverageEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.STRUCTURALLY_DEGENERATE
    assert "n_complete_compounds == 0" in result.rationale


# ── Scaffold diversity (the one governed-magnitude dimension) ────────────────


def test_scaffold_diversity_met_on_healthy_corpus() -> None:
    """healthy_records() has 8 distinct scaffold families (== the floor)."""
    profile = build_profile(healthy_records())
    result = ScaffoldDiversityEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.GOVERNED_THRESHOLD_MET
    assert str(GOVERNED_SCAFFOLD_FAMILY_FLOOR) in result.rationale
    assert "CAVEAT" in result.rationale  # component-restricted count unavailable


def test_scaffold_diversity_not_met_below_floor() -> None:
    records = [r for r in healthy_records() if r["inchikey"] in ("IK0", "IK1")]
    profile = build_profile(records)
    result = ScaffoldDiversityEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.GOVERNED_THRESHOLD_NOT_MET


def test_scaffold_diversity_cites_governed_floor_not_invented() -> None:
    profile = build_profile(healthy_records())
    result = ScaffoldDiversityEvaluator().evaluate(profile)
    assert result.supporting_metrics["governed_floor"] == 8
    assert result.supporting_metrics["scaffold_families_in_largest_component"] is None


# ── Publication concentration ────────────────────────────────────────────────


def test_publication_concentration_non_degenerate_with_two_sources() -> None:
    profile = build_profile(healthy_records())
    result = PublicationConcentrationEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.NON_DEGENERATE_UNQUANTIFIED


def test_publication_concentration_warning_single_source() -> None:
    profile = build_profile(degenerate_records())
    result = PublicationConcentrationEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.WARNING
    assert "one publication" in result.rationale


def test_publication_concentration_insufficient_data_when_none() -> None:
    records = [{**r, "publication_id": None} for r in degenerate_records()]
    profile = build_profile(records)
    result = PublicationConcentrationEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.INSUFFICIENT_DATA


# ── Confidence ────────────────────────────────────────────────────────────────


def test_confidence_non_degenerate_when_scores_present() -> None:
    profile = build_profile(healthy_records())
    result = ConfidenceEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.NON_DEGENERATE_UNQUANTIFIED
    assert result.supporting_metrics["mean_confidence"] is not None


def test_confidence_insufficient_data_when_absent() -> None:
    profile = build_profile(degenerate_records())  # conf=None throughout
    result = ConfidenceEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.INSUFFICIENT_DATA


# ── Missingness ───────────────────────────────────────────────────────────────


def test_missingness_non_degenerate_on_healthy_corpus() -> None:
    profile = build_profile(healthy_records())
    result = MissingnessEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.NON_DEGENERATE_UNQUANTIFIED


def test_missingness_degenerate_when_no_isoform_pair_co_measured() -> None:
    profile = build_profile(degenerate_records())
    result = MissingnessEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.STRUCTURALLY_DEGENERATE


# ── Structural coverage (extension-point stub) ────────────────────────────────


def test_structural_coverage_always_not_yet_available() -> None:
    profile = build_profile(healthy_records())
    result = StructuralCoverageEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.NOT_YET_AVAILABLE


def test_structural_coverage_never_fabricates_when_field_present() -> None:
    """Even if a future caller supplies structural_coverage, this evaluator
    does not itself interpret it (ADR-0009 says implementation comes later)."""
    records = healthy_records()
    gs = build_graph_stats_from_records(records)
    report = characterize(records, snapshot_sha256=SNAPSHOT_SHA)
    profile = freeze_corpus_profile(
        SNAPSHOT_SHA,
        gs,
        report,
        sw(),
        policy(),
        None,
        structural_coverage=StructuralCoverageStats(experimental_pdb_coverage=4),
    )
    result = StructuralCoverageEvaluator().evaluate(profile)
    assert result.status == DimensionStatus.NOT_YET_AVAILABLE
    assert result.supporting_metrics["structural_coverage_present"] is True

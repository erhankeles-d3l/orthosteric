"""CorpusQualityGatePolicy: GDR-003 §4 aggregation rule, firewall, traceability."""

from __future__ import annotations

import inspect

from orthosteric.policy import CorpusQualityGatePolicy, GateStatus
from orthosteric.quality import CorpusQualityAssessment, CorpusQualityAssessor, default_evaluators
from tests.quality._fixtures import build_profile, degenerate_records, healthy_records


def _assess(records: list[dict[str, object]]) -> CorpusQualityAssessment:
    assessor = CorpusQualityAssessor(default_evaluators())
    return assessor.assess(build_profile(records))


def test_healthy_corpus_yields_proceed_or_warning_never_stop_or_redesign() -> None:
    """healthy_records() has no STRUCTURALLY_DEGENERATE or GOVERNED_THRESHOLD_
    NOT_MET dimension; structural_coverage is always NOT_YET_AVAILABLE, so the
    floor outcome is WARNING, not PROCEED, until that dimension has real data."""
    assessment = _assess(healthy_records())
    decision = CorpusQualityGatePolicy().evaluate(assessment)
    assert decision.status in (GateStatus.PROCEED, GateStatus.WARNING)


def test_structural_coverage_not_yet_available_forces_at_least_warning() -> None:
    """Fail-closed: NOT_YET_AVAILABLE never silently contributes to PROCEED."""
    assessment = _assess(healthy_records())
    decision = CorpusQualityGatePolicy().evaluate(assessment)
    assert decision.status == GateStatus.WARNING
    assert "structural_coverage" in decision.rationale


def test_degenerate_corpus_yields_stop() -> None:
    assessment = _assess(degenerate_records())
    decision = CorpusQualityGatePolicy().evaluate(assessment)
    assert decision.status == GateStatus.STOP
    assert "STRUCTURALLY_DEGENERATE" in decision.rationale


def test_below_scaffold_floor_yields_redesign_not_stop() -> None:
    """A GOVERNED_THRESHOLD_NOT_MET dimension without any STRUCTURALLY_
    DEGENERATE dimension present yields REDESIGN, distinct from STOP."""
    records = [r for r in healthy_records() if r["inchikey"] in ("IK0", "IK1")]
    assessment = _assess(records)
    decision = CorpusQualityGatePolicy().evaluate(assessment)
    assert decision.status == GateStatus.REDESIGN
    assert "GOVERNED_THRESHOLD_NOT_MET" in decision.rationale


def test_stop_takes_priority_over_redesign() -> None:
    """A corpus failing BOTH the degenerate and governed-threshold checks
    must report STOP, the more severe outcome, per the GDR-003 §4 rule order."""
    assessment = _assess(degenerate_records())  # also fails scaffold floor
    decision = CorpusQualityGatePolicy().evaluate(assessment)
    assert decision.status == GateStatus.STOP


# ── Traceability ─────────────────────────────────────────────────────────────


def test_decision_references_assessment_content_hash() -> None:
    assessment = _assess(healthy_records())
    decision = CorpusQualityGatePolicy().evaluate(assessment)
    assert decision.assessment_content_sha256 == assessment.assessment_content_sha256


def test_dimension_summary_includes_every_dimension() -> None:
    assessment = _assess(healthy_records())
    decision = CorpusQualityGatePolicy().evaluate(assessment)
    assert set(decision.dimension_summary) == {d.dimension for d in assessment.dimensions}


def test_full_traceability_chain_decision_to_snapshot() -> None:
    """Decision -> Assessment -> Profile -> Snapshot, per the instruction's
    'maintain complete backward traceability' requirement."""
    profile = build_profile(healthy_records())
    assessor = CorpusQualityAssessor(default_evaluators())
    assessment = assessor.assess(profile)
    decision = CorpusQualityGatePolicy().evaluate(assessment)
    assert decision.assessment_content_sha256 == assessment.assessment_content_sha256
    assert assessment.profile_sha256 == profile.profile_sha256


# ── Criterion firewall ────────────────────────────────────────────────────────


def test_gate_decision_never_criterion_eligible() -> None:
    assessment = _assess(healthy_records())
    decision = CorpusQualityGatePolicy().evaluate(assessment)
    assert decision.criterion_eligible is False


def test_gate_policy_computes_no_statistics_itself() -> None:
    """The policy's evaluate() signature accepts only a CorpusQualityAssessment
    -- no raw records, no CorpusProfile, no GraphStats."""
    params = inspect.signature(CorpusQualityGatePolicy.evaluate).parameters
    assert "assessment" in params
    assert "records" not in params
    assert "profile" not in params


# ── Determinism ───────────────────────────────────────────────────────────────


def test_same_assessment_same_decision() -> None:
    assessment = _assess(healthy_records())
    policy = CorpusQualityGatePolicy()
    d1 = policy.evaluate(assessment)
    d2 = policy.evaluate(assessment)
    assert d1.to_dict() == d2.to_dict()

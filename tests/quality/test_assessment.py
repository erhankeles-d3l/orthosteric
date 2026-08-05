"""CorpusQualityAssessor: determinism, immutability, traceability, extensibility."""

from __future__ import annotations

import json

import pytest

from orthosteric.quality import (
    ASSESSMENT_ALGORITHM_VERSION,
    ConnectivityEvaluator,
    CorpusQualityAssessor,
    DimensionAssessment,
    DimensionStatus,
    QualityDimensionEvaluator,
    default_evaluators,
)
from tests.quality._fixtures import build_profile, degenerate_records, healthy_records


def test_default_evaluators_cover_all_named_dimensions() -> None:
    assessor = CorpusQualityAssessor(default_evaluators())
    names = set(assessor.registered_dimensions)
    assert names == {
        "connectivity",
        "coverage",
        "scaffold_diversity",
        "publication_concentration",
        "confidence",
        "missingness",
        "structural_coverage",
    }


def test_assess_produces_one_dimension_assessment_per_evaluator() -> None:
    assessor = CorpusQualityAssessor(default_evaluators())
    profile = build_profile(healthy_records())
    assessment = assessor.assess(profile)
    assert len(assessment.dimensions) == 7


def test_assessment_profile_sha256_matches_source_profile() -> None:
    assessor = CorpusQualityAssessor(default_evaluators())
    profile = build_profile(healthy_records())
    assessment = assessor.assess(profile)
    assert assessment.profile_sha256 == profile.profile_sha256


# ── Determinism ───────────────────────────────────────────────────────────────


def test_same_profile_same_content_hash() -> None:
    assessor = CorpusQualityAssessor(default_evaluators())
    profile = build_profile(healthy_records())
    a1 = assessor.assess(profile)
    a2 = assessor.assess(profile)
    assert a1.assessment_content_sha256 == a2.assessment_content_sha256


def test_assessed_at_utc_excluded_from_hash() -> None:
    assessor = CorpusQualityAssessor(default_evaluators())
    profile = build_profile(healthy_records())
    a1 = assessor.assess(profile)
    a2 = assessor.assess(profile)
    assert a1.assessment_content_sha256 == a2.assessment_content_sha256
    assert a1.assessed_at_utc != ""


def test_different_profile_different_content_hash() -> None:
    assessor = CorpusQualityAssessor(default_evaluators())
    a1 = assessor.assess(build_profile(healthy_records()))
    a2 = assessor.assess(build_profile(degenerate_records()))
    assert a1.assessment_content_sha256 != a2.assessment_content_sha256


def test_algorithm_version_pinned() -> None:
    assert ASSESSMENT_ALGORITHM_VERSION == "corpus_quality_rules_v1_gdr003"


# ── Immutability ──────────────────────────────────────────────────────────────


def test_assessment_is_frozen() -> None:
    assessor = CorpusQualityAssessor(default_evaluators())
    assessment = assessor.assess(build_profile(healthy_records()))
    with pytest.raises((AttributeError, TypeError)):
        assessment.assessment_content_sha256 = "tampered"  # type: ignore[misc]


def test_dimension_assessment_is_frozen() -> None:
    assessor = CorpusQualityAssessor(default_evaluators())
    assessment = assessor.assess(build_profile(healthy_records()))
    with pytest.raises((AttributeError, TypeError)):
        assessment.dimensions[0].status = DimensionStatus.WARNING  # type: ignore[misc]


# ── Traceability ─────────────────────────────────────────────────────────────


def test_dimension_lookup_by_name() -> None:
    assessor = CorpusQualityAssessor(default_evaluators())
    assessment = assessor.assess(build_profile(healthy_records()))
    found = assessment.dimension("connectivity")
    assert found is not None
    assert found.dimension == "connectivity"
    assert assessment.dimension("nonexistent") is None


def test_to_dict_is_json_serializable() -> None:
    assessor = CorpusQualityAssessor(default_evaluators())
    assessment = assessor.assess(build_profile(healthy_records()))
    d = json.loads(json.dumps(assessment.to_dict()))
    assert d["assessment_content_sha256"] == assessment.assessment_content_sha256
    assert len(d["dimensions"]) == 7


# ── Extensibility ─────────────────────────────────────────────────────────────


class _CustomDimension(QualityDimensionEvaluator):
    """A new dimension added without modifying any existing evaluator or the
    assessor itself (ADR-0009 §3)."""

    @property
    def dimension_name(self) -> str:
        return "mutation_coverage_demo"

    def evaluate(self, profile: object) -> DimensionAssessment:  # noqa: ARG002
        return DimensionAssessment(
            dimension=self.dimension_name,
            status=DimensionStatus.NOT_YET_AVAILABLE,
            rationale="Demonstration extension dimension.",
            supporting_metrics={},
            provenance="none (demo)",
        )


def test_new_dimension_requires_no_change_to_existing_evaluators() -> None:
    assessor = CorpusQualityAssessor([ConnectivityEvaluator(), _CustomDimension()])
    assessment = assessor.assess(build_profile(healthy_records()))
    assert assessment.dimension("mutation_coverage_demo") is not None
    assert assessment.dimension("connectivity") is not None


def test_assessor_rejects_duplicate_dimension_names() -> None:
    with pytest.raises(ValueError, match="Duplicate dimension_name"):
        CorpusQualityAssessor([ConnectivityEvaluator(), ConnectivityEvaluator()])


def test_assessor_rejects_empty_evaluator_set() -> None:
    with pytest.raises(ValueError, match="at least one evaluator"):
        CorpusQualityAssessor([])

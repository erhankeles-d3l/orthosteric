"""SelectivityPolicy: deterministic tier assignment and governed gates.

Validates ADR-0008 requirements:
  - deterministic tier assignment
  - configurable thresholds (no hard-coded cutoff)
  - governed gates (§2.2 Indeterminate, §2.3(3) mixed class, §2.3(6) floor,
    missing != inactive)
  - full selectivity vector retained
  - AUDITOR-5 advisory on non-normalized metrics
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from orthosteric.data.provenance.enums import MeasurementClass
from orthosteric.policy import (
    AUDITOR5_ADVISORY,
    BELOW_LOWEST_TIER,
    BindingClass,
    NormalizationStatus,
    PolicyStatus,
    SelectivityPolicy,
    SelectivityTier,
    SelectivityTierTable,
)
from tests.policy._fixtures import (
    ALPHA,
    BETA,
    DELTA,
    GAMMA,
    config,
    iso,
    prediction,
    worked_example,
)

# ── worked example and tier boundaries ────────────────────────────────────────


def test_worked_example_yields_tier_c() -> None:
    outcome = SelectivityPolicy(config()).evaluate(worked_example())
    assert outcome.status == PolicyStatus.CLASSIFIED
    assert outcome.classification == "TIER_C"


def test_worked_example_fold_values_and_limiting_isoform() -> None:
    outcome = SelectivityPolicy(config()).evaluate(worked_example())
    vec = outcome.detail["selectivity_vector"]
    assert vec["limiting_isoform"] == BETA
    assert Decimal(vec["min_fold"]) == pytest.approx(Decimal("170"), abs=1)
    folds = {k: Decimal(v) for k, v in vec["fold_selectivities"].items()}
    assert folds[BETA] == pytest.approx(Decimal("170"), abs=1)
    assert folds[GAMMA] == pytest.approx(Decimal("340"), abs=1)
    assert folds[DELTA] == pytest.approx(Decimal("240"), abs=1)


@pytest.mark.parametrize(
    ("delta_log", "expected"),
    [
        ("0.0", BELOW_LOWEST_TIER),  # 1x
        ("0.9", BELOW_LOWEST_TIER),  # ~7.9x, below 10x
        ("1.0", "TIER_A"),  # exactly 10x -> inclusive
        ("1.4", "TIER_A"),  # ~25x
        ("2.0", "TIER_C"),  # exactly 100x -> inclusive
        ("2.4", "TIER_C"),  # ~251x
        ("2.5", "TIER_D"),  # ~316x
        ("3.0", "TIER_E"),  # exactly 1000x -> inclusive
        ("4.0", "TIER_E"),  # 10000x, saturates at highest band
    ],
)
def test_tier_boundaries_are_inclusive_and_deterministic(delta_log: str, expected: str) -> None:
    """Each band's minimum is inclusive; above the top band saturates."""
    ref = Decimal("9.0")
    off = ref - Decimal(delta_log)
    pred = prediction(
        iso(ALPHA, format(ref, "f")),
        iso(BETA, format(off, "f")),
        iso(GAMMA, format(off, "f")),
        iso(DELTA, format(off, "f")),
    )
    assert SelectivityPolicy(config()).evaluate(pred).classification == expected


def test_smin_is_the_minimum_not_the_mean() -> None:
    """One poorly-spared isoform must dominate the classification."""
    pred = prediction(
        iso(ALPHA, "9.0"),
        iso(BETA, "8.5"),  # only ~3.2x -> below Tier A
        iso(GAMMA, "5.0"),  # 10000x
        iso(DELTA, "5.0"),  # 10000x
    )
    outcome = SelectivityPolicy(config()).evaluate(pred)
    assert outcome.classification == BELOW_LOWEST_TIER
    assert outcome.detail["selectivity_vector"]["limiting_isoform"] == BETA


def test_deterministic_across_repeated_evaluation() -> None:
    policy = SelectivityPolicy(config())
    pred = worked_example()
    first = policy.evaluate(pred)
    second = policy.evaluate(pred)
    assert first.to_canonical_dict() == second.to_canonical_dict()


# ── configurability ──────────────────────────────────────────────────────────


def test_thresholds_are_configurable_not_hard_coded() -> None:
    """The same prediction classifies differently under a different tier table."""
    strict = SelectivityTierTable(
        tiers=(
            SelectivityTier(name="STRICT_1", min_fold=Decimal("500")),
            SelectivityTier(name="STRICT_2", min_fold=Decimal("5000")),
        )
    )
    pred = worked_example()  # Smin ~170x
    assert SelectivityPolicy(config()).evaluate(pred).classification == "TIER_C"
    assert (
        SelectivityPolicy(config(selectivity_tiers=strict)).evaluate(pred).classification
        == BELOW_LOWEST_TIER
    )


def test_custom_tier_names_are_respected() -> None:
    table = SelectivityTierTable(
        tiers=(SelectivityTier(name="PRIORITY_LOW", min_fold=Decimal("10")),)
    )
    outcome = SelectivityPolicy(config(selectivity_tiers=table)).evaluate(worked_example())
    assert outcome.classification == "PRIORITY_LOW"


def test_off_target_set_is_configurable() -> None:
    """Restricting the off-target set changes which isoform can be limiting."""
    pred = prediction(
        iso(ALPHA, "9.0"),
        iso(BETA, "8.5"),  # limiting if included
        iso(GAMMA, "5.0"),
        iso(DELTA, "5.0"),
    )
    cfg = config(off_target_isoforms=(GAMMA, DELTA))
    outcome = SelectivityPolicy(cfg).evaluate(pred)
    assert outcome.classification == "TIER_E"
    assert BETA not in outcome.detail["selectivity_vector"]["fold_selectivities"]


# ── governed gates ───────────────────────────────────────────────────────────


def test_potency_floor_yields_undefined_not_low_tier() -> None:
    """Constitution §2.3(6): below the floor, selectivity is *undefined*."""
    pred = prediction(
        iso(ALPHA, "6.5"),  # below 7.0 floor
        iso(BETA, "3.0"),  # would otherwise be ~3160x
        iso(GAMMA, "3.0"),
        iso(DELTA, "3.0"),
    )
    outcome = SelectivityPolicy(config()).evaluate(pred)
    assert outcome.status == PolicyStatus.UNDEFINED_POTENCY_FLOOR
    assert outcome.classification is None
    assert "2.3(6)" in outcome.rationale


def test_potency_floor_boundary_is_inclusive() -> None:
    """PAct exactly at the floor satisfies '>= 7.0'."""
    pred = prediction(
        iso(ALPHA, "7.0"),
        iso(BETA, "5.0"),
        iso(GAMMA, "5.0"),
        iso(DELTA, "5.0"),
    )
    outcome = SelectivityPolicy(config()).evaluate(pred)
    assert outcome.status == PolicyStatus.CLASSIFIED


def test_indeterminate_off_target_is_not_read_as_spared() -> None:
    """Constitution §2.2: Indeterminate contributes zero to selectivity claims."""
    pred = prediction(
        iso(ALPHA, "9.0"),
        iso(BETA, "5.0", binding_class=BindingClass.INDETERMINATE),
        iso(GAMMA, "5.0"),
        iso(DELTA, "5.0"),
    )
    outcome = SelectivityPolicy(config()).evaluate(pred)
    assert outcome.status == PolicyStatus.UNDEFINED_INDETERMINATE
    assert outcome.classification is None
    assert "2.2" in outcome.rationale


def test_indeterminate_reference_also_undefined() -> None:
    pred = prediction(
        iso(ALPHA, "9.0", binding_class=BindingClass.INDETERMINATE),
        iso(BETA, "5.0"),
        iso(GAMMA, "5.0"),
        iso(DELTA, "5.0"),
    )
    assert SelectivityPolicy(config()).evaluate(pred).status == PolicyStatus.UNDEFINED_INDETERMINATE


def test_non_productive_off_target_is_classifiable() -> None:
    """NON_PRODUCTIVE is positive evidence of sparing, unlike INDETERMINATE."""
    pred = prediction(
        iso(ALPHA, "9.0"),
        iso(BETA, "5.0", binding_class=BindingClass.NON_PRODUCTIVE),
        iso(GAMMA, "5.0", binding_class=BindingClass.NON_PRODUCTIVE),
        iso(DELTA, "5.0", binding_class=BindingClass.NON_PRODUCTIVE),
    )
    assert SelectivityPolicy(config()).evaluate(pred).status == PolicyStatus.CLASSIFIED


def test_mixed_measurement_class_is_undefined() -> None:
    """Constitution §2.3(3): biochemical and cellular are never pooled."""
    pred = prediction(
        iso(ALPHA, "9.0", measurement_class=MeasurementClass.BIOCHEMICAL),
        iso(BETA, "5.0", measurement_class=MeasurementClass.CELLULAR),
        iso(GAMMA, "5.0", measurement_class=MeasurementClass.BIOCHEMICAL),
        iso(DELTA, "5.0", measurement_class=MeasurementClass.BIOCHEMICAL),
    )
    outcome = SelectivityPolicy(config()).evaluate(pred)
    assert outcome.status == PolicyStatus.UNDEFINED_MIXED_CLASS
    assert "2.3(3)" in outcome.rationale


def test_missing_prediction_is_not_inactive() -> None:
    pred = prediction(
        iso(ALPHA, "9.0"),
        iso(BETA, None),  # no point estimate
        iso(GAMMA, "5.0"),
        iso(DELTA, "5.0"),
    )
    outcome = SelectivityPolicy(config()).evaluate(pred)
    assert outcome.status == PolicyStatus.UNDEFINED_MISSING_PREDICTION
    assert "not inactive" in outcome.rationale


def test_absent_isoform_entirely_is_missing() -> None:
    pred = prediction(iso(ALPHA, "9.0"), iso(BETA, "5.0"))  # gamma, delta absent
    assert (
        SelectivityPolicy(config()).evaluate(pred).status
        == PolicyStatus.UNDEFINED_MISSING_PREDICTION
    )


# ── AUDITOR-5 advisory ───────────────────────────────────────────────────────


def test_non_normalized_metric_raises_auditor5_advisory() -> None:
    pred = prediction(
        iso(ALPHA, "9.301"),
        iso(BETA, "7.071"),
        iso(GAMMA, "6.770"),
        iso(DELTA, "6.921"),
        normalization=NormalizationStatus.NOT_NORMALIZED,
    )
    outcome = SelectivityPolicy(config()).evaluate(pred)
    assert outcome.classification == "TIER_C"  # still computed
    assert AUDITOR5_ADVISORY in outcome.governance_flags


def test_normalized_metric_raises_no_advisory() -> None:
    outcome = SelectivityPolicy(config()).evaluate(worked_example())
    assert AUDITOR5_ADVISORY not in outcome.governance_flags


def test_policy_output_is_never_criterion_eligible() -> None:
    assert SelectivityPolicy(config()).evaluate(worked_example()).criterion_eligible is False

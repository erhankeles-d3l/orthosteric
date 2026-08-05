"""PotencyPolicy, ConfidencePolicy, UncertaintyPolicy."""

from __future__ import annotations

from decimal import Decimal

import pytest

from orthosteric.policy import (
    ConfidencePolicy,
    PolicyStatus,
    PotencyPolicy,
    UncertaintyPolicy,
)
from tests.policy._fixtures import ALPHA, BETA, DELTA, GAMMA, config, iso, prediction

# ── PotencyPolicy ────────────────────────────────────────────────────────────


def test_potency_pass_at_and_above_floor() -> None:
    policy = PotencyPolicy(config())
    for pact in ("7.0", "9.5"):
        pred = prediction(iso(ALPHA, pact))
        assert policy.evaluate(pred).classification == "PASS"


def test_potency_fail_below_floor() -> None:
    outcome = PotencyPolicy(config()).evaluate(prediction(iso(ALPHA, "6.99")))
    assert outcome.classification == "FAIL"
    assert outcome.detail["floor"] == "7.0"


def test_potency_missing_reference_is_undefined() -> None:
    outcome = PotencyPolicy(config()).evaluate(prediction(iso(BETA, "8.0")))
    assert outcome.status == PolicyStatus.UNDEFINED_MISSING_PREDICTION


def test_potency_records_governance_deviation_when_floor_overridden() -> None:
    cfg = config(potency_floor_p_activity=Decimal("6.0"))
    outcome = PotencyPolicy(cfg).evaluate(prediction(iso(ALPHA, "6.5")))
    assert outcome.classification == "PASS"  # passes the overridden floor
    assert any("GOVERNANCE_DEVIATION" in f for f in outcome.governance_flags)


# ── ConfidencePolicy (§2.4 product, not min) ──────────────────────────────────


def _conf_prediction(a: float, b: float, g: float, d: float) -> object:
    return prediction(
        iso(ALPHA, "9.0", confidence=a),
        iso(BETA, "5.0", confidence=b),
        iso(GAMMA, "5.0", confidence=g),
        iso(DELTA, "5.0", confidence=d),
    )


def test_joint_confidence_is_product_not_minimum() -> None:
    """Constitution §2.4: the min-rule is wrong; joint confidence is a product
    and is strictly lower than the weakest component when others are < 1."""
    outcome = ConfidencePolicy(config()).evaluate(_conf_prediction(0.9, 0.9, 0.9, 0.9))  # type: ignore[arg-type]
    joint = outcome.detail["joint_confidence"]
    weakest = outcome.detail["weakest_component"]
    assert joint == pytest.approx(0.9**4)
    assert joint < weakest, "product must be below the weakest component"


def test_joint_confidence_never_exceeds_weakest_component() -> None:
    policy = ConfidencePolicy(config())
    for values in [(1.0, 1.0, 1.0, 0.4), (0.5, 0.6, 0.7, 0.8)]:
        outcome = policy.evaluate(_conf_prediction(*values))  # type: ignore[arg-type]
        assert outcome.detail["joint_confidence"] <= outcome.detail["weakest_component"]


def test_confidence_threshold_classification() -> None:
    cfg = config(min_confidence=0.5)
    policy = ConfidencePolicy(cfg)
    assert policy.evaluate(_conf_prediction(1.0, 1.0, 1.0, 1.0)).classification == "PASS"  # type: ignore[arg-type]
    # 0.8 per target: min-rule would give 0.8 and PASS; the product is
    # 0.8**4 == 0.4096 and correctly FAILS a 0.5 threshold. This is the
    # concrete consequence of Constitution §2.4 rejecting the min-rule.
    outcome = policy.evaluate(_conf_prediction(0.8, 0.8, 0.8, 0.8))  # type: ignore[arg-type]
    assert outcome.detail["weakest_component"] == pytest.approx(0.8)
    assert outcome.detail["joint_confidence"] == pytest.approx(0.8**4)
    assert outcome.classification == "FAIL"


def test_confidence_reports_per_target_values() -> None:
    """§2.4 requires per-target confidence always be reported, not just joint."""
    outcome = ConfidencePolicy(config()).evaluate(_conf_prediction(0.9, 0.8, 0.7, 0.6))  # type: ignore[arg-type]
    per_target = outcome.detail["per_target_confidence"]
    assert set(per_target) == {ALPHA, BETA, GAMMA, DELTA}


def test_confidence_states_correlation_assumption() -> None:
    """§2.4 requires the correlation assumption be stated, not implied."""
    outcome = ConfidencePolicy(config()).evaluate(_conf_prediction(0.9, 0.9, 0.9, 0.9))  # type: ignore[arg-type]
    assert "independence" in outcome.detail["correlation_assumption"]


def test_confidence_abstains_when_a_confidence_is_missing() -> None:
    pred = prediction(
        iso(ALPHA, "9.0", confidence=0.9),
        iso(BETA, "5.0"),  # no confidence
        iso(GAMMA, "5.0", confidence=0.9),
        iso(DELTA, "5.0", confidence=0.9),
    )
    outcome = ConfidencePolicy(config()).evaluate(pred)
    assert outcome.status == PolicyStatus.ABSTAINED
    assert outcome.classification is None


# ── UncertaintyPolicy (§2.4 noise floor) ──────────────────────────────────────


def _width_prediction(width: float) -> object:
    return prediction(
        iso(ALPHA, "9.0", interval_width=width),
        iso(BETA, "5.0", interval_width=width),
        iso(GAMMA, "5.0", interval_width=width),
        iso(DELTA, "5.0", interval_width=width),
    )


def test_uncertainty_abstains_when_no_floor_configured() -> None:
    """The floor is a SCI0-016 output; §2.4's '>= 0.3' is not assumed."""
    outcome = UncertaintyPolicy(config()).evaluate(_width_prediction(0.1))  # type: ignore[arg-type]
    assert outcome.status == PolicyStatus.ABSTAINED
    assert any("SCI0-016" in f for f in outcome.governance_flags)


def test_uncertainty_fails_interval_narrower_than_floor() -> None:
    cfg = config(label_noise_floor_log_units=0.3)
    outcome = UncertaintyPolicy(cfg).evaluate(_width_prediction(0.1))  # type: ignore[arg-type]
    assert outcome.classification == "FAIL"
    assert len(outcome.detail["violating_isoforms"]) == 4


def test_uncertainty_passes_interval_at_or_above_floor() -> None:
    cfg = config(label_noise_floor_log_units=0.3)
    outcome = UncertaintyPolicy(cfg).evaluate(_width_prediction(0.3))  # type: ignore[arg-type]
    assert outcome.classification == "PASS"
    assert outcome.detail["violating_isoforms"] == []


def test_uncertainty_abstains_when_width_missing() -> None:
    cfg = config(label_noise_floor_log_units=0.3)
    pred = prediction(
        iso(ALPHA, "9.0", interval_width=0.5),
        iso(BETA, "5.0"),  # no width
        iso(GAMMA, "5.0", interval_width=0.5),
        iso(DELTA, "5.0", interval_width=0.5),
    )
    assert UncertaintyPolicy(cfg).evaluate(pred).status == PolicyStatus.ABSTAINED

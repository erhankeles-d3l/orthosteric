"""SCI1-013 through SCI1-016 tests: metrics, calibration, uncertainty, binding."""

from __future__ import annotations

import numpy as np
import pytest

from orthosteric.eval import (
    CALIBRATION_ALGORITHM_VERSION,
    METRICS_ALGORITHM_VERSION,
    PRODUCTIVE_BINDING_ALGORITHM_VERSION,
    UNCERTAINTY_ALGORITHM_VERSION,
    BindingClassification,
    CalibrationResult,
    ProductiveBindingConfig,
    SelectivityTarget,
    compose_selectivity_confidence,
    ece_per_target,
    log_selectivity_ratio,
    per_target_rmse,
    rmse,
    sharpness,
)
from orthosteric.eval._productive_binding import classify_productive_binding
from orthosteric.eval._uncertainty import CorrelationAssumption

# ── SCI1-013: Metrics ─────────────────────────────────────────────────────────


def test_log_selectivity_ratio_alpha_selective() -> None:
    assert log_selectivity_ratio(8.0, 6.0) == pytest.approx(2.0)


def test_log_selectivity_ratio_symmetric() -> None:
    assert log_selectivity_ratio(6.0, 8.0) == pytest.approx(-2.0)


def test_log_selectivity_ratio_equal() -> None:
    assert log_selectivity_ratio(7.0, 7.0) == pytest.approx(0.0)


def test_rmse_basic() -> None:
    pred = np.array([1.0, 2.0, 3.0])
    act = np.array([1.0, 2.0, 3.0])
    assert rmse(pred, act) == pytest.approx(0.0)


def test_rmse_known_value() -> None:
    pred = np.array([0.0, 1.0])
    act = np.array([1.0, 0.0])
    assert rmse(pred, act) == pytest.approx(1.0)


def test_rmse_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="Shape mismatch"):
        rmse(np.array([1.0, 2.0]), np.array([1.0]))


def test_rmse_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        rmse(np.array([]), np.array([]))


def test_per_target_rmse_multiple_axes() -> None:
    result = per_target_rmse(
        predicted={"alpha_vs_beta": np.array([1.0, 2.0]), "alpha_vs_gamma": np.array([0.0, 3.0])},
        actual={"alpha_vs_beta": np.array([1.0, 2.0]), "alpha_vs_gamma": np.array([1.0, 2.0])},
    )
    assert "alpha_vs_beta" in result
    assert result["alpha_vs_beta"] == pytest.approx(0.0)
    assert result["alpha_vs_gamma"] > 0.0


def test_per_target_rmse_missing_key_skipped() -> None:
    result = per_target_rmse(
        predicted={"alpha_vs_beta": np.array([1.0])},
        actual={"alpha_vs_gamma": np.array([1.0])},
    )
    assert result == {}


def test_metrics_algorithm_version_pinned() -> None:
    assert METRICS_ALGORITHM_VERSION == "metrics_v1_sci1013"


def test_selectivity_target_is_frozen() -> None:
    st = SelectivityTarget(
        pac_alpha=8.0,
        lr_vs_beta=2.0,
        lr_vs_gamma=1.5,
        lr_vs_delta=1.0,
        ci_half=0.3,
        compound_id="CMP001",
        smiles=None,
        assay_atp_mm=1.0,
        within_study=True,
    )
    with pytest.raises((AttributeError, TypeError)):
        st.pac_alpha = 9.0  # type: ignore[misc]


# ── SCI1-014: Calibration ─────────────────────────────────────────────────────


def test_ece_perfect_calibration() -> None:
    confs = np.array([0.9, 0.8, 0.7])
    in_int = np.array([True, True, True])
    r = ece_per_target(confs, in_int, "PI3Kalpha")
    assert isinstance(r, CalibrationResult)
    assert r.target_key == "PI3Kalpha"
    assert r.n_samples == 3


def test_ece_empty() -> None:
    r = ece_per_target(np.array([]), np.array([], dtype=bool), "PI3Kalpha")
    assert r.ece == 0.0
    assert r.meets_s4 is True


def test_ece_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="Shape mismatch"):
        ece_per_target(np.array([0.9]), np.array([True, False]), "x")


def test_ece_meets_s4_threshold() -> None:
    r = ece_per_target(
        np.linspace(0.0, 1.0, 100),
        np.array([False] * 50 + [True] * 50),
        "PI3Kalpha",
    )
    assert r.meets_s4 == (r.ece <= 0.10)


def test_sharpness_computes() -> None:
    widths = np.array([0.5, 0.5, 0.5])
    assert sharpness(widths) == pytest.approx(0.5)


def test_sharpness_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        sharpness(np.array([]))


def test_calibration_algorithm_version_pinned() -> None:
    assert CALIBRATION_ALGORITHM_VERSION == "calibration_v1_sci1014"


def test_calibration_result_is_frozen() -> None:
    r = ece_per_target(np.array([0.9]), np.array([True]), "PI3Kalpha")
    with pytest.raises((AttributeError, TypeError)):
        r.ece = 0.99  # type: ignore[misc]


# ── SCI1-015: Uncertainty composition ────────────────────────────────────────


def test_compose_independent_lower_than_weakest() -> None:
    """Constitution §2.4: joint < min(per-target). Product rule."""
    sc = compose_selectivity_confidence(
        0.9, 0.8, 0.8, 0.8, "CMP001", CorrelationAssumption.INDEPENDENT
    )
    assert sc.joint_confidence < min(0.9, 0.8)
    assert abs(sc.joint_confidence - 0.9 * 0.8**3) < 1e-6


def test_compose_not_min_rule() -> None:
    """The v3.x min-rule was wrong. Joint must NOT equal min of per-target."""
    sc = compose_selectivity_confidence(
        0.9, 0.8, 0.7, 0.8, "CMP001", CorrelationAssumption.INDEPENDENT
    )
    assert sc.joint_confidence != min(0.9, 0.8, 0.7, 0.8)


def test_compose_frechet_lower_bound() -> None:
    """Fréchet bound: max(0, sum - (n-1))."""
    sc = compose_selectivity_confidence(
        0.9, 0.8, 0.8, 0.8, "CMP001", CorrelationAssumption.FRECHET_LOWER
    )
    expected_frechet = max(0.0, 0.9 + 0.8 + 0.8 + 0.8 - 3)
    assert abs(sc.joint_confidence - expected_frechet) < 1e-6


def test_compose_with_none_isoform() -> None:
    """Only alpha required. Beta/gamma/delta optional (not measured)."""
    sc = compose_selectivity_confidence(0.9, None, None, None, "CMP001")
    assert sc.joint_confidence == pytest.approx(0.9)


def test_compose_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="0, 1"):
        compose_selectivity_confidence(1.5, 0.8, 0.8, 0.8, "CMP001")


def test_uncertainty_algorithm_version_pinned() -> None:
    assert UNCERTAINTY_ALGORITHM_VERSION == "uncertainty_v1_sci1015"


def test_selectivity_confidence_is_frozen() -> None:
    sc = compose_selectivity_confidence(0.9, 0.8, 0.8, 0.8, "CMP001")
    with pytest.raises((AttributeError, TypeError)):
        sc.joint_confidence = 0.0  # type: ignore[misc]


# ── SCI1-016: Indeterminate binding ──────────────────────────────────────────


def test_productive_all_criteria_met() -> None:
    r = classify_productive_binding(
        "CMP001",
        "PI3Kalpha",
        n_docking_converged=4,
        has_required_contacts=True,
        has_heavy_clash=False,
        n_md_egress=0,
    )
    assert r.classification == BindingClassification.PRODUCTIVE
    assert r.contributes_to_selectivity is True
    assert r.is_indeterminate is False


def test_nonproductive_on_clash() -> None:
    r = classify_productive_binding(
        "CMP001",
        "PI3Kalpha",
        n_docking_converged=4,
        has_required_contacts=True,
        has_heavy_clash=True,
        n_md_egress=0,
    )
    assert r.classification == BindingClassification.NON_PRODUCTIVE
    assert r.contributes_to_selectivity is False


def test_nonproductive_on_egress() -> None:
    r = classify_productive_binding(
        "CMP001",
        "PI3Kalpha",
        n_docking_converged=4,
        has_required_contacts=True,
        has_heavy_clash=False,
        n_md_egress=2,
    )
    assert r.classification == BindingClassification.NON_PRODUCTIVE


def test_indeterminate_when_no_data() -> None:
    r = classify_productive_binding("CMP001", "PI3Kalpha")
    assert r.classification == BindingClassification.INDETERMINATE
    assert r.contributes_to_selectivity is False
    assert r.is_indeterminate is True
    assert len(r.indeterminate_reason) > 0


def test_indeterminate_insufficient_docking() -> None:
    """3 of 5 converged but default requires 3 -- actually passes.
    2 of 5 converged -- should be INDETERMINATE or at least not PRODUCTIVE."""
    r = classify_productive_binding(
        "CMP001",
        "PI3Kalpha",
        n_docking_converged=2,
        has_required_contacts=True,
        has_heavy_clash=False,
        n_md_egress=0,
    )
    assert r.classification == BindingClassification.INDETERMINATE


def test_indeterminate_contributes_zero() -> None:
    """Constitution §2.2: Indeterminate contributes ZERO to selectivity claims."""
    r = classify_productive_binding("CMP001", "PI3Kalpha")
    assert r.is_indeterminate
    assert r.contributes_to_selectivity is False  # not weak evidence of sparing


def test_three_class_vocabulary_complete() -> None:
    vals = {c.value for c in BindingClassification}
    assert vals == {"productive", "non_productive", "indeterminate"}


def test_productive_binding_algorithm_version_pinned() -> None:
    assert PRODUCTIVE_BINDING_ALGORITHM_VERSION == "productive_binding_v1_sci1016"


def test_productive_binding_config_is_frozen() -> None:
    cfg = ProductiveBindingConfig()
    with pytest.raises((AttributeError, TypeError)):
        cfg.docking_rmsd_cutoff_angstrom = 1.0  # type: ignore[misc]

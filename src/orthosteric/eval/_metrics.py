"""Selectivity metrics: log-ratio targets, per-target RMSE, and RMSE.

Authority: SCI1-013. Constitution §2.3(4), §1.4 (S2 criterion).

Constitution §2.3(4) selectivity target:
  S_1 = (pAct_alpha, pAct_alpha - pAct_beta,
         pAct_alpha - pAct_gamma, pAct_alpha - pAct_delta) +/- CI

  The log-selectivity-ratio is (pAct_alpha - pAct_x): positive means
  alpha-preferential, negative means x-preferential. This is signed
  and isoform-specific -- never a single "selectivity" scalar.

Constitution §1.4 S2 criterion:
  Beats a ligand-only baseline on log-selectivity-ratio prediction
  by >= 0.3 log RMSE on held-out series.
  S2 threshold = 0.3 log unit improvement over baseline.

Scientific rule classification
  RULE_AVAILABLE:  log-selectivity-ratio definition as pAct difference.
    This is the standard biochemical definition of selectivity from
    IC50 ratios, linearized via pIC50 = -log10(IC50).
  RULE_AVAILABLE:  RMSE as the primary prediction error metric for
    log-activity predictions (standard practice; used in S2).
  RULE_MISSING:    None of the thresholds in this module. S2_RMSE_IMPROVEMENT
    is stated in the Constitution (0.3) but is sealed at Stage 0 and
    must not be hardcoded as a production threshold here.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "METRICS_ALGORITHM_VERSION",
    "SelectivityTarget",
    "log_selectivity_ratio",
    "per_target_rmse",
    "rmse",
]

METRICS_ALGORITHM_VERSION = "metrics_v1_sci1013"

# S2 threshold stated in Constitution §1.4 -- for reference only.
# Do not use as a hardcoded production gate; that gate lives in eval/_gate.py.
_CONSTITUTION_S2_RMSE_IMPROVEMENT = 0.3  # log units


@dataclass(frozen=True, slots=True)
class SelectivityTarget:
    """Constitution §2.3(4) selectivity target for one compound.

    Attributes:
        pac_alpha:     pActivity (pIC50 or equivalent) at PI3Kalpha.
        lr_vs_beta:    pAct_alpha - pAct_beta  (positive = alpha-selective).
        lr_vs_gamma:   pAct_alpha - pAct_gamma.
        lr_vs_delta:   pAct_alpha - pAct_delta.
        ci_half:       Half-width of confidence interval on pac_alpha.
        compound_id:   Identifier for the compound.
        assay_atp_mm:  ATP concentration in assay (mM). None if unavailable.
                       Required for §2.3 compliance (never pool across ATP conc.).
        within_study:  True iff all four isoform measurements from one study.
    """

    pac_alpha: float
    lr_vs_beta: float | None
    lr_vs_gamma: float | None
    lr_vs_delta: float | None
    ci_half: float | None
    compound_id: str
    assay_atp_mm: float | None
    within_study: bool


def log_selectivity_ratio(pac_alpha: float, pac_other: float) -> float:
    """Signed log-selectivity-ratio (Constitution §2.3(4)).

    Returns pAct_alpha - pAct_other.
    Positive: alpha-preferential.
    Negative: other-isoform-preferential.
    """
    return pac_alpha - pac_other


def rmse(
    predicted: NDArray[np.float64],
    actual: NDArray[np.float64],
) -> float:
    """Root-mean-squared error on log-activity or log-selectivity-ratio values.

    Both arrays must be the same shape with no NaN values.
    """
    if predicted.shape != actual.shape:
        raise ValueError(f"Shape mismatch: predicted {predicted.shape} vs actual {actual.shape}")
    if predicted.size == 0:
        raise ValueError("Cannot compute RMSE on empty arrays")
    return float(np.sqrt(np.mean((predicted - actual) ** 2)))


def per_target_rmse(
    predicted: dict[str, NDArray[np.float64]],
    actual: dict[str, NDArray[np.float64]],
) -> dict[str, float]:
    """Per-target RMSE for each isoform-pair selectivity axis.

    Parameters
    ----------
    predicted:  dict mapping target_key to predicted log-ratio array.
    actual:     dict mapping target_key to actual log-ratio array.

    Returns:
    -------
    dict mapping target_key to RMSE. Missing keys (no data) are omitted.

    Convention for target keys: "alpha_vs_beta", "alpha_vs_gamma", etc.
    These are the isoform-pair axes, not aggregated.
    """
    result: dict[str, float] = {}
    for key in sorted(predicted):
        if key not in actual:
            continue
        pred_arr = predicted[key]
        act_arr = actual[key]
        if pred_arr.size == 0:
            continue
        result[key] = rmse(pred_arr, act_arr)
    return result

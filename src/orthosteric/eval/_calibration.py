"""Per-target calibration: ECE and sharpness.

Authority: SCI1-014. Constitution §1.4 (S4: ECE <= 0.10 per target),
  §2.4 (uncertainty must be per-target, never aggregated).

Constitution §1.4 S4b -- per-target calibration:
  ECE <= 0.10 for each of alpha, beta, gamma, delta SEPARATELY.
  Aggregated ECE across isoforms is not an admissible criterion.

Scientific rule classification
  RULE_AVAILABLE:  ECE definition (standard probabilistic calibration metric):
    ECE = sum_b |freq_b - conf_b| * n_b / N  (equal-mass binning).
  RULE_AVAILABLE:  Sharpness definition: mean predicted interval width.
    A sharp model concentrates its probability mass; a well-calibrated
    model assigns this mass correctly.
  RULE_MISSING:    Optimal bin count for ECE. n_bins=10 is standard but
    not governed here; it is a parameter of the CalibrationResult.
  RULE_MISSING:    Whether to use equal-width or equal-mass bins.
    This module uses equal-width; equal-mass is an alternative.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "CALIBRATION_ALGORITHM_VERSION",
    "CalibrationResult",
    "ece_per_target",
    "sharpness",
]

_S4_ECE_THRESHOLD = 0.10  # Constitution §1.4

CALIBRATION_ALGORITHM_VERSION = "calibration_v1_sci1014"


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    """ECE and sharpness for one prediction target.

    Attributes:
        target_key:    Identifies the isoform or isoform-pair (e.g. 'PI3Kalpha').
        ece:           Expected Calibration Error in [0, 1]. Lower is better.
        sharpness:     Mean predicted interval half-width. Lower = sharper.
        n_samples:     Number of compounds evaluated.
        n_bins:        Number of equal-width calibration bins used.
        meets_s4:      True iff ECE <= 0.10 (Constitution §1.4 S4).
        algorithm_version: Pinned version.
    """

    target_key: str
    ece: float
    sharpness: float | None
    n_samples: int
    n_bins: int
    meets_s4: bool
    algorithm_version: str

    @property
    def s4_threshold(self) -> float:
        """Constitution §1.4 S4 ECE threshold."""
        return 0.10


def ece_per_target(
    confidences: NDArray[np.float64],
    in_interval: NDArray[np.bool_],
    target_key: str,
    n_bins: int = 10,
    predicted_widths: NDArray[np.float64] | None = None,
) -> CalibrationResult:
    """Compute ECE for one prediction target.

    Parameters
    ----------
    confidences:    Predicted confidence in [0, 1] for each compound.
    in_interval:    Whether the true value falls in the predicted interval.
    target_key:     Isoform identifier (e.g. 'PI3Kalpha').
    n_bins:         Number of equal-width calibration bins.
    predicted_widths: Predicted interval half-widths (for sharpness). Optional.

    Returns:
    -------
    `CalibrationResult` for this target. Do not aggregate across targets.
    """
    if confidences.shape != in_interval.shape:
        raise ValueError(
            f"Shape mismatch: confidences {confidences.shape} vs in_interval {in_interval.shape}"
        )
    n = len(confidences)
    if n == 0:
        return CalibrationResult(
            target_key=target_key,
            ece=0.0,
            sharpness=None,
            n_samples=0,
            n_bins=n_bins,
            meets_s4=True,
            algorithm_version=CALIBRATION_ALGORITHM_VERSION,
        )

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece_acc = 0.0
    for lo, hi in itertools.pairwise(bins):
        mask = (confidences >= lo) & (confidences < hi)
        if not mask.any():
            continue
        conf_b = float(np.mean(confidences[mask]))
        freq_b = float(np.mean(in_interval[mask]))
        ece_acc += abs(conf_b - freq_b) * mask.sum() / n

    sharp = float(np.mean(predicted_widths)) if predicted_widths is not None else None
    meets_s4 = ece_acc <= _S4_ECE_THRESHOLD
    return CalibrationResult(
        target_key=target_key,
        ece=round(ece_acc, 6),
        sharpness=sharp,
        n_samples=n,
        n_bins=n_bins,
        meets_s4=meets_s4,
        algorithm_version=CALIBRATION_ALGORITHM_VERSION,
    )


def sharpness(predicted_widths: NDArray[np.float64]) -> float:
    """Mean predicted interval half-width (sharpness measure).

    Smaller = sharper predictions. Sharpness without calibration is
    meaningless; always report alongside ECE.
    """
    if predicted_widths.size == 0:
        raise ValueError("Cannot compute sharpness on empty array")
    return float(np.mean(predicted_widths))

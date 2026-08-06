"""Uncertainty composition as an explicit conjunction.

Authority: SCI1-015. Constitution §2.4.

Constitution §2.4 mandate:
  "A selectivity claim is a conjunction (alpha productive AND the rest
  spared), so joint confidence composes as a product over correlated
  events and is lower than the weakest component, not equal to it."

  The v3.x min-rule was wrong. This module implements the conjunction
  composition: joint_confidence = product(per_target_confidences) for
  independent events, or a conservative lower bound when correlation
  is asserted.

Scientific rule classification
  RULE_AVAILABLE:  Product rule for independent events: P(A and B) = P(A)*P(B)
    for independent events.
  RULE_AVAILABLE:  Fréchet inequality: P(A and B) >= P(A) + P(B) - 1
    (i.e. >= 0 when no independence assumed; this is the Fréchet lower bound).
  RULE_MISSING:    The correlation structure between per-target confidence
    estimates. Independence is a strong assumption; correlation > 0 would
    increase the joint confidence above the product.
  RULE_MISSING:    Whether the per-target confidences are calibrated (see
    SCI1-014). Uncalibrated confidence does not support valid conjunction.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

__all__ = [
    "UNCERTAINTY_ALGORITHM_VERSION",
    "CorrelationAssumption",
    "SelectivityConfidence",
    "compose_selectivity_confidence",
]

UNCERTAINTY_ALGORITHM_VERSION = "uncertainty_v1_sci1015"


class CorrelationAssumption(StrEnum):
    """Correlation model for uncertainty composition (Constitution §2.4)."""

    INDEPENDENT = "independent"  # product rule: P(A and B) = P(A)*P(B)
    FRECHET_LOWER = "frechet_lower"  # P(A and B) >= P(A)+P(B)-1 (conservative)
    NOT_SPECIFIED = "not_specified"  # return both bounds; do not choose


@dataclass(frozen=True, slots=True)
class SelectivityConfidence:
    """Joint confidence for an alpha-selective claim (Constitution §2.4).

    Records per-target confidences separately, never aggregates them
    into a single number until an explicit conjunction is formed.

    Attributes:
        conf_alpha_productive:  Confidence that alpha is productive.
        conf_beta_spared:       Confidence that beta is spared. None if unavailable.
        conf_gamma_spared:      Confidence that gamma is spared.
        conf_delta_spared:      Confidence that delta is spared.
        joint_confidence:       Conjunction confidence under `correlation_assumption`.
        joint_lower_bound:      Fréchet lower bound (always computed).
        correlation_assumption: Which composition rule was applied.
        compound_id:            Compound identifier.
        note:                   Governance note about the composition.
        algorithm_version:      Pinned version.
    """

    conf_alpha_productive: float
    conf_beta_spared: float | None
    conf_gamma_spared: float | None
    conf_delta_spared: float | None
    joint_confidence: float
    joint_lower_bound: float
    correlation_assumption: CorrelationAssumption
    compound_id: str
    note: str
    algorithm_version: str


_CONJUNCTION_NOTE = (
    "Constitution §2.4: joint confidence is a conjunction (product for independent, "
    "Frechet lower bound for unknown correlation). The v3.x min-rule was incorrect. "
    "RULE_MISSING: correlation structure between per-target confidences not governed."
)


def compose_selectivity_confidence(
    conf_alpha: float,
    conf_beta: float | None,
    conf_gamma: float | None,
    conf_delta: float | None,
    compound_id: str,
    assumption: CorrelationAssumption = CorrelationAssumption.NOT_SPECIFIED,
) -> SelectivityConfidence:
    """Compose per-target confidences into a joint selectivity confidence.

    Parameters
    ----------
    conf_alpha:     Confidence alpha is productive [0, 1].
    conf_beta:      Confidence beta is spared [0, 1], or None.
    conf_gamma:     Confidence gamma is spared [0, 1], or None.
    conf_delta:     Confidence delta is spared [0, 1], or None.
    compound_id:    Compound identifier.
    assumption:     Correlation model for composition.

    Returns:
    -------
    `SelectivityConfidence` with both the product (independent) and
    Fréchet lower bound, plus the value under `assumption`.
    """
    available = [c for c in [conf_alpha, conf_beta, conf_gamma, conf_delta] if c is not None]
    if not available:
        raise ValueError("At least conf_alpha is required")
    for c in available:
        if not (0.0 <= c <= 1.0):
            raise ValueError(f"Confidence values must be in [0, 1], got {c}")

    # Product (independent events)
    product = float(np.prod(available))
    # Fréchet lower bound: max(0, sum - (n - 1))
    n = len(available)
    frechet = max(0.0, float(sum(available)) - (n - 1))

    if assumption == CorrelationAssumption.INDEPENDENT:
        joint = product
    elif assumption == CorrelationAssumption.FRECHET_LOWER:
        joint = frechet
    else:
        # NOT_SPECIFIED: return the product (more informative) but note both
        joint = product

    return SelectivityConfidence(
        conf_alpha_productive=conf_alpha,
        conf_beta_spared=conf_beta,
        conf_gamma_spared=conf_gamma,
        conf_delta_spared=conf_delta,
        joint_confidence=round(joint, 6),
        joint_lower_bound=round(frechet, 6),
        correlation_assumption=assumption,
        compound_id=compound_id,
        note=_CONJUNCTION_NOTE,
        algorithm_version=UNCERTAINTY_ALGORITHM_VERSION,
    )

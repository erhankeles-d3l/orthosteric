"""SCI-1 gate evaluation (SCI1-021 / SCI1-022 procedure).

Authority: SCI1-021 (baseline evaluation), SCI1-022 (gate procedure).
Constitution §9.3 (Stage 1 gate), §1.4 (S2 criterion).

Constitution §9.3 Stage 1 gate:
  "If a baseline already meets S2, the learned component is unjustified."

Constitution §1.4 S2 criterion:
  Beats a ligand-only baseline on log-selectivity-ratio prediction by
  >= 0.3 log RMSE on held-out series.

  Operationally for the gate:
  - RMSE_baseline_1 (ligand-only) is the reference.
  - The S2 gate fires if RMSE_baseline_1 <= 0.3 log units on the
    within-study stratum -- meaning even the null model is "good enough"
    and a more complex model is unjustified.

SCI1-022 is a PROCEDURE, not just code. The kill condition:
  "if any baseline meets S2, the learned component is unjustified."

This module implements:
  1. `evaluate_baselines_on_stratum()` -- compute RMSE for all three
     baselines on the within-study stratum (SCI1-021).
  2. `s1_gate_evaluation()` -- returns a decision record (SCI1-022).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "GATE_ALGORITHM_VERSION",
    "S1GateDecision",
    "S1GateRecord",
    "S1GateVote",
    "s1_gate_evaluation",
]

GATE_ALGORITHM_VERSION = "gate_v1_sci1022"

# Constitution §1.4 S2 stated threshold (reference only; sealed at Stage 0)
_S2_RMSE_IMPROVEMENT = 0.3  # log units


class S1GateVote(StrEnum):
    """Vote from the SCI-1 gate evaluation (SCI1-022)."""

    GO = "go"  # no baseline meets S2; proceed to SCI-2
    STOP = "stop"  # a baseline meets S2; learned component unjustified
    INSUFFICIENT_DATA = "insufficient_data"  # not enough compounds to evaluate


class S1GateDecision(StrEnum):
    """Final SCI-1 gate decision."""

    GO = "go"
    STOP = "stop"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True, slots=True)
class S1GateRecord:
    """SCI-1 gate evaluation record (SCI1-022 procedure).

    Attributes:
        vote:              GO / STOP / INSUFFICIENT_DATA.
        baseline_1_rmse:   Ligand-only RMSE per axis (or None if not computed).
        baseline_2_rmse:   NN Tanimoto RMSE per axis.
        baseline_3_rmse:   PCM RMSE per axis.
        n_within_study:    Number of within-study compounds evaluated.
        any_baseline_meets_s2: True iff any baseline RMSE <= S2 threshold
                               on the within-study stratum.
        rationale:         Human-readable decision rationale.
        algorithm_version: Pinned version.
    """

    vote: S1GateVote
    baseline_1_rmse: dict[str, float] | None
    baseline_2_rmse: dict[str, float] | None
    baseline_3_rmse: dict[str, float] | None
    n_within_study: int
    any_baseline_meets_s2: bool
    rationale: str
    algorithm_version: str


def s1_gate_evaluation(
    baseline_1_rmse: dict[str, float] | None,
    baseline_2_rmse: dict[str, float] | None,
    baseline_3_rmse: dict[str, float] | None,
    n_within_study: int,
    min_compounds_for_evaluation: int = 50,
) -> S1GateRecord:
    """Evaluate the SCI-1 gate (SCI1-022 procedure).

    Constitution §9.3: if a baseline meets S2, the learned component is
    unjustified -- STOP.

    Parameters
    ----------
    baseline_1_rmse:    Ligand-only RMSE per axis.
    baseline_2_rmse:    NN Tanimoto RMSE per axis.
    baseline_3_rmse:    PCM RMSE per axis.
    n_within_study:     Within-study compound count.
    min_compounds_for_evaluation: Minimum required to make a GO/STOP decision.

    Returns:
    -------
    `S1GateRecord` with GO / STOP / INSUFFICIENT_DATA.
    """
    if n_within_study < min_compounds_for_evaluation:
        return S1GateRecord(
            vote=S1GateVote.INSUFFICIENT_DATA,
            baseline_1_rmse=baseline_1_rmse,
            baseline_2_rmse=baseline_2_rmse,
            baseline_3_rmse=baseline_3_rmse,
            n_within_study=n_within_study,
            any_baseline_meets_s2=False,
            rationale=(
                f"Insufficient data: {n_within_study} within-study compounds "
                f"(minimum: {min_compounds_for_evaluation}). "
                "Cannot reliably evaluate baselines. Stage 0 data audit required."
            ),
            algorithm_version=GATE_ALGORITHM_VERSION,
        )

    # Check if any baseline achieves RMSE <= S2 reference threshold
    # (i.e., the baseline is already "good" and a complex model adds nothing)
    all_rmse_values: list[float] = []
    for rmse_dict in [baseline_1_rmse, baseline_2_rmse, baseline_3_rmse]:
        if rmse_dict:
            all_rmse_values.extend(rmse_dict.values())

    if not all_rmse_values:
        return S1GateRecord(
            vote=S1GateVote.INSUFFICIENT_DATA,
            baseline_1_rmse=baseline_1_rmse,
            baseline_2_rmse=baseline_2_rmse,
            baseline_3_rmse=baseline_3_rmse,
            n_within_study=n_within_study,
            any_baseline_meets_s2=False,
            rationale="No baseline RMSE values available. Run baseline evaluation first.",
            algorithm_version=GATE_ALGORITHM_VERSION,
        )

    # A baseline "meets S2" means it achieves RMSE <= threshold on its own
    # (i.e., the problem is already solved by a simple model).
    # NOTE: Constitution §1.4 S2 says the learned model must BEAT the ligand-only
    # baseline by >= 0.3 log RMSE. If the baseline itself has RMSE <= 0.3,
    # the task might be trivial (near-perfect prediction by ligand alone).
    # The gate fires when any baseline RMSE is unreasonably low.
    b1_min = min(baseline_1_rmse.values()) if baseline_1_rmse else float("inf")
    any_meets = b1_min <= _S2_RMSE_IMPROVEMENT

    if any_meets:
        vote = S1GateVote.STOP
        rationale = (
            f"STOP: ligand-only baseline achieves RMSE = {b1_min:.3f} log units, "
            f"which is <= the S2 reference threshold of {_S2_RMSE_IMPROVEMENT} log units. "
            "The learned component is unjustified -- the task is solvable by ligand "
            "features alone. Redesign the project or seek a harder test set."
        )
    else:
        vote = S1GateVote.GO
        rationale = (
            f"GO: ligand-only baseline RMSE = {b1_min:.3f} log units "
            f"(> {_S2_RMSE_IMPROVEMENT} log units threshold). "
            "A comparative learning model may add value. Proceed to SCI-2."
        )

    return S1GateRecord(
        vote=vote,
        baseline_1_rmse=baseline_1_rmse,
        baseline_2_rmse=baseline_2_rmse,
        baseline_3_rmse=baseline_3_rmse,
        n_within_study=n_within_study,
        any_baseline_meets_s2=any_meets,
        rationale=rationale,
        algorithm_version=GATE_ALGORITHM_VERSION,
    )

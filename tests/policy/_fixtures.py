"""Shared synthetic prediction builders.

Every value here is explicitly synthetic. No prediction, activity value, or
model output in this package is derived from real data or presented as a
scientific result (CLAUDE.md §1).
"""

from __future__ import annotations

from decimal import Decimal

from orthosteric.data.provenance.enums import MeasurementClass
from orthosteric.policy import (
    BindingClass,
    IsoformPrediction,
    NormalizationStatus,
    PolicyConfig,
    PredictionInput,
)

ALPHA = "PI3Kalpha"
BETA = "PI3Kbeta"
GAMMA = "PI3Kgamma"
DELTA = "PI3Kdelta"
OFF_TARGETS = (BETA, GAMMA, DELTA)

SYNTHETIC_SNAPSHOT_SHA = "0" * 64


def config(**overrides: object) -> PolicyConfig:
    base: dict[str, object] = {
        "config_version": "test-config-1",
        "reference_isoform": ALPHA,
        "off_target_isoforms": OFF_TARGETS,
    }
    base.update(overrides)
    return PolicyConfig(**base)  # type: ignore[arg-type]


def iso(
    isoform: str,
    p_activity: str | None,
    *,
    binding_class: BindingClass = BindingClass.PRODUCTIVE,
    measurement_class: MeasurementClass = MeasurementClass.BIOCHEMICAL,
    confidence: float | None = None,
    interval_width: float | None = None,
) -> IsoformPrediction:
    return IsoformPrediction(
        isoform=isoform,
        p_activity=Decimal(p_activity) if p_activity is not None else None,
        binding_class=binding_class,
        measurement_class=measurement_class,
        confidence=confidence,
        interval_width=interval_width,
    )


def prediction(
    *predictions: IsoformPrediction,
    normalization: NormalizationStatus = NormalizationStatus.CHENG_PRUSOFF_APPLIED,
    prediction_id: str = "PRED-1",
    compound_id: str = "ABCDEFGHIJKLMNOPQRSTUVWXY-Z",
    model_version: str = "gen-1",
) -> PredictionInput:
    return PredictionInput(
        prediction_id=prediction_id,
        compound_id=compound_id,
        predictions=predictions,
        normalization=normalization,
        model_version=model_version,
        evidence_snapshot_sha256=SYNTHETIC_SNAPSHOT_SHA,
    )


def worked_example() -> PredictionInput:
    """The ADR-0008 / README worked example, in pAct terms.

    alpha 0.5 nM -> pAct 9.301; beta 85 nM -> 7.071;
    gamma 170 nM -> 6.770; delta 120 nM -> 6.921.
    Expected: fold beta ~170, gamma ~340, delta ~240; Smin ~170 -> TIER_C.
    """
    return prediction(
        iso(ALPHA, "9.301"),
        iso(BETA, "7.071"),
        iso(GAMMA, "6.770"),
        iso(DELTA, "6.921"),
    )

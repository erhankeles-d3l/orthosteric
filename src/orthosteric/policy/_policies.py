"""Concrete decision policies.

Authority: ADR-0008 [Architectural].
Constitution sections served: §2.2, §2.3(3), §2.3(4), §2.3(6), §2.4.

Each policy classifies a prediction. None modifies evidence, harmonized data,
features, or models — `PredictionInput` and its members are frozen.

Selectivity representation
--------------------------
Constitution §2.3(4) defines the primary target in log space:
``S1 = (pAct_a, pAct_a - pAct_b, pAct_a - pAct_g, pAct_a - pAct_d)``. The
fold-selectivity a medicinal chemist reads as "170x" is the antilog of the same
quantity: ``S_x = 10 ** (pAct_a - pAct_x)``, identical to
``Activity_x / Activity_a`` when activities are IC50/Ki concentrations. This
module computes in log space (the governed representation) and exposes
fold-change as a derived view, so both are available and neither is a separate
source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from orthosteric.policy._base import Policy, PolicyOutcome, PolicyStatus
from orthosteric.policy._config import PolicyConfig
from orthosteric.policy._prediction import (
    BindingClass,
    IsoformPrediction,
    NormalizationStatus,
    PredictionInput,
)

__all__ = [
    "AUDITOR5_ADVISORY",
    "ConfidencePolicy",
    "PotencyPolicy",
    "SelectivityPolicy",
    "SelectivityVector",
    "UncertaintyPolicy",
]

AUDITOR5_ADVISORY = (
    "AUDITOR-5/NOT_NORMALIZED: cross-isoform fold-selectivity computed from a "
    "potency metric that has not undergone Cheng-Prusoff normalization. The "
    "Class I isoforms differ in ATP Km and IC50 depends on assay [ATP] "
    "(Constitution §2.3 preamble), so this value is not comparable across "
    "assays with differing [ATP]. Cheng-Prusoff normalization is blocked: "
    "AUDITOR-5 is INSUFFICIENT_EVIDENCE (no authoritative per-isoform ATP Km "
    "source). Usable for internal prioritization only; never criterion-eligible."
)


@dataclass(frozen=True, slots=True)
class SelectivityVector:
    """The full per-off-target selectivity vector for one compound.

    Retained alongside the scalar classification so downstream analysis is not
    limited to ``Smin`` (which discards which isoform was the constraint).

    Attributes:
        reference_isoform: Isoform selectivity is measured against.
        log_differences: ``{isoform: pAct_reference - pAct_isoform}``.
        fold_selectivities: ``{isoform: 10 ** log_difference}``.
        min_fold: ``Smin`` — the minimum across `fold_selectivities`.
        limiting_isoform: The isoform attaining `min_fold`; the binding
            constraint on this compound's selectivity.
    """

    reference_isoform: str
    log_differences: dict[str, Decimal]
    fold_selectivities: dict[str, Decimal]
    min_fold: Decimal
    limiting_isoform: str

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "fold_selectivities": {
                k: format(v, "f") for k, v in sorted(self.fold_selectivities.items())
            },
            "limiting_isoform": self.limiting_isoform,
            "log_differences": {k: format(v, "f") for k, v in sorted(self.log_differences.items())},
            "min_fold": format(self.min_fold, "f"),
            "reference_isoform": self.reference_isoform,
        }


class SelectivityPolicy(Policy):
    """Classifies fold-selectivity into configured prioritization tiers.

    Governed gates applied before any tier is assigned:

    * **§2.3(6) potency floor** — if ``pAct_reference`` is below the configured
      floor, selectivity is *undefined*. The outcome is
      `UNDEFINED_POTENCY_FLOOR`, not a low tier: "undefined" and "poorly
      selective" are different statements.
    * **§2.2 Indeterminate** — if the reference or any required off-target is
      `INDETERMINATE`, there is no valid selectivity claim. §2.2: Indeterminate
      "is not weak evidence of sparing and contributes zero to selectivity
      claims." Reading it as sparing would manufacture selectivity from absence
      of evidence.
    * **§2.3(3) measurement class** — biochemical and cellular selectivity are
      separate targets, never pooled. A prediction mixing classes across the
      isoforms needed is `UNDEFINED_MIXED_CLASS`.
    * **Missing prediction** — an isoform with no point estimate is missing,
      not inactive, and yields `UNDEFINED_MISSING_PREDICTION`.
    """

    _POLICY_ID = "selectivity_tier"
    _POLICY_VERSION = "1.0.0"

    def __init__(self, config: PolicyConfig) -> None:
        self._config = config

    @property
    def policy_id(self) -> str:
        return self._POLICY_ID

    @property
    def policy_version(self) -> str:
        return self._POLICY_VERSION

    def evaluate(self, prediction: PredictionInput) -> PolicyOutcome:
        cfg = self._config
        validated = self._validate(prediction)
        if isinstance(validated, PolicyOutcome):
            return validated
        reference_p_activity, off_targets = validated

        vector = _selectivity_vector(cfg.reference_isoform, reference_p_activity, off_targets)
        classification = cfg.selectivity_tiers.classify(vector.min_fold)

        flags: list[str] = list(cfg.governance_deviations())
        if prediction.normalization == NormalizationStatus.NOT_NORMALIZED:
            flags.append(AUDITOR5_ADVISORY)

        return PolicyOutcome(
            policy_id=self._POLICY_ID,
            policy_version=self._POLICY_VERSION,
            status=PolicyStatus.CLASSIFIED,
            classification=classification,
            detail={"selectivity_vector": vector.to_canonical_dict()},
            rationale=(
                f"Smin={format(vector.min_fold, 'f')}x limited by "
                f"{vector.limiting_isoform}; classified {classification} against "
                f"config {cfg.config_version}."
            ),
            governance_flags=tuple(flags),
        )

    def _validate(
        self, prediction: PredictionInput
    ) -> PolicyOutcome | tuple[Decimal, list[tuple[str, Decimal]]]:
        """Apply governed gates.

        Returns a blocking `PolicyOutcome`, or the validated potency values.
        Returning the values rather than the records is what lets the caller
        proceed without narrowing assertions.
        """
        cfg = self._config

        # Single pass over off-targets: partition into resolved and missing,
        # narrowing `p_activity` to Decimal as we go.
        resolved: list[tuple[str, IsoformPrediction]] = []
        off_values: list[tuple[str, Decimal]] = []
        missing: list[str] = []
        for iso in cfg.off_target_isoforms:
            candidate = prediction.get(iso)
            if candidate is None or candidate.p_activity is None:
                missing.append(iso)
            else:
                resolved.append((iso, candidate))
                off_values.append((iso, candidate.p_activity))

        reference = prediction.get(cfg.reference_isoform)
        if reference is None or reference.p_activity is None:
            return self._undefined(
                PolicyStatus.UNDEFINED_MISSING_PREDICTION,
                f"No point estimate for "
                f"{sorted({cfg.reference_isoform, *missing})}. Missing is not "
                "inactive; no selectivity is computed.",
            )
        reference_p_activity = reference.p_activity

        if missing:
            return self._undefined(
                PolicyStatus.UNDEFINED_MISSING_PREDICTION,
                f"No point estimate for {sorted(missing)}. Missing is not "
                "inactive; no selectivity is computed.",
            )

        present = [reference, *[p for _, p in resolved]]

        indeterminate = [
            p.isoform for p in present if p.binding_class == BindingClass.INDETERMINATE
        ]
        if indeterminate:
            return self._undefined(
                PolicyStatus.UNDEFINED_INDETERMINATE,
                f"Indeterminate binding class for {sorted(indeterminate)}. "
                "Constitution §2.2: Indeterminate is not weak evidence of "
                "sparing and contributes zero to selectivity claims.",
            )

        classes = {p.measurement_class for p in present}
        if len(classes) > 1:
            return self._undefined(
                PolicyStatus.UNDEFINED_MIXED_CLASS,
                f"Mixed measurement classes {sorted(c.value for c in classes)}. "
                "Constitution §2.3(3): biochemical and cellular selectivity are "
                "separate targets, never pooled.",
            )

        if reference_p_activity < cfg.potency_floor_p_activity:
            return self._undefined(
                PolicyStatus.UNDEFINED_POTENCY_FLOOR,
                f"pAct({cfg.reference_isoform})="
                f"{format(reference_p_activity, 'f')} is below the potency floor "
                f"{format(cfg.potency_floor_p_activity, 'f')}. Constitution "
                "§2.3(6): selectivity is undefined below the floor - this is not "
                "a low tier.",
                extra_flags=cfg.governance_deviations(),
            )

        return reference_p_activity, off_values

    def _undefined(
        self,
        status: PolicyStatus,
        rationale: str,
        extra_flags: tuple[str, ...] = (),
    ) -> PolicyOutcome:
        return PolicyOutcome(
            policy_id=self._POLICY_ID,
            policy_version=self._POLICY_VERSION,
            status=status,
            classification=None,
            rationale=rationale,
            governance_flags=extra_flags,
        )


class PotencyPolicy(Policy):
    """Classifies whether the reference isoform meets the potency floor.

    Reported separately from selectivity because Constitution §2.3(6) frames
    the objective as "maximize selectivity **subject to** the floor" — the floor
    is a constraint in its own right, not merely a precondition that disappears
    once satisfied.
    """

    _POLICY_ID = "potency_floor"
    _POLICY_VERSION = "1.0.0"

    def __init__(self, config: PolicyConfig) -> None:
        self._config = config

    @property
    def policy_id(self) -> str:
        return self._POLICY_ID

    @property
    def policy_version(self) -> str:
        return self._POLICY_VERSION

    def evaluate(self, prediction: PredictionInput) -> PolicyOutcome:
        cfg = self._config
        reference = prediction.get(cfg.reference_isoform)
        if reference is None or reference.p_activity is None:
            return PolicyOutcome(
                policy_id=self._POLICY_ID,
                policy_version=self._POLICY_VERSION,
                status=PolicyStatus.UNDEFINED_MISSING_PREDICTION,
                classification=None,
                rationale=f"No point estimate for {cfg.reference_isoform}.",
            )
        meets = reference.p_activity >= cfg.potency_floor_p_activity
        return PolicyOutcome(
            policy_id=self._POLICY_ID,
            policy_version=self._POLICY_VERSION,
            status=PolicyStatus.CLASSIFIED,
            classification="PASS" if meets else "FAIL",
            detail={
                "floor": format(cfg.potency_floor_p_activity, "f"),
                "p_activity": format(reference.p_activity, "f"),
            },
            rationale=(
                f"pAct({cfg.reference_isoform})="
                f"{format(reference.p_activity, 'f')} vs floor "
                f"{format(cfg.potency_floor_p_activity, 'f')} (§2.3(6))."
            ),
            governance_flags=cfg.governance_deviations(),
        )


class ConfidencePolicy(Policy):
    """Classifies joint confidence across the isoforms a claim requires.

    Constitution §2.4: a selectivity claim is a conjunction (reference
    productive AND the rest spared), so joint confidence "composes as a product
    over correlated events and is *lower* than the weakest component, not equal
    to it. (v3.x's min-rule was wrong.)" This policy therefore multiplies and
    never takes a minimum. Per-target confidences are reported alongside the
    joint value, as §2.4 also requires.

    The product treats the events as independent, which §2.4 notes they are not.
    Independence is the conservative direction here only if correlations are
    non-negative; the assumption is recorded explicitly in `detail` rather than
    buried, since §2.4 requires the correlation assumption be stated.
    """

    _POLICY_ID = "joint_confidence"
    _POLICY_VERSION = "1.0.0"
    _CORRELATION_ASSUMPTION = "independence_assumed_correlation_unmodelled"

    def __init__(self, config: PolicyConfig) -> None:
        self._config = config

    @property
    def policy_id(self) -> str:
        return self._POLICY_ID

    @property
    def policy_version(self) -> str:
        return self._POLICY_VERSION

    def evaluate(self, prediction: PredictionInput) -> PolicyOutcome:
        cfg = self._config
        needed = (cfg.reference_isoform, *cfg.off_target_isoforms)
        per_target: dict[str, float] = {}
        for iso in needed:
            p = prediction.get(iso)
            if p is None or p.confidence is None:
                return PolicyOutcome(
                    policy_id=self._POLICY_ID,
                    policy_version=self._POLICY_VERSION,
                    status=PolicyStatus.ABSTAINED,
                    classification=None,
                    rationale=(
                        f"No confidence supplied for {iso}; joint confidence is "
                        "not estimated rather than assumed."
                    ),
                )
            per_target[iso] = p.confidence

        joint = 1.0
        for value in per_target.values():
            joint *= value

        return PolicyOutcome(
            policy_id=self._POLICY_ID,
            policy_version=self._POLICY_VERSION,
            status=PolicyStatus.CLASSIFIED,
            classification="PASS" if joint >= cfg.min_confidence else "FAIL",
            detail={
                "correlation_assumption": self._CORRELATION_ASSUMPTION,
                "joint_confidence": joint,
                "min_confidence": cfg.min_confidence,
                "per_target_confidence": dict(sorted(per_target.items())),
                "weakest_component": min(per_target.values()),
            },
            rationale=(
                f"Joint confidence {joint:.6f} (product over {len(per_target)} "
                f"targets, §2.4) vs threshold {cfg.min_confidence}. Weakest "
                f"component {min(per_target.values()):.6f}; the product is at or "
                "below it, never above."
            ),
        )


class UncertaintyPolicy(Policy):
    """Classifies whether predictive intervals respect the label-noise floor.

    Constitution §2.4: "No model may claim precision below the noise floor of
    its labels." The floor is a project measurement — the output of `SCI0-016`,
    which has not run. This policy therefore **abstains** when no floor is
    configured rather than substituting a plausible number: §2.4's "typically
    >= 0.3 log units" is a general observation about assay data, not this
    project's measured floor.
    """

    _POLICY_ID = "uncertainty_floor"
    _POLICY_VERSION = "1.0.0"

    def __init__(self, config: PolicyConfig) -> None:
        self._config = config

    @property
    def policy_id(self) -> str:
        return self._POLICY_ID

    @property
    def policy_version(self) -> str:
        return self._POLICY_VERSION

    def evaluate(self, prediction: PredictionInput) -> PolicyOutcome:
        cfg = self._config
        floor = cfg.label_noise_floor_log_units
        if floor is None:
            return PolicyOutcome(
                policy_id=self._POLICY_ID,
                policy_version=self._POLICY_VERSION,
                status=PolicyStatus.ABSTAINED,
                classification=None,
                rationale=(
                    "No label_noise_floor_log_units configured. The floor is an "
                    "output of SCI0-016, which has not run; §2.4's 'typically "
                    ">= 0.3 log units' is a general observation, not this "
                    "project's measured floor, and is not assumed here."
                ),
                governance_flags=(
                    "RULE_MISSING/SCI0-016: label noise floor not yet measured; "
                    "uncertainty policy abstains.",
                ),
            )

        needed = (cfg.reference_isoform, *cfg.off_target_isoforms)
        widths: dict[str, float] = {}
        for iso in needed:
            p = prediction.get(iso)
            if p is None or p.interval_width is None:
                return PolicyOutcome(
                    policy_id=self._POLICY_ID,
                    policy_version=self._POLICY_VERSION,
                    status=PolicyStatus.ABSTAINED,
                    classification=None,
                    rationale=f"No interval width supplied for {iso}.",
                )
            widths[iso] = p.interval_width

        # A claimed interval narrower than the label noise floor claims
        # precision the labels cannot support (§2.4).
        violating = sorted(iso for iso, w in widths.items() if w < floor)
        return PolicyOutcome(
            policy_id=self._POLICY_ID,
            policy_version=self._POLICY_VERSION,
            status=PolicyStatus.CLASSIFIED,
            classification="FAIL" if violating else "PASS",
            detail={
                "interval_widths": dict(sorted(widths.items())),
                "label_noise_floor_log_units": floor,
                "violating_isoforms": violating,
            },
            rationale=(
                f"Intervals narrower than the {floor} log-unit floor: {violating or 'none'} (§2.4)."
            ),
        )


# ── helpers ───────────────────────────────────────────────────────────────────


def _selectivity_vector(
    reference_isoform: str,
    reference_p_activity: Decimal,
    off_targets: list[tuple[str, Decimal]],
) -> SelectivityVector:
    """Compute log differences and fold selectivities per Constitution §2.3(4).

    ``log_difference = pAct_reference - pAct_offtarget`` and
    ``fold = 10 ** log_difference``, which equals
    ``Activity_offtarget / Activity_reference`` for concentration-valued
    activities.
    """
    log_diffs: dict[str, Decimal] = {}
    folds: dict[str, Decimal] = {}
    for iso, p_activity in off_targets:
        delta = reference_p_activity - p_activity
        log_diffs[iso] = delta
        folds[iso] = Decimal(10) ** delta

    limiting = min(folds, key=lambda k: folds[k])
    return SelectivityVector(
        reference_isoform=reference_isoform,
        log_differences=log_diffs,
        fold_selectivities=folds,
        min_fold=folds[limiting],
        limiting_isoform=limiting,
    )

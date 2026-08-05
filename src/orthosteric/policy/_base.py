"""Common policy interface and outcome type.

Authority: ADR-0008 [Architectural].

Extensibility contract
----------------------
Every policy implements :class:`Policy`. Adding a policy (ADMET,
developability, or any future project-specific rule) means adding a class that
implements this interface and registering the instance with
:class:`~orthosteric.policy.PolicyEngine` at construction. No existing module
changes. The engine iterates whatever it was given.

Criterion firewall (Constitution §1.4)
--------------------------------------
Every :class:`PolicyOutcome` carries ``criterion_eligible = False``. Policy
thresholds express current project prioritization, are expected to change
between projects, and are explicitly not scientific claims about PI3K. The
Constitution's S-criteria thresholds are fixed before training (§1.4) and
sealed by `SCI0-029`; conflating the two would open a route to post-hoc
threshold selection, the failure `R23` describes. The field exists so misuse is
loud in any artefact that serializes an outcome.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from orthosteric.policy._prediction import PredictionInput

__all__ = ["Policy", "PolicyOutcome", "PolicyStatus"]


class PolicyStatus(StrEnum):
    """Outcome status of a single policy evaluation.

    The `UNDEFINED_*` members are distinct from a low classification. A
    compound below the Constitution §2.3(6) potency floor has *undefined*
    selectivity — not weak selectivity — and a compound with an
    `INDETERMINATE` off-target has no valid selectivity claim at all (§2.2),
    rather than a poor one.
    """

    CLASSIFIED = "classified"
    UNDEFINED_POTENCY_FLOOR = "undefined_potency_floor"  # §2.3(6)
    UNDEFINED_INDETERMINATE = "undefined_indeterminate"  # §2.2
    UNDEFINED_MIXED_CLASS = "undefined_mixed_measurement_class"  # §2.3(3)
    UNDEFINED_MISSING_PREDICTION = "undefined_missing_prediction"
    ABSTAINED = "abstained"  # policy declines: required input not supplied
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class PolicyOutcome:
    """Result of evaluating one policy against one prediction.

    Attributes:
        policy_id: Stable policy identifier.
        policy_version: Policy implementation version.
        status: See :class:`PolicyStatus`.
        classification: Policy-specific label (e.g. ``TIER_C``, ``PASS``),
            or ``None`` when `status` is not `CLASSIFIED`.
        detail: Derived quantities the policy computed, for audit. Values are
            JSON-serializable.
        rationale: Human-readable explanation, citing the governing rule where
            a Constitution section determined the outcome.
        governance_flags: Advisories that do not change the classification but
            must travel with it — e.g. the `AUDITOR-5` non-normalized-metric
            advisory.
        criterion_eligible: Always ``False``. See module docstring.
    """

    policy_id: str
    policy_version: str
    status: PolicyStatus
    classification: str | None
    detail: Mapping[str, Any] = field(default_factory=dict)
    rationale: str = ""
    governance_flags: tuple[str, ...] = ()
    criterion_eligible: bool = False

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "criterion_eligible": self.criterion_eligible,
            "detail": dict(sorted(self.detail.items())),
            "governance_flags": list(self.governance_flags),
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "rationale": self.rationale,
            "status": self.status.value,
        }


class Policy(ABC):
    """Interface every decision policy implements.

    Implementations must be deterministic: the same `PredictionInput` and the
    same configuration must produce the same `PolicyOutcome`, with no reliance
    on wall-clock time, randomness, or mutable global state.

    Implementations must not mutate the prediction, the evidence corpus, any
    feature representation, or any model. `PredictionInput` and its members are
    frozen dataclasses, so this is enforced by the type rather than by
    convention.
    """

    @property
    @abstractmethod
    def policy_id(self) -> str:
        """Stable identifier, recorded in decision provenance."""

    @property
    @abstractmethod
    def policy_version(self) -> str:
        """Implementation version, recorded in decision provenance."""

    @abstractmethod
    def evaluate(self, prediction: PredictionInput) -> PolicyOutcome:
        """Classify `prediction`. Must not raise on well-formed input."""

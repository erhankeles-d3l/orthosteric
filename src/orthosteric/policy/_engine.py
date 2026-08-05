"""Policy engine and decision provenance.

Authority: ADR-0008 [Architectural].

Determinism and the timestamp
-----------------------------
`SCI0-011` established the project's rule for this: a timestamp is provenance
metadata and must not make otherwise identical artefacts non-deterministic.
The same rule applies here. `decision_content_sha256` is computed over the
prediction, the policy configuration, the participating policy identifiers and
versions, and the software provenance — **not** over
`decision_timestamp_utc`. Two evaluations of the same prediction under the same
configuration and toolchain therefore produce an identical content hash, while
still recording when each was taken.

Canonical serialization is implemented locally rather than reused from
`data.snapshots._builder`, because ENG §2 import contract 1 forbids
cross-package imports of `_`-prefixed internal modules. The conventions match
(sorted keys, compact separators, `Decimal` as fixed-point text) so the two
produce comparable output.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from orthosteric.data.snapshots import SoftwareProvenance
from orthosteric.policy._base import Policy, PolicyOutcome
from orthosteric.policy._config import PolicyConfig
from orthosteric.policy._prediction import PredictionInput

__all__ = ["DecisionProvenance", "DecisionRecord", "PolicyEngine"]

DECISION_SCHEMA_VERSION = "policy_decision_v1"


def _canonical_default(obj: object) -> object:
    if isinstance(obj, Decimal):
        return format(obj, "f")
    if hasattr(obj, "value"):  # StrEnum
        return obj.value
    return str(obj)


def _stable_json(obj: object) -> str:
    return json.dumps(
        obj, sort_keys=True, default=_canonical_default, separators=(",", ":"), ensure_ascii=True
    )


@dataclass(frozen=True, slots=True)
class DecisionProvenance:
    """Everything needed to reproduce one decision.

    Attributes:
        schema_version: Decision schema version.
        prediction_id: Identifier of the prediction classified.
        compound_id: Compound identity (InChIKey / internal_id).
        model_version: Model generation that produced the prediction.
        evidence_snapshot_sha256: `SCI0-011` snapshot hash the model was
            trained against — the anchor that makes a decision reproducible
            from the immutable corpus.
        policy_config_version: `PolicyConfig.config_version`.
        threshold_configuration: The full resolved configuration, not a
            reference to it, so a decision remains interpretable even if the
            configuration file later changes.
        policies: ``((policy_id, policy_version), ...)`` for every policy that
            participated, in evaluation order.
        software: Toolchain provenance, reused from `SCI0-011` rather than
            redefined.
        decision_timestamp_utc: When the decision was taken. Excluded from
            `decision_content_sha256` — see module docstring.
        decision_content_sha256: Content hash over prediction + configuration +
            policies + software.
    """

    schema_version: str
    prediction_id: str
    compound_id: str
    model_version: str
    evidence_snapshot_sha256: str
    policy_config_version: str
    threshold_configuration: dict[str, Any]
    policies: tuple[tuple[str, str], ...]
    software: SoftwareProvenance
    decision_timestamp_utc: str
    decision_content_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "compound_id": self.compound_id,
            "decision_content_sha256": self.decision_content_sha256,
            "decision_timestamp_utc": self.decision_timestamp_utc,
            "evidence_snapshot_sha256": self.evidence_snapshot_sha256,
            "model_version": self.model_version,
            "policies": [list(p) for p in self.policies],
            "policy_config_version": self.policy_config_version,
            "prediction_id": self.prediction_id,
            "schema_version": self.schema_version,
            "software": self.software.to_canonical_dict(),
            "threshold_configuration": self.threshold_configuration,
        }


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """The complete, immutable result of evaluating a prediction.

    Attributes:
        outcomes: One `PolicyOutcome` per registered policy, in order.
        provenance: See :class:`DecisionProvenance`.
        governance_flags: Union of all outcome flags, deduplicated and sorted,
            so a consumer need not walk every outcome to notice one.
        criterion_eligible: Always ``False`` (ADR-0008 criterion firewall).
            No decision record may be reported as, or used to compute, S1-S10.
    """

    outcomes: tuple[PolicyOutcome, ...]
    provenance: DecisionProvenance
    governance_flags: tuple[str, ...] = field(default_factory=tuple)
    criterion_eligible: bool = False

    def outcome_for(self, policy_id: str) -> PolicyOutcome | None:
        for o in self.outcomes:
            if o.policy_id == policy_id:
                return o
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion_eligible": self.criterion_eligible,
            "governance_flags": list(self.governance_flags),
            "outcomes": [o.to_canonical_dict() for o in self.outcomes],
            "provenance": self.provenance.to_dict(),
        }


class PolicyEngine:
    """Runs a set of policies over predictions and records provenance.

    Extensibility: the engine has no knowledge of any specific policy. Adding
    one means passing another :class:`~orthosteric.policy.Policy` instance to
    the constructor; no code here changes.

    The engine never modifies the prediction, the evidence corpus, features, or
    models. It reads a frozen `PredictionInput` and returns a frozen
    `DecisionRecord`.
    """

    def __init__(
        self,
        policies: Sequence[Policy],
        config: PolicyConfig,
        software: SoftwareProvenance | None = None,
    ) -> None:
        if not policies:
            raise ValueError("PolicyEngine requires at least one policy")
        ids = [p.policy_id for p in policies]
        if len(set(ids)) != len(ids):
            raise ValueError(f"Duplicate policy_id values registered: {ids}")
        self._policies = tuple(policies)
        self._config = config
        self._software = software if software is not None else SoftwareProvenance.collect()

    @property
    def registered_policies(self) -> tuple[tuple[str, str], ...]:
        return tuple((p.policy_id, p.policy_version) for p in self._policies)

    def decide(self, prediction: PredictionInput) -> DecisionRecord:
        """Evaluate every registered policy against `prediction`."""
        outcomes = tuple(p.evaluate(prediction) for p in self._policies)

        flags = sorted({f for o in outcomes for f in o.governance_flags})

        content = _stable_json(
            {
                "policies": [list(p) for p in self.registered_policies],
                "prediction": prediction.to_canonical_dict(),
                "schema_version": DECISION_SCHEMA_VERSION,
                "software": self._software.to_canonical_dict(),
                "threshold_configuration": self._config.to_canonical_dict(),
            }
        )
        content_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()

        provenance = DecisionProvenance(
            schema_version=DECISION_SCHEMA_VERSION,
            prediction_id=prediction.prediction_id,
            compound_id=prediction.compound_id,
            model_version=prediction.model_version,
            evidence_snapshot_sha256=prediction.evidence_snapshot_sha256,
            policy_config_version=self._config.config_version,
            threshold_configuration=self._config.to_canonical_dict(),
            policies=self.registered_policies,
            software=self._software,
            decision_timestamp_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            decision_content_sha256=content_sha,
        )

        return DecisionRecord(
            outcomes=outcomes,
            provenance=provenance,
            governance_flags=tuple(flags),
        )

    def decide_batch(self, predictions: Sequence[PredictionInput]) -> tuple[DecisionRecord, ...]:
        """Evaluate a batch. Order of the input sequence is preserved."""
        return tuple(self.decide(p) for p in predictions)

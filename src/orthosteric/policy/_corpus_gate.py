"""Corpus quality gate decision.

The final stage of the profile-to-decision pipeline.

Authority: `ADR-0009` §5; `GDR-003` §4 (the exact aggregation rule).

`CorpusQualityGatePolicy` is a small sibling construct to the `Policy` ABC
(`ADR-0008`, `_base.py`), not an implementation of it: its input is a
`CorpusQualityAssessment` (`quality/`), not a `PredictionInput`. The two
kinds of decision — a prediction-level classification and a corpus-adequacy
gate — are genuinely different, and forcing one interface onto both would
hide that difference rather than express it (`ADR-0009` §5, alternatives
considered).

Criterion firewall (unchanged from `ADR-0008`): `GateDecision.
criterion_eligible` is always `False`. A corpus-adequacy gate decision is not
a Constitution `S1`-`S10` criterion either.

The policy layer computes no statistics itself: `evaluate()` takes only an
already-computed `CorpusQualityAssessment` and reads nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from orthosteric.quality import CorpusQualityAssessment, DimensionStatus

__all__ = ["CorpusQualityGatePolicy", "GateDecision", "GateStatus"]


class GateStatus(StrEnum):
    """Overall recommendation.

    See `GDR-003` §4 for the exact rule that produces each value —
    categorical set-membership logic, never a weighted score.
    """

    PROCEED = "proceed"
    WARNING = "warning"
    REDESIGN = "redesign"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class GateDecision:
    """Result of applying the `GDR-003` §4 aggregation rule to one assessment.

    Attributes:
        status: See `GateStatus`.
        rationale: Names which dimension(s) drove the outcome.
        dimension_summary: ``{dimension_name: status.value}`` for every
            assessed dimension — "no information may be hidden."
        assessment_content_sha256: The `CorpusQualityAssessment` this
            decision was computed from — completes the traceability chain
            Decision -> Assessment -> Profile -> Snapshot -> Raw evidence.
        policy_id: Stable identifier.
        policy_version: Implementation version.
        criterion_eligible: Always `False` (ADR-0008/ADR-0009 firewall).
    """

    status: GateStatus
    rationale: str
    dimension_summary: dict[str, str]
    assessment_content_sha256: str
    policy_id: str
    policy_version: str
    criterion_eligible: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "assessment_content_sha256": self.assessment_content_sha256,
            "criterion_eligible": self.criterion_eligible,
            "dimension_summary": dict(sorted(self.dimension_summary.items())),
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "rationale": self.rationale,
            "status": self.status.value,
        }


class CorpusQualityGatePolicy:
    """Applies the GDR-003 §4 aggregation rule to a `CorpusQualityAssessment`.

    ```
    STOP      if any dimension is STRUCTURALLY_DEGENERATE
    REDESIGN  else if any dimension is GOVERNED_THRESHOLD_NOT_MET
    WARNING   else if any dimension is WARNING, INSUFFICIENT_DATA, or
                   NOT_YET_AVAILABLE
    PROCEED   otherwise
    ```

    Fail-closed: `INSUFFICIENT_DATA` and `NOT_YET_AVAILABLE` fold into
    `WARNING`, never `PROCEED` — an assessed dimension with no data is never
    silently treated as adequate.
    """

    policy_id = "corpus_quality_gate"
    policy_version = "1.0.0"

    def evaluate(self, assessment: CorpusQualityAssessment) -> GateDecision:
        summary = {d.dimension: d.status.value for d in assessment.dimensions}

        degenerate = [
            d.dimension
            for d in assessment.dimensions
            if d.status == DimensionStatus.STRUCTURALLY_DEGENERATE
        ]
        if degenerate:
            return self._decision(
                GateStatus.STOP,
                f"STRUCTURALLY_DEGENERATE in {sorted(degenerate)}: the corpus "
                "cannot support the comparative learning task as currently "
                "assembled.",
                summary,
                assessment.assessment_content_sha256,
            )

        not_met = [
            d.dimension
            for d in assessment.dimensions
            if d.status == DimensionStatus.GOVERNED_THRESHOLD_NOT_MET
        ]
        if not_met:
            return self._decision(
                GateStatus.REDESIGN,
                f"GOVERNED_THRESHOLD_NOT_MET in {sorted(not_met)}: an "
                "already-sealed Constitution or Governance Decision Record "
                "criterion is not satisfied.",
                summary,
                assessment.assessment_content_sha256,
            )

        warn_like = {
            DimensionStatus.WARNING,
            DimensionStatus.INSUFFICIENT_DATA,
            DimensionStatus.NOT_YET_AVAILABLE,
        }
        warned = [d.dimension for d in assessment.dimensions if d.status in warn_like]
        if warned:
            return self._decision(
                GateStatus.WARNING,
                f"Non-fatal concern(s) in {sorted(warned)}: reviewed at the "
                "SCI0-031 gate before proceeding, per GDR-002/GDR-003.",
                summary,
                assessment.assessment_content_sha256,
            )

        return self._decision(
            GateStatus.PROCEED,
            "No dimension flagged STRUCTURALLY_DEGENERATE, "
            "GOVERNED_THRESHOLD_NOT_MET, WARNING, INSUFFICIENT_DATA, or "
            "NOT_YET_AVAILABLE.",
            summary,
            assessment.assessment_content_sha256,
        )

    def _decision(
        self,
        status: GateStatus,
        rationale: str,
        summary: dict[str, str],
        assessment_sha: str,
    ) -> GateDecision:
        return GateDecision(
            status=status,
            rationale=rationale,
            dimension_summary=summary,
            assessment_content_sha256=assessment_sha,
            policy_id=self.policy_id,
            policy_version=self.policy_version,
        )

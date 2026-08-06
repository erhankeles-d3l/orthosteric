"""Corpus lifecycle pipeline — chains CorpusSnapshotV2 → Profile → QA → Gate → Eligibility.

This module is in ``policy/`` because it is the only layer that can import
from both ``quality/`` (CorpusQualityAssessor, CorpusQualityAssessment) and
``data/`` (CorpusSnapshotV2, CorpusProfile, CorpusDataMode).  No layer below
``policy/`` can reach ``quality/``.

The pipeline enforces the lifecycle order:

    CorpusSnapshotV2
          |
          CorpusProfile          (computed from snapshot — data/)
          |
          CorpusQualityAssessment  (computed from profile — quality/)
          |
          GateDecision           (computed from assessment — policy/)
          |
          LifecyclePipelineResult (eligibility + provenance)

A Model Generation may ONLY be registered if the result is eligible and if
the data mode is SCIENTIFIC_CORPUS (enforced here).  Synthetic fixtures and
development-real snapshots are explicitly rejected.

Authority: SCI2-001 lifecycle requirements; ADR-0009; ADR-0008; GDR-004.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from orthosteric.data.corpus_lifecycle import (
    CorpusDataMode,
    CorpusLifecycleStage,
    DataModeViolation,
)
from orthosteric.data.snapshots._builder import CorpusSnapshotV2
from orthosteric.data.snapshots._profile import CorpusProfile
from orthosteric.data.snapshots._registry import CorpusSnapshotRegistry
from orthosteric.learning._interfaces import (
    AD_ALGORITHM_ID,
    ALPHAFOLD_TREATMENT_ID,
    LOSS_FUNCTION_ID,
    UNCERTAINTY_METHOD_ID,
    ModelGenerationRecord,
)
from orthosteric.policy._corpus_gate import CorpusQualityGatePolicy, GateDecision, GateStatus
from orthosteric.quality._assessment import CorpusQualityAssessment, CorpusQualityAssessor

__all__ = [
    "LIFECYCLE_PIPELINE_VERSION",
    "CorpusLifecyclePipeline",
    "LifecycleEligibility",
    "LifecyclePipelineResult",
]

LIFECYCLE_PIPELINE_VERSION = "lifecycle_pipeline_v1"


# ── Eligibility vocabulary ─────────────────────────────────────────────────────


class LifecycleEligibility(StrEnum):
    """Whether a snapshot may be used to register a Model Generation.

    Eligible states require gate = PROCEED or WARNING AND data mode =
    SCIENTIFIC_CORPUS.  All other states are ineligible.
    """

    ELIGIBLE = "eligible"
    INELIGIBLE_GATE_STOP = "ineligible_gate_stop"
    INELIGIBLE_GATE_REDESIGN = "ineligible_gate_redesign"
    INELIGIBLE_DATA_MODE = "ineligible_data_mode"
    PENDING = "pending"  # pipeline not fully run yet


# ── Pipeline result ─────────────────────────────────────────────────────────────


def _stable_json(obj: Any) -> str:
    def default(o: Any) -> Any:
        if hasattr(o, "value"):
            return o.value
        return str(o)

    return json.dumps(
        obj, sort_keys=True, default=default, separators=(",", ":"), ensure_ascii=True
    )


@dataclass(frozen=True, slots=True)
class LifecyclePipelineResult:
    """Complete lifecycle evaluation for one corpus snapshot.

    Attributes:
    ----------
    snapshot_sha:
        SHA-256 of the evaluated snapshot.
    data_mode:
        Data mode label of the snapshot.
    eligibility:
        Whether the snapshot may serve as a training snapshot.
    lifecycle_stage:
        Most advanced stage the snapshot reached in this run.
    profile:
        Computed CorpusProfile, or None if computation was not requested.
    assessment:
        CorpusQualityAssessment, or None if quality assessment was not run.
    gate_decision:
        GateDecision, or None if gate was not evaluated.
    eligible_for_training:
        True iff eligibility == ELIGIBLE.
    ineligibility_reason:
        Human-readable explanation when not eligible.
    pipeline_version:
        Version of this pipeline module.
    created_at_utc:
        ISO-8601 UTC timestamp (provenance only; excluded from result SHA).
    result_sha256:
        Content hash of this result (excluding ``created_at_utc``).
    """

    snapshot_sha: str
    data_mode: CorpusDataMode
    eligibility: LifecycleEligibility
    lifecycle_stage: CorpusLifecycleStage
    profile: CorpusProfile | None
    assessment: CorpusQualityAssessment | None
    gate_decision: GateDecision | None
    eligible_for_training: bool
    ineligibility_reason: str | None
    pipeline_version: str
    created_at_utc: str
    result_sha256: str


def _build_result(
    snapshot_sha: str,
    data_mode: CorpusDataMode,
    eligibility: LifecycleEligibility,
    lifecycle_stage: CorpusLifecycleStage,
    profile: CorpusProfile | None,
    assessment: CorpusQualityAssessment | None,
    gate_decision: GateDecision | None,
    ineligibility_reason: str | None,
) -> LifecyclePipelineResult:
    eligible = eligibility == LifecycleEligibility.ELIGIBLE
    payload = _stable_json(
        {
            "assessment_sha": assessment.assessment_content_sha256 if assessment else None,
            "data_mode": data_mode.value,
            "eligibility": eligibility.value,
            "gate_decision_status": gate_decision.status.value if gate_decision else None,
            "lifecycle_stage": lifecycle_stage.value,
            "pipeline_version": LIFECYCLE_PIPELINE_VERSION,
            "profile_sha": profile.profile_sha256 if profile else None,
            "snapshot_sha": snapshot_sha,
        }
    )
    result_sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return LifecyclePipelineResult(
        snapshot_sha=snapshot_sha,
        data_mode=data_mode,
        eligibility=eligibility,
        lifecycle_stage=lifecycle_stage,
        profile=profile,
        assessment=assessment,
        gate_decision=gate_decision,
        eligible_for_training=eligible,
        ineligibility_reason=ineligibility_reason,
        pipeline_version=LIFECYCLE_PIPELINE_VERSION,
        created_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        result_sha256=result_sha,
    )


# ── Pipeline ──────────────────────────────────────────────────────────────────


class CorpusLifecyclePipeline:
    """Chains CorpusProfile → CorpusQualityAssessment → GateDecision → Eligibility.

    Usage
    -----
    ```python
    pipeline = CorpusLifecyclePipeline(assessor=assessor, gate_policy=gate)
    result = pipeline.run(snapshot, data_mode=CorpusDataMode.SCIENTIFIC_CORPUS, profile=profile)
    if result.eligible_for_training:
        mg = pipeline.register_model_generation(result, snapshot, ...)
    ```

    Parameters
    ----------
    assessor:
        Configured ``CorpusQualityAssessor`` instance.
    gate_policy:
        ``CorpusQualityGatePolicy`` instance.
    registry:
        Optional ``CorpusSnapshotRegistry`` to update automatically on each run
        and model-generation registration.
    """

    def __init__(
        self,
        assessor: CorpusQualityAssessor,
        gate_policy: CorpusQualityGatePolicy,
        registry: CorpusSnapshotRegistry | None = None,
    ) -> None:
        self._assessor = assessor
        self._gate = gate_policy
        self._registry = registry

    def run(
        self,
        snapshot: CorpusSnapshotV2,
        data_mode: CorpusDataMode,
        profile: CorpusProfile,
    ) -> LifecyclePipelineResult:
        """Run the full lifecycle evaluation for a snapshot.

        Parameters
        ----------
        snapshot:
            Immutable corpus snapshot to evaluate.
        data_mode:
            The data-mode classification for this snapshot.
        profile:
            Pre-computed CorpusProfile for this snapshot.  The profile must
            have been produced from the same snapshot (callers are responsible
            for ensuring this — the pipeline does not re-derive the profile).

        Returns:
        -------
        LifecyclePipelineResult
            Full eligibility result.
        """
        sha = snapshot.manifest.snapshot_sha256

        # Step 1 — data mode check
        if data_mode == CorpusDataMode.SYNTHETIC_FIXTURE:
            result = _build_result(
                sha,
                data_mode,
                eligibility=LifecycleEligibility.INELIGIBLE_DATA_MODE,
                lifecycle_stage=CorpusLifecycleStage.PROFILE_COMPUTED,
                profile=profile,
                assessment=None,
                gate_decision=None,
                ineligibility_reason=(
                    "Synthetic fixtures are never eligible for model training "
                    "(CorpusDataMode.SYNTHETIC_FIXTURE)."
                ),
            )
            self._update_registry(snapshot, data_mode, CorpusLifecycleStage.PROFILE_COMPUTED)
            return result

        # Step 2 — quality assessment
        assessment = self._assessor.assess(profile)
        self._update_registry(snapshot, data_mode, CorpusLifecycleStage.QUALITY_ASSESSED)

        # Step 3 — gate decision
        gate_decision = self._gate.evaluate(assessment)
        gate_stage = _gate_status_to_stage(gate_decision.status)
        self._update_registry(snapshot, data_mode, gate_stage)

        # Step 4 — eligibility.
        # Data-mode check precedes gate-status check: DEVELOPMENT_REAL is always
        # ineligible for scientific model generation regardless of gate outcome,
        # because the data mode is the fundamental qualifier, not the quality score.
        if data_mode != CorpusDataMode.SCIENTIFIC_CORPUS:
            eligibility = LifecycleEligibility.INELIGIBLE_DATA_MODE
            reason = (
                f"data_mode={data_mode.value!r} is not SCIENTIFIC_CORPUS. "
                "Development-real snapshots may not be used for scientific model generations."
            )
        elif gate_decision.status == GateStatus.STOP:
            eligibility = LifecycleEligibility.INELIGIBLE_GATE_STOP
            reason = f"Corpus quality gate returned STOP. Rationale: {gate_decision.rationale}"
        elif gate_decision.status == GateStatus.REDESIGN:
            eligibility = LifecycleEligibility.INELIGIBLE_GATE_REDESIGN
            reason = f"Corpus quality gate returned REDESIGN. Rationale: {gate_decision.rationale}"
        else:
            eligibility = LifecycleEligibility.ELIGIBLE
            reason = None

        result = _build_result(
            sha,
            data_mode,
            eligibility=eligibility,
            lifecycle_stage=gate_stage,
            profile=profile,
            assessment=assessment,
            gate_decision=gate_decision,
            ineligibility_reason=reason,
        )
        return result

    def register_model_generation(
        self,
        pipeline_result: LifecyclePipelineResult,
        snapshot: CorpusSnapshotV2,
        model_generation_id: str,
        architecture_description: str,
        feature_config_version: str,
        training_split_id: str,
        random_seed: int | None = None,
    ) -> ModelGenerationRecord:
        """Register a Model Generation against an eligible snapshot.

        Raises DataModeViolation if the snapshot is not eligible (e.g. if data
        mode is SYNTHETIC_FIXTURE or gate returned STOP/REDESIGN).

        Returns a ``ModelGenerationRecord`` with all governed algorithm IDs
        populated from the project's accepted GDRs.
        """
        if not pipeline_result.eligible_for_training:
            msg = (
                f"Cannot register Model Generation for snapshot "
                f"{pipeline_result.snapshot_sha[:16]}…: "
                f"{pipeline_result.ineligibility_reason}"
            )
            raise DataModeViolation(msg)

        sha = snapshot.manifest.snapshot_sha256

        record = ModelGenerationRecord(
            generation_id=model_generation_id,
            training_snapshot_sha=sha,
            feature_config_version=feature_config_version,
            training_split_id=training_split_id,
            architecture_description=architecture_description,
            loss_function_id=LOSS_FUNCTION_ID,
            uncertainty_method_id=UNCERTAINTY_METHOD_ID,
            ad_algorithm_id=AD_ALGORITHM_ID,
            alphafold_treatment=ALPHAFOLD_TREATMENT_ID,
            missingness_encoding="ordinal_plus_unavailable_mask",
            random_seed=random_seed,
            phase_committed="Core+Extension",
            s10_committed=False,  # Phase 2 conditional on GGR-002e
            s9_committed=False,  # Phase 2 conditional on GGR-002d
            algorithm_version="sci2_interfaces_v1_sci2001",
        )

        if self._registry is not None:
            self._registry.register(snapshot, pipeline_result.data_mode)
            self._registry.register_model_generation(sha, model_generation_id)

        return record

    # ── Internal ──────────────────────────────────────────────────────────────

    def _update_registry(
        self,
        snapshot: CorpusSnapshotV2,
        data_mode: CorpusDataMode,
        stage: CorpusLifecycleStage,
    ) -> None:
        if self._registry is None:
            return
        sha = snapshot.manifest.snapshot_sha256
        if not self._registry.is_known(sha):
            self._registry.register(snapshot, data_mode)
        self._registry.advance_stage(sha, stage)


def _gate_status_to_stage(status: GateStatus) -> CorpusLifecycleStage:
    return {
        GateStatus.PROCEED: CorpusLifecycleStage.GATE_DECIDED_PROCEED,
        GateStatus.WARNING: CorpusLifecycleStage.GATE_DECIDED_WARNING,
        GateStatus.REDESIGN: CorpusLifecycleStage.GATE_DECIDED_REDESIGN,
        GateStatus.STOP: CorpusLifecycleStage.GATE_DECIDED_STOP,
    }[status]

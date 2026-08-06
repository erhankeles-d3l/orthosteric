"""SCI-2 interface schema -- frozen dataclasses for the learning/ contract.

Authority: SCI2-001 specification; ADR-0010; Constitution §4.1--§4.7.

This module defines the type-level contract for SCI-2 without implementing
the model. No model weights, no loss functions, no training loops.

Scientific invariants encoded here (from SCI2-001 §2--§4):

1. ComparativeInput carries all four isoforms jointly (not independently).
   A missing isoform is UNAVAILABLE, distinguishable from ABSENT.
2. ComparativePrediction carries direct log-ratio predictions per axis,
   not per-isoform absolute potencies for post-hoc differencing.
3. Every prediction carries full provenance.
4. Per-target applicability domain is per isoform axis, not molecule-level.
5. INDETERMINATE binding does not collapse to zero selectivity -- it is
   a distinct classification with no sparing information.
6. AlphaFold sources are explicitly labeled; never treated as experimental.

ADR-0010 import-layer order (BINDING):
  generation/ policy/ eval/ interpretation/ learning/ features/ pocket/ ...
  learning/ is BELOW eval/ and interpretation/.
  This module MUST NOT import from eval/, interpretation/, policy/, or generation/.
  Types shared between layers are defined here (learning/) and imported
  upward by eval/ when needed; never the reverse.

All GOVERNANCE_DECISION_REQUIRED choices from SCI2-001 §14 are stored as
None in the relevant fields until their GDRs resolve them.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

__all__ = [
    "INTERFACES_ALGORITHM_VERSION",
    "ApplicabilityDomainResult",
    "BindingEvidence",
    "ComparativeInput",
    "ComparativePrediction",
    "DegeneracyTestRecord",
    "DegeneracyTestStatus",
    "IsoformEvidence",
    "JointUncertaintyMethod",
    "MissingnessFlag",
    "ModelGenerationRecord",
]

INTERFACES_ALGORITHM_VERSION = "sci2_interfaces_v1_sci2001"


# ── Vocabulary enums (defined here; eval/ may import these upward) ────────────


class MissingnessFlag(StrEnum):
    """Five-state interaction vocabulary at the model boundary.

    FROZEN (Constitution §4.2(5), §2.2): UNAVAILABLE and NOT_APPLICABLE
    MUST NOT be treated as equivalent to ABSENT.

    Note: eval/_interaction_fingerprint.InteractionStatus uses parallel
    vocabulary. Both exist to respect the ADR-0010 import order.
    """

    OBSERVED = "observed"  # positive evidence present
    CANDIDATE = "candidate"  # geometry present; threshold ungoverned
    ABSENT = "absent"  # structure available; interaction absent
    UNAVAILABLE = "unavailable"  # structure not available; NOT negative evidence
    NOT_APPLICABLE = "not_applicable"  # chemistry incompatible; NOT negative evidence


class BindingEvidence(StrEnum):
    """Ternary binding classification for one compound at one isoform.

    FROZEN (Constitution §2.2): INDETERMINATE is a distinct class, NOT weak
    non-productive evidence. INDETERMINATE contributes ZERO to selectivity claims.

    Note: eval/_productive_binding.BindingClassification uses the same
    vocabulary. Both exist to respect the ADR-0010 import order.
    """

    PRODUCTIVE = "productive"
    NON_PRODUCTIVE = "non_productive"
    INDETERMINATE = "indeterminate"  # zero contribution; not weak sparing evidence


class JointUncertaintyMethod(StrEnum):
    """Method used to compose per-target confidences into joint selectivity confidence.

    FROZEN (Constitution §2.4): conjunction product, NOT min-rule.
    GOVERNANCE_DECISION_REQUIRED (GGR-007): which method is used for SCI-2.
    """

    INDEPENDENT_PRODUCT = "independent_product"  # P(A and B) = P(A)*P(B)
    FRECHET_LOWER = "frechet_lower"  # max(0, sum - (n-1))
    NOT_SPECIFIED = "not_specified"  # RULE_MISSING; do not invent


# ── Core dataclasses ──────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class IsoformEvidence:
    """Structural evidence for one isoform in a ComparativeInput.

    An UNAVAILABLE isoform (no admissible structure) must be represented
    with all_unavailable=True, not omitted. The SCI-2 model requires all
    four isoforms present; missing isoforms are UNAVAILABLE, not ABSENT.

    GOVERNANCE_DECISION_REQUIRED (GGR-005): whether AlphaFold-derived
    features are included with a source indicator or excluded. The
    is_alphafold flag is required regardless of which option is chosen.

    The features field uses Any to avoid importing FeaturePipelineResult
    at runtime (that type requires BioPython and other heavy dependencies).
    At evaluation time, caller supplies a features._pipeline.FeaturePipelineResult.
    """

    isoform: str
    structure_record_id: str | None  # None if UNAVAILABLE
    features: Any | None  # FeaturePipelineResult | None
    is_alphafold: bool  # True if source is AlphaFold
    all_unavailable: bool  # True if no admissible structure exists
    conformational_state: str  # from MDStatus/ConformationalStateLabel
    algorithm_version: str  # from features pipeline version


@dataclass(frozen=True, slots=True)
class ComparativeInput:
    """One SCI-2 training/evaluation example: compound + all four isoforms.

    Constitution §4.1, §4.2, ADR-0010 §5 invariant 4 (FROZEN):
    Must include all four isoforms jointly. Fewer than four isoforms is
    non-compliant unless missing isoforms are represented as UNAVAILABLE.

    The activity_target field uses Any to avoid importing SelectivityTarget
    from eval/ (which is above learning/ in the import order).
    Callers pass an eval._metrics.SelectivityTarget for training examples.
    """

    compound_id: str
    ligand_inchikey: str | None
    alpha: IsoformEvidence  # PI3Kalpha structural evidence
    beta: IsoformEvidence  # PI3Kbeta structural evidence
    gamma: IsoformEvidence  # PI3Kgamma structural evidence
    delta: IsoformEvidence  # PI3Kdelta structural evidence
    activity_target: Any | None  # SelectivityTarget | None; Any avoids upward import
    training_snapshot_sha: str | None  # SCI0-011 content hash
    feature_config_version: str  # FeatureConfig version (SCI1-008)
    split_id: str | None  # links to scaffold split record
    algorithm_version: str

    @property
    def n_isoforms_available(self) -> int:
        """Number of isoforms with admissible structural evidence."""
        return sum(
            1 for ev in (self.alpha, self.beta, self.gamma, self.delta) if not ev.all_unavailable
        )

    @property
    def any_alphafold(self) -> bool:
        """True if any isoform uses AlphaFold structure."""
        return any(ev.is_alphafold for ev in (self.alpha, self.beta, self.gamma, self.delta))

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "algorithm_version": self.algorithm_version,
                "alpha_record_id": self.alpha.structure_record_id,
                "beta_record_id": self.beta.structure_record_id,
                "compound_id": self.compound_id,
                "delta_record_id": self.delta.structure_record_id,
                "feature_config_version": self.feature_config_version,
                "gamma_record_id": self.gamma.structure_record_id,
                "ligand_inchikey": self.ligand_inchikey,
                "split_id": self.split_id,
                "training_snapshot_sha": self.training_snapshot_sha,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ApplicabilityDomainResult:
    """Per-target applicability domain flags.

    Constitution §4.2(4) (FROZEN): per-target AD, not a single molecule flag.
    Separate flags per isoform and per selectivity axis.
    GOVERNANCE_DECISION_REQUIRED (GGR-004): AD algorithm not yet specified.
    """

    compound_id: str
    in_ad_alpha: bool  # within training distribution for PI3Kalpha
    in_ad_beta: bool  # within training distribution for PI3Kbeta
    in_ad_gamma: bool  # within training distribution for PI3Kgamma
    in_ad_delta: bool  # within training distribution for PI3Kdelta
    in_ad_lr_vs_beta: bool  # selectivity axis alpha-vs-beta within AD
    in_ad_lr_vs_gamma: bool
    in_ad_lr_vs_delta: bool
    ad_algorithm: str  # RULE_MISSING until GGR-004 resolved
    model_generation_id: str
    algorithm_version: str

    @property
    def any_out_of_ad(self) -> bool:
        """True if any target is outside the applicability domain."""
        return not all(
            [
                self.in_ad_alpha,
                self.in_ad_beta,
                self.in_ad_gamma,
                self.in_ad_delta,
                self.in_ad_lr_vs_beta,
                self.in_ad_lr_vs_gamma,
                self.in_ad_lr_vs_delta,
            ]
        )


@dataclass(frozen=True, slots=True)
class ComparativePrediction:
    """SCI-2 model output for one compound.

    Constitution §4.2(1) (FROZEN): direct log-ratio predictions per
    selectivity axis, NOT per-isoform absolute potencies for post-hoc
    differencing.

    All provenance fields are required (ADR-0010 §5 invariant 2, FROZEN).
    Uncertainty fields are None until GGR-007 (uncertainty method) resolves.

    Structure sources follow the format "pdb:{pdb_id}" or "alphafold:{ac}".
    """

    compound_id: str
    # Direct log-ratio predictions (Constitution §4.2(1))
    predicted_lr_vs_beta: float | None  # Delta_alpha_beta; positive = alpha-selective
    predicted_lr_vs_gamma: float | None  # Delta_alpha_gamma
    predicted_lr_vs_delta: float | None  # Delta_alpha_delta
    predicted_pac_alpha: float | None  # pAct_alpha (for S4a calibration)
    # Uncertainty (GOVERNANCE_DECISION_REQUIRED GGR-007; representation not yet specified)
    uncertainty_lr_vs_beta: float | None
    uncertainty_lr_vs_gamma: float | None
    uncertainty_lr_vs_delta: float | None
    uncertainty_pac_alpha: float | None
    # Binding classification per isoform (Constitution §2.2)
    alpha_binding: BindingEvidence
    beta_binding: BindingEvidence
    gamma_binding: BindingEvidence
    delta_binding: BindingEvidence
    # Per-target applicability domain
    applicability_domain: ApplicabilityDomainResult
    # Uncertainty composition method (Constitution §2.4: NOT min-rule)
    joint_uncertainty_method: JointUncertaintyMethod
    # Provenance (all required -- ADR-0010 §5 invariant 2)
    model_generation_id: str
    training_snapshot_sha: str
    feature_config_version: str
    training_split_id: str
    alpha_structure_source: str  # "pdb:1E8X" or "alphafold:P42336"
    beta_structure_source: str
    gamma_structure_source: str
    delta_structure_source: str
    algorithm_version: str

    @property
    def any_isoform_indeterminate(self) -> bool:
        """True if any isoform is INDETERMINATE; no selectivity claim possible."""
        return BindingEvidence.INDETERMINATE in (
            self.alpha_binding,
            self.beta_binding,
            self.gamma_binding,
            self.delta_binding,
        )

    @property
    def any_alphafold_source(self) -> bool:
        """True if any structure source is AlphaFold."""
        return any(
            src.startswith("alphafold:")
            for src in (
                self.alpha_structure_source,
                self.beta_structure_source,
                self.gamma_structure_source,
                self.delta_structure_source,
            )
        )

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "algorithm_version": self.algorithm_version,
                "alpha_binding": self.alpha_binding.value,
                "beta_binding": self.beta_binding.value,
                "compound_id": self.compound_id,
                "delta_binding": self.delta_binding.value,
                "feature_config_version": self.feature_config_version,
                "gamma_binding": self.gamma_binding.value,
                "joint_uncertainty_method": self.joint_uncertainty_method.value,
                "model_generation_id": self.model_generation_id,
                "predicted_lr_vs_beta": self.predicted_lr_vs_beta,
                "predicted_lr_vs_delta": self.predicted_lr_vs_delta,
                "predicted_lr_vs_gamma": self.predicted_lr_vs_gamma,
                "predicted_pac_alpha": self.predicted_pac_alpha,
                "training_snapshot_sha": self.training_snapshot_sha,
                "training_split_id": self.training_split_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class DegeneracyTestStatus(StrEnum):
    """Pass/fail/inconclusive status for a degeneracy battery test."""

    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"  # data insufficient for a determination
    NOT_RUN = "not_run"  # test not yet executed
    NOT_APPLICABLE = "not_applicable"  # test not in committed phase scope


@dataclass(frozen=True, slots=True)
class DegeneracyTestRecord:
    """One result from the Constitution §4.3 degeneracy battery.

    All numerical thresholds trace to their source (RULE_AVAILABLE or
    RULE_MISSING). Pass/fail decisions must not be made without a governed
    threshold -- use INCONCLUSIVE when the threshold is unsettled.
    """

    test_name: str  # "pocket_shuffle", "ligand_only_ablation", etc.
    status: DegeneracyTestStatus
    metric_name: str  # "rmse_degradation_log_units", etc.
    metric_value: float | None
    threshold: float | None  # None if RULE_MISSING
    threshold_source: str  # "RULE_AVAILABLE:Constitution §1.4 S3" or "RULE_MISSING"
    is_hard_gate: bool  # True if failure is a kill criterion
    phase_required: str  # "Phase 1", "Phase 2", or "Phase 3"
    model_generation_id: str
    notes: str
    algorithm_version: str


@dataclass(frozen=True, slots=True)
class ModelGenerationRecord:
    """Immutable record of a frozen SCI-2 model generation.

    Constitution §0.4: a model generation is frozen architecture +
    training data + hyperparameters. Provides the provenance required by
    ADR-0010 §5 invariant 2 and SCI2-001 §4.8.

    GOVERNANCE_DECISION_REQUIRED fields are None until their GDRs resolve.
    """

    generation_id: str  # deterministic hash of all inputs
    training_snapshot_sha: str  # SCI0-011 content hash
    feature_config_version: str  # FeatureConfig version string
    training_split_id: str  # scaffold split used for training
    architecture_description: str  # e.g. "graph_transformer_v1"
    loss_function_id: str | None  # RULE_MISSING until GGR-003
    uncertainty_method_id: str | None  # RULE_MISSING until GGR-007
    ad_algorithm_id: str | None  # RULE_MISSING until GGR-004
    alphafold_treatment: str | None  # RULE_MISSING until GGR-005
    missingness_encoding: str | None  # RULE_MISSING until GGR-006 confirmed
    random_seed: int | None  # None for deterministic pipelines
    phase_committed: str | None  # "Phase 1", "Phase 2", or None if not recorded
    s10_committed: bool  # False until Phase 2 is committed
    s9_committed: bool  # False until Phase 2 is committed
    algorithm_version: str


# ── Algorithm version constants from GDR-005 through GDR-009 ─────────────────

# GDR-005: Applicability domain algorithm
AD_ALGORITHM_ID: str = "leverage_knn_tanimoto_95pct_v1"
AD_ALGORITHM_GDR: str = "GDR-005"
AD_COVERAGE_PERCENTILE: float = 95.0  # RULE_AVAILABLE (Tropsha 2003; OECD QSAR guidance)
AD_TANIMOTO_FP_RADIUS: int = 2
AD_TANIMOTO_FP_NBITS: int = 2048

# GDR-006: AlphaFold model-level treatment
ALPHAFOLD_TREATMENT_ID: str = "alphafold_include_source_indicator_v1"
ALPHAFOLD_TREATMENT_GDR: str = "GDR-006"

# GDR-007: Uncertainty representation
UNCERTAINTY_METHOD_ID: str = "heteroscedastic_gaussian_v1"
UNCERTAINTY_METHOD_GDR: str = "GDR-007"
UNCERTAINTY_COVERAGE: float = 0.95  # 95% predictive interval for S4b
UNCERTAINTY_Z_95: float = 1.96  # z-score for 95% normal CI

# GDR-008: Censored likelihood form
CENSORED_LIKELIHOOD_ID: str = "tobit1_censored_normal_v1"
CENSORED_LIKELIHOOD_GDR: str = "GDR-008"

# GDR-009: Loss function and validation protocol
LOSS_FUNCTION_ID: str = "tobit1_gaussian_nll_equal_weight_v1"
VALIDATION_PROTOCOL_ID: str = "scaffold_loso_cv_v1"
LOSS_FUNCTION_GDR: str = "GDR-009"
LOSS_N_OUTPUT_HEADS: int = 4  # pAct_alpha + 3 Delta axes -- FROZEN by §4.2(2)
LOSS_EQUAL_WEIGHT: float = 1.0  # FROZEN: all heads equal (implements §4.2(2))

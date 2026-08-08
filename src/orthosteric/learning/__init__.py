"""learning package -- Comparative representation learning (Phase C SCI-2).

Authority: ADR-0010 [Architectural]; SCI2-001 specification.
Responsibility (ENG §2): comparative representation learning --
always ``compound + all_isoforms -> joint_representation``,
never ``compound -> activity``.

Gate constraint (SI3): no model implementation code until SCI1-022 has
recorded a GO decision on real data AND phase commitment is recorded AND
Stage 0 pre-registrations are sealed (SCI2-001 §0 blocking items).

Current state: SCI1-022 executed and recorded GO on Activity Snapshot A4
(ADR-0015, docs/governance/SCI1022_GATE_RECORD_A4.json, 2026-08-06).
Phase commitment recorded (GDR-004, Core+Extension). Model implementation
code (`_baseline_models.py`) is authorized for the SCI2-002 Core scope
(Charter §9.0 Phase 1: comparative discrimination, degeneracy battery,
determinant recovery -- criteria S1-S6). Phase 1 supports no determinant
claim and no generality claim (Charter §9.0 claim ceiling). GGR-002a and
GGR-002b remain GDR_REQUIRED and are NOT required for Phase 1 Core, per
the Charter's own scoping -- see ADR-0015 and GDR-012/013 for why they are
not blockers here.
"""

from orthosteric.learning._interfaces import (
    AD_ALGORITHM_GDR,
    AD_ALGORITHM_ID,
    AD_COVERAGE_PERCENTILE,
    AD_TANIMOTO_FP_NBITS,
    AD_TANIMOTO_FP_RADIUS,
    ALPHAFOLD_TREATMENT_GDR,
    ALPHAFOLD_TREATMENT_ID,
    CENSORED_LIKELIHOOD_GDR,
    CENSORED_LIKELIHOOD_ID,
    INTERFACES_ALGORITHM_VERSION,
    LOSS_EQUAL_WEIGHT,
    LOSS_FUNCTION_GDR,
    LOSS_FUNCTION_ID,
    LOSS_N_OUTPUT_HEADS,
    UNCERTAINTY_COVERAGE,
    UNCERTAINTY_METHOD_GDR,
    UNCERTAINTY_METHOD_ID,
    UNCERTAINTY_Z_95,
    VALIDATION_PROTOCOL_ID,
    ApplicabilityDomainResult,
    BindingEvidence,
    ComparativeInput,
    ComparativePrediction,
    DegeneracyTestRecord,
    DegeneracyTestStatus,
    IsoformEvidence,
    JointUncertaintyMethod,
    MissingnessFlag,
    ModelGenerationRecord,
)

__all__ = [
    "AD_ALGORITHM_GDR",
    "AD_ALGORITHM_ID",
    "AD_COVERAGE_PERCENTILE",
    "AD_TANIMOTO_FP_NBITS",
    "AD_TANIMOTO_FP_RADIUS",
    "ALPHAFOLD_TREATMENT_GDR",
    "ALPHAFOLD_TREATMENT_ID",
    "CENSORED_LIKELIHOOD_GDR",
    "CENSORED_LIKELIHOOD_ID",
    "INTERFACES_ALGORITHM_VERSION",
    "LOSS_EQUAL_WEIGHT",
    "LOSS_FUNCTION_GDR",
    "LOSS_FUNCTION_ID",
    "LOSS_N_OUTPUT_HEADS",
    "UNCERTAINTY_COVERAGE",
    "UNCERTAINTY_METHOD_GDR",
    "UNCERTAINTY_METHOD_ID",
    "UNCERTAINTY_Z_95",
    "VALIDATION_PROTOCOL_ID",
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

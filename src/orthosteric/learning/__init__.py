"""learning package -- Comparative representation learning (Phase C SCI-2).

Authority: ADR-0010 [Architectural]; SCI2-001 specification.
Responsibility (ENG §2): comparative representation learning --
always ``compound + all_isoforms -> joint_representation``,
never ``compound -> activity``.

Gate constraint (SI3): no model implementation code until SCI1-022 has
recorded a GO decision on real data AND phase commitment is recorded AND
Stage 0 pre-registrations are sealed (SCI2-001 §0 blocking items).

Current state: interfaces sealed; model code NOT YET AUTHORIZED.
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

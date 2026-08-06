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
    INTERFACES_ALGORITHM_VERSION,
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

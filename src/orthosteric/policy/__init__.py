"""policy package — Decision Policy Layer.

Authority: `ADR-0008` [Architectural].
Responsibility (ENG §2): classify model predictions against configurable,
versioned project objectives. Must not contain evidence loading, harmonization,
featurization, model definition, training, or criterion evaluation.

This layer operates exclusively on model outputs. It never modifies evidence,
harmonized data, feature representations, or learned models — enforced
mechanically: `policy/` is the highest layer in the `.importlinter` layers
contract, so no lower layer can import it.

Not a numbered stage. `SCI-4` is Cross-family transfer (Constitution §9.6,
criterion S7); see `ADR-0008` for why this is a layer rather than a stage.

No policy output is criterion-eligible. Policy thresholds are project
prioritization criteria, not scientific claims about PI3K, and may not be
reported as or used to compute S1-S10 (Constitution §1.4 firewall, `ADR-0008`).
"""

from orthosteric.policy._base import Policy, PolicyOutcome, PolicyStatus
from orthosteric.policy._config import (
    BELOW_LOWEST_TIER,
    CONSTITUTION_POTENCY_FLOOR,
    DEFAULT_SELECTIVITY_TIERS,
    PolicyConfig,
    SelectivityTier,
    SelectivityTierTable,
)
from orthosteric.policy._engine import (
    DECISION_SCHEMA_VERSION,
    DecisionProvenance,
    DecisionRecord,
    PolicyEngine,
)
from orthosteric.policy._policies import (
    AUDITOR5_ADVISORY,
    ConfidencePolicy,
    PotencyPolicy,
    SelectivityPolicy,
    SelectivityVector,
    UncertaintyPolicy,
)
from orthosteric.policy._prediction import (
    BindingClass,
    IsoformPrediction,
    NormalizationStatus,
    PredictionInput,
)

__all__ = [
    "AUDITOR5_ADVISORY",
    "BELOW_LOWEST_TIER",
    "CONSTITUTION_POTENCY_FLOOR",
    "DECISION_SCHEMA_VERSION",
    "DEFAULT_SELECTIVITY_TIERS",
    "BindingClass",
    "ConfidencePolicy",
    "DecisionProvenance",
    "DecisionRecord",
    "IsoformPrediction",
    "NormalizationStatus",
    "Policy",
    "PolicyConfig",
    "PolicyEngine",
    "PolicyOutcome",
    "PolicyStatus",
    "PotencyPolicy",
    "PredictionInput",
    "SelectivityPolicy",
    "SelectivityTier",
    "SelectivityTierTable",
    "SelectivityVector",
    "UncertaintyPolicy",
]

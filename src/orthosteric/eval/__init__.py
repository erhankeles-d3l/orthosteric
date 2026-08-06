"""eval package -- Evaluation metrics and calibration (Phase C SCI-1).

Authority: ADR-0010 [Architectural]; SCI1-012 through SCI1-022.
Responsibility: selectivity metrics, calibration, uncertainty composition,
  binding classification, splitting, baselines, and gate evaluation.

No model training or prediction occurs here. This package evaluates
model outputs against ground-truth activity data.

Must NOT import: learning/, interpretation/, generation/.
May import: features/, pocket/, quality/, data/, runtime/.

Gate constraint (SI3 / SCI1-022): no model/ or train/ code may exist
until SCI1-022 (gate evaluation) records a GO decision.
"""

from orthosteric.eval._calibration import (
    CALIBRATION_ALGORITHM_VERSION,
    CalibrationResult,
    ece_per_target,
    sharpness,
)
from orthosteric.eval._metrics import (
    METRICS_ALGORITHM_VERSION,
    SelectivityTarget,
    log_selectivity_ratio,
    per_target_rmse,
    rmse,
)
from orthosteric.eval._productive_binding import (
    PRODUCTIVE_BINDING_ALGORITHM_VERSION,
    BindingClassification,
    ProductiveBindingConfig,
    ProductiveBindingRecord,
)
from orthosteric.eval._uncertainty import (
    UNCERTAINTY_ALGORITHM_VERSION,
    SelectivityConfidence,
    compose_selectivity_confidence,
)

__all__ = [
    "CALIBRATION_ALGORITHM_VERSION",
    "METRICS_ALGORITHM_VERSION",
    "PRODUCTIVE_BINDING_ALGORITHM_VERSION",
    "UNCERTAINTY_ALGORITHM_VERSION",
    "BindingClassification",
    "CalibrationResult",
    "ProductiveBindingConfig",
    "ProductiveBindingRecord",
    "SelectivityConfidence",
    "SelectivityTarget",
    "compose_selectivity_confidence",
    "ece_per_target",
    "log_selectivity_ratio",
    "per_target_rmse",
    "rmse",
    "sharpness",
]

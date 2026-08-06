"""eval package -- Evaluation metrics, baselines, and gate (Phase C SCI-1).

Authority: ADR-0010; SCI1-012 through SCI1-022.
No model training. Evaluates predictions against ground-truth activity data.
Gate constraint: no model/ or train/ code until SCI1-022 GO decision.
"""

from orthosteric.eval._baselines import (
    BASELINES_ALGORITHM_VERSION,
    BaselinePredictor,
    LigandOnlyBaseline,
    NearestNeighborBaseline,
    ProteochemometricBaseline,
    baseline_rmse,
)
from orthosteric.eval._calibration import (
    CALIBRATION_ALGORITHM_VERSION,
    CalibrationResult,
    ece_per_target,
    sharpness,
)
from orthosteric.eval._gate import (
    GATE_ALGORITHM_VERSION,
    S1GateDecision,
    S1GateRecord,
    S1GateVote,
    s1_gate_evaluation,
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
from orthosteric.eval._splitting import (
    SPLITTING_ALGORITHM_VERSION,
    ScaffoldSplit,
    scaffold_split,
)
from orthosteric.eval._stratum import (
    STRATUM_ALGORITHM_VERSION,
    ActivityRecord,
    StratumResult,
    load_within_study_stratum,
)
from orthosteric.eval._uncertainty import (
    UNCERTAINTY_ALGORITHM_VERSION,
    SelectivityConfidence,
    compose_selectivity_confidence,
)

__all__ = [
    "BASELINES_ALGORITHM_VERSION",
    "CALIBRATION_ALGORITHM_VERSION",
    "GATE_ALGORITHM_VERSION",
    "METRICS_ALGORITHM_VERSION",
    "PRODUCTIVE_BINDING_ALGORITHM_VERSION",
    "SPLITTING_ALGORITHM_VERSION",
    "STRATUM_ALGORITHM_VERSION",
    "UNCERTAINTY_ALGORITHM_VERSION",
    "ActivityRecord",
    "BaselinePredictor",
    "BindingClassification",
    "CalibrationResult",
    "LigandOnlyBaseline",
    "NearestNeighborBaseline",
    "ProductiveBindingConfig",
    "ProductiveBindingRecord",
    "ProteochemometricBaseline",
    "S1GateDecision",
    "S1GateRecord",
    "S1GateVote",
    "ScaffoldSplit",
    "SelectivityConfidence",
    "SelectivityTarget",
    "StratumResult",
    "baseline_rmse",
    "compose_selectivity_confidence",
    "ece_per_target",
    "load_within_study_stratum",
    "log_selectivity_ratio",
    "per_target_rmse",
    "rmse",
    "s1_gate_evaluation",
    "scaffold_split",
    "sharpness",
]

"""quality package — Corpus Quality Assessment Layer.

Authority: `ADR-0009` [Architectural]; `GDR-003` [Scientific] (dimension
rules).
Responsibility (ENG §2): interpret a `SCI0-011`/`GDR-002` `CorpusProfile`
into a transparent, per-dimension adequacy assessment. Must not contain
profile computation, raw-record access, or decision-policy logic.

Three distinct layers, not to be merged (ADR-0009):
  CorpusProfile              descriptive only — data.snapshots (GDR-002)
  CorpusQualityAssessment    interpretive — this package
  Decision Policy            policy/ (ADR-0008) — consumes only the
                             assessment, never raw statistics

Enforced mechanically: `quality/` sits directly above `data/` in the
`.importlinter` layers contract, so `data/` cannot import it — the profile
cannot depend on its own interpretation. `policy/` sits above `quality/`, so
it can consume this package's output.
"""

from orthosteric.quality._assessment import (
    ASSESSMENT_ALGORITHM_VERSION,
    QUALITY_ASSESSMENT_SCHEMA_VERSION,
    CorpusQualityAssessment,
    CorpusQualityAssessor,
)
from orthosteric.quality._dimensions import (
    GOVERNED_SCAFFOLD_FAMILY_FLOOR,
    ConfidenceEvaluator,
    ConnectivityEvaluator,
    CoverageEvaluator,
    DimensionAssessment,
    DimensionStatus,
    MissingnessEvaluator,
    PublicationConcentrationEvaluator,
    QualityDimensionEvaluator,
    ScaffoldDiversityEvaluator,
    StructuralCoverageEvaluator,
)

__all__ = [
    "ASSESSMENT_ALGORITHM_VERSION",
    "GOVERNED_SCAFFOLD_FAMILY_FLOOR",
    "QUALITY_ASSESSMENT_SCHEMA_VERSION",
    "ConfidenceEvaluator",
    "ConnectivityEvaluator",
    "CorpusQualityAssessment",
    "CorpusQualityAssessor",
    "CoverageEvaluator",
    "DimensionAssessment",
    "DimensionStatus",
    "MissingnessEvaluator",
    "PublicationConcentrationEvaluator",
    "QualityDimensionEvaluator",
    "ScaffoldDiversityEvaluator",
    "StructuralCoverageEvaluator",
]


def default_evaluators() -> tuple[QualityDimensionEvaluator, ...]:
    """The standard evaluator set.

    Every dimension named in `ADR-0009`/`GDR-003` that has real data behind
    it today, plus the structural-coverage extension-point stub.

    A caller may construct `CorpusQualityAssessor` with a different set
    (e.g. to add a future dimension); this is the default for convenience,
    not the only permitted configuration.
    """
    return (
        ConnectivityEvaluator(),
        CoverageEvaluator(),
        ScaffoldDiversityEvaluator(),
        PublicationConcentrationEvaluator(),
        ConfidenceEvaluator(),
        MissingnessEvaluator(),
        StructuralCoverageEvaluator(),
    )

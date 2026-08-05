"""Input contract for the Decision Policy Layer.

Authority: ADR-0008 [Architectural].
Constitution sections served: §2.2 (Productive / Non-productive /
  Indeterminate), §2.3(3) (biochemical and cellular never pooled),
  §2.3(4) (primary target expressed as log differences).

Why this contract lives here rather than in `model/`
-----------------------------------------------------
`policy/` is the highest layer in the import graph (ADR-0008): it may import
lower layers, and no lower layer may import it. Defining the input contract
here means `SCI-2`/`SCI-3` satisfy a contract owned by the consumer, and the
policy layer never reaches upward into a model package. It also means this
layer is buildable and testable before any model exists — which is the state
of the repository as of this module's introduction.

No prediction is fabricated by this module. It defines types only.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from orthosteric.data.provenance.enums import MeasurementClass

__all__ = [
    "BindingClass",
    "IsoformPrediction",
    "NormalizationStatus",
    "PredictionInput",
]


class BindingClass(StrEnum):
    """Constitution §2.2 productive-binding classification.

    `INDETERMINATE` is a first-class state, not a missing value and not weak
    evidence of sparing: §2.2 states it "contributes zero to selectivity
    claims," and that "a model unable to output Indeterminate per target is
    non-compliant." Policies must therefore never read `INDETERMINATE` as
    though the target were spared.
    """

    PRODUCTIVE = "productive"
    NON_PRODUCTIVE = "non_productive"
    INDETERMINATE = "indeterminate"


class NormalizationStatus(StrEnum):
    """Whether the potency metric has been made cross-isoform comparable.

    Constitution §2.3 preamble: the Class I isoforms "differ in ATP Km. IC50
    depends on assay ATP concentration." Cheng-Prusoff conversion to Ki is the
    normalization that makes cross-isoform ratios comparable, and it is
    currently blocked — `AUDITOR-5` is `INSUFFICIENT_EVIDENCE` (no
    authoritative per-isoform ATP Km source; see
    `docs/governance/SCI0-028-GOVERNANCE-GAP-REPORT.md` §7).

    This enum makes that state explicit on every prediction rather than
    leaving it implicit. `NOT_NORMALIZED` does not block a prioritization
    tier from being computed — the arithmetic is well defined — but it does
    raise a governance flag recorded in the decision, and no policy output is
    ever criterion-eligible regardless (ADR-0008 criterion firewall).
    """

    CHENG_PRUSOFF_APPLIED = "cheng_prusoff_applied"
    NOT_NORMALIZED = "not_normalized"
    NORMALIZATION_NOT_REQUIRED = "normalization_not_required"


@dataclass(frozen=True, slots=True)
class IsoformPrediction:
    """A predicted quantity for one isoform.

    Attributes:
        isoform: Isoform designation, e.g. ``PI3Kalpha``.
        p_activity: Predicted potency on the log scale (``pAct``; higher is
            more potent), as :class:`~decimal.Decimal` so that decision
            content hashes are byte-reproducible. ``None`` when the model
            produced no point estimate for this isoform — which is missing,
            not inactive.
        binding_class: Constitution §2.2 class.
        measurement_class: Biochemical or cellular. Carried per isoform so
            §2.3(3)'s "never pooled" rule is checkable rather than assumed.
        confidence: Per-target confidence in ``[0, 1]``, or ``None``.
            Reported per target, never only jointly (§2.4).
        interval_width: Width of the predictive interval in log units, or
            ``None``. Compared against a caller-supplied label-noise floor by
            :class:`~orthosteric.policy.UncertaintyPolicy`; §2.4 forbids
            claiming precision below that floor.
    """

    isoform: str
    p_activity: Decimal | None
    binding_class: BindingClass
    measurement_class: MeasurementClass
    confidence: float | None = None
    interval_width: float | None = None


@dataclass(frozen=True, slots=True)
class PredictionInput:
    """One model prediction for one compound across one or more isoforms.

    Attributes:
        prediction_id: Identifier of this prediction, recorded in decision
            provenance.
        compound_id: Compound identity — a `HarmonizedCompound.internal_id`
            (InChIKey) from `SCI0-008b`/`c`, never a raw source identifier.
        predictions: Per-isoform predicted quantities.
        normalization: See :class:`NormalizationStatus`.
        model_version: Model generation identifier (Constitution §0.4:
            frozen architecture + training data + hyperparameters).
        evidence_snapshot_sha256: The `SCI0-011` snapshot hash the model was
            trained against. This is what makes a decision reproducible from
            the immutable corpus.
    """

    prediction_id: str
    compound_id: str
    predictions: tuple[IsoformPrediction, ...]
    normalization: NormalizationStatus
    model_version: str
    evidence_snapshot_sha256: str

    def get(self, isoform: str) -> IsoformPrediction | None:
        """Return the prediction for `isoform`, or ``None`` if absent.

        Absent means the model did not predict this isoform. It does not mean
        the compound is inactive there.
        """
        for p in self.predictions:
            if p.isoform == isoform:
                return p
        return None

    def to_canonical_dict(self) -> dict[str, object]:
        """Stable, sorted representation for the decision content hash."""
        return {
            "compound_id": self.compound_id,
            "evidence_snapshot_sha256": self.evidence_snapshot_sha256,
            "model_version": self.model_version,
            "normalization": self.normalization.value,
            "prediction_id": self.prediction_id,
            "predictions": [
                {
                    "binding_class": p.binding_class.value,
                    "confidence": p.confidence,
                    "interval_width": p.interval_width,
                    "isoform": p.isoform,
                    "measurement_class": p.measurement_class.value,
                    "p_activity": format(p.p_activity, "f") if p.p_activity is not None else None,
                }
                for p in sorted(self.predictions, key=lambda x: x.isoform)
            ],
        }

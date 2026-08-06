"""Model Generation 1 v1 interface -- encoder / head / objective, modular.

Objective: SCI2-002, informed by the Family B controlled result
(analysis/run_family_b_controlled_comparison.py): comparative PLS beat
independent PLS on RMSE on all three S1 difference axes (alpha_vs_beta
-0.0135, alpha_vs_gamma -0.0052, alpha_vs_delta -0.0367), sign accuracy
mixed (better on 2/3, worse on alpha_vs_gamma by 0.028), same estimator
family, feature representation, split, seed, and component-selection
budget. This is evidence supporting the comparative-learning hypothesis
under this ligand-only PLS baseline -- not general superiority, and not a
determinant claim (Charter SS9.0 Phase 1 claim ceiling).

Architecture
------------
    molecule (+ optional structural/interaction evidence)
              |
              v
    MoleculeEncoder            -- swappable: MorganEncoder implemented;
              |                   future GNN/3D/learned encoders possible
              v
    representation (+ optional structural features, concatenated)
              |
              v
    RegressionHead             -- swappable: PLSHead implemented (the
              |                   controlled-experiment winner); Ridge or
              |                   a future neural head could replace it
              v
    ComparativeObjective        -- swappable: INDEPENDENT (N separate
              |                   single-output heads, no shared latent
              |                   space), MULTI_TASK_ABSOLUTE (one joint
              |                   head, shared latent space, trained on
              |                   absolute [alpha,beta,gamma,delta]), or
              |                   COMPARATIVE (one joint head, shared
              |                   latent space, trained on the S1
              |                   difference vector directly)
              v
    prediction: {isoform: pAct}

`ComparativeSelectivityModelV1` is the orchestrator that wires these three
together. Swapping the encoder, head, or objective never requires
rewriting the other two -- each is an independent constructor argument.
This third objective (MULTI_TASK_ABSOLUTE) exists specifically to
decompose the Family B result (COMPARATIVE beat INDEPENDENT) into its two
possible causes -- shared representation vs. comparative target
formulation -- via the three-way Baseline 0/1/2 ablation in
analysis/run_baseline1_absolute_pls.py: MULTI_TASK_ABSOLUTE shares
INDEPENDENT's target semantics (absolute isoform activities) but
COMPARATIVE's shared latent space, isolating the shared-representation
effect on its own.

Structural evidence extension boundary (Phase 6, partially implemented)
---------------------------------------------------------------------
`fit()`/`predict()` accept an optional `structural_features` mapping
(compound_id/smiles -> feature vector) and a `structural_mode`
(`StructuralFeatureMode`) governing how missing entries are handled:

  SKIP_MISSING (default; the only mode tested/used before this session):
    a compound absent from `structural_features` is DROPPED from that
    fit/predict call. Correct and honest, but at low coverage (verified
    empirically: 28/1,267 = 2.2% for PIK3Kgamma PDB evidence, see
    docs/STRUCTURAL_EVIDENCE_PI3KG_REPORT.md) it collapses the effective
    training set and cannot support a meaningful experiment.

  INDICATOR_ZERO_FILL: a compound absent from `structural_features`
    contributes a zero-filled structural block PLUS an explicit
    presence-indicator feature (1.0 if the structural data was real,
    0.0 if zero-filled) appended to the representation. The model can
    therefore learn to treat the two cases differently -- the zero fill
    is never presented as if it were a real measurement, because the
    indicator bit makes "no evidence" a first-class, distinguishable
    signal rather than an indistinguishable zero. All examples remain in
    the fit; none are dropped.

When `structural_features` is None (the only case exercised before this
session), the model is ligand-only and MUST be reported as "Model
Generation 1 -- ligand-only comparative baseline", never as using
structural evidence. UNAVAILABLE is never converted to a fabricated
non-zero value under either mode; only the *handling* of a documented,
explicit zero differs between modes.

Generative extension boundary (not implemented; Phase 7)
--------------------------------------------------------------
`SelectivityScorer` is the documented interface a future generative model
would call to score a candidate molecule against the trained comparative
model, without needing to know about encoders, heads, or objectives.
`ComparativeSelectivityModelV1.as_scorer()` returns one. No generator
exists in this repository; this is the connection point only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

from orthosteric.data._comparative_example import ComparativeExample

__all__ = [
    "MODEL_V1_POLICY_ID",
    "ComparativeObjective",
    "ComparativeSelectivityModelV1",
    "MoleculeEncoder",
    "MorganEncoder",
    "PLSHead",
    "RegressionHead",
    "SelectivityScorer",
    "StructuralFeatureMode",
]

MODEL_V1_POLICY_ID = "model_generation_1_v1_encoder_head_objective"

_NON_REFERENCE_ISOFORMS = ("PI3Kbeta", "PI3Kgamma", "PI3Kdelta")
_AXIS_ATTR = {"PI3Kbeta": "lr_vs_beta", "PI3Kgamma": "lr_vs_gamma", "PI3Kdelta": "lr_vs_delta"}
_MIN_ROWS_TO_FIT = 2  # any regression backend needs at least 2 rows


class ComparativeObjective(StrEnum):
    """Which target structure the model is trained on. ENGINEERING CHOICE
    -- ordinary methodological classification, not a governed threshold.
    """

    #: N separate single-output models, one per alpha-vs-X difference,
    #: no shared latent space or parameters across outputs.
    INDEPENDENT = "independent"

    #: One joint model, shared latent space, trained on the ABSOLUTE
    #: four-isoform activity vector [alpha, beta, gamma, delta].
    #: Selectivity differences are derived post hoc (pred_alpha - pred_X),
    #: never trained on directly. Isolates the shared-representation
    #: effect from the comparative-target effect (see module docstring).
    MULTI_TASK_ABSOLUTE = "multi_task_absolute"

    #: One joint model whose targets are the full S1 vector at once,
    #: with genuine shared-parameter/latent coupling across outputs.
    COMPARATIVE = "comparative"


class StructuralFeatureMode(StrEnum):
    """How `structural_features` handles compounds with no structural
    evidence. ENGINEERING CHOICE, documented in the module docstring.
    """

    #: Drop any compound absent from structural_features. Default;
    #: unchanged behaviour from before this session.
    SKIP_MISSING = "skip_missing"

    #: Zero-fill the structural block for an absent compound and append
    #: an explicit 1.0/0.0 presence-indicator feature so the model can
    #: distinguish "no evidence" from a genuine zero-valued measurement.
    INDICATOR_ZERO_FILL = "indicator_zero_fill"


class MoleculeEncoder(Protocol):
    """Molecule -> fixed-length representation. Swappable: MorganEncoder
    today; a GNN, 3D, or learned encoder implements the same contract.
    """

    def encode(self, smiles: str) -> NDArray[np.float64] | None: ...
    def output_dim(self) -> int: ...


@dataclass(frozen=True, slots=True)
class MorganEncoder:
    """Morgan (ECFP4) fingerprint encoder -- the Family B winner's
    representation. Radius/bits are documented defaults, not governed.
    """

    radius: int = 2
    n_bits: int = 2048

    def encode(self, smiles: str) -> NDArray[np.float64] | None:
        from rdkit import Chem  # noqa: PLC0415
        from rdkit.Chem import rdMolDescriptors  # noqa: PLC0415

        try:
            mol = Chem.MolFromSmiles(smiles)
            fp = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, self.radius, nBits=self.n_bits)
            return np.array(list(fp), dtype=np.float64)
        except Exception:
            return None

    def output_dim(self) -> int:
        return self.n_bits


class RegressionHead(Protocol):
    """X -> Y regression contract. Swappable: PLSHead (Family B winner)
    today; Ridge or a future neural head implement the same contract.
    """

    def fit(self, x: NDArray[np.float64], y: NDArray[np.float64]) -> None: ...
    def predict(self, x: NDArray[np.float64]) -> NDArray[np.float64]: ...


@dataclass
class PLSHead:
    """PLSRegression head. n_components is selected by the caller
    (train/validation only, never the held-out test set -- see
    analysis/run_family_b_controlled_comparison.py's selection procedure)
    and passed in already chosen; this class does not select components
    itself, keeping selection and fitting separable.
    """

    n_components: int = 8
    _model: Any = field(default=None, repr=False)

    def fit(self, x: NDArray[np.float64], y: NDArray[np.float64]) -> None:
        from sklearn.cross_decomposition import PLSRegression  # noqa: PLC0415

        k = max(1, min(self.n_components, x.shape[0] - 1, x.shape[1]))
        self._model = PLSRegression(n_components=k)
        self._model.fit(x, y)

    def predict(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        if self._model is None:
            raise RuntimeError("PLSHead.predict() called before fit()")
        return np.asarray(self._model.predict(x))


class SelectivityScorer(Protocol):
    """Generative-model extension boundary (Phase 7, not implemented).
    A future generator calls score(smiles) to obtain the predicted S1
    vector for a candidate molecule, without needing to know about
    encoders, heads, or objectives.
    """

    def score(self, smiles: str) -> dict[str, float]: ...


@dataclass
class ComparativeSelectivityModelV1:
    """Model Generation 1 orchestrator: wires an encoder, a head, and an
    objective together. Ligand-only unless structural_features is
    supplied to fit()/predict() (Phase 6 extension boundary; not exercised
    by any current caller -- see module docstring).
    """

    encoder: MoleculeEncoder
    objective: ComparativeObjective
    head_factory: Any  # Callable[[], RegressionHead]
    structural_mode: StructuralFeatureMode = field(default=StructuralFeatureMode.SKIP_MISSING)
    _heads: dict[str, RegressionHead] = field(default_factory=dict, repr=False)
    _fitted: bool = field(default=False, repr=False)
    policy: str = field(default=MODEL_V1_POLICY_ID)

    def _features(
        self,
        examples_or_smiles: Sequence[ComparativeExample | str],
        structural_features: Mapping[str, NDArray[np.float64]] | None,
    ) -> tuple[NDArray[np.float64], list[int]]:
        struct_dim = 0
        if (
            structural_features
            and self.structural_mode is StructuralFeatureMode.INDICATOR_ZERO_FILL
        ):
            struct_dim = len(next(iter(structural_features.values())))

        rows: list[NDArray[np.float64]] = []
        keep_idx: list[int] = []
        for i, item in enumerate(examples_or_smiles):
            smi: str | None = item.smiles if isinstance(item, ComparativeExample) else item
            if smi is None:
                continue
            enc = self.encoder.encode(smi)
            if enc is None:
                continue
            if structural_features is not None:
                key: str = item.compound_id if isinstance(item, ComparativeExample) else smi
                extra = structural_features.get(key)
                if self.structural_mode is StructuralFeatureMode.INDICATOR_ZERO_FILL:
                    if extra is None:
                        # Never fabricated as a real measurement: the
                        # presence bit (final element, 0.0) explicitly
                        # marks this block as zero-filled, not observed.
                        enc = np.concatenate([enc, np.zeros(struct_dim), [0.0]])
                    else:
                        enc = np.concatenate([enc, extra, [1.0]])
                else:  # SKIP_MISSING (default; unchanged prior behaviour)
                    if extra is None:
                        continue  # never fabricate; skip rather than zero-fill
                    enc = np.concatenate([enc, extra])
            rows.append(enc)
            keep_idx.append(i)
        if not rows:
            return np.empty((0, self.encoder.output_dim())), []
        return np.stack(rows), keep_idx

    def fit(
        self,
        examples: list[ComparativeExample],
        structural_features: Mapping[str, NDArray[np.float64]] | None = None,
    ) -> None:
        x, keep_idx = self._features(examples, structural_features)
        kept = [examples[i] for i in keep_idx]
        if len(kept) < _MIN_ROWS_TO_FIT:
            return  # too few usable rows to fit any regression; never fabricate
        if self.objective is ComparativeObjective.INDEPENDENT:
            for iso in _NON_REFERENCE_ISOFORMS:
                y = np.array([getattr(e, _AXIS_ATTR[iso]) for e in kept])
                head = self.head_factory()
                head.fit(x, y)
                self._heads[iso] = head
        elif self.objective is ComparativeObjective.MULTI_TASK_ABSOLUTE:
            alpha = np.array([e.pac_alpha for e in kept])
            y = np.column_stack(
                [alpha]
                + [
                    alpha - np.array([getattr(e, _AXIS_ATTR[iso]) for e in kept])
                    for iso in _NON_REFERENCE_ISOFORMS
                ]
            )  # absolute [alpha, beta, gamma, delta], recovered via alpha - diff
            head = self.head_factory()
            head.fit(x, y)
            self._heads["_joint"] = head
        else:  # COMPARATIVE
            y = np.column_stack(
                [np.array([e.pac_alpha for e in kept])]
                + [
                    np.array([getattr(e, _AXIS_ATTR[iso]) for e in kept])
                    for iso in _NON_REFERENCE_ISOFORMS
                ]
            )
            head = self.head_factory()
            head.fit(x, y)
            self._heads["_joint"] = head
        self._fitted = True

    def predict(
        self,
        smiles: str,
        structural_features: Mapping[str, NDArray[np.float64]] | None = None,
    ) -> dict[str, float]:
        if not self._fitted:
            return {}
        x, keep_idx = self._features([smiles], structural_features)
        if not keep_idx:
            return {}
        if self.objective is ComparativeObjective.INDEPENDENT:
            return {
                iso: float(self._heads[iso].predict(x)[0])
                for iso in _NON_REFERENCE_ISOFORMS
                if iso in self._heads
            }
        head = self._heads.get("_joint")
        if head is None:
            return {}
        pred = head.predict(x)[0]
        if self.objective is ComparativeObjective.MULTI_TASK_ABSOLUTE:
            # Head was trained directly on [alpha, beta, gamma, delta]
            # (absolute values) -- no arithmetic needed to recover them.
            return {
                "PI3Kalpha": float(pred[0]),
                **{iso: float(pred[i + 1]) for i, iso in enumerate(_NON_REFERENCE_ISOFORMS)},
            }
        # COMPARATIVE: head was trained on [alpha, diff_beta, diff_gamma,
        # diff_delta]. pred[i+1] is a DIFFERENCE, not an absolute isoform
        # value -- must reconstruct via alpha - diff. (This reconstruction
        # was previously missing here -- a real bug caught while adding
        # MULTI_TASK_ABSOLUTE and re-reading this method; the standalone
        # analysis/run_family_b_controlled_comparison.py script never had
        # this bug because it evaluated the diff prediction directly
        # against the actual diff, never relabeling it as an isoform value.)
        alpha_pred = float(pred[0])
        return {
            "PI3Kalpha": alpha_pred,
            **{
                iso: alpha_pred - float(pred[i + 1])
                for i, iso in enumerate(_NON_REFERENCE_ISOFORMS)
            },
        }

    def as_scorer(self) -> SelectivityScorer:
        """Generative-model extension boundary (Phase 7): returns an
        object exposing only score(smiles) -> dict, hiding encoder/head/
        objective from any future generator.
        """
        model = self

        class _Scorer:
            def score(self, smiles: str) -> dict[str, float]:
                return model.predict(smiles)

        return _Scorer()

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
              |                   space) or COMPARATIVE (one joint head,
              |                   shared latent space across all outputs)
              v
    prediction: {isoform: pAct}

`ComparativeSelectivityModelV1` is the orchestrator that wires these three
together. Swapping the encoder, head, or objective never requires
rewriting the other two -- each is an independent constructor argument.

Structural evidence extension boundary (not implemented; Phase 6)
---------------------------------------------------------------------
`fit()`/`predict()` accept an optional `structural_features` mapping
(compound_id/smiles -> feature vector). When None (the only case
exercised today), the model is ligand-only and MUST be reported as
"Model Generation 1 -- ligand-only comparative baseline", never as using
structural evidence. When provided in a future session, features are
concatenated to the encoder's ligand representation before the head sees
them -- the encoder and head code do not change. No structural evidence
is fabricated, imputed, or synthesized here; UNAVAILABLE is never
converted to a zero vector by this module (the caller must supply real
per-compound arrays or omit the compound).

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

    #: One joint model whose targets are the full S1 vector at once,
    #: with genuine shared-parameter/latent coupling across outputs.
    COMPARATIVE = "comparative"


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
    _heads: dict[str, RegressionHead] = field(default_factory=dict, repr=False)
    _fitted: bool = field(default=False, repr=False)
    policy: str = field(default=MODEL_V1_POLICY_ID)

    def _features(
        self,
        examples_or_smiles: Sequence[ComparativeExample | str],
        structural_features: Mapping[str, NDArray[np.float64]] | None,
    ) -> tuple[NDArray[np.float64], list[int]]:
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
        return {
            "PI3Kalpha": float(pred[0]),
            **{iso: float(pred[i + 1]) for i, iso in enumerate(_NON_REFERENCE_ISOFORMS)},
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

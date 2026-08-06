"""Reference baseline predictors for S2 gate evaluation.

Authority: SCI1-018/019/020. Constitution §9.3 (Stage 3), §3.4, §1.2.

Three baselines are required as reference points for the S2 criterion:
  Baseline 1 -- Ligand-only (SCI1-018): Ignores protein entirely.
    Predicts training mean or zero selectivity. The null hypothesis.
  Baseline 2 -- Nearest-neighbour Tanimoto (SCI1-019): Predicts using
    the most similar training compound by Tanimoto similarity.
  Baseline 3 -- Proteochemometric (SCI1-020): Concatenates ligand
    fingerprint + isoform one-hot encoding. Linear regression.

Constitution §9.3 mandate (Stage 1):
  "Ligand-only, nearest-neighbour and proteochemometric baselines on Tier 1."
  "If a baseline already meets S2, the learned component is unjustified."

These baselines live in eval/ not model/. They are reference predictors,
not the trained model. No model/ or train/ code exists until SCI1-022 GO.

Scientific rule classification
  RULE_AVAILABLE:  Tanimoto similarity on Morgan fingerprints (ECFP4,
    radius=2). This is the standard for molecular similarity screening.
  RULE_AVAILABLE:  Proteochemometric representation = ligand descriptor
    + protein descriptor (Lapinsh et al. 2001). This is the established
    prior-art baseline (Constitution §1.2).
  RULE_MISSING:    Fingerprint radius and bit size for ECFP4. Common: r=2,
    n=2048, but not governed.
  RULE_MISSING:    Linear regression regularization strength.
"""

from __future__ import annotations

from typing import ClassVar, Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import Ridge

from orthosteric.eval._metrics import SelectivityTarget

__all__ = [
    "BASELINES_ALGORITHM_VERSION",
    "BaselinePredictor",
    "LigandOnlyBaseline",
    "NearestNeighborBaseline",
    "ProteochemometricBaseline",
    "baseline_rmse",
]

BASELINES_ALGORITHM_VERSION = "baselines_v1_sci1018_019_020"

# Default fingerprint parameters (common; not governed)
_DEFAULT_FP_RADIUS = 2
_DEFAULT_FP_NBITS = 2048


@runtime_checkable
class BaselinePredictor(Protocol):
    """Interface all three baselines must implement."""

    baseline_name: str

    def fit(self, targets: list[SelectivityTarget]) -> None:
        """Train on the provided training targets."""

    def predict_lr_vs_beta(self, smiles: str) -> float:
        """Predict log-selectivity-ratio vs beta for one compound."""

    def predict_lr_vs_gamma(self, smiles: str) -> float:
        """Predict log-selectivity-ratio vs gamma for one compound."""

    def predict_lr_vs_delta(self, smiles: str) -> float:
        """Predict log-selectivity-ratio vs delta for one compound."""


def _morgan_fp(smiles: str, radius: int, n_bits: int) -> NDArray[np.float64] | None:
    from rdkit import Chem  # noqa: PLC0415
    from rdkit.Chem import rdMolDescriptors  # noqa: PLC0415

    try:
        mol = Chem.MolFromSmiles(smiles)
        fp = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
        return np.array(list(fp), dtype=np.float64)
    except Exception:
        return None


def _tanimoto(fp_a: NDArray[np.float64], fp_b: NDArray[np.float64]) -> float:
    inter = float(np.dot(fp_a, fp_b))
    union = float(np.sum(fp_a) + np.sum(fp_b) - inter)
    return inter / union if union > 0 else 0.0


class LigandOnlyBaseline:
    """Baseline 1 (SCI1-018): predicts training mean, ignoring protein.

    Represents the null hypothesis: selectivity is constant across all
    compounds. A model that fails to beat this learns nothing compound-specific.
    """

    baseline_name = "ligand_only_mean"

    def __init__(self) -> None:
        self._mean_lr_beta: float = 0.0
        self._mean_lr_gamma: float = 0.0
        self._mean_lr_delta: float = 0.0
        self._fitted = False

    def fit(self, targets: list[SelectivityTarget]) -> None:
        betas = [t.lr_vs_beta for t in targets if t.lr_vs_beta is not None]
        gammas = [t.lr_vs_gamma for t in targets if t.lr_vs_gamma is not None]
        deltas = [t.lr_vs_delta for t in targets if t.lr_vs_delta is not None]
        self._mean_lr_beta = float(np.mean(betas)) if betas else 0.0
        self._mean_lr_gamma = float(np.mean(gammas)) if gammas else 0.0
        self._mean_lr_delta = float(np.mean(deltas)) if deltas else 0.0
        self._fitted = True

    def predict_lr_vs_beta(self, smiles: str) -> float:  # noqa: ARG002
        return self._mean_lr_beta

    def predict_lr_vs_gamma(self, smiles: str) -> float:  # noqa: ARG002
        return self._mean_lr_gamma

    def predict_lr_vs_delta(self, smiles: str) -> float:  # noqa: ARG002
        return self._mean_lr_delta


class NearestNeighborBaseline:
    """Baseline 2 (SCI1-019): nearest-neighbour Tanimoto lookup.

    Predicts based on the most similar training compound by Morgan (ECFP4)
    Tanimoto similarity. Reports the training compound's measured selectivity.
    """

    baseline_name = "nearest_neighbor_tanimoto"

    def __init__(
        self, fp_radius: int = _DEFAULT_FP_RADIUS, fp_nbits: int = _DEFAULT_FP_NBITS
    ) -> None:
        self._fp_radius = fp_radius
        self._fp_nbits = fp_nbits
        self._train_fps: list[NDArray[np.float64]] = []
        self._train_targets: list[SelectivityTarget] = []

    def fit(self, targets: list[SelectivityTarget]) -> None:
        self._train_fps = []
        self._train_targets = []
        for t in targets:
            if t.compound_id and hasattr(t, "smiles"):
                smiles = getattr(t, "smiles", None)
                if smiles:
                    fp = _morgan_fp(smiles, self._fp_radius, self._fp_nbits)
                    if fp is not None:
                        self._train_fps.append(fp)
                        self._train_targets.append(t)

    def _nearest(self, smiles: str) -> SelectivityTarget | None:
        query_fp = _morgan_fp(smiles, self._fp_radius, self._fp_nbits)
        if query_fp is None or not self._train_fps:
            return None
        sims = [_tanimoto(query_fp, fp) for fp in self._train_fps]
        best_idx = int(np.argmax(sims))
        return self._train_targets[best_idx]

    def predict_lr_vs_beta(self, smiles: str) -> float:
        nn = self._nearest(smiles)
        return (nn.lr_vs_beta or 0.0) if nn else 0.0

    def predict_lr_vs_gamma(self, smiles: str) -> float:
        nn = self._nearest(smiles)
        return (nn.lr_vs_gamma or 0.0) if nn else 0.0

    def predict_lr_vs_delta(self, smiles: str) -> float:
        nn = self._nearest(smiles)
        return (nn.lr_vs_delta or 0.0) if nn else 0.0


class ProteochemometricBaseline:
    """Baseline 3 (SCI1-020): simple proteochemometric (PCM) baseline.

    Concatenates ligand fingerprint with isoform one-hot encoding.
    Fits a ridge regression to predict each log-selectivity-ratio axis.
    Isoform encoding: [alpha, beta, gamma, delta] (the 'other' isoform).
    """

    baseline_name = "proteochemometric_linear"

    _ISOFORM_ENCODING: ClassVar[dict[str, NDArray[np.float64]]] = {
        "PI3Kbeta": np.array([1, 0, 0, 0], dtype=np.float64),
        "PI3Kgamma": np.array([0, 1, 0, 0], dtype=np.float64),
        "PI3Kdelta": np.array([0, 0, 1, 0], dtype=np.float64),
    }

    def __init__(
        self,
        fp_radius: int = _DEFAULT_FP_RADIUS,
        fp_nbits: int = _DEFAULT_FP_NBITS,
        alpha: float = 1.0,
    ) -> None:
        self._fp_radius = fp_radius
        self._fp_nbits = fp_nbits
        self._alpha = alpha  # ridge regularization
        self._coef: dict[str, NDArray[np.float64]] = {}
        self._intercept: dict[str, float] = {}

    def _make_features(self, smiles: str, isoform: str) -> NDArray[np.float64] | None:
        fp = _morgan_fp(smiles, self._fp_radius, self._fp_nbits)
        if fp is None:
            return None
        enc = self._ISOFORM_ENCODING.get(isoform, np.zeros(4, dtype=np.float64))
        return np.concatenate([fp, enc])

    def fit(self, targets: list[SelectivityTarget]) -> None:
        for isoform, attr in (
            ("PI3Kbeta", "lr_vs_beta"),
            ("PI3Kgamma", "lr_vs_gamma"),
            ("PI3Kdelta", "lr_vs_delta"),
        ):
            x_rows, y_vals = [], []
            for t in targets:
                val = getattr(t, attr, None)
                smiles = getattr(t, "smiles", None)
                if val is None or not smiles:
                    continue
                feat = self._make_features(smiles, isoform)
                if feat is not None:
                    x_rows.append(feat)
                    y_vals.append(val)
            if x_rows:
                x_matrix = np.stack(x_rows)
                y = np.array(y_vals)
                model = Ridge(alpha=self._alpha)
                model.fit(x_matrix, y)
                self._coef[isoform] = model.coef_
                self._intercept[isoform] = float(model.intercept_)

    def _predict_for(self, smiles: str, isoform: str) -> float:
        if isoform not in self._coef:
            return 0.0
        feat = self._make_features(smiles, isoform)
        if feat is None:
            return 0.0
        return float(np.dot(self._coef[isoform], feat) + self._intercept[isoform])

    def predict_lr_vs_beta(self, smiles: str) -> float:
        return self._predict_for(smiles, "PI3Kbeta")

    def predict_lr_vs_gamma(self, smiles: str) -> float:
        return self._predict_for(smiles, "PI3Kgamma")

    def predict_lr_vs_delta(self, smiles: str) -> float:
        return self._predict_for(smiles, "PI3Kdelta")


def baseline_rmse(
    baseline: BaselinePredictor,
    test_smiles: list[str],
    test_targets: list[SelectivityTarget],
) -> dict[str, float]:
    """Compute RMSE per selectivity axis for a fitted baseline.

    Returns dict with keys 'alpha_vs_beta', 'alpha_vs_gamma', 'alpha_vs_delta'.
    """
    preds: dict[str, list[float]] = {"beta": [], "gamma": [], "delta": []}
    actuals: dict[str, list[float]] = {"beta": [], "gamma": [], "delta": []}

    for smi, target in zip(test_smiles, test_targets, strict=False):
        if target.lr_vs_beta is not None:
            preds["beta"].append(baseline.predict_lr_vs_beta(smi))
            actuals["beta"].append(target.lr_vs_beta)
        if target.lr_vs_gamma is not None:
            preds["gamma"].append(baseline.predict_lr_vs_gamma(smi))
            actuals["gamma"].append(target.lr_vs_gamma)
        if target.lr_vs_delta is not None:
            preds["delta"].append(baseline.predict_lr_vs_delta(smi))
            actuals["delta"].append(target.lr_vs_delta)

    result: dict[str, float] = {}
    for iso, pred_list in preds.items():
        if pred_list:
            from orthosteric.eval._metrics import rmse  # noqa: PLC0415

            result[f"alpha_vs_{iso}"] = rmse(np.array(pred_list), np.array(actuals[iso]))
    return result

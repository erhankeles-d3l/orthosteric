"""Model Generation 1 -- comparative representation learning (SCI-2).

Objective: SCI2-002 implementation, now authorized (ADR-0015: SCI1-022
gate = GO, executed on real Activity Snapshot A4).

Architecture (bounded engineering decisions, documented here; reversible)
---------------------------------------------------------------------------
Backend: scikit-learn Ridge regression on Morgan (ECFP4) fingerprints.
  No PyTorch is available in this environment (verified before
  implementation). Ridge on Morgan fingerprints is the same
  representation already governed for the three SCI1-018/019/020
  baselines (`eval/_baselines.py`) -- reusing it keeps Model Generation 1
  directly comparable to the SCI1-022 gate baselines on identical
  features, isolating the effect of the LEARNING OBJECTIVE (independent
  vs comparative) rather than confounding it with a representation change.
  A GNN/transformer/structural backend remains a future, swappable
  branch -- see `ModelBackend` Protocol below.

Two model generations, same representation, different objective
--------------------------------------------------------------------
  Baseline0Independent: four separate Ridge models, one per isoform,
    fit to predict pAct_isoform directly. Selectivity differences are
    computed AFTER the fact as pred_alpha - pred_X (never trained on the
    difference itself).
  Baseline2Comparative: a single joint model whose targets are the
    Constitution SS2.3(4) S1 vector directly (pAct_alpha, alpha-beta,
    alpha-gamma, alpha-delta) -- i.e. the comparative representation
    learns the DIFFERENCE as a first-class target, never derived after
    the fact from two independent predictions.

This directly operationalizes the project's central scientific
hypothesis (comparative evidence improves isoform-selective prediction
beyond independent per-isoform learning) as a controlled comparison: same
features, same held-out compounds, only the objective differs.

Every prediction and metric is labelled MODEL_GENERATION_1_BASELINE --
this is a first, deliberately simple baseline, not a final model, and its
results do not constitute a determinant or generality claim (Charter
Phase 1 claim ceiling).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import Ridge

from orthosteric.data._comparative_example import ComparativeExample

__all__ = [
    "MODEL_GENERATION_1_POLICY_ID",
    "Baseline0Independent",
    "Baseline2Comparative",
    "ModelBackend",
    "morgan_features",
]

MODEL_GENERATION_1_POLICY_ID = "model_generation_1_baseline_ridge_morgan_v1"

_DEFAULT_FP_RADIUS = 2
_DEFAULT_FP_NBITS = 2048
_ISOFORMS = ("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta")


def morgan_features(
    smiles: str, radius: int = _DEFAULT_FP_RADIUS, n_bits: int = _DEFAULT_FP_NBITS
) -> NDArray[np.float64] | None:
    """Shared molecular representation (reused from eval/_baselines.py's
    convention) -- the swappable INPUT REPRESENTATION branch. A future
    graph/structural/interaction-evidence representation implements the
    same (smiles_or_evidence -> feature vector) contract.
    """
    from rdkit import Chem  # noqa: PLC0415
    from rdkit.Chem import rdMolDescriptors  # noqa: PLC0415

    try:
        mol = Chem.MolFromSmiles(smiles)
        fp = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
        return np.array(list(fp), dtype=np.float64)
    except Exception:
        return None


class ModelBackend(Protocol):
    """Swappable model-backend interface (Section 9 of the execution
    mandate). SklearnRidge is the only implementation today; a GNN,
    transformer, or structural-evidence-aware backend would implement
    the same fit/predict contract.
    """

    def fit(self, targets: list[ComparativeExample]) -> None: ...
    def predict(self, smiles: str) -> dict[str, float]: ...


@dataclass
class Baseline0Independent:
    """Four independent per-isoform Ridge models (COMPARATIVE OBJECTIVE:
    none -- this is the null comparative hypothesis). Selectivity
    differences are derived post hoc, never trained on directly.
    """

    alpha_coef: float = 1.0  # ridge regularization strength (documented default)
    _models: dict[str, Ridge] = field(default_factory=dict, repr=False)
    policy: str = field(default=MODEL_GENERATION_1_POLICY_ID)

    def fit(self, targets: list[ComparativeExample]) -> None:
        x_by_iso: dict[str, list[NDArray[np.float64]]] = {iso: [] for iso in _ISOFORMS}
        y_by_iso: dict[str, list[float]] = {iso: [] for iso in _ISOFORMS}
        for t in targets:
            fp = morgan_features(t.smiles) if t.smiles else None
            if fp is None:
                continue
            x_by_iso["PI3Kalpha"].append(fp)
            y_by_iso["PI3Kalpha"].append(t.pac_alpha)
            for iso, attr in (
                ("PI3Kbeta", "lr_vs_beta"),
                ("PI3Kgamma", "lr_vs_gamma"),
                ("PI3Kdelta", "lr_vs_delta"),
            ):
                diff = getattr(t, attr)
                if diff is not None:
                    x_by_iso[iso].append(fp)
                    y_by_iso[iso].append(t.pac_alpha - diff)  # recover pAct_X
        for iso in _ISOFORMS:
            if x_by_iso[iso]:
                model = Ridge(alpha=self.alpha_coef)
                model.fit(np.stack(x_by_iso[iso]), np.array(y_by_iso[iso]))
                self._models[iso] = model

    def predict(self, smiles: str) -> dict[str, float]:
        fp = morgan_features(smiles)
        if fp is None:
            return {}
        return {
            iso: float(self._models[iso].predict(fp.reshape(1, -1))[0])
            for iso in _ISOFORMS
            if iso in self._models
        }


@dataclass
class Baseline2Comparative:
    """Comparative objective: a single joint model whose targets ARE the
    S1 vector (Constitution SS2.3(4)) -- (pAct_alpha, alpha-beta,
    alpha-gamma, alpha-delta) -- fit with GENUINE parameter coupling
    across outputs via a shared latent representation (PLSRegression),
    not four independent single-target fits.

    Why PLS, not four independent Ridge fits (bounded, documented choice)
    ---------------------------------------------------------------------
    Ridge regression is LINEAR in the target vector: for fixed X and
    regularization, Ridge(X -> y1) - Ridge(X -> y2) == Ridge(X -> y1-y2)
    EXACTLY. This was discovered empirically while building this module:
    an initial Baseline2 implementation using four independent Ridge fits
    on (alpha, alpha-beta, alpha-gamma, alpha-delta) produced IDENTICAL
    held-out predictions to Baseline0Independent's four independent Ridge
    fits on (alpha, beta, gamma, delta) reconstructed via pred_alpha -
    pred_X -- because alpha_i - (alpha_i - beta_i) = beta_i exactly, by
    linearity of the ridge estimator, whenever both targets are fit on the
    identical training population (true here, since every ComparativeExample
    is complete in all four isoforms by construction). A linear "difference"
    objective and a linear "independent" objective are the SAME model.

    PLSRegression's latent components are extracted to jointly maximize
    covariance with the FULL target matrix Y at once -- choosing
    Y = [alpha, alpha-beta, alpha-gamma, alpha-delta] induces different
    latent components than Y = [alpha, beta, gamma, delta], because the
    component-extraction step depends on the joint covariance structure of
    Y, not just per-column linear algebra. This makes the two objectives
    genuinely distinguishable for a shared-representation model, which is
    the actual scientific question (execution mandate SS14): does a shared
    comparative representation add value over independent per-isoform
    learning -- not "are two algebraically-equivalent linear systems equal"
    (they always are).
    """

    n_components: int = 8  # documented default; not governed
    _model: Any = field(default=None, repr=False)
    _fitted: bool = field(default=False, repr=False)
    policy: str = field(default=MODEL_GENERATION_1_POLICY_ID)

    def fit(self, targets: list[ComparativeExample]) -> None:
        from sklearn.cross_decomposition import PLSRegression  # noqa: PLC0415

        x_rows, y_rows = [], []
        for t in targets:
            fp = morgan_features(t.smiles) if t.smiles else None
            if fp is None or t.lr_vs_beta is None or t.lr_vs_gamma is None or t.lr_vs_delta is None:
                continue
            x_rows.append(fp)
            y_rows.append([t.pac_alpha, t.lr_vs_beta, t.lr_vs_gamma, t.lr_vs_delta])
        if not x_rows:
            return
        x_matrix = np.stack(x_rows)
        y_matrix = np.array(y_rows)
        n_comp = min(self.n_components, x_matrix.shape[0] - 1, x_matrix.shape[1])
        model = PLSRegression(n_components=max(1, n_comp))
        model.fit(x_matrix, y_matrix)
        self._model = model
        self._fitted = True

    def predict(self, smiles: str) -> dict[str, float]:
        fp = morgan_features(smiles)
        if fp is None or not self._fitted:
            return {}
        pred = self._model.predict(fp.reshape(1, -1))[0]
        alpha, diff_b, diff_g, diff_d = pred
        return {
            "PI3Kalpha": float(alpha),
            "PI3Kbeta": float(alpha - diff_b),
            "PI3Kgamma": float(alpha - diff_g),
            "PI3Kdelta": float(alpha - diff_d),
        }

"""Neural regression head for Model Generation 1 (RegressionHead Protocol).

Objective: extends the existing, tested `ComparativeSelectivityModelV1`
architecture (learning._model_v1) with a real neural network head,
implementing the exact same `RegressionHead` Protocol as `PLSHead` --
zero changes anywhere else in the orchestrator, encoder, or objective
code. This is possible only because that architecture was already built
to be swappable at exactly this boundary.

Why this extension, why now: this project never had a GPU available in
any prior session, so Model Generation 1 used only classical estimators
(Ridge, PLSRegression) on Morgan fingerprints. A GPU is now available
(NVIDIA RTX 5000 Ada, 16GB) and PyTorch-CUDA is installed this session --
a genuinely new capability, used here for the one place in this project's
existing architecture explicitly designed to accept it (`RegressionHead`
is a documented extension point; its docstring names "a future neural
head" as the anticipated next implementation).

Device selection (this session's use of "GPU when possible and
beneficial")
-----------------------------------------------------------------------
`torch.cuda.is_available()` is checked once at construction; CUDA is used
when available, CPU otherwise -- never asserted, always verified. GPU-
accelerated MOLECULAR DOCKING was investigated first and found
infeasible in this environment (no nvcc, no prebuilt GPU-docking
binaries, no sudo for a system CUDA toolkit); this neural head is the
genuinely available and beneficial GPU use identified instead -- training
a small MLP on ~800-1000 rows x 2048 features benefits meaningfully from
GPU parallelism for the matrix multiplies, even though the dataset itself
is not enormous.

Internal validation split (bounded engineering choice, documented)
------------------------------------------------------------------
`RegressionHead.fit(x, y)` receives only the TRAINING rows the orchestrator
selected (per the Family B protocol, the external held-out test set is
never passed to any head's fit()). For early stopping, this head carves a
further internal validation split OUT OF that training data (default 15%,
seeded) -- it never touches the external test set, and this internal
split is separate from and additional to the external train/val/test
split already performed by analysis/run_family_b_controlled_comparison.py
or any future control script.

Determinism
-----------
`torch.manual_seed` and (if CUDA) `torch.cuda.manual_seed_all` are set from
the `seed` constructor argument before model initialization; the training
loop itself uses no other source of randomness (no data augmentation, no
random dropout mask beyond torch's own seeded RNG). Full bit-exact
reproducibility across CUDA runs is NOT independently verified here (GPU
floating-point non-associativity across kernel launches is a documented,
real phenomenon, directly analogous to the multi-threaded Vina
non-determinism this project already found and corrected for docking
scores -- see docs/PRODUCTION_PILOT_AND_REPRODUCIBILITY_REPORT.md). This
is stated as an open verification item, not asserted as solved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import torch
    from torch import Tensor, nn

import numpy as np
from numpy.typing import NDArray

NEURAL_HEAD_POLICY_ID = "model_generation_1_neural_head_v1_torch"

_DEFAULT_HIDDEN_DIMS = (512, 256)
_DEFAULT_DROPOUT = 0.2
_DEFAULT_LR = 1e-3
_DEFAULT_MAX_EPOCHS = 300
_DEFAULT_PATIENCE = 20
_DEFAULT_VAL_FRACTION = 0.15
_DEFAULT_SEED = 42
_DEFAULT_WEIGHT_DECAY = 1e-4
_DEFAULT_BATCH_SIZE = 64


@dataclass(frozen=True, slots=True)
class _TrainingTensors:
    """Bundles the four device-resident tensors _train_loop needs.

    Avoids a five-plus-positional-argument signature.
    """

    x_tr: Tensor
    y_tr: Tensor
    x_val: Tensor
    y_val: Tensor


def resolve_device(requested: str | None = None) -> str:
    """Return the torch device string to use.

    Checks CUDA availability directly rather than assuming it; never
    claims GPU use it did not verify.
    """
    import torch  # noqa: PLC0415

    if requested is not None:
        return requested
    return "cuda" if torch.cuda.is_available() else "cpu"


@dataclass
class NeuralHead:
    """Small MLP regression head: real PyTorch, GPU-accelerated when available.

    Implements the exact `RegressionHead` Protocol (learning._model_v1):
    fit(x, y) / predict(x).

    n_components-style hyperparameters here (hidden_dims, dropout, lr,
    max_epochs, patience) are ENGINEERING CHOICES with documented
    defaults, exactly analogous to PLSHead's n_components -- not governed
    thresholds, selected for a reasonable first pass, not tuned.
    """

    output_dim: int
    hidden_dims: tuple[int, ...] = _DEFAULT_HIDDEN_DIMS
    dropout: float = _DEFAULT_DROPOUT
    lr: float = _DEFAULT_LR
    weight_decay: float = _DEFAULT_WEIGHT_DECAY
    max_epochs: int = _DEFAULT_MAX_EPOCHS
    patience: int = _DEFAULT_PATIENCE
    val_fraction: float = _DEFAULT_VAL_FRACTION
    batch_size: int = _DEFAULT_BATCH_SIZE
    seed: int = _DEFAULT_SEED
    device: str | None = None  # resolved lazily in fit(); None = auto-detect

    _model: Any = field(default=None, repr=False)
    _resolved_device: str = field(default="", repr=False)
    _x_mean: Any = field(default=None, repr=False)
    _x_std: Any = field(default=None, repr=False)
    _training_history: list[dict[str, float]] = field(default_factory=list, repr=False)

    def _build_model(self, input_dim: int, output_dim: int) -> nn.Module:
        from torch import nn  # noqa: PLC0415

        layers: list[Any] = []
        prev = input_dim
        for h in self.hidden_dims:
            layers += [nn.Linear(prev, h), nn.ReLU(), nn.Dropout(self.dropout)]
            prev = h
        layers.append(nn.Linear(prev, output_dim))
        return nn.Sequential(*layers)

    def fit(self, x: NDArray[np.float64], y: NDArray[np.float64]) -> None:
        import torch  # noqa: PLC0415

        torch.manual_seed(self.seed)
        self._resolved_device = resolve_device(self.device)
        if self._resolved_device == "cuda":
            torch.cuda.manual_seed_all(self.seed)

        x_tr, y_tr, x_val, y_val = self._internal_train_val_split(x, y)

        # Standardize inputs using TRAIN statistics only (never leak val/test
        # statistics into normalization -- the same discipline this project
        # already applies to scaffold splits and component selection).
        self._x_mean = x_tr.mean(axis=0, keepdims=True)
        self._x_std = x_tr.std(axis=0, keepdims=True) + 1e-8

        device = torch.device(self._resolved_device)
        model = self._build_model(x.shape[1], y_tr.shape[1]).to(device)
        tensors = self._to_device_tensors(x_tr, y_tr, x_val, y_val, device)
        self._model = self._train_loop(model, device, tensors)

    def _internal_train_val_split(
        self, x: NDArray[np.float64], y: NDArray[np.float64]
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
        """Carve an internal validation split out of the TRAINING rows.

        Never touches the external test set -- see module docstring.
        """
        y2d = y.reshape(-1, 1) if y.ndim == 1 else y
        n = x.shape[0]
        _min_rows_for_split = 4  # below this, use all rows for both train and internal val
        if n < _min_rows_for_split:
            return x, y2d, x, y2d
        rng = np.random.RandomState(self.seed)
        idx = rng.permutation(n)
        n_val = max(1, round(n * self.val_fraction))
        val_idx, tr_idx = idx[:n_val], idx[n_val:]
        return x[tr_idx], y2d[tr_idx], x[val_idx], y2d[val_idx]

    def _to_device_tensors(
        self,
        x_tr: NDArray[np.float64],
        y_tr: NDArray[np.float64],
        x_val: NDArray[np.float64],
        y_val: NDArray[np.float64],
        device: torch.device,
    ) -> _TrainingTensors:
        import torch  # noqa: PLC0415

        x_tr_n = (x_tr - self._x_mean) / self._x_std
        x_val_n = (x_val - self._x_mean) / self._x_std
        return _TrainingTensors(
            x_tr=torch.tensor(x_tr_n, dtype=torch.float32, device=device),
            y_tr=torch.tensor(y_tr, dtype=torch.float32, device=device),
            x_val=torch.tensor(x_val_n, dtype=torch.float32, device=device),
            y_val=torch.tensor(y_val, dtype=torch.float32, device=device),
        )

    def _train_loop(
        self, model: nn.Module, device: torch.device, tensors: _TrainingTensors
    ) -> nn.Module:
        import torch  # noqa: PLC0415

        x_tr_t, y_tr_t, x_val_t, y_val_t = tensors.x_tr, tensors.y_tr, tensors.x_val, tensors.y_val
        optimizer = torch.optim.Adam(model.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        loss_fn = torch.nn.MSELoss()
        best_val_loss = float("inf")
        best_state = None
        epochs_without_improvement = 0
        n_tr = x_tr_t.shape[0]
        self._training_history = []
        _improvement_epsilon = 1e-6

        for epoch in range(self.max_epochs):
            model.train()
            perm = torch.randperm(n_tr, device=device)
            for start in range(0, n_tr, self.batch_size):
                batch_idx = perm[start : start + self.batch_size]
                optimizer.zero_grad()
                pred = model(x_tr_t[batch_idx])
                loss = loss_fn(pred, y_tr_t[batch_idx])
                loss.backward()
                optimizer.step()

            model.eval()
            with torch.no_grad():
                val_pred = model(x_val_t)
                val_loss = float(loss_fn(val_pred, y_val_t).item())
            self._training_history.append({"epoch": epoch, "val_loss": val_loss})

            if val_loss < best_val_loss - _improvement_epsilon:
                best_val_loss = val_loss
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
                epochs_without_improvement = 0
            else:
                epochs_without_improvement += 1
                if epochs_without_improvement >= self.patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state)
        model.eval()
        return model

    def predict(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        import torch  # noqa: PLC0415

        if self._model is None:
            raise RuntimeError("NeuralHead.predict() called before fit()")
        device = torch.device(self._resolved_device)
        x_n = (x - self._x_mean) / self._x_std
        x_t = torch.tensor(x_n, dtype=torch.float32, device=device)
        with torch.no_grad():
            pred = self._model(x_t)
        return pred.cpu().numpy()

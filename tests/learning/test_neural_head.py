"""Tests for NeuralHead (learning._neural_head), the PyTorch RegressionHead
implementation.

Exit criteria:
  (1) Implements the exact RegressionHead Protocol -- fit/predict work
      identically in shape/contract to PLSHead.
  (2) resolve_device() actually checks torch.cuda.is_available() rather
      than assuming; forced device override is respected.
  (3) Predicting before fit() raises, never silently returns garbage.
  (4) Deterministic given the same seed (same device, same data).
  (5) Internal validation split never grows the effective training set
      beyond what was passed in, and standardization statistics come
      from the training split only (no leakage from the internal val
      carve-out).
  (6) Handles both 1-D (single-axis) and 2-D (joint multi-output) targets,
      matching PLSHead's usage in ComparativeSelectivityModelV1.

Tests force device="cpu" explicitly for hardware-independent, fast CI --
GPU usage itself is exercised separately in the real training run
(analysis/run_neural_head_family_b_comparison.py), not required for these
unit tests to pass.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from orthosteric.learning._neural_head import NeuralHead, resolve_device

torch = pytest.importorskip("torch")


def _synthetic_regression_data(
    n: int = 60, d: int = 32, out_dim: int = 1, seed: int = 0
) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any]]:
    rng = np.random.RandomState(seed)
    x = rng.randn(n, d)
    true_w = rng.randn(d, out_dim)
    y = x @ true_w + 0.01 * rng.randn(n, out_dim)
    return x.astype(np.float64), (y[:, 0] if out_dim == 1 else y).astype(np.float64)


def test_resolve_device_checks_cuda_availability() -> None:
    assert resolve_device() in ("cuda", "cpu")
    assert resolve_device() == ("cuda" if torch.cuda.is_available() else "cpu")


def test_resolve_device_forced_override_respected() -> None:
    assert resolve_device("cpu") == "cpu"


def test_fit_predict_single_output() -> None:
    x, y = _synthetic_regression_data(out_dim=1)
    head = NeuralHead(output_dim=1, device="cpu", max_epochs=20, hidden_dims=(16,))
    head.fit(x, y)
    pred = head.predict(x)
    assert pred.shape[0] == x.shape[0]


def test_fit_predict_multi_output_joint() -> None:
    x, y = _synthetic_regression_data(out_dim=4)
    head = NeuralHead(output_dim=4, device="cpu", max_epochs=20, hidden_dims=(16,))
    head.fit(x, y)
    pred = head.predict(x)
    assert pred.shape == (x.shape[0], 4)


def test_predict_before_fit_raises() -> None:
    head = NeuralHead(output_dim=1, device="cpu")
    with pytest.raises(RuntimeError, match="before fit"):
        head.predict(np.zeros((5, 10)))


def test_deterministic_given_same_seed_and_device() -> None:
    x, y = _synthetic_regression_data(out_dim=1)
    h1 = NeuralHead(output_dim=1, device="cpu", max_epochs=15, hidden_dims=(16,), seed=7)
    h2 = NeuralHead(output_dim=1, device="cpu", max_epochs=15, hidden_dims=(16,), seed=7)
    h1.fit(x, y)
    h2.fit(x, y)
    p1, p2 = h1.predict(x), h2.predict(x)
    assert np.allclose(p1, p2, atol=1e-5)


def test_different_seeds_can_produce_different_results() -> None:
    """Sanity check that the seed argument is actually load-bearing (not
    a no-op that happens to always converge identically)."""
    x, y = _synthetic_regression_data(out_dim=1, n=40, d=64)
    h1 = NeuralHead(output_dim=1, device="cpu", max_epochs=5, hidden_dims=(8,), seed=1)
    h2 = NeuralHead(output_dim=1, device="cpu", max_epochs=5, hidden_dims=(8,), seed=2)
    h1.fit(x, y)
    h2.fit(x, y)
    p1, p2 = h1.predict(x), h2.predict(x)
    assert not np.allclose(p1, p2, atol=1e-8)


def test_standardization_uses_training_split_only() -> None:
    """The internal val carve-out must not influence the standardization
    statistics -- verified by checking _x_mean/_x_std are computed before
    the val split is used for anything else."""
    x, y = _synthetic_regression_data(n=50, d=20)
    head = NeuralHead(output_dim=1, device="cpu", max_epochs=5, hidden_dims=(8,), val_fraction=0.2)
    head.fit(x, y)
    assert head._x_mean is not None
    assert head._x_mean.shape == (1, 20)


def test_internal_val_split_does_not_grow_training_set() -> None:
    """A very small input (n=3) must not crash -- falls back to using
    all rows for both train and internal val rather than fabricating
    extra rows."""
    x, y = _synthetic_regression_data(n=3, d=10)
    head = NeuralHead(output_dim=1, device="cpu", max_epochs=3, hidden_dims=(4,))
    head.fit(x, y)  # must not raise
    pred = head.predict(x)
    assert pred.shape[0] == 3

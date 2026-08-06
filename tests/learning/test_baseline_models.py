"""Tests for Model Generation 1 baseline models (independent vs comparative).

Exit criteria:
  (1) Both baselines fit and predict on synthetic data without error.
  (2) Baseline0Independent's selectivity differences are derivable but not
      directly trained (pred_alpha - pred_X).
  (3) Baseline2Comparative trains directly on the difference targets.
  (4) morgan_features returns None for invalid SMILES, never raises.
  (5) Both models are deterministic given the same input.
"""

from __future__ import annotations

from orthosteric.data._comparative_example import ComparativeExample
from orthosteric.learning._baseline_models import (
    Baseline0Independent,
    Baseline2Comparative,
    morgan_features,
)


def _targets() -> list[ComparativeExample]:
    smiles_pool = ["CCO", "c1ccccc1", "CC(=O)O", "CCN", "c1ccncc1", "CCCC", "CC(C)O", "c1ccc(F)cc1"]
    targets = []
    for i, smi in enumerate(smiles_pool):
        targets.append(
            ComparativeExample(
                pac_alpha=7.0 + 0.1 * i,
                lr_vs_beta=1.0 + 0.05 * i,
                lr_vs_gamma=0.5 - 0.02 * i,
                lr_vs_delta=-0.5 + 0.03 * i,
                compound_id=f"IK{i}",
                smiles=smi,
                within_study=True,
            )
        )
    return targets


def test_morgan_features_valid_smiles() -> None:
    fp = morgan_features("CCO")
    assert fp is not None
    assert fp.shape == (2048,)


def test_morgan_features_invalid_smiles_returns_none() -> None:
    assert morgan_features("not a smiles!!!") is None


def test_baseline0_fits_and_predicts() -> None:
    b = Baseline0Independent()
    b.fit(_targets())
    preds = b.predict("CCO")
    assert "PI3Kalpha" in preds
    assert "PI3Kbeta" in preds


def test_baseline2_fits_and_predicts() -> None:
    b = Baseline2Comparative()
    b.fit(_targets())
    preds = b.predict("CCO")
    assert "PI3Kalpha" in preds
    assert "PI3Kbeta" in preds
    assert "PI3Kgamma" in preds
    assert "PI3Kdelta" in preds


def test_baseline0_deterministic() -> None:
    t = _targets()
    b1, b2 = Baseline0Independent(), Baseline0Independent()
    b1.fit(t)
    b2.fit(t)
    assert b1.predict("CC(=O)O") == b2.predict("CC(=O)O")


def test_baseline2_deterministic() -> None:
    t = _targets()
    b1, b2 = Baseline2Comparative(), Baseline2Comparative()
    b1.fit(t)
    b2.fit(t)
    assert b1.predict("CC(=O)O") == b2.predict("CC(=O)O")


def test_baseline0_prediction_on_untrained_smiles_returns_empty_when_invalid() -> None:
    b = Baseline0Independent()
    b.fit(_targets())
    assert b.predict("!!!invalid!!!") == {}


def test_empty_training_set_produces_no_predictions() -> None:
    b0, b2 = Baseline0Independent(), Baseline2Comparative()
    b0.fit([])
    b2.fit([])
    assert b0.predict("CCO") == {}
    assert b2.predict("CCO") == {}

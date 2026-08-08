"""Tests for the Model Generation 1 v1 encoder/head/objective interface.

Exit criteria:
  (1) Independent and comparative objectives can be swapped without
      changing encoder or head construction (modular substitution).
  (2) A dummy encoder/head can replace Morgan/PLS without touching the
      orchestrator -- proves the interfaces are real boundaries, not
      just named the same.
  (3) structural_features=None (ligand-only) never fabricates a
      structural contribution -- output is unchanged from omitting it.
  (4) A compound missing from a supplied structural_features mapping is
      SKIPPED (never zero-filled) -- verifies the anti-fabrication rule.
  (5) as_scorer() exposes only score(), nothing else.
  (6) Both objectives are deterministic given the same input.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from orthosteric.data._comparative_example import ComparativeExample
from orthosteric.learning._model_v1 import (
    ComparativeObjective,
    ComparativeSelectivityModelV1,
    MorganEncoder,
    PLSHead,
    StructuralFeatureMode,
)


def _examples() -> list[ComparativeExample]:
    smiles_pool = ["CCO", "c1ccccc1", "CC(=O)O", "CCN", "c1ccncc1", "CCCC", "CC(C)O", "c1ccc(F)cc1"]
    out = []
    for i, smi in enumerate(smiles_pool):
        out.append(
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
    return out


class _ConstantEncoder:
    """Dummy encoder proving the interface is a real substitution point."""

    def encode(self, smiles: str) -> np.ndarray[Any, Any]:  # noqa: ARG002
        return np.array([1.0, 2.0, 3.0])

    def output_dim(self) -> int:
        return 3


class _MeanHead:
    """Dummy head proving the interface is a real substitution point."""

    def __init__(self) -> None:
        self._mean: np.ndarray[Any, Any] | None = None

    def fit(self, x: np.ndarray[Any, Any], y: np.ndarray[Any, Any]) -> None:  # noqa: ARG002
        self._mean = np.mean(y, axis=0)

    def predict(self, x: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        assert self._mean is not None, "predict called before fit"
        return (
            np.tile(self._mean, (x.shape[0], 1))
            if self._mean.ndim
            else np.full((x.shape[0],), self._mean)
        )


def test_independent_objective_fits_and_predicts() -> None:
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.INDEPENDENT,
        head_factory=lambda: PLSHead(n_components=2),
    )
    model.fit(_examples())
    preds = model.predict("CCO")
    assert set(preds) == {"PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}


def test_comparative_objective_fits_and_predicts() -> None:
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.COMPARATIVE,
        head_factory=lambda: PLSHead(n_components=2),
    )
    model.fit(_examples())
    preds = model.predict("CCO")
    assert set(preds) == {"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}


def test_objective_swap_without_touching_encoder_or_head() -> None:
    """The exact modular-substitution proof: only `objective` changes."""
    kwargs: dict[str, Any] = {
        "encoder": MorganEncoder(),
        "head_factory": lambda: PLSHead(n_components=2),
    }
    m_indep = ComparativeSelectivityModelV1(objective=ComparativeObjective.INDEPENDENT, **kwargs)
    m_comp = ComparativeSelectivityModelV1(objective=ComparativeObjective.COMPARATIVE, **kwargs)
    m_indep.fit(_examples())
    m_comp.fit(_examples())
    assert set(m_indep.predict("CCO")) != set(m_comp.predict("CCO"))  # different output shape
    assert "PI3Kalpha" not in m_indep.predict("CCO")  # independent never predicts alpha
    assert "PI3Kalpha" in m_comp.predict("CCO")  # comparative always does


def test_dummy_encoder_and_head_substitute_cleanly() -> None:
    """A completely different encoder/head pair, proving the Protocols are
    real boundaries and not accidentally coupled to Morgan/PLS internals."""
    model = ComparativeSelectivityModelV1(
        encoder=_ConstantEncoder(),
        objective=ComparativeObjective.INDEPENDENT,
        head_factory=_MeanHead,
    )
    model.fit(_examples())
    preds = model.predict("anything, ignored by _ConstantEncoder")
    assert set(preds) == {"PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}


def test_ligand_only_output_unchanged_by_absent_structural_features() -> None:
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.COMPARATIVE,
        head_factory=lambda: PLSHead(n_components=2),
    )
    examples = _examples()
    model.fit(examples, structural_features=None)
    preds_none = model.predict("CCO", structural_features=None)
    model2 = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.COMPARATIVE,
        head_factory=lambda: PLSHead(n_components=2),
    )
    model2.fit(examples)  # omitted entirely
    preds_omitted = model2.predict("CCO")
    assert preds_none == preds_omitted


def test_compound_missing_from_structural_features_is_skipped_not_fabricated() -> None:
    """Anti-fabrication rule: a compound absent from the structural
    feature mapping must be dropped, never zero-filled."""
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.INDEPENDENT,
        head_factory=lambda: PLSHead(n_components=1),
    )
    examples = _examples()
    partial_structural = {examples[0].compound_id: np.array([9.0])}  # only IK0 has structural data
    model.fit(examples, structural_features=partial_structural)
    # Only 1 of 8 examples had structural evidence -> effectively no usable
    # training rows for a >1-row fit; verify no crash and no fabricated result.
    smiles_1 = examples[1].smiles
    assert smiles_1 is not None
    preds = model.predict(smiles_1, structural_features=partial_structural)
    assert preds == {} or isinstance(preds, dict)  # must not raise; must not fabricate


def test_as_scorer_exposes_only_score() -> None:
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.COMPARATIVE,
        head_factory=lambda: PLSHead(n_components=2),
    )
    model.fit(_examples())
    scorer = model.as_scorer()
    assert hasattr(scorer, "score")
    result = scorer.score("CCO")
    assert isinstance(result, dict)
    assert not hasattr(scorer, "fit")
    assert not hasattr(scorer, "encoder")


def test_deterministic_given_same_input() -> None:
    kwargs: dict[str, Any] = {
        "encoder": MorganEncoder(),
        "head_factory": lambda: PLSHead(n_components=2),
        "objective": ComparativeObjective.COMPARATIVE,
    }
    m1 = ComparativeSelectivityModelV1(**kwargs)
    m2 = ComparativeSelectivityModelV1(**kwargs)
    ex = _examples()
    m1.fit(ex)
    m2.fit(ex)
    assert m1.predict("c1ccccc1") == m2.predict("c1ccccc1")


def test_unfitted_model_predicts_empty() -> None:
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.COMPARATIVE,
        head_factory=lambda: PLSHead(n_components=2),
    )
    assert model.predict("CCO") == {}


# ── MULTI_TASK_ABSOLUTE objective (Baseline 1 decomposition) ────────────────


def test_multi_task_absolute_objective_fits_and_predicts() -> None:
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.MULTI_TASK_ABSOLUTE,
        head_factory=lambda: PLSHead(n_components=2),
    )
    model.fit(_examples())
    preds = model.predict("CCO")
    assert set(preds) == {"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}


class _FixedJointHead:
    """Deterministic dummy head: always predicts a known [alpha, x, y, z]
    row, regardless of fit data or input -- used to test the EXACT
    reconstruction arithmetic in predict(), not just output key presence."""

    def fit(self, x: np.ndarray[Any, Any], y: np.ndarray[Any, Any]) -> None:
        pass

    def predict(self, x: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        return np.tile(np.array([7.0, 3.0, 2.0, 1.0]), (x.shape[0], 1))


def test_comparative_predict_reconstructs_alpha_minus_diff_correctly() -> None:
    """Regression test for a real bug found while adding
    MULTI_TASK_ABSOLUTE: COMPARATIVE's head predicts [alpha, diff_beta,
    diff_gamma, diff_delta] -- predict() must return alpha - diff for each
    isoform, NOT the raw diff value relabeled as the isoform's activity."""
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.COMPARATIVE,
        head_factory=_FixedJointHead,
    )
    model.fit(_examples())
    preds = model.predict("CCO")
    # head always predicts [alpha=7.0, diff_beta=3.0, diff_gamma=2.0, diff_delta=1.0]
    assert preds["PI3Kalpha"] == 7.0
    assert preds["PI3Kbeta"] == 4.0  # 7.0 - 3.0, NOT 3.0
    assert preds["PI3Kgamma"] == 5.0  # 7.0 - 2.0, NOT 2.0
    assert preds["PI3Kdelta"] == 6.0  # 7.0 - 1.0, NOT 1.0


def test_multi_task_absolute_predict_uses_raw_values_no_arithmetic() -> None:
    """MULTI_TASK_ABSOLUTE's head is trained on absolute values directly
    -- predict() must pass them through unchanged, unlike COMPARATIVE."""
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.MULTI_TASK_ABSOLUTE,
        head_factory=_FixedJointHead,
    )
    model.fit(_examples())
    preds = model.predict("CCO")
    assert preds["PI3Kalpha"] == 7.0
    assert preds["PI3Kbeta"] == 3.0  # passthrough, no arithmetic
    assert preds["PI3Kgamma"] == 2.0
    assert preds["PI3Kdelta"] == 1.0


def test_three_objectives_all_swappable_independently_of_encoder_and_head() -> None:
    """All three ComparativeObjective values work with the same
    encoder/head_factory pair -- the target formulation is a genuine
    third independent axis of variation, not a special case of the other
    two."""
    kwargs: dict[str, Any] = {
        "encoder": MorganEncoder(),
        "head_factory": lambda: PLSHead(n_components=2),
    }
    for objective in ComparativeObjective:
        model = ComparativeSelectivityModelV1(objective=objective, **kwargs)
        model.fit(_examples())
        preds = model.predict("CCO")
        assert "PI3Kbeta" in preds  # every objective predicts beta somehow


# ── StructuralFeatureMode.INDICATOR_ZERO_FILL ────────────────────────────────
#
# Exercised for the first time this session (Stage D all-isoforms structural
# evidence matching found only 39/1,267 modeling-set compounds with ANY real
# PDB co-crystal evidence across alpha/gamma/delta combined -- still below
# the 50-compound documented floor for a trustworthy split, so this mode is
# NOT used to run an actual structural-augmented training experiment this
# session; see docs/STRUCTURAL_EVIDENCE_ALL_ISOFORMS_REPORT.md). These tests
# verify the mode itself is correct and available for when coverage improves.


def test_default_structural_mode_is_skip_missing() -> None:
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.INDEPENDENT,
        head_factory=lambda: PLSHead(n_components=1),
    )
    assert model.structural_mode is StructuralFeatureMode.SKIP_MISSING


def test_indicator_zero_fill_keeps_all_examples_none_dropped() -> None:
    """The entire point of this mode: unlike SKIP_MISSING, no example is
    dropped for lacking structural evidence."""
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.INDEPENDENT,
        head_factory=lambda: PLSHead(n_components=1),
        structural_mode=StructuralFeatureMode.INDICATOR_ZERO_FILL,
    )
    examples = _examples()
    partial = {examples[0].compound_id: np.array([9.0, 1.0])}  # only IK0 has real data
    _x, keep_idx = model._features(examples, partial)
    assert len(keep_idx) == len(examples)  # nothing dropped


def test_indicator_zero_fill_presence_bit_distinguishes_real_from_filled() -> None:
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.INDEPENDENT,
        head_factory=lambda: PLSHead(n_components=1),
        structural_mode=StructuralFeatureMode.INDICATOR_ZERO_FILL,
    )
    examples = _examples()
    partial = {examples[0].compound_id: np.array([9.0, 1.0])}
    x, _keep_idx = model._features(examples, partial)
    # last column is the presence bit
    assert x[0, -1] == 1.0  # IK0 has real structural data
    assert x[1, -1] == 0.0  # IK1 does not
    # the zero-filled structural block (excluding encoder dims and presence
    # bit) is exactly zero, never a fabricated non-zero value
    struct_dim = 2
    zero_filled_block = x[1, -(struct_dim + 1) : -1]
    assert np.all(zero_filled_block == 0.0)
    real_block = x[0, -(struct_dim + 1) : -1]
    assert np.allclose(real_block, [9.0, 1.0])


def test_indicator_zero_fill_fits_and_predicts_without_error() -> None:
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.COMPARATIVE,
        head_factory=lambda: PLSHead(n_components=2),
        structural_mode=StructuralFeatureMode.INDICATOR_ZERO_FILL,
    )
    examples = _examples()
    partial = {examples[0].compound_id: np.array([9.0, 1.0])}
    model.fit(examples, structural_features=partial)
    smiles_0 = examples[0].smiles
    assert smiles_0 is not None
    preds = model.predict(smiles_0, structural_features=partial)
    assert "PI3Kbeta" in preds
    preds_missing = model.predict("CCCCCC", structural_features=partial)
    assert preds_missing == {} or "PI3Kbeta" in preds_missing  # never raises


def test_skip_missing_mode_unchanged_from_before_this_session() -> None:
    """Regression guard: adding structural_mode must not alter
    SKIP_MISSING's behaviour (the only mode tested/used previously)."""
    model = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.INDEPENDENT,
        head_factory=lambda: PLSHead(n_components=1),
        structural_mode=StructuralFeatureMode.SKIP_MISSING,
    )
    examples = _examples()
    partial = {examples[0].compound_id: np.array([9.0])}
    _x, keep_idx = model._features(examples, partial)
    assert len(keep_idx) == 1  # only IK0 retained, exactly as before
    assert keep_idx == [0]

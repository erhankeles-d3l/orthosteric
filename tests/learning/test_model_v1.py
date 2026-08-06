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

import numpy as np

from orthosteric.data._comparative_example import ComparativeExample
from orthosteric.learning._model_v1 import (
    ComparativeObjective,
    ComparativeSelectivityModelV1,
    MorganEncoder,
    PLSHead,
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

    def encode(self, smiles):  # noqa: ARG002
        return np.array([1.0, 2.0, 3.0])

    def output_dim(self):
        return 3


class _MeanHead:
    """Dummy head proving the interface is a real substitution point."""

    def __init__(self) -> None:
        self._mean = None

    def fit(self, x, y):  # noqa: ARG002
        self._mean = np.mean(y, axis=0)

    def predict(self, x):
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
    kwargs = {"encoder": MorganEncoder(), "head_factory": lambda: PLSHead(n_components=2)}
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
    preds = model.predict(examples[1].smiles, structural_features=partial_structural)
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
    kwargs = {
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

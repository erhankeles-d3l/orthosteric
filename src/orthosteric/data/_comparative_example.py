"""Comparative training/evaluation example -- shared, layer-neutral type.

Objective: SI17 (import-linter Contract 4, layer dependency direction).
`orthosteric.eval` sits ABOVE `orthosteric.learning` in the layer stack
(ADR-0010): eval may depend on learning, learning may never depend on eval.

`orthosteric.eval._metrics.SelectivityTarget` is the eval-layer type used
by the SCI1-018/019/020 baselines and the SCI1-022 gate. Model Generation 1
(`orthosteric.learning._baseline_models`) needs the same fields but must
not import from `eval`. `ComparativeExample` is that shared representation,
defined at the `data` layer (below both `eval` and `learning`, so both may
depend on it) with a structurally identical field set to `SelectivityTarget`.

This is an ENGINEERING CHOICE (Category B: reversible, documented,
compatible with the existing governed layering; not a new scientific
claim) -- it does not redefine what a selectivity target IS, only where
its type lives.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ComparativeExample"]


@dataclass(frozen=True, slots=True)
class ComparativeExample:
    """One compound's comparative selectivity example, for model training
    and evaluation. Field semantics identical to
    `orthosteric.eval._metrics.SelectivityTarget` (Constitution SS2.3(4)
    S1 vector); duplicated here, not imported, to respect SI17 layering.

    Attributes:
        pac_alpha:    pActivity (pIC50 or equivalent) at PI3Kalpha.
        lr_vs_beta:   pAct_alpha - pAct_beta (positive = alpha-selective).
        lr_vs_gamma:  pAct_alpha - pAct_gamma.
        lr_vs_delta:  pAct_alpha - pAct_delta.
        compound_id:  Identifier for the compound.
        smiles:       Canonical SMILES, or None if unavailable.
        within_study: True iff all four isoform measurements are
                      comparable per Constitution SS2.3(1) (GDR-011
                      C1_PRIMARY panel).
    """

    pac_alpha: float
    lr_vs_beta: float | None
    lr_vs_gamma: float | None
    lr_vs_delta: float | None
    compound_id: str
    smiles: str | None
    within_study: bool

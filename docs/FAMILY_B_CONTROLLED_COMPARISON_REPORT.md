# Family B Controlled Comparison: Independent vs Comparative PLS

**Date:** 2026-08-06
**Snapshot:** A4, `SNAP-05748f6627ea` (unmodified — verified before/after)
**Purpose:** resolve the Ridge-vs-PLS confound in the prior baseline run
by holding estimator family, features, split, seed, and component budget
identical between the independent and comparative objectives.

## Controls held constant

| Control | Value |
|---|---|
| Feature representation | Morgan (ECFP4, r=2, 2048-bit) |
| Estimator family | `sklearn.cross_decomposition.PLSRegression` (both arms) |
| Split | scaffold-aware, seed=42, train=822 / val=191 / test=254, overlap=0 |
| Component grid | {1, 2, 4, 8, 16, 32} |
| Component selection | train (fit) + validation (score) only; test set never touched during selection |

## Component-selection procedure (documented, ENGINEERING CHOICE, not governed)

- **Independent** family: three separate single-output PLS-1 models
  (one per α−β, α−γ, α−δ), each selects its **own** best `n_components`
  from the grid via its own validation RMSE — fair, since these are
  genuinely independent models.
- **Comparative** family: one joint model selects **one** `n_components`
  via the **mean** validation RMSE across all three difference axes,
  since it is a single shared model.

Selected: independent → 2/2/2 components (β/γ/δ); comparative → 8 components.

## Results (held-out test, n=254)

| Model | Estimator | Features | n_comp | RMSE α−β | RMSE α−γ | RMSE α−δ | Sign acc β/γ/δ | Agg. RMSE | Agg. sign acc |
|---|---|---|---|---:|---:|---:|---|---:|---:|
| Independent PLS | PLS-1 ×3 | Morgan | 2/2/2 | 0.688 | 0.689 | 0.668 | .567/.693/.705 | 0.682 | 0.655 |
| Comparative PLS | PLS ×1 (joint) | Morgan | 8 | 0.675 | 0.684 | 0.632 | .575/.665/.783 | 0.663 | 0.675 |

## Per-axis comparison (comparative − independent)

| Axis | ΔRMSE | ΔSign acc | Verdict |
|---|---:|---:|---|
| α−β | −0.0135 | +0.0079 | comparative better |
| α−γ | −0.0052 | −0.0276 | comparative better (RMSE); worse (sign) |
| α−δ | −0.0367 | +0.0787 | comparative better |

## Verdict

**Comparative objective: WIN** on RMSE — better on 3/3 axes, no axis worse.
Sign accuracy is **better on 2/3 axes, worse on α−γ** by 0.028.

Consistent, but not uniform: the RMSE advantage is not concentrated in
one axis (all three improve, ranging −0.005 to −0.037), while the sign-
accuracy picture is mixed. The largest single improvement (α−δ, both
RMSE and sign accuracy) suggests the advantage may be somewhat isoform-
pair-dependent rather than a uniform "comparative always helps by X."

## Correct scientific framing

> This is evidence supporting the comparative-learning hypothesis under
> the current ligand-only PLS baseline, with a genuinely controlled
> comparison (same estimator, features, split, seed, and selection
> procedure). It is not evidence of general superiority, not a
> determinant claim, and not the final word — a single controlled run at
> one point in the component-selection grid, on one split, with one
> feature representation.

Full numeric output: `docs/governance/FAMILY_B_CONTROLLED_COMPARISON_A4.json`.
Reproducible via `analysis/run_family_b_controlled_comparison.py`.

## What this motivated: Model Generation 1 v1 interface

`src/orthosteric/learning/_model_v1.py` implements the architecture below,
informed by (not hard-wired to) this result — the PLS head and comparative
objective are the *default* choice, not the *only* one:

```
molecule (+ optional structural evidence, not exercised today)
        |
        v
MoleculeEncoder   -- swappable: MorganEncoder implemented
        |
        v
representation
        |
        v
RegressionHead    -- swappable: PLSHead implemented (this session's winner)
        |
        v
ComparativeObjective -- swappable: INDEPENDENT | COMPARATIVE
        |
        v
{isoform: pAct}
```

- Encoder, head, and objective are independent constructor arguments to
  `ComparativeSelectivityModelV1`; swapping one never requires touching
  the others (proven by `test_objective_swap_without_touching_encoder_or_head`
  and `test_dummy_encoder_and_head_substitute_cleanly`).
- Structural evidence extension point: `fit()`/`predict()` accept an
  optional `structural_features` mapping. `None` today (ligand-only,
  labelled as such). A compound missing from a supplied mapping is
  **skipped, never zero-filled** — the anti-fabrication rule is a tested
  invariant (`test_compound_missing_from_structural_features_is_skipped_not_fabricated`).
- Generative extension point: `as_scorer()` returns a `SelectivityScorer`
  exposing only `score(smiles) -> dict`, hiding encoder/head/objective
  from any future generator. No generator implemented.

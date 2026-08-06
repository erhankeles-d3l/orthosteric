# Three-Way Ablation: Independent vs Multi-Task-Absolute vs Comparative PLS

**Date:** 2026-08-06
**Snapshot:** A4, `SNAP-05748f6627ea` (unmodified — verified before/after)
**Purpose:** decompose the Family B result (comparative PLS beat
independent PLS on RMSE) into its two candidate causes — shared
representation vs. comparative target formulation.

## Controls (identical to Family B)

Morgan (r=2, 2048-bit), PLSRegression backend for all three arms, scaffold
split seed=42 (train=822/val=191/test=254, overlap=0), component grid
{1,2,4,8,16,32}, train+validation-only selection, test set never touched
during selection.

All three baselines implemented via `orthosteric.learning._model_v1.
ComparativeSelectivityModelV1` directly — the same orchestrator, only the
`objective` argument differs. This is the modular architecture doing real
experimental work, not just passing isolated unit tests.

## Selected components

- Baseline 0 (independent): β=2, γ=2, δ=2 (each axis its own selection)
- Baseline 1 (multi-task absolute): 8 (one joint model, mean-val-RMSE selection)
- Baseline 2 (comparative): 8 (same selection procedure as Baseline 1)

## Three-way matrix (held-out test, n=254)

| Model | Target | Shared latent | RMSE α−β | RMSE α−γ | RMSE α−δ | Agg. RMSE | Sign β | Sign γ | Sign δ | Agg. sign |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline 0 | selectivity differences | No | 0.688 | 0.689 | 0.668 | **0.682** | .567 | .693 | .705 | .655 |
| Baseline 1 | absolute α/β/γ/δ | Yes | 0.757 | 0.694 | 0.707 | **0.719** | .547 | .685 | .823 | .685 |
| Baseline 2 | selectivity differences | Yes | 0.675 | 0.684 | 0.632 | **0.663** | .575 | .665 | .783 | .675 |

## Decomposition

```
Shared representation alone (Baseline 0 -> Baseline 1):  RMSE 0.682 -> 0.719   (WORSE by 0.037)
Comparative target, same shared repr (Baseline 1 -> 2):  RMSE 0.719 -> 0.663   (BETTER by 0.056)
Net effect (Baseline 0 -> Baseline 2):                    RMSE 0.682 -> 0.663   (BETTER by 0.019)
```

## Scientific Decomposition

**None of the four anticipated cases fit cleanly — this is a fifth,
genuinely informative pattern the mandate didn't enumerate:
Baseline 1 < Baseline 0 < Baseline 2** (using "<" for "worse than" on
aggregate RMSE).

- **Shared representation alone is net HARMFUL here** (Baseline 1 is
  *worse* than Baseline 0 by 0.037 RMSE). A single joint PLS model
  spending its limited components on predicting four *absolute* isoform
  activities appears to dilute the representation relative to three
  independently-optimized single-target models — each independent model
  can spend its entire (small, k=2) component budget on exactly one
  target; the joint model must compromise across four.
- **The comparative target formulation is what converts this into a net
  win.** Training the same shared-latent architecture on differences
  directly (Baseline 2) not only erases Baseline 1's deficit but goes on
  to beat Baseline 0 by 0.019 RMSE.

**Classification: COMPARATIVE-TARGET EFFECT — but stronger than the
mandate's Case 1 anticipated**, because Case 1 assumed Baseline 1 ≈
Baseline 0 (shared representation being neutral). Here shared
representation alone is actively counterproductive, and the entire net
benefit — and then some, since it also has to overcome Baseline 1's
deficit — comes from training on the comparative target directly.

This is, if anything, **stronger evidence for building comparative-target
training into Model Generation 1 as a first-class objective** than a
clean monotonic Case 3 would have been: it rules out "any shared
representation helps" as the mechanism and isolates the effect specifically
to training on the S1 difference vector.

Caveats, stated plainly:
- One controlled run, one split, one seed, one feature representation.
- Sign accuracy is less clean: Baseline 1 has the *best* δ sign accuracy
  (.823) of all three models despite the worst RMSE — a reminder that
  RMSE and sign accuracy can disagree, and neither should be read as the
  single ground truth for "the model that predicts selectivity best."

Full numeric output: `docs/governance/THREE_WAY_ABLATION_A4.json`.
Reproducible via `analysis/run_baseline1_absolute_pls.py`.

## Architectural Consequence

Encoder, head, and target/objective are confirmed as genuinely independent
modules — `MULTI_TASK_ABSOLUTE` was added as a third `ComparativeObjective`
value with zero changes to `MoleculeEncoder`/`RegressionHead`, and this
experiment ran all three objectives through the identical orchestrator
class. This ablation would not have been possible to run this cleanly
without that separation already in place.

A real bug was found and fixed while extending the interface:
`ComparativeSelectivityModelV1.predict()`'s `COMPARATIVE` branch was
returning the raw predicted *difference* mislabeled as the isoform's
absolute activity, instead of reconstructing `alpha − diff`. This was
caught because adding `MULTI_TASK_ABSOLUTE` (which correctly needs no
such arithmetic) forced a side-by-side re-read of the method. Fixed, with
a regression test (`test_comparative_predict_reconstructs_alpha_minus_diff_correctly`)
using a deterministic dummy head so the exact arithmetic is checked, not
just output-key presence. The standalone Family B script never had this
bug (it evaluated the diff prediction against the actual diff directly,
never relabeling it), so the Family B numbers are unaffected.

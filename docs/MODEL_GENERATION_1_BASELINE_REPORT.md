# Model Generation 1 — Baseline Report (MODEL_GENERATION_1_BASELINE)

**Date:** 2026-08-06
**Snapshot:** A4, `SNAP-05748f6627ea` (unmodified — verified via md5sum before/after every run)
**Status label:** `MODEL_GENERATION_1_BASELINE` — a first, deliberately
simple baseline. Not a final model. No determinant or generality claim
(Charter §9.0 Phase 1 claim ceiling).

## Precondition: SCI1-022 gate = GO

See `ADR-0015-sci1022-gate-executed-go.md` and
`SCI1022_GATE_RECORD_A4.json`. Executed for real on A4 (this had never
been run before this session — code existed, no record did).

## Dataset

1,267 `SelectivityTarget`s built from A4's C1_PRIMARY (GDR-011) panels via
GDR-013's deterministic aggregation — every target complete in all four
isoforms, differences computed strictly within one panel, multi-panel
compounds' differences combined by median (documented in
`eval/_target_construction.py`).

Scaffold split (seed=42, SCI1-017): train 822 / val 191 / test 254
compounds; 407/57/115 scaffolds; overlap 0.

## Architecture

Representation: Morgan (ECFP4, r=2, 2048 bit) fingerprints — identical to
the SCI1-018/019/020 baselines, so the comparison isolates the *objective*
(independent vs comparative), not the representation.

- **Baseline0Independent**: four separate Ridge models, one per isoform.
  Selectivity differences derived post hoc (pred_α − pred_X), never
  trained directly.
- **Baseline2Comparative**: one joint PLSRegression model, fit on the S1
  vector (pAct_α, α−β, α−γ, α−δ) directly, with genuine shared-latent
  parameter coupling across all four outputs.

### A finding worth stating plainly

An earlier implementation of Baseline2 used four independent Ridge fits on
the difference targets instead of the absolute targets. That produced
**mathematically identical** held-out predictions to Baseline0 — not a
coincidence, a consequence of Ridge regression being linear in the target
vector: `Ridge(X→α) − Ridge(X→α−β) ≡ Ridge(X→β)` exactly, whenever both
targets are fit on the same rows (guaranteed here, since every target is
4-isoform-complete by construction). **A linear "predict the difference"
objective and a linear "predict independently" objective are the same
model.** This is why Baseline2 was rebuilt on PLSRegression: PLS's latent
components are extracted from the joint covariance of the full target
matrix, so choosing which columns go into that matrix genuinely changes
the model, unlike four separate linear fits.

## Results (held-out test, n=254)

| Axis | Independent RMSE | Comparative RMSE | Independent sign_acc | Comparative sign_acc |
|---|---:|---:|---:|---:|
| α (absolute) | 0.851 | 0.736 | — | — |
| α−β | 0.674 | 0.675 | 0.587 | 0.575 |
| α−γ | 0.760 | 0.684 | 0.685 | 0.665 |
| α−δ | 0.714 | 0.632 | 0.795 | 0.783 |

## Honest reading

- **Mixed result.** Comparative (PLS) beats independent (Ridge) on
  difference-RMSE for α−γ and α−δ, ties on α−β. Sign accuracy is
  consistently *slightly worse* for comparative across all three axes.
  The comparative model's absolute-α RMSE also improved (0.85→0.74),
  which may simply reflect PLS regularizing better than Ridge on this
  feature set generally, confounding the objective comparison with a
  backend comparison.
- **This baseline cannot cleanly separate "comparative objective helps"
  from "PLS vs Ridge as an estimator."** A rigorous test would hold the
  backend family fixed and vary only the objective (e.g. multi-output
  Ridge with genuine shared regularization vs independent Ridge) — not
  yet built. This is flagged as a design limitation of this baseline, not
  papered over.
- **Sign accuracy (0.57–0.80) is well above chance (0.5) for both models**
  on all three axes — some real, structure-derived selectivity signal
  exists in this feature representation, consistent with the SCI1-022
  finding that NN/PCM baselines already substantially beat ligand-only.

## What this baseline does NOT establish

- Not a determinant claim (Charter §9.0).
- Not evidence that PLS-style comparative learning is "the" right
  objective — only that, for these two specific estimator families, the
  comparative variant is directionally competitive on 2/3 axes and not
  clearly worse. A confound (backend family) remains unresolved.
- Not integrated with structural/interaction evidence (GDR-006's AlphaFold
  treatment, PDB structures) — pure ligand representation only.
- Not using GGR-002a (exploratory scaffold pairs) or GGR-002b
  (per-isoform-pair noise floor) as auxiliary evidence yet — both remain
  available, governed, and explicitly labeled, but unused in this baseline.

## Reproducibility

`analysis/run_modelgen1_baseline_comparison.py` — deterministic given A4 +
scaffold split seed 42. Full numeric output:
`docs/governance/MODELGEN1_BASELINE_COMPARISON_A4.json`.

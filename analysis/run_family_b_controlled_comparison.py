"""Family B controlled comparison: Independent PLS vs Comparative PLS.

Objective: resolve the Ridge-vs-PLS confound from the prior baseline run
by holding the estimator family, feature representation, data split,
seed, and component-selection budget IDENTICAL between the two objectives
under test. The only intended difference is:

  independent objective (three separate single-output PLS-1 models,
    one per alpha-vs-X difference, no shared latent space)
       vs
  comparative objective (one joint PLS model sharing latent components
    across all four S1 targets simultaneously)

Component selection (bounded, documented engineering choice; not governed)
------------------------------------------------------------------------------
Grid: {1, 2, 4, 8, 16, 32} components (capped by min(n_features, n_train-1)).
Selection uses TRAIN (fit) + VALIDATION (score) only -- the held-out TEST
set is never touched during model selection, only for final reporting.
  - Independent family: each of the three difference targets selects its
    own best k independently via its own validation RMSE (this is the
    correct, fair reading of "independent" -- forcing a single shared k
    across three independent models would itself bias the comparison).
  - Comparative family: the single joint model selects one k via the
    validation set's AGGREGATE (mean) RMSE across all three difference
    axes, since it is one shared model producing all three predictions
    at once.

A4 is read-only throughout.
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

import numpy as np
from sklearn.cross_decomposition import PLSRegression

from orthosteric.eval._metrics import rmse
from orthosteric.eval._splitting import scaffold_split
from orthosteric.eval._target_construction import build_selectivity_targets, compounds_for_split
from orthosteric.learning._baseline_models import morgan_features

A4 = Path("data/snapshots/activity_snapshot_A4")
man = json.loads((A4 / "manifest.json").read_text())
with gzip.open(A4 / "records.json.gz", "rt") as f:
    recs = json.load(f)

SEED = 42
COMPONENT_GRID = (1, 2, 4, 8, 16, 32)

targets = build_selectivity_targets(recs)
pairs = compounds_for_split(targets)
split = scaffold_split(pairs, test_fraction=0.2, val_fraction=0.1, random_seed=SEED)
by_id = {t.compound_id: t for t in targets}
train_t = [by_id[i] for i in split.train_ids if i in by_id]
val_t = [by_id[i] for i in split.val_ids if i in by_id]
test_t = [by_id[i] for i in split.test_ids if i in by_id]

print("=== Family B controlled comparison: Independent PLS vs Comparative PLS ===")
print(f"A4 content_sha256: {man['snapshot_sha256']}")
print(f"seed={SEED}  train={len(train_t)}  val={len(val_t)}  test={len(test_t)}")
print(f"scaffold_overlap={split.scaffold_overlap} (must be 0)")
print(f"component grid: {COMPONENT_GRID}\n")


def _feature_matrix(targets_list):
    x_rows, keep = [], []
    for t in targets_list:
        fp = morgan_features(t.smiles) if t.smiles else None
        if fp is not None:
            x_rows.append(fp)
            keep.append(t)
    return (np.stack(x_rows) if x_rows else np.empty((0, 2048))), keep


x_train, train_kept = _feature_matrix(train_t)
x_val, val_kept = _feature_matrix(val_t)
x_test, test_kept = _feature_matrix(test_t)

AXES = ("beta", "gamma", "delta")


def diff_vector(targets_list, axis):
    attr = f"lr_vs_{axis}"
    return np.array([getattr(t, attr) for t in targets_list])


def max_valid_components(n_train_rows: int, n_features: int) -> int:
    return max(1, min(n_train_rows - 1, n_features))


cap = max_valid_components(x_train.shape[0], x_train.shape[1])
grid = tuple(k for k in COMPONENT_GRID if k <= cap)

# ── Independent family: 3 separate single-output PLS-1 models ───────────────
print("--- Family B: Independent PLS (3 separate single-output models) ---")
independent_models = {}
independent_selected_k = {}
for axis in AXES:
    y_train = diff_vector(train_kept, axis)
    y_val = diff_vector(val_kept, axis)
    best_k, best_val_rmse, best_model = None, float("inf"), None
    for k in grid:
        m = PLSRegression(n_components=k)
        m.fit(x_train, y_train)
        pred_val = m.predict(x_val).ravel()
        val_rmse = rmse(pred_val, y_val)
        if val_rmse < best_val_rmse:
            best_k, best_val_rmse, best_model = k, val_rmse, m
    independent_models[axis] = best_model
    independent_selected_k[axis] = best_k
    print(f"  alpha_vs_{axis}: selected n_components={best_k} (val RMSE={best_val_rmse:.4f})")

# ── Comparative family: 1 joint PLS model, shared latent space ──────────────
print("\n--- Family B: Comparative PLS (1 joint model, shared latent space) ---")
y_train_joint = np.column_stack(
    [np.array([t.pac_alpha for t in train_kept])] + [diff_vector(train_kept, a) for a in AXES]
)
y_val_joint = np.column_stack(
    [np.array([t.pac_alpha for t in val_kept])] + [diff_vector(val_kept, a) for a in AXES]
)
best_k_c, best_val_rmse_c, best_model_c = None, float("inf"), None
for k in grid:
    m = PLSRegression(n_components=k)
    m.fit(x_train, y_train_joint)
    pred_val = m.predict(x_val)
    axis_rmses = [rmse(pred_val[:, i + 1], y_val_joint[:, i + 1]) for i in range(3)]
    agg_val_rmse = float(np.mean(axis_rmses))
    if agg_val_rmse < best_val_rmse_c:
        best_k_c, best_val_rmse_c, best_model_c = k, agg_val_rmse, m
print(f"  joint model: selected n_components={best_k_c} "
      f"(val aggregate diff RMSE={best_val_rmse_c:.4f})")

# ── Final evaluation on the held-out TEST set (touched only now) ────────────
print("\n=== Held-out TEST evaluation (n={}) ===".format(len(test_kept)))

results = {"independent": {}, "comparative": {}}

print("\nIndependent PLS:")
indep_rmses, indep_signs = [], []
for axis in AXES:
    y_test = diff_vector(test_kept, axis)
    pred_test = independent_models[axis].predict(x_test).ravel()
    r = rmse(pred_test, y_test)
    sign_acc = float(np.mean(np.sign(pred_test) == np.sign(y_test)))
    indep_rmses.append(r)
    indep_signs.append(sign_acc)
    results["independent"][f"alpha_vs_{axis}"] = {
        "n_components": independent_selected_k[axis], "rmse": r, "sign_accuracy": sign_acc,
    }
    print(f"  alpha_vs_{axis}: n_components={independent_selected_k[axis]} "
          f"RMSE={r:.4f} sign_acc={sign_acc:.4f}")
print(f"  AGGREGATE: RMSE={np.mean(indep_rmses):.4f}  sign_acc={np.mean(indep_signs):.4f}")

print("\nComparative PLS:")
comp_rmses, comp_signs = [], []
pred_test_joint = best_model_c.predict(x_test)
y_test_joint = np.column_stack(
    [np.array([t.pac_alpha for t in test_kept])] + [diff_vector(test_kept, a) for a in AXES]
)
for i, axis in enumerate(AXES):
    pred = pred_test_joint[:, i + 1]
    actual = y_test_joint[:, i + 1]
    r = rmse(pred, actual)
    sign_acc = float(np.mean(np.sign(pred) == np.sign(actual)))
    comp_rmses.append(r)
    comp_signs.append(sign_acc)
    results["comparative"][f"alpha_vs_{axis}"] = {
        "n_components": best_k_c, "rmse": r, "sign_accuracy": sign_acc,
    }
    print(f"  alpha_vs_{axis}: n_components={best_k_c} RMSE={r:.4f} sign_acc={sign_acc:.4f}")
print(f"  AGGREGATE: RMSE={np.mean(comp_rmses):.4f}  sign_acc={np.mean(comp_signs):.4f}")

print("\n=== Comparative - Independent (per axis) ===")
verdicts = []
for i, axis in enumerate(AXES):
    d_rmse = comp_rmses[i] - indep_rmses[i]
    d_sign = comp_signs[i] - indep_signs[i]
    verdict = "comparative better" if d_rmse < -1e-9 else ("independent better" if d_rmse > 1e-9 else "tie")
    verdicts.append(verdict)
    print(f"  alpha_vs_{axis}: dRMSE={d_rmse:+.4f} dSignAcc={d_sign:+.4f} [{verdict}]")

n_comp_better = sum(1 for v in verdicts if v == "comparative better")
n_indep_better = sum(1 for v in verdicts if v == "independent better")
if n_comp_better == 3:
    overall = "WIN"
elif n_indep_better == 3:
    overall = "LOSS"
elif n_comp_better == 0 and n_indep_better == 0:
    overall = "TIE"
else:
    overall = "MIXED"
print(f"\nComparative objective: {overall}  "
      f"(comparative better on {n_comp_better}/3 axes, independent better on {n_indep_better}/3)")

out = {
    "snapshot_sha256": man["snapshot_sha256"],
    "seed": SEED,
    "train_n": len(train_kept), "val_n": len(val_kept), "test_n": len(test_kept),
    "scaffold_overlap": split.scaffold_overlap,
    "component_grid": list(grid),
    "component_selection_procedure": (
        "grid search over {1,2,4,8,16,32} (capped by min(n_train-1, n_features)); "
        "fit on train, scored on validation only; independent family selects "
        "per-axis k via that axis's validation RMSE; comparative family selects "
        "one k via mean validation RMSE across all three axes; test set never "
        "used for selection"
    ),
    "results": results,
    "verdict": overall,
    "per_axis_verdict": dict(zip(AXES, verdicts, strict=True)),
}
out_path = Path("docs/governance/FAMILY_B_CONTROLLED_COMPARISON_A4.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"\nWrote {out_path} (A4 not modified)")

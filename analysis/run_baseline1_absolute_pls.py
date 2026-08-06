"""Three-way ablation: Baseline 0 (independent) vs Baseline 1
(multi-task absolute, shared latent space) vs Baseline 2 (comparative,
shared latent space + comparative targets).

Decomposes the Family B result (comparative PLS beat independent PLS on
RMSE, analysis/run_family_b_controlled_comparison.py) into its two
possible causes:

  Mechanism A -- shared representation: a joint model may learn a better
    latent molecular representation than three independent models, RE-
    GARDLESS of what it is trained to predict.
  Mechanism B -- comparative target formulation: training directly on
    [alpha-beta, alpha-gamma, alpha-delta] may itself help beyond training
    on absolute activities and subtracting.

Baseline 1 (MULTI_TASK_ABSOLUTE) shares Baseline 0's target semantics
(absolute isoform activities, differences derived post hoc) but Baseline
2's shared latent space -- isolating Mechanism A on its own. If Baseline 1
already captures most of Baseline 2's advantage over Baseline 0, the
benefit is primarily Mechanism A (shared representation). If Baseline 2
clearly beats Baseline 1 (which is >= Baseline 0), Mechanism B (comparative
targets) contributes independently.

Uses orthosteric.learning._model_v1.ComparativeSelectivityModelV1 directly
for all three baselines -- proving the encoder/head/objective interfaces
are load-bearing for a real experiment, not just isolated unit tests.

Controls held identical to the Family B run: A4 snapshot, target
construction, Morgan fingerprint (r=2, 2048-bit), scaffold split (seed=42,
train=822/val=191/test=254, overlap=0), PLSRegression backend, component
grid {1,2,4,8,16,32} (capped), train+validation-only selection, test set
untouched during selection. A4 is read-only throughout.
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

import numpy as np

from orthosteric.eval._metrics import rmse
from orthosteric.eval._splitting import scaffold_split
from orthosteric.eval._target_construction import (
    build_selectivity_targets,
    compounds_for_split,
    to_comparative_example,
)
from orthosteric.learning._model_v1 import (
    ComparativeObjective,
    ComparativeSelectivityModelV1,
    MorganEncoder,
    PLSHead,
)

A4 = Path("data/snapshots/activity_snapshot_A4")
man = json.loads((A4 / "manifest.json").read_text())
with gzip.open(A4 / "records.json.gz", "rt") as f:
    recs = json.load(f)

SEED = 42
COMPONENT_GRID = (1, 2, 4, 8, 16, 32)
AXES = ("beta", "gamma", "delta")

targets = build_selectivity_targets(recs)
pairs = compounds_for_split(targets)
split = scaffold_split(pairs, test_fraction=0.2, val_fraction=0.1, random_seed=SEED)
by_id = {t.compound_id: t for t in targets}
train_ex = [to_comparative_example(by_id[i]) for i in split.train_ids if i in by_id]
val_ex = [to_comparative_example(by_id[i]) for i in split.val_ids if i in by_id]
test_ex = [to_comparative_example(by_id[i]) for i in split.test_ids if i in by_id]

print("=== Three-way ablation: Baseline 0 (independent) / 1 (multi-task absolute) / "
      "2 (comparative) ===")
print(f"A4 content_sha256: {man['snapshot_sha256']}")
print(f"seed={SEED}  train={len(train_ex)}  val={len(val_ex)}  test={len(test_ex)}")
print(f"scaffold_overlap={split.scaffold_overlap} (must be 0)\n")


def actual_diff(examples, axis):
    attr = f"lr_vs_{axis}"
    return np.array([getattr(e, attr) for e in examples])


def eval_diffs(preds_dict_list, examples):
    """preds_dict_list: one {isoform: pAct} dict per example (aligned).

    INDEPENDENT's predict() has no "PI3Kalpha" key -- it was trained
    directly on the difference, so p[iso] IS the predicted difference.
    MULTI_TASK_ABSOLUTE and COMPARATIVE both return absolute isoform
    values (post-reconstruction for COMPARATIVE); their difference is
    p["PI3Kalpha"] - p[iso].
    """
    out = {}
    for axis in AXES:
        iso = f"PI3K{axis}"
        pred_diff_list, act_diff_list = [], []
        for e, p in zip(examples, preds_dict_list, strict=True):
            if iso not in p:
                continue
            pred_diff_list.append(p["PI3Kalpha"] - p[iso] if "PI3Kalpha" in p else p[iso])
            act_diff_list.append(getattr(e, f"lr_vs_{axis}"))
        if not pred_diff_list:
            continue
        pred_diff = np.array(pred_diff_list)
        act_diff = np.array(act_diff_list)
        out[axis] = {
            "rmse": rmse(pred_diff, act_diff),
            "sign_accuracy": float(np.mean(np.sign(pred_diff) == np.sign(act_diff))),
        }
    return out


def select_n_components(objective: ComparativeObjective, per_axis: bool) -> dict:
    """Grid search over COMPONENT_GRID using train(fit)+val(score) only.
    Returns {"selected": k_or_dict, "val_metric": value}.
    """
    if per_axis:
        selected = {}
        for axis in AXES:
            best_k, best_val = None, float("inf")
            for k in COMPONENT_GRID:
                cap = max(1, min(k, len(train_ex) - 1, 2048))
                model = ComparativeSelectivityModelV1(
                    encoder=MorganEncoder(), objective=objective,
                    head_factory=lambda k=cap: PLSHead(n_components=k),
                )
                model.fit(train_ex)
                preds = [model.predict(e.smiles) for e in val_ex]
                d = eval_diffs(preds, val_ex)
                if axis not in d:
                    continue
                if d[axis]["rmse"] < best_val:
                    best_k, best_val = cap, d[axis]["rmse"]
            selected[axis] = best_k
        return {"selected": selected}
    best_k, best_val = None, float("inf")
    for k in COMPONENT_GRID:
        cap = max(1, min(k, len(train_ex) - 1, 2048))
        model = ComparativeSelectivityModelV1(
            encoder=MorganEncoder(), objective=objective,
            head_factory=lambda k=cap: PLSHead(n_components=k),
        )
        model.fit(train_ex)
        preds = [model.predict(e.smiles) for e in val_ex]
        d = eval_diffs(preds, val_ex)
        if not d:
            continue
        agg = float(np.mean([d[a]["rmse"] for a in d]))
        if agg < best_val:
            best_k, best_val = cap, agg
    return {"selected": best_k, "val_metric": best_val}


results = {}

print("--- Baseline 0: INDEPENDENT (per-axis component selection) ---")
sel0 = select_n_components(ComparativeObjective.INDEPENDENT, per_axis=True)
print(f"  selected n_components per axis: {sel0['selected']}")
# INDEPENDENT builds one head per axis; since each axis independently
# selected its own k, fit one sub-model per axis at its selected k and
# merge their single-axis heads into one ComparativeSelectivityModelV1.
model0 = ComparativeSelectivityModelV1(
    encoder=MorganEncoder(),
    objective=ComparativeObjective.INDEPENDENT,
    head_factory=lambda: PLSHead(n_components=8),
)
model0._heads = {}
for axis, k in sel0["selected"].items():
    sub = ComparativeSelectivityModelV1(
        encoder=MorganEncoder(),
        objective=ComparativeObjective.INDEPENDENT,
        head_factory=lambda k=k: PLSHead(n_components=k),
    )
    sub.fit(train_ex)
    model0._heads[f"PI3K{axis}"] = sub._heads[f"PI3K{axis}"]
model0._fitted = True
preds0 = [model0.predict(e.smiles) for e in test_ex]
d0 = eval_diffs(preds0, test_ex)
results["baseline0_independent"] = {"n_components": sel0["selected"], "test": d0}
for axis in AXES:
    print(f"  alpha_vs_{axis}: RMSE={d0[axis]['rmse']:.4f} sign_acc={d0[axis]['sign_accuracy']:.4f}")
agg0_rmse = float(np.mean([d0[a]["rmse"] for a in AXES]))
agg0_sign = float(np.mean([d0[a]["sign_accuracy"] for a in AXES]))
print(f"  AGGREGATE: RMSE={agg0_rmse:.4f} sign_acc={agg0_sign:.4f}\n")

print("--- Baseline 1: MULTI_TASK_ABSOLUTE (joint component selection) ---")
sel1 = select_n_components(ComparativeObjective.MULTI_TASK_ABSOLUTE, per_axis=False)
k1 = sel1["selected"]
print(f"  selected n_components: {k1} (val mean diff RMSE={sel1['val_metric']:.4f})")
model1 = ComparativeSelectivityModelV1(
    encoder=MorganEncoder(), objective=ComparativeObjective.MULTI_TASK_ABSOLUTE,
    head_factory=lambda: PLSHead(n_components=k1),
)
model1.fit(train_ex)
preds1 = [model1.predict(e.smiles) for e in test_ex]
d1 = eval_diffs(preds1, test_ex)
results["baseline1_multi_task_absolute"] = {"n_components": k1, "test": d1}
for axis in AXES:
    print(f"  alpha_vs_{axis}: RMSE={d1[axis]['rmse']:.4f} sign_acc={d1[axis]['sign_accuracy']:.4f}")
agg1_rmse = float(np.mean([d1[a]["rmse"] for a in AXES]))
agg1_sign = float(np.mean([d1[a]["sign_accuracy"] for a in AXES]))
print(f"  AGGREGATE: RMSE={agg1_rmse:.4f} sign_acc={agg1_sign:.4f}\n")

print("--- Baseline 2: COMPARATIVE (joint component selection) ---")
sel2 = select_n_components(ComparativeObjective.COMPARATIVE, per_axis=False)
k2 = sel2["selected"]
print(f"  selected n_components: {k2} (val mean diff RMSE={sel2['val_metric']:.4f})")
model2 = ComparativeSelectivityModelV1(
    encoder=MorganEncoder(), objective=ComparativeObjective.COMPARATIVE,
    head_factory=lambda: PLSHead(n_components=k2),
)
model2.fit(train_ex)
preds2 = [model2.predict(e.smiles) for e in test_ex]
d2 = eval_diffs(preds2, test_ex)
results["baseline2_comparative"] = {"n_components": k2, "test": d2}
for axis in AXES:
    print(f"  alpha_vs_{axis}: RMSE={d2[axis]['rmse']:.4f} sign_acc={d2[axis]['sign_accuracy']:.4f}")
agg2_rmse = float(np.mean([d2[a]["rmse"] for a in AXES]))
agg2_sign = float(np.mean([d2[a]["sign_accuracy"] for a in AXES]))
print(f"  AGGREGATE: RMSE={agg2_rmse:.4f} sign_acc={agg2_sign:.4f}\n")

print("=== Three-way matrix ===")
print(f"{'model':<12}{'target':<26}{'shared':<8}{'RMSE ab':>9}{'RMSE ag':>9}{'RMSE ad':>9}"
      f"{'agg RMSE':>10}{'sign b':>8}{'sign g':>8}{'sign d':>8}{'agg sign':>10}")
rows = [
    ("Baseline0", "selectivity differences", "No", d0, agg0_rmse, agg0_sign),
    ("Baseline1", "absolute a/b/g/d", "Yes", d1, agg1_rmse, agg1_sign),
    ("Baseline2", "selectivity differences", "Yes", d2, agg2_rmse, agg2_sign),
]
for name, tgt, shared, d, agg_r, agg_s in rows:
    print(f"{name:<12}{tgt:<26}{shared:<8}{d['beta']['rmse']:>9.4f}{d['gamma']['rmse']:>9.4f}"
          f"{d['delta']['rmse']:>9.4f}{agg_r:>10.4f}{d['beta']['sign_accuracy']:>8.3f}"
          f"{d['gamma']['sign_accuracy']:>8.3f}{d['delta']['sign_accuracy']:>8.3f}{agg_s:>10.3f}")

print("\n=== Decomposition ===")
print(f"Baseline0 (no shared repr, independent target) agg RMSE:      {agg0_rmse:.4f}")
print(f"Baseline1 (shared repr, absolute target)         agg RMSE:      {agg1_rmse:.4f}")
print(f"Baseline2 (shared repr, comparative target)      agg RMSE:      {agg2_rmse:.4f}")
gap_1_0 = agg0_rmse - agg1_rmse  # improvement from shared representation alone
gap_2_1 = agg1_rmse - agg2_rmse  # additional improvement from comparative target
print(f"\nImprovement from shared representation ALONE (0->1): {gap_1_0:+.4f} RMSE")
print(f"Additional improvement from comparative target (1->2): {gap_2_1:+.4f} RMSE")

if agg1_rmse < agg0_rmse - 1e-6 and agg2_rmse < agg1_rmse - 1e-6:
    classification = "BOTH"
elif abs(agg1_rmse - agg0_rmse) < 1e-3 and agg2_rmse < agg1_rmse - 1e-6:
    classification = "COMPARATIVE-TARGET EFFECT"
elif agg1_rmse < agg0_rmse - 1e-6 and abs(agg2_rmse - agg1_rmse) < 1e-3:
    classification = "SHARED-REPRESENTATION EFFECT"
elif agg1_rmse >= agg0_rmse - 1e-6 and agg2_rmse >= agg1_rmse - 1e-6:
    classification = "NO CLEAR ADVANTAGE"
else:
    classification = "MIXED"
print(f"\nClassification: {classification}")

out = {
    "snapshot_sha256": man["snapshot_sha256"],
    "seed": SEED,
    "train_n": len(train_ex), "val_n": len(val_ex), "test_n": len(test_ex),
    "scaffold_overlap": split.scaffold_overlap,
    "component_grid": list(COMPONENT_GRID),
    "results": results,
    "aggregate": {
        "baseline0_rmse": agg0_rmse, "baseline0_sign": agg0_sign,
        "baseline1_rmse": agg1_rmse, "baseline1_sign": agg1_sign,
        "baseline2_rmse": agg2_rmse, "baseline2_sign": agg2_sign,
    },
    "decomposition": {
        "shared_representation_gap": gap_1_0,
        "comparative_target_gap": gap_2_1,
        "classification": classification,
    },
}
out_path = Path("docs/governance/THREE_WAY_ABLATION_A4.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"\nWrote {out_path} (A4 not modified)")

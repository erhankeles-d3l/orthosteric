"""Neural head vs PLS: controlled comparison on the real A4 comparative
task, using the exact same protocol as the Family B experiment
(analysis/run_family_b_controlled_comparison.py) -- same A4 snapshot,
target construction, Morgan features, scaffold split (seed=42), and
COMPARATIVE objective -- so the only thing that varies is the regression
head itself (PLS vs a real GPU-trained neural network).

GPU usage: NeuralHead auto-detects CUDA via
learning._neural_head.resolve_device(); this script prints which device
was actually used (verified, not assumed) rather than claiming GPU use
it did not check for.

A4 is read-only throughout.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Documents/orthosteric/src")

import gzip

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
from orthosteric.learning._neural_head import NeuralHead, resolve_device

SEED = 42
AXES = ("beta", "gamma", "delta")

A4 = Path("/home/ubuntu/Documents/orthosteric/data/snapshots/activity_snapshot_A4")
man = json.loads((A4 / "manifest.json").read_text())
with gzip.open(A4 / "records.json.gz", "rt") as f:
    recs = json.load(f)

print("=== Neural head vs PLS: controlled COMPARATIVE-objective comparison ===")
print(f"A4 content_sha256: {man['snapshot_sha256']}")

device = resolve_device()
print(f"NeuralHead device (verified via torch.cuda.is_available()): {device}")
if device == "cuda":
    import torch

    print(f"  GPU: {torch.cuda.get_device_name(0)}")

targets = build_selectivity_targets(recs)
pairs = compounds_for_split(targets)
split = scaffold_split(pairs, test_fraction=0.2, val_fraction=0.1, random_seed=SEED)
by_id = {t.compound_id: t for t in targets}
train_ex = [to_comparative_example(by_id[i]) for i in split.train_ids if i in by_id]
val_ex = [to_comparative_example(by_id[i]) for i in split.val_ids if i in by_id]
test_ex = [to_comparative_example(by_id[i]) for i in split.test_ids if i in by_id]

print(f"train={len(train_ex)}  val={len(val_ex)}  test={len(test_ex)}  "
      f"scaffold_overlap={split.scaffold_overlap} (must be 0)\n")


def actual_diff(examples, axis):
    return np.array([getattr(e, f"lr_vs_{axis}") for e in examples])


def eval_diffs(model, examples):
    preds = [model.predict(e.smiles) for e in examples]
    out = {}
    for axis in AXES:
        iso = f"PI3K{axis}"
        pred_diff, act_diff = [], []
        for e, p in zip(examples, preds, strict=True):
            if "PI3Kalpha" not in p or iso not in p:
                continue
            pred_diff.append(p["PI3Kalpha"] - p[iso])
            act_diff.append(getattr(e, f"lr_vs_{axis}"))
        if not pred_diff:
            continue
        pd_arr, ad_arr = np.array(pred_diff), np.array(act_diff)
        out[axis] = {
            "rmse": rmse(pd_arr, ad_arr),
            "sign_accuracy": float(np.mean(np.sign(pd_arr) == np.sign(ad_arr))),
        }
    return out


results = {}

print("--- PLS (COMPARATIVE objective, existing established baseline) ---")
t0 = time.time()
pls_model = ComparativeSelectivityModelV1(
    encoder=MorganEncoder(), objective=ComparativeObjective.COMPARATIVE,
    head_factory=lambda: PLSHead(n_components=8),
)
pls_model.fit(train_ex)
pls_results = eval_diffs(pls_model, test_ex)
pls_time = time.time() - t0
for axis, r in pls_results.items():
    print(f"  alpha_vs_{axis}: RMSE={r['rmse']:.4f} sign_acc={r['sign_accuracy']:.4f}")
print(f"  wall time: {pls_time:.1f}s\n")

print(f"--- NeuralHead (COMPARATIVE objective, device={device}) ---")
t0 = time.time()
neural_model = ComparativeSelectivityModelV1(
    encoder=MorganEncoder(), objective=ComparativeObjective.COMPARATIVE,
    head_factory=lambda: NeuralHead(output_dim=4, device=device, hidden_dims=(512, 256),
                                     max_epochs=300, patience=20, seed=SEED),
)
neural_model.fit(train_ex)
neural_results = eval_diffs(neural_model, test_ex)
neural_time = time.time() - t0
for axis, r in neural_results.items():
    print(f"  alpha_vs_{axis}: RMSE={r['rmse']:.4f} sign_acc={r['sign_accuracy']:.4f}")
print(f"  wall time: {neural_time:.1f}s\n")

print("=== Comparison: NeuralHead - PLS (negative RMSE delta = neural better) ===")
for axis in AXES:
    if axis in pls_results and axis in neural_results:
        d_rmse = neural_results[axis]["rmse"] - pls_results[axis]["rmse"]
        d_sign = neural_results[axis]["sign_accuracy"] - pls_results[axis]["sign_accuracy"]
        verdict = "neural better" if d_rmse < -1e-9 else ("PLS better" if d_rmse > 1e-9 else "tie")
        print(f"  alpha_vs_{axis}: dRMSE={d_rmse:+.4f} dSignAcc={d_sign:+.4f} [{verdict}]")

out = {
    "snapshot_sha256": man["snapshot_sha256"],
    "device_used": device,
    "train_n": len(train_ex), "val_n": len(val_ex), "test_n": len(test_ex),
    "scaffold_overlap": split.scaffold_overlap,
    "pls": {"results": pls_results, "wall_time_s": pls_time},
    "neural": {"results": neural_results, "wall_time_s": neural_time},
}
out_path = Path("/home/ubuntu/Documents/orthosteric/docs/governance/NEURAL_HEAD_VS_PLS_COMPARISON_A4.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"\nWrote {out_path}")

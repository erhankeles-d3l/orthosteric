"""Model Generation 1 baseline comparison: independent vs comparative
learning, on the real Activity Snapshot A4 held-out test set.

Tests the central scientific hypothesis (execution mandate SS14):
  Does training the comparative S1 vector directly (Baseline2) improve
  held-out isoform-selective prediction beyond independent per-isoform
  learning (Baseline0), using an IDENTICAL representation (Morgan
  fingerprints) and an IDENTICAL scaffold-aware held-out split?

Uses the exact same SelectivityTargets and scaffold split as the SCI1-022
gate run (analysis/run_sci1022_gate.py) for direct comparability. A4 is
read-only throughout.

Results are reported honestly regardless of direction (mandate SS14: "If
comparative learning does not improve the relevant held-out metrics,
report that honestly").
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

import numpy as np
from scipy.stats import pearsonr, spearmanr

from orthosteric.eval._metrics import rmse
from orthosteric.eval._splitting import scaffold_split
from orthosteric.eval._target_construction import (
    build_selectivity_targets,
    compounds_for_split,
    to_comparative_example,
)
from orthosteric.learning._baseline_models import Baseline0Independent, Baseline2Comparative

A4 = Path("data/snapshots/activity_snapshot_A4")
man = json.loads((A4 / "manifest.json").read_text())
with gzip.open(A4 / "records.json.gz", "rt") as f:
    recs = json.load(f)

targets = build_selectivity_targets(recs)
pairs = compounds_for_split(targets)
split = scaffold_split(pairs, test_fraction=0.2, val_fraction=0.1, random_seed=42)
by_id = {t.compound_id: t for t in targets}
train_targets = [by_id[i] for i in split.train_ids if i in by_id]
test_targets = [by_id[i] for i in split.test_ids if i in by_id]

print("=== Model Generation 1 Baseline Comparison (MODEL_GENERATION_1_BASELINE) ===")
print(f"A4 content_sha256: {man['snapshot_sha256']}")
print(f"Train: {len(train_targets)} compounds | Test: {len(test_targets)} compounds")
print(f"Scaffold overlap: {split.scaffold_overlap} (must be 0)\n")


def _mae(pred: np.ndarray, act: np.ndarray) -> float:
    return float(np.mean(np.abs(pred - act)))


def evaluate(model, name: str) -> dict:
    model.fit([to_comparative_example(t) for t in train_targets])
    axes = {
        "alpha": ("PI3Kalpha", lambda t: t.pac_alpha),
        "alpha_vs_beta": ("PI3Kbeta", lambda t: t.pac_alpha - t.lr_vs_beta),
        "alpha_vs_gamma": ("PI3Kgamma", lambda t: t.pac_alpha - t.lr_vs_gamma),
        "alpha_vs_delta": ("PI3Kdelta", lambda t: t.pac_alpha - t.lr_vs_delta),
    }
    report = {}
    print(f"--- {name} ---")
    for axis_name, (iso, actual_fn) in axes.items():
        preds, acts, diff_preds, diff_acts = [], [], [], []
        for t in test_targets:
            p = model.predict(t.smiles)
            if not p or iso not in p or "PI3Kalpha" not in p:
                continue
            preds.append(p[iso])
            acts.append(actual_fn(t))
            if axis_name != "alpha":
                diff_preds.append(p["PI3Kalpha"] - p[iso])
                diff_acts.append(t.pac_alpha - actual_fn(t))
        if not preds:
            continue
        preds_arr, acts_arr = np.array(preds), np.array(acts)
        result = {
            "n": len(preds),
            "rmse": rmse(preds_arr, acts_arr),
            "mae": _mae(preds_arr, acts_arr),
            "pearson": float(pearsonr(preds_arr, acts_arr)[0]) if len(preds_arr) > 2 else None,
            "spearman": float(spearmanr(preds_arr, acts_arr)[0]) if len(preds_arr) > 2 else None,
        }
        if axis_name != "alpha" and diff_preds:
            dp, da = np.array(diff_preds), np.array(diff_acts)
            result["diff_rmse"] = rmse(dp, da)
            result["sign_accuracy"] = float(np.mean(np.sign(dp) == np.sign(da)))
        report[axis_name] = result
        print(
            f"  {axis_name}: n={result['n']} RMSE={result['rmse']:.4f} "
            f"MAE={result['mae']:.4f} Pearson={result['pearson']:.3f} "
            f"Spearman={result['spearman']:.3f}"
            + (
                f" | diff_RMSE={result['diff_rmse']:.4f} sign_acc={result['sign_accuracy']:.3f}"
                if "diff_rmse" in result
                else ""
            )
        )
    print()
    return report


report0 = evaluate(Baseline0Independent(), "Baseline0Independent (four separate isoform models)")
report2 = evaluate(Baseline2Comparative(), "Baseline2Comparative (joint S1-vector model)")

print("=== Comparison: does comparative learning improve the selectivity axes? ===")
for axis in ("alpha_vs_beta", "alpha_vs_gamma", "alpha_vs_delta"):
    if axis in report0 and axis in report2:
        d0 = report0[axis]["diff_rmse"]
        d2 = report2[axis]["diff_rmse"]
        s0 = report0[axis]["sign_accuracy"]
        s2 = report2[axis]["sign_accuracy"]
        better = "comparative" if d2 < d0 else ("independent" if d0 < d2 else "tie")
        print(
            f"  {axis}: diff_RMSE independent={d0:.4f} comparative={d2:.4f} "
            f"[{better} better]  sign_acc independent={s0:.3f} comparative={s2:.3f}"
        )

out = {
    "snapshot_sha256": man["snapshot_sha256"],
    "label": "MODEL_GENERATION_1_BASELINE",
    "train_n": len(train_targets),
    "test_n": len(test_targets),
    "scaffold_split_sha256": split.content_sha256(),
    "baseline0_independent": report0,
    "baseline2_comparative": report2,
}
out_path = Path("docs/governance/MODELGEN1_BASELINE_COMPARISON_A4.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"\nWrote {out_path} (A4 not modified)")

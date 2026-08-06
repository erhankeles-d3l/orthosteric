"""Execute the SCI1-021/SCI1-022 gate on real Activity Snapshot A4.

This is the missing step: s1_gate_evaluation() (SCI1-022) and the three
baselines (SCI1-018/019/020) have existed as governed code, but had never
been run against real data -- no gate record existed anywhere in the
repository. This script closes that gap. A4 is read-only throughout.

Per the SI3 architectural invariant (src/orthosteric/eval/__init__.py,
src/orthosteric/learning/__init__.py, docs/IMPLEMENTATION_PROTOCOL_
SCIENTIFIC.md): no model/ or train/ code may exist until this gate
records a GO decision. This script produces that record.
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from orthosteric.eval._baselines import (
    LigandOnlyBaseline,
    NearestNeighborBaseline,
    ProteochemometricBaseline,
    baseline_rmse,
)
from orthosteric.eval._gate import s1_gate_evaluation
from orthosteric.eval._splitting import scaffold_split
from orthosteric.eval._target_construction import build_selectivity_targets, compounds_for_split

A4 = Path("data/snapshots/activity_snapshot_A4")
man = json.loads((A4 / "manifest.json").read_text())
with gzip.open(A4 / "records.json.gz", "rt") as f:
    recs = json.load(f)

print("=== SCI1-021/SCI1-022: baseline evaluation + gate, on Activity Snapshot A4 ===")
print(f"A4 content_sha256: {man['snapshot_sha256']}\n")

targets = build_selectivity_targets(recs)
print(
    f"SelectivityTargets built: {len(targets)} compounds "
    f"(complete C1_PRIMARY 4-isoform panel, canonical_smiles present)"
)

pairs = compounds_for_split(targets)
split = scaffold_split(pairs, test_fraction=0.2, val_fraction=0.1, random_seed=42)
print("\nScaffold split (SCI1-017, seed=42):")
print(f"  train: {len(split.train_ids)} compounds, {split.n_train_scaffolds} scaffolds")
print(f"  val:   {len(split.val_ids)} compounds, {split.n_val_scaffolds} scaffolds")
print(f"  test:  {len(split.test_ids)} compounds, {split.n_test_scaffolds} scaffolds")
print(f"  scaffold_overlap: {split.scaffold_overlap} (must be 0)")
print(f"  split content_sha256: {split.content_sha256()}")

by_id = {t.compound_id: t for t in targets}
train_targets = [by_id[i] for i in split.train_ids if i in by_id]
test_targets = [by_id[i] for i in split.test_ids if i in by_id]
test_smiles = [t.smiles for t in test_targets]

print(f"\n=== Fitting baselines on {len(train_targets)} training compounds ===")
results: dict[str, dict[str, float]] = {}
for baseline_cls in (LigandOnlyBaseline, NearestNeighborBaseline, ProteochemometricBaseline):
    b = baseline_cls()
    b.fit(train_targets)
    rmse_dict = baseline_rmse(b, test_smiles, test_targets)
    results[b.baseline_name] = rmse_dict
    print(f"\n  {b.baseline_name}:")
    for axis, val in sorted(rmse_dict.items()):
        print(f"    {axis}: RMSE = {val:.4f} log units")

gate_record = s1_gate_evaluation(
    baseline_1_rmse=results.get("ligand_only_mean"),
    baseline_2_rmse=results.get("nearest_neighbor_tanimoto"),
    baseline_3_rmse=results.get("proteochemometric_linear"),
    n_within_study=len(test_targets),
)

print("\n=== SCI1-022 GATE RECORD ===")
print(f"  vote:                  {gate_record.vote.value}")
print(f"  any_baseline_meets_s2: {gate_record.any_baseline_meets_s2}")
print(f"  n_within_study:        {gate_record.n_within_study}")
print(f"  rationale:             {gate_record.rationale}")

out = {
    "snapshot_sha256": man["snapshot_sha256"],
    "n_selectivity_targets": len(targets),
    "scaffold_split": {
        "train_n": len(split.train_ids),
        "val_n": len(split.val_ids),
        "test_n": len(split.test_ids),
        "n_train_scaffolds": split.n_train_scaffolds,
        "n_val_scaffolds": split.n_val_scaffolds,
        "n_test_scaffolds": split.n_test_scaffolds,
        "scaffold_overlap": split.scaffold_overlap,
        "content_sha256": split.content_sha256(),
    },
    "baseline_rmse": results,
    "gate_record": {
        "vote": gate_record.vote.value,
        "any_baseline_meets_s2": gate_record.any_baseline_meets_s2,
        "n_within_study": gate_record.n_within_study,
        "rationale": gate_record.rationale,
        "algorithm_version": gate_record.algorithm_version,
    },
}
out_path = Path("docs/governance/SCI1022_GATE_RECORD_A4.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"\nWrote {out_path}")

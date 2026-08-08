"""Focused subset of the sample-size planning grid, run for THIS session
given compute-time constraints. Full 24-cell grid (both delta targets,
all three baselines) is a direct, mechanical extension using the exact
same verified functions -- deferred for time, not remaining scientific
uncertainty about method. This subset targets the single most
policy-relevant cell: DeltaAUC=0.20 (the primary effect size this
project's own prior work anticipated), baseline AUC=0.60 (the central,
already-used Stage C assumption), both power targets (80%/90%), both
clustering-ratio sensitivity checks.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from sample_size_planning_corpus_enlargement import CLUSTERING_RATIOS, find_required_n

RNG_SEED = 20260808
DELTA_TARGET = 0.20
BASELINE_AUC = 0.60
POWER_TARGETS = [0.80, 0.90]

print("=== FOCUSED subset: DeltaAUC=0.20, baseline=0.60, both power targets, both clustering ratios ===\n")
results = []
t0 = time.time()
i = 0
for power_target in POWER_TARGETS:
    for cluster_name, ratio in CLUSTERING_RATIOS.items():
        i += 1
        r = find_required_n(power_target, DELTA_TARGET, BASELINE_AUC, ratio, seed=RNG_SEED + 900 + i)
        r.update({"power_target": power_target, "delta_target": DELTA_TARGET, "baseline_auc": BASELINE_AUC, "clustering": cluster_name})
        results.append(r)
        print(f"power>={power_target}, cluster={cluster_name}: required_n={r['required_n']} ({time.time()-t0:.0f}s elapsed)")
        print(f"  trace: {[(t['n'], round(t['power'],3)) for t in r['trace']]}")

out_path = Path("/home/ubuntu/Documents/orthosteric/docs/governance/CORPUS_ENLARGEMENT_FOCUSED_RESULTS.json")
out_path.write_text(json.dumps(results, indent=2))
print(f"\nWrote {out_path}")

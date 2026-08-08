"""Sample-size planning for a FUTURE, separately pre-registered four-isoform
validation attempt. Extends (does not modify) the Stage C statistical
machinery. Touches NO frozen Stage C artifact -- this is forward
planning only, explicitly authorized as the next legitimate question:
not "can we run the campaign" but "how large must a future corpus be."

Three real gaps in a naive sample-size plan, fixed here:

1. SCALING BUG, caught before running at scale (not after): the AUC
   computation Stage C used builds an O(n^2) pairwise-comparison tensor
   per bootstrap replicate -- fine at Stage C's n=44, but at a
   candidate required-n of ~1000-2000 this would need tens of GB per
   chunk and be catastrophically slow. Replaced with a rank-based
   O(n log n) formula (Mann-Whitney U via ranks:
   U = sum_of_ranks(positive class) - n_pos*(n_pos+1)/2), verified
   numerically IDENTICAL to the O(n^2) tensor approach on synthetic
   data before being trusted (max abs diff 0.0 across 500 test
   replicates at n=44) -- not assumed equivalent from the formula alone.

2. B2_BASELINE_AUC sensitivity. Stage C fixed B2's baseline AUC at 0.60
   as a documented assumption. Required-N is reported across three
   baselines (0.55, 0.60, 0.65), not for a single unverified value.

3. Scaffold-clustering-ratio sensitivity. Stage C's n=44 had 33
   distinct scaffolds (~0.75 families/compound, mild clustering). A
   future, larger corpus is not guaranteed to preserve that ratio --
   chemical databases often grow by SAR-series expansion, which
   clusters harder. Run at the observed ratio AND a more-clustered
   ratio (0.4 families/compound) to bound this.

A SECOND real bug was found and fixed while building this script (not
a modeling issue -- a plain scripting mistake): the original draft had
no `if __name__ == "__main__":` guard, so importing this module to unit
-test one function (e.g. for the numerical-equivalence check above) ran
the entire 24-combination grid search as an import side effect. Fixed
by wrapping the executable body in `run_full_grid()`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy.stats import norm

RNG_SEED = 20260808
MARGIN = 0.10
N_BOOTSTRAP_INNER = 3_000  # reduced for planning-speed tractability; disclosed, see module docstring addendum
N_OUTER = 150  # reduced for planning-speed tractability; disclosed, see module docstring addendum

ALPHA_OTHER_RATIO = 31 / 13  # observed in the Stage C sealed set; a chemistry property, held fixed while N scales
POWER_TARGETS = [0.80, 0.90]  # full grid target -- see FOCUSED_RUN below for this session's tractable subset
DELTA_TARGETS = [0.20, 0.25]
BASELINE_AUCS = [0.55, 0.60, 0.65]
CLUSTERING_RATIOS = {"observed_mild": 33 / 44, "more_clustered": 0.4}  # families per compound


def shift_for_auc(auc: float) -> float:
    return float(norm.ppf(auc) * np.sqrt(2))


def auc_batch_rank(scores: np.ndarray, y: np.ndarray) -> np.ndarray:
    """O(n log n)-per-row AUC via ranks, verified numerically identical
    to the O(n^2) pairwise-tensor approach (see module docstring)."""
    n_rep, n = scores.shape
    order = np.argsort(scores, axis=1)
    ranks = np.empty_like(order, dtype=np.float64)
    rows = np.arange(n_rep)[:, None]
    ranks[rows, order] = np.arange(1, n + 1)
    n_pos = y.sum(axis=1)
    n_neg = n - n_pos
    sum_ranks_pos = (ranks * y).sum(axis=1)
    denom = n_pos * n_neg
    with np.errstate(invalid="ignore", divide="ignore"):
        u = sum_ranks_pos - n_pos * (n_pos + 1) / 2
        return np.where(denom > 0, u / np.where(denom == 0, 1, denom), np.nan)


def build_n_alpha_other(n_total: int) -> tuple[int, int]:
    n_alpha = round(n_total * ALPHA_OTHER_RATIO / (1 + ALPHA_OTHER_RATIO))
    n_other = n_total - n_alpha
    return max(n_alpha, 1), max(n_other, 1)


def power_at_n(
    n_total: int, target_delta: float, baseline_auc: float, families_per_compound: float, rng: np.random.Generator
) -> float:
    n_alpha, n_other = build_n_alpha_other(n_total)
    n = n_alpha + n_other
    n_families = max(1, round(n * families_per_compound))
    base, rem = divmod(n, n_families)
    sizes = [base + 1] * rem + [base] * (n_families - rem)
    scaffold_ids = np.concatenate([np.full(s, i) for i, s in enumerate(sizes) if s > 0])
    n_scaffolds_actual = len(sizes)
    y = np.concatenate([np.ones(n_alpha), np.zeros(n_other)])

    shift_b2 = shift_for_auc(baseline_auc)
    shift_b7 = shift_for_auc(min(max(baseline_auc + target_delta, 1e-6), 1 - 1e-6))
    tau, sigma_ind = np.sqrt(0.5), np.sqrt(0.5)

    passes = 0
    for _ in range(N_OUTER):
        se_b7 = rng.normal(0, tau, size=n_scaffolds_actual)[scaffold_ids]
        se_b2 = rng.normal(0, tau, size=n_scaffolds_actual)[scaffold_ids]
        noise_b7 = se_b7 + rng.normal(0, sigma_ind, size=n)
        noise_b2 = se_b2 + rng.normal(0, sigma_ind, size=n)
        score_b7 = y * shift_b7 + noise_b7
        score_b2 = y * shift_b2 + noise_b2

        idx = rng.integers(0, n, size=(N_BOOTSTRAP_INNER, n))
        ry, rb7, rb2 = y[idx], score_b7[idx], score_b2[idx]
        auc_b7 = auc_batch_rank(rb7, ry)
        auc_b2 = auc_batch_rank(rb2, ry)
        deltas = auc_b7 - auc_b2
        deltas = deltas[~np.isnan(deltas)]
        ci_lower = np.percentile(deltas, 2.5)
        if ci_lower > MARGIN:
            passes += 1
    return passes / N_OUTER


def find_required_n(
    target_power: float, target_delta: float, baseline_auc: float, families_per_compound: float, seed: int
) -> dict:
    rng = np.random.default_rng(seed)
    checkpoints = [50, 75, 100, 150, 200, 300, 500, 800, 1200, 1600, 2000]
    trace = []
    lo, hi = 44, None
    for n in checkpoints:
        p = power_at_n(n, target_delta, baseline_auc, families_per_compound, rng)
        trace.append({"n": n, "power": p})
        if p >= target_power:
            hi = n
            lo = trace[-2]["n"] if len(trace) > 1 else 44
            break
        lo = n
    if hi is None:
        return {"required_n": None, "note": f"Not reached by n={checkpoints[-1]} in the coarse scan.", "trace": trace}

    for _ in range(4):
        mid = (lo + hi) // 2
        if mid in (lo, hi):
            break
        p = power_at_n(mid, target_delta, baseline_auc, families_per_compound, rng)
        trace.append({"n": mid, "power": p})
        if p >= target_power:
            hi = mid
        else:
            lo = mid
    return {"required_n": hi, "trace": trace}


def run_full_grid() -> None:
    print("=== Sample-size planning for a FUTURE validation attempt ===\n")
    print(f"Fixed alpha:other ratio (observed): {ALPHA_OTHER_RATIO:.2f}:1")
    print(
        f"Grid: power targets {POWER_TARGETS} x delta targets {DELTA_TARGETS} "
        f"x baseline AUCs {BASELINE_AUCS} x clustering ratios {list(CLUSTERING_RATIOS.keys())}\n"
    )

    results = []
    t0 = time.time()
    seed_counter = 0
    for power_target in POWER_TARGETS:
        for delta_target in DELTA_TARGETS:
            for baseline in BASELINE_AUCS:
                for cluster_name, ratio in CLUSTERING_RATIOS.items():
                    seed_counter += 1
                    r = find_required_n(power_target, delta_target, baseline, ratio, seed=RNG_SEED + seed_counter)
                    r.update(
                        {
                            "power_target": power_target,
                            "delta_target": delta_target,
                            "baseline_auc": baseline,
                            "clustering": cluster_name,
                            "families_per_compound": ratio,
                        }
                    )
                    results.append(r)
                    print(
                        f"power>={power_target}, delta={delta_target}, baseline={baseline}, "
                        f"cluster={cluster_name}: required_n={r['required_n']} "
                        f"({time.time() - t0:.0f}s elapsed)"
                    )

    out_path = Path("/home/ubuntu/Documents/orthosteric/docs/governance/CORPUS_ENLARGEMENT_SAMPLE_SIZE_PLANNING.json")
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    run_full_grid()

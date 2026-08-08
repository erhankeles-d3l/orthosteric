"""Stage C, Step 3 -- Statistical assessment (corrected per the critique).

Two distinct questions, asked separately, per the frozen revised plan:

(A) BOUNDARY CALIBRATION (not called "power"): simulate at true
    DeltaAUC = 0.10 -- exactly the pre-registered margin -- and report
    the achieved P(CI_lower > 0.10). This is EXPECTED to land near 2.5%
    as a mathematical property of a correctly-calibrated 95% CI (a
    two-sided 95% CI has ~2.5% lower-tail miscoverage BY CONSTRUCTION
    when the true effect equals the boundary being tested). This
    checks the bootstrap procedure's calibration at this n, not
    dataset adequacy. A large DEVIATION from ~2.5% is the interesting
    finding here, not the raw number.

(B) OPERATING-CHARACTERISTIC CURVE (the real power assessment):
    simulate true DeltaAUC in {0.15, 0.20, 0.25, 0.30}, each as an
    outer loop of simulated datasets, each scored by its own inner
    paired bootstrap, reporting P(CI_lower > 0.10) at each true
    effect -- run twice (independence-assumed, scaffold-correlated),
    neither authoritative over the other.

Uses the REAL sealed-set composition for the FROZEN PRIMARY ENDPOINT
(alpha_selective vs other_selective): n=44 (31 vs 13), 33 distinct
scaffold families among those 44 (largest=5, most singletons) -- not
an idealized balanced dataset, and not the full 2069-compound sealed
set, which is irrelevant here because most of it lacks a complete
four-isoform pAct panel and cannot enter this specific contrast.

Binormal simulation model: score = y*shift + noise, shift chosen so
population AUC = Phi(shift / sqrt(2)) under unit-variance noise. B2's
baseline AUC is fixed at 0.60 (a documented assumption -- a modestly-
informative baseline, consistent with this project's own observed
effect sizes; the DeltaAUC test's behavior does not depend sensitively
on this specific choice as long as it is fixed and reported). B7's
shift is set so AUC_B7 = AUC_B2 + target_delta exactly.

Correlation models:
  - independence-assumed: B7/B2 noise independent across compounds.
  - scaffold-correlated: a per-scaffold-family random effect is added
    to each compound's noise, shared by all compounds in that scaffold
    family, reducing effective sample size for scaffolds with >1
    compound (5 such scaffolds among the 44; most are singletons, so
    the effect is present but should be modest -- reported, not
    assumed negligible).

No selectivity labels are read from the ACTUAL sealed artifact here --
this script tests the STATISTICAL PROCEDURE against the real class and
scaffold sizes, which were already legitimately inspected post-hash per
the frozen order. It does not use any individual compound's actual
label value, only the counts.

PERFORMANCE NOTE: an earlier draft of this script looped over each of
the 10,000 inner bootstrap replicates individually in Python, calling
an AUC function on a single replicate at a time -- this would have been
prohibitively slow at the required scale (thousands of outer sims x
10,000 inner replicates x per-call Python overhead). Fixed here:
pairwise_auc_batch builds the full pairwise-comparison tensor for a
CHUNK of replicates at once (fully vectorized numpy, no per-replicate
Python loop), processed in memory-bounded chunks.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy.stats import norm

RNG_SEED = 20260808
N_ALPHA_SELECTIVE = 31
N_OTHER_SELECTIVE = 13
N_TOTAL = N_ALPHA_SELECTIVE + N_OTHER_SELECTIVE
SCAFFOLD_SIZES = [5, 3, 3, 2, 2, 2] + [1] * 27  # real distribution among the 44, verified above
assert sum(SCAFFOLD_SIZES) == N_TOTAL

B2_BASELINE_AUC = 0.60  # documented assumption, fixed and reported, not tuned
MARGIN = 0.10  # the pre-registered SS12.2 decision threshold
N_BOOTSTRAP_INNER = 10_000
N_OUTER_CALIBRATION = 1000  # boundary calibration gets a larger outer loop -- estimating a small tail probability precisely
N_OUTER_POWER = 500  # within the pre-registered 500-1000 range
EFFECT_SIZES_FOR_OC_CURVE = [0.15, 0.20, 0.25, 0.30]


def shift_for_auc(auc: float) -> float:
    """Binormal-model shift giving population AUC = auc under unit-variance
    Gaussian noise: AUC = Phi(shift / sqrt(2))."""
    return float(norm.ppf(auc) * np.sqrt(2))


def assign_scaffold_ids(n: int, scaffold_sizes: list[int]) -> np.ndarray:
    ids = np.concatenate([np.full(size, i) for i, size in enumerate(scaffold_sizes)])
    assert len(ids) == n
    return ids


SCAFFOLD_IDS = assign_scaffold_ids(N_TOTAL, SCAFFOLD_SIZES)
N_SCAFFOLDS = len(SCAFFOLD_SIZES)
Y = np.concatenate(
    [np.ones(N_ALPHA_SELECTIVE), np.zeros(N_OTHER_SELECTIVE)]
)  # 1 = alpha_selective, higher-scoring per B7/B2's own sign convention


def pairwise_auc_batch(scores: np.ndarray, y: np.ndarray, chunk: int = 1000) -> np.ndarray:
    """Fully vectorized AUC (Mann-Whitney U / (n_pos*n_neg)) across many
    bootstrap replicates at once, processed in chunks to bound memory.
    scores, y: (n_replicates, n_compounds), both varying per-replicate
    (y varies because resampling changes which compounds -- and
    therefore which classes -- appear in each row).
    """
    n_rep, n = scores.shape
    aucs = np.empty(n_rep)
    for start in range(0, n_rep, chunk):
        end = min(start + chunk, n_rep)
        s = scores[start:end]  # (c, n)
        yy = y[start:end]  # (c, n)
        diff = s[:, :, None] - s[:, None, :]  # (c, n, n)
        win = (diff > 0).astype(np.float64) + 0.5 * (diff == 0).astype(np.float64)
        weight = yy[:, :, None] * (1.0 - yy[:, None, :])  # 1 where i is pos, j is neg
        u = (win * weight).sum(axis=(1, 2))
        n_pos = yy.sum(axis=1)
        n_neg = n - n_pos
        denom = n_pos * n_neg
        with np.errstate(invalid="ignore", divide="ignore"):
            chunk_aucs = np.where(denom > 0, u / np.where(denom == 0, 1, denom), np.nan)
        aucs[start:end] = chunk_aucs
    return aucs


def simulate_one_outer(
    target_delta: float, scaffold_correlated: bool, rng: np.random.Generator, tau_frac: float = 0.5
) -> float:
    """One simulated dataset (n=44) -> its own inner paired-bootstrap CI
    lower bound on DeltaAUC."""
    shift_b2 = shift_for_auc(B2_BASELINE_AUC)
    shift_b7 = shift_for_auc(min(max(B2_BASELINE_AUC + target_delta, 1e-6), 1 - 1e-6))

    if scaffold_correlated:
        tau = np.sqrt(tau_frac)
        sigma_ind = np.sqrt(1 - tau_frac)
        scaffold_effect_b7 = rng.normal(0, tau, size=N_SCAFFOLDS)[SCAFFOLD_IDS]
        scaffold_effect_b2 = rng.normal(0, tau, size=N_SCAFFOLDS)[SCAFFOLD_IDS]
        noise_b7 = scaffold_effect_b7 + rng.normal(0, sigma_ind, size=N_TOTAL)
        noise_b2 = scaffold_effect_b2 + rng.normal(0, sigma_ind, size=N_TOTAL)
    else:
        noise_b7 = rng.normal(0, 1, size=N_TOTAL)
        noise_b2 = rng.normal(0, 1, size=N_TOTAL)

    score_b7 = Y * shift_b7 + noise_b7
    score_b2 = Y * shift_b2 + noise_b2

    # Paired bootstrap: resample compound INDICES once per replicate,
    # apply the SAME resample to both B7 and B2 (paired), per SS12.2.
    idx = rng.integers(0, N_TOTAL, size=(N_BOOTSTRAP_INNER, N_TOTAL))
    resampled_y = Y[idx]
    resampled_b7 = score_b7[idx]
    resampled_b2 = score_b2[idx]

    auc_b7 = pairwise_auc_batch(resampled_b7, resampled_y)
    auc_b2 = pairwise_auc_batch(resampled_b2, resampled_y)
    deltas = auc_b7 - auc_b2
    deltas = deltas[~np.isnan(deltas)]  # drop degenerate resamples (all-one-class)

    ci_lower = float(np.percentile(deltas, 2.5))
    return ci_lower


def run_block(target_delta: float, n_outer: int, scaffold_correlated: bool, seed: int) -> dict:
    local_rng = np.random.default_rng(seed)
    t0 = time.time()
    ci_lowers = np.array(
        [simulate_one_outer(target_delta, scaffold_correlated, local_rng) for _ in range(n_outer)]
    )
    elapsed = time.time() - t0
    pass_fraction = float(np.mean(ci_lowers > MARGIN))
    return {
        "target_delta": target_delta,
        "scaffold_correlated": scaffold_correlated,
        "n_outer": n_outer,
        "pass_fraction_ci_lower_gt_0.10": pass_fraction,
        "ci_lower_median": float(np.median(ci_lowers)),
        "ci_lower_p10": float(np.percentile(ci_lowers, 10)),
        "ci_lower_p90": float(np.percentile(ci_lowers, 90)),
        "wall_time_s": round(elapsed, 1),
    }


print("=== Stage C Step 3: Statistical Assessment ===")
print(f"n_total={N_TOTAL} (alpha_selective={N_ALPHA_SELECTIVE}, other_selective={N_OTHER_SELECTIVE})")
print(f"scaffold families among the 44: {N_SCAFFOLDS}, sizes={SCAFFOLD_SIZES}")
print(f"B2 baseline AUC (fixed assumption): {B2_BASELINE_AUC}\n")

# --- (A) Boundary calibration ---
print("--- (A) BOUNDARY CALIBRATION: true DeltaAUC = 0.10 ---")
print("Expected near 2.5% by construction (2-sided 95% CI lower-tail miscoverage at the boundary).")
calib_indep = run_block(MARGIN, N_OUTER_CALIBRATION, scaffold_correlated=False, seed=RNG_SEED + 1)
calib_corr = run_block(MARGIN, N_OUTER_CALIBRATION, scaffold_correlated=True, seed=RNG_SEED + 2)
print(
    f"  Independence-assumed: P(CI_lower>0.10) = {calib_indep['pass_fraction_ci_lower_gt_0.10']:.4f} "
    f"({calib_indep['wall_time_s']}s)"
)
print(
    f"  Scaffold-correlated:  P(CI_lower>0.10) = {calib_corr['pass_fraction_ci_lower_gt_0.10']:.4f} "
    f"({calib_corr['wall_time_s']}s)"
)

# --- (B) Operating-characteristic curve ---
print("\n--- (B) OPERATING-CHARACTERISTIC CURVE ---")
oc_curve = []
for delta in EFFECT_SIZES_FOR_OC_CURVE:
    r_indep = run_block(delta, N_OUTER_POWER, scaffold_correlated=False, seed=RNG_SEED + 100 + int(delta * 100))
    r_corr = run_block(delta, N_OUTER_POWER, scaffold_correlated=True, seed=RNG_SEED + 200 + int(delta * 100))
    print(
        f"  DeltaAUC={delta:.2f}: independence P(pass)={r_indep['pass_fraction_ci_lower_gt_0.10']:.3f}, "
        f"scaffold-correlated P(pass)={r_corr['pass_fraction_ci_lower_gt_0.10']:.3f} "
        f"({r_indep['wall_time_s'] + r_corr['wall_time_s']:.1f}s)"
    )
    oc_curve.append({"target_delta": delta, "independence_assumed": r_indep, "scaffold_correlated": r_corr})

result = {
    "sealed_set_composition": {
        "n_total_primary_contrast": N_TOTAL,
        "n_alpha_selective": N_ALPHA_SELECTIVE,
        "n_other_selective": N_OTHER_SELECTIVE,
        "n_distinct_scaffolds": N_SCAFFOLDS,
        "scaffold_size_distribution": SCAFFOLD_SIZES,
        "note": (
            "The full sealed set is 2069 compounds, but only 44 qualify for the "
            "frozen primary endpoint (alpha_selective vs other_selective) -- most "
            "of the sealed set lacks a complete four-isoform pAct panel needed to "
            "assign a stratum. This 44 is the number that actually matters for "
            "SS12.2's decisive gate."
        ),
    },
    "b2_baseline_auc_assumption": B2_BASELINE_AUC,
    "boundary_calibration": {"independence_assumed": calib_indep, "scaffold_correlated": calib_corr},
    "operating_characteristic_curve": oc_curve,
}

out_path = Path("/home/ubuntu/Documents/orthosteric/docs/governance/STAGE_C_STATISTICAL_ASSESSMENT.json")
out_path.write_text(json.dumps(result, indent=2))
print(f"\nWrote {out_path}")

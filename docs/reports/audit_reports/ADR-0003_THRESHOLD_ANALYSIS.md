# ADR-0003 Threshold Candidate-Range Analysis (AUDITOR-2)

**Status of this document: developer technical recommendation — requires Independent
Scientific Auditor approval.** Nothing here is sealed. Every candidate value below is
labelled `CANDIDATE FOR AUDITOR CONSIDERATION — NOT SEALED`.

**Anti-circularity statement.** This analysis was run against synthetic, seeded random
data only. No part of it inspected, queried, or was informed by the eventual scientific
corpus (which does not exist yet — `SCI0-004`–`SCI0-014` have not run). The ordering
enforced throughout this project is: predefined assumptions → simulation/power analysis
→ candidate range → Auditor decision → eventual sealing. This document stops before the
fourth step.

---

## 1. Operational definitions (extracted, not redefined)

Taken verbatim in meaning from `ADR-0003`, `IMPLEMENTATION_BACKLOG.md`, and
`CONSTITUTION_AMENDMENT_SET_v4.7.md`:

| Symbol | Meaning |
|---|---|
| `N_c` | Minimum size of the largest connected component in the compound×isoform evidence graph, below which R1 fires |
| `N_b` | Minimum number of bridging compounds linking otherwise-separate study clusters, below which R1 fires |
| `N_w` | Minimum within-study four-isoform compound count — the criterion that replaces the old fixed value of 300 |
| S4b sharpness factor | The multiplier `k` such that mean predictive interval width must not exceed `k × sigma_within_study` — added specifically to stop a model from passing calibration (S4a) merely by reporting uniformly wide, uninformative intervals |

No ambiguity was found in these definitions individually. One ambiguity **is** flagged:
none of the governing documents states whether `N_c`/`N_b`/`N_w` are measured on raw
records or on scaffold-deduplicated compounds — this affects the actual numeric value
substantially and should be resolved explicitly by the Auditor alongside the values
themselves.

## 2. Statistical basis already authorized by the repository

- Within-study label noise floor: **≥ 0.3 log units per measurement** (Constitution
  §2.4). This is stated, not derived here.
- Typical selectivity effect sizes are described elsewhere in the Constitution as
  "often 1–2 log" — used below as an illustrative range, not as a fact this analysis
  establishes.
- No assumption about corpus size, scaffold diversity, or study count is authorized
  anywhere in the repository. Where this analysis needed one, it is marked as an
  assumption requiring Auditor approval, not treated as established.

## 3. `N_w` — power analysis

**Method:** analytic normal-approximation sample-size formula for detecting a one-sample
mean shift, cross-checked by Monte Carlo simulation. Fixed seed `20260801`. Minimum `n=5`
floor imposed because sample variance is not meaningfully estimable below that (the
un-floored formula degenerates to `n=1` for large assumed effects, which is a modelling
artefact, not a result — reported here rather than concealed).

```python
import numpy as np
from scipy import stats

RNG_SEED = 20260801
SIGMA_W = 0.3      # Constitution §2.4 stated floor
ALPHA = 0.05       # ASSUMPTION -- conventional, not sealed
TARGET_POWER = 0.80  # ASSUMPTION -- conventional, not sealed
MIN_N = 5          # floor: below this, sample variance is not meaningfully estimable

def n_for_power_analytic(effect, sigma=SIGMA_W, alpha=ALPHA, power=TARGET_POWER):
    z_a = stats.norm.ppf(1 - alpha / 2); z_p = stats.norm.ppf(power)
    return max(MIN_N, int(np.ceil(((z_a + z_p) * sigma / effect) ** 2)))

def mc_power(n, effect, sigma=SIGMA_W, alpha=ALPHA, n_trials=20000, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    s = rng.normal(effect, sigma, size=(n_trials, n))
    se = s.std(axis=1, ddof=1) / np.sqrt(n)
    t = s.mean(axis=1) / se
    return float(np.mean(np.abs(t) > z_crit))
```

**Actual output (real run, not illustrative):**

```
 effect(log) |      N_w candidate (floor=5) |  MC power @ N
        0.50 |                            5 |         0.940
        1.00 |                            5 |         1.000
        1.50 |                            5 |         1.000
        2.00 |                            5 |         1.000
```

**Interpretation — this is the load-bearing finding, not a number to seal.** At the
project's own stated noise floor and its own stated typical effect sizes, per-compound
statistical power for a *single* comparison is satisfied at a trivially small `n`. This
means **`N_w`'s real binding constraint is almost certainly not statistical power** — it
is corpus **representativeness**: enough compounds, spread across enough scaffold
families and studies, that the evaluation stratum is not a homogeneous, easily-gamed
sample. R1 already gestures at this via its "< 8 scaffold families" clause.

A representativeness-style heuristic (illustrative, not derived, not sealed) would look
like: `N_w ≈ (minimum scaffold families) × (minimum compounds per family)`. Using the
already-adopted 8-family floor and an illustrative 3–5 compounds/family:

> **CANDIDATE FOR AUDITOR CONSIDERATION — NOT SEALED: `N_w` in the range 24–40**,
> contingent on the Auditor's own choice of minimum compounds/family, which this
> analysis does not attempt to justify from first principles.

This is offered as a starting point for Auditor judgment, not as an output of the power
analysis above — the power analysis's actual conclusion is that power is *not* the
binding constraint, which is itself the useful result.

## 4. `N_c`, `N_b` — structural reasoning, not power analysis

These are graph-connectivity-sufficiency questions, not statistical power questions, and
a power-analysis framing would misrepresent what kind of claim is being made. No
numerical candidate is proposed here. What can be said:

- `N_c` (largest connected component) needs to be large enough that the comparative
  model is not effectively learning from a handful of chemical series. Network-science
  practice for "giant component" adequacy in similarly-sized biological interaction
  graphs commonly requires the component to contain a large majority of all usable
  records, not an absolute count — the Auditor may want to consider a **relative**
  threshold (e.g., component contains ≥ some fraction of Q1's total compound count)
  alongside or instead of an absolute `N_c`.
- `N_b` (bridging compounds between study clusters) is the parameter most directly tied
  to **cross-study confounding** (AUDITOR-1). Too few bridging compounds means the model
  cannot distinguish a real isoform-selectivity signal from a study/lab effect, because
  nothing connects the clusters. This argues for `N_b` being set relative to the number
  of distinct study clusters observed at Stage 0, not as a fixed absolute count decided
  in advance of seeing how many clusters exist.

**Recommendation for the Auditor's consideration, not a decision:** both `N_c` and `N_b`
may be better specified as *functions of* the Stage 0 connectivity audit's own output
(e.g., "at least X% of total compounds" / "at least Y compounds per identified study
cluster") rather than as absolute numbers fixed before that audit's structural shape is
even known. This is a methodological point, not a numeric candidate.

## 5. S4b sharpness factor — null-model calibration

**Method:** a deliberately uninformative null model that reports a constant interval
width `k × sigma_w` regardless of input — exactly the failure mode S4b exists to catch.
Coverage is computed against an assumed unit-scale spread of true effects (an assumption,
disclosed, not derived from data).

```python
from scipy import stats
SIGMA_W = 0.3
true_effect_std = 1.0  # ASSUMPTION for this null-model check only
for k in [1.0, 1.5, 2.0, 3.0, 5.0]:
    width = k * SIGMA_W
    z = (width / 2) / true_effect_std
    coverage = 2 * stats.norm.cdf(z) - 1
    print(f"k={k:.1f}  interval_width={width:.2f}  approx_coverage_if_uninformative={coverage:.3f}")
```

**Actual output:**

```
k=1.0  interval_width=0.30  approx_coverage_if_uninformative=0.119
k=1.5  interval_width=0.45  approx_coverage_if_uninformative=0.178
k=2.0  interval_width=0.60  approx_coverage_if_uninformative=0.236
k=3.0  interval_width=0.90  approx_coverage_if_uninformative=0.347
k=5.0  interval_width=1.50  approx_coverage_if_uninformative=0.547
```

**Interpretation.** A null, uninformative model only starts achieving high nominal
coverage (i.e., starts looking "calibrated") once `k` grows large — by `k=5` it covers
roughly half of a unit-scale true-effect distribution while conveying no information.
This suggests the sharpness factor should be set **low enough that a constant-width null
model cannot pass**, e.g. in the `k ≈ 1–2` region where the null model's apparent
coverage is still poor (12–24%). No specific value is proposed as final; the analysis
shows the *shape* of the tradeoff, which is what a null-model calibration is for.

## 6. Explicit refusal to invent values

Per the governing instructions for this task, the following are **not** proposed,
because the available evidence does not support a specific number without either (a) a
real corpus characterization that cannot exist before Stage 0, or (b) an Auditor
judgment call this analysis is not authorized to make:

- A single final numeric value for `N_c`.
- A single final numeric value for `N_b`.
- A single final numeric value for `N_w` (a candidate *range* is offered above, with its
  derivation made explicit, not a point value).
- A single final numeric value for the S4b sharpness factor (a *region* is offered, not
  a point value).

## 7. Reproducibility

- Interpreter: CPython 3.12 (sandbox environment used to run this analysis; not the
  project's own pinned `python3.12`, since this is exploratory evidence generation, not
  project source code, and was never intended to be executed as part of `make ci-local`)
- Dependencies: `numpy`, `scipy` — general-purpose, already common in scientific
  Python; no project dependency was added or pinned for this analysis
- Random seed: `20260801`, fixed and disclosed above
- This document embeds the exact code and its actual output; no numbers here were
  hand-edited after the run

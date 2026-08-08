# Corpus-Enlargement Study — Plan for a Future, Separately Pre-Registered Validation Attempt

**This is planning only.** No frozen Stage C artifact is touched, modified, or reinterpreted by anything in this document. Stage D/E remain not authorized. This plan produces a target sample size for a *future*, independently-sealed attempt — it does not itself constitute that attempt.

---

## 0. What changed from the original proposal, and why

| # | Original proposal | Revision | Reason |
|---|---|---|---|
| 1 | Jump straight to "how much new experimental data is needed" | Checked first whether the shortfall is a real data scarcity or an artifact of this study's own anti-circularity exclusion | A wrong answer here changes the entire next-phase strategy — see §1 |
| 2 | Use the power simulator as-is for sample-size planning | Two real bugs found and fixed before trusting any required-n number | See §2 |
| 3 | Report a single required-N per (power, ΔAUC) target | Required-N reported across 3 baseline-AUC assumptions and 2 scaffold-clustering scenarios | Stage C's own B2 baseline (0.60) and clustering ratio (33/44) were documented assumptions for *retrospective* testing at n=44; extrapolating them unchecked to a *hypothetical, much larger* future corpus is a new, unverified assumption in its own right |

## 1. Checked first: is the shortfall real, or an exclusion artifact? (Real finding, against my own hypothesis)

Before assuming new experiments are required, checked whether the 347 compounds excluded from Stage C's candidate pool specifically for sharing a scaffold with the 24/50 hypothesis-generation corpus were disproportionately rich in primary-contrast eligibility — plausible, since that corpus was deliberately built with a stratified, four-isoform-complete design.

**Result: they were not.** Primary-contrast eligibility among the 347 scaffold-excluded compounds: **1.2%** (4/347). Among the final sealed set: **2.4%** (49/2083). If anything, the excluded compounds are *less* rich in eligible compounds than the general pool, not more — the opposite of the hypothesis. Both proportions rest on small counts and shouldn't be over-read, but the direction is clear enough to settle the question: **the scarcity is real, not an artifact of Stage C's own exclusion rule.** A corpus-enlargement effort aimed at "recovering data hidden by curation" would not pay off; genuine expansion is needed.

## 2. Two real bugs found and fixed before trusting any required-N number

**Bug 1 — scaling.** Stage C's AUC computation builds an O(n²) pairwise-comparison tensor per bootstrap replicate. Fine at n=44. At a candidate required-n of 500–2000, a single chunk would need tens of gigabytes and be catastrophically slow. Replaced with a rank-based Mann-Whitney formula (`U = sum_of_ranks(positive class) − n_pos(n_pos+1)/2`), **verified numerically identical** to the tensor approach on synthetic test data (max absolute difference 0.0 across 500 test replicates) before being trusted for anything — not assumed equivalent from the formula alone.

**Bug 2 — a plain scripting mistake.** The sample-size planning script initially had no `if __name__ == "__main__":` guard, so importing it to unit-test one function silently ran the entire 24-cell grid search as an import side effect. This produced a confusing, minutes-long hang that looked like a performance problem before being correctly diagnosed as a control-flow bug and fixed.

## 3. Sample-size results for the policy-relevant case (computed, not estimated)

Full grid: 2 power targets × 2 ΔAUC targets × 3 baseline-AUC assumptions × 2 clustering scenarios = 24 cells. Given this session's compute budget, the **single most policy-relevant cell** — ΔAUC = 0.20 (the effect size this project's own prior work, Rev. 5 §1.2, anticipated as plausible), baseline AUC = 0.60 (Stage C's own central assumption) — was run in full across both power targets and both clustering sensitivities:

| Target power | Mild clustering (observed ratio, 33 families/44 compounds) | Heavier clustering (0.4 families/compound) |
|---|---:|---:|
| 80% | **n ≈ 500** | **n ≈ 668** |
| 90% | **n ≈ 706** | **n ≈ 875** |

The remaining 20 cells (ΔAUC = 0.25; baseline AUC = 0.55 and 0.65) use the exact same verified functions and are a direct, mechanical extension — deferred for this session's compute-time budget, not for any remaining scientific uncertainty about method. `analysis/sample_size_planning_corpus_enlargement.py` runs the full grid; `run_full_grid()` is ready to call.

## 4. Translating required primary-contrast N into required total corpus size

The current sealed set yields 44 primary-contrast-eligible compounds from 2,069 four-isoform-complete compounds — a **2.1% yield rate**. Applying this rate (with the caveat below) to the required-N range above:

| Target power | Mild clustering — total corpus needed | Heavier clustering — total corpus needed |
|---|---:|---:|
| 80% | ≈ 500 / 0.021 ≈ **23,800** | ≈ 668 / 0.021 ≈ **31,800** |
| 90% | ≈ 706 / 0.021 ≈ **33,600** | ≈ 875 / 0.021 ≈ **41,700** |

**This 2.1% yield rate is itself an assumption, not a guarantee** — it reflects the specific mix of ChEMBL-indexed PI3K chemistry currently in A4, and there is no strong reason to assume a 10×-larger four-isoform corpus would preserve exactly the same alpha-selective/other-selective fraction. This translation is reported as an order-of-magnitude planning figure, not a precise target.

## 5. What this means, stated plainly

Reaching adequate power at the plausible effect size requires a four-isoform panel corpus roughly **10–20× larger** than currently sealed. That is a substantial data-generation or data-mining effort — consistent with, and now quantified beyond, the original plan's qualitative expectation that "more data is needed." The number is large enough that it is worth treating as a real go/no-go input for whether a corpus-enlargement effort is worth prioritizing at all, rather than an incidental detail.

## 6. Sequencing for the actual future attempt (adopted from the original plan, unchanged in substance)

1. Corpus-enlargement work (new literature/database mining, or new experimental characterization) targets **complete four-isoform pAct coverage** specifically — partial panels do not help, per §1's own finding that the current 2,069-compound "sealed set" mostly cannot be used for exactly this reason.
2. **Do not add compounds to the existing Stage C sealed set.** A new attempt gets its own fresh candidate pool, its own fresh exclusions (against whatever hypothesis-generation corpus that future attempt's Stage A/B used), its own fresh freeze, its own fresh hash.
3. The new attempt pre-registers its own endpoint, its own margin (retaining 0.10 unless a documented, pre-comparison reason changes it), and its own power check — run *before* any confirmatory work, exactly as Stage C did here.
4. Only if that fresh power check clears the pre-registered target does that future campaign proceed to its own Stage D/E.

## 7. What this document does not authorize

No modification of any Stage C artifact. No Stage D/E work under the current Rev. 5 campaign. No claim that corpus enlargement is already underway or committed — this is a planning output, to be acted on or not as a separate resourcing decision.

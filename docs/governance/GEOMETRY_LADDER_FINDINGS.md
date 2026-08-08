# Geometry-Sensitivity Ladder — Full Results (8-Action Plan)

Executes Actions 1–8. Builds on Phases 0–8 (commit `268167c`) without
modifying any of that work. All new code additive; existing tests,
outputs, and hashes untouched.

## Action 1 — Ladder execution, and a disclosed derivation-rule limitation

Boundaries frozen deterministically from the already-committed coarse
values before any Rep3b/Rep3c result was computed (`frozen_ladder_boundaries`,
9 passing tests). No new docking or parsing beyond one necessary reparse
pass to obtain raw per-pose distances not previously saved to disk
(`data/structural_evidence/raw_interactions/`), which now removes the
need for any further reparse in future geometry work.

**Finding, not a bug — verified before reporting, not assumed:** the
"fine" rung is numerically identical to "intermediate" for both
datasets. Root cause confirmed by inspecting the raw distance
distributions directly: the fine rung's one additional cutpoint
(`close_max / 2`, e.g. 1.5 Å for H-bonds, 2.0 Å for hydrophobic
contacts, 1.6 Å for charged contacts) falls **below the minimum distance
ever actually observed** for every interaction type present in this
corpus (observed minima: H-bond 2.62–2.70 Å, hydrophobic 2.68 Å, charged
contact 2.62–2.69 Å, salt bridge 2.80–3.02 Å — all consistent with basic
steric/electronic constraints on how close these contacts can physically
get). The cutpoint is real, frozen, and correctly computed; it simply
never gets crossed by any real docked geometry, so it splits nothing.

Per Action 1's own rule, this boundary is **not** retuned now that the
result is known. This is reported as a genuine property of the specific
pre-registered derivation choice (bisecting the theoretical range
`[0, close_max]`), not a failure of the ladder concept — a future,
separately-scoped "fine" rung derived from the *observed* distance
distribution (e.g. a low percentile of real data) rather than a
theoretical range would be a different, legitimate experiment, proposed
here only as a follow-up, not substituted in after the fact.

**Also confirmed, not assumed:** zero π–π or cation–π interactions were
detected anywhere in either corpus. The aromatic-geometry design
decisions in `_representation_2_3.py` (distance-only, no opportunistic
angle) were correctly implemented but never actually exercised by this
real data — worth stating plainly rather than silently.

**Consequence:** this dataset supports three meaningfully distinct
rungs — no-geometry (Rep 2), coarse (Rep 3a), intermediate (Rep 3b) —
not four. Rep 3c is reported alongside Rep 3b throughout for
completeness and transparency, but does not add information for this
corpus.

## Actions 2, 3, 6 — Normalized score, bootstrapped differences, complexity diagnostics

Full per-rung, per-stratum table (raw net score, normalized net score,
mean occupied bins/compound, and all three pairwise difference-CIs):
`docs/governance/GEOMETRY_LADDER_STATISTICS.json`.

**The real trajectory, using the corrected (normalized, difference-bootstrapped) metric — 50-compound dataset:**

| Rung | alpha vs other_selective Δ (normalized) | 95% CI | Excludes zero? |
|---|---:|---|---|
| Rep 2 (no geometry) | +0.224 | [+0.086, +0.355] | Yes |
| Rep 3a (coarse) | +0.203 | [+0.105, +0.303] | Yes |
| Rep 3b (intermediate) | +0.147 | [+0.059, +0.232] | Yes |
| Rep 3c (fine) | +0.147 | [+0.059, +0.232] | Yes (= Rep 3b, see Action 1) |

**This is a materially stronger and more precise result than what was reported before this analysis**, for two reasons: (1) it survives the bin-count-inflation check — the effect persists after normalizing by occupied-bin count, so it is not simply an artifact of geometry adding more bins; (2) it persists across every meaningfully distinct rung tested, with a real but mild monotonic *attenuation* in magnitude (+0.224 → +0.203 → +0.147), not a disappearance or reversal.

The other two contrasts tell a genuinely different story, and reporting only the one above would misrepresent the full result:

| Contrast | Rep 2 | Rep 3a | Rep 3b/3c |
|---|---|---|---|
| alpha vs non_selective | not significant | not significant | not significant |
| alpha vs intermediate | significant (barely: CI [+0.002, +0.310]) | significant (barely: CI [+0.006, +0.230]) | **not significant** (CI [−0.002, +0.134]) |
| alpha vs other_selective | significant | significant | significant (attenuated) |

alpha-vs-non_selective is a stable null throughout. alpha-vs-intermediate starts marginally significant and **loses significance by the intermediate geometry rung** — this specific contrast shows real fragmentation, and reporting it as "stable" would be wrong.

**24-compound dataset — same qualitative shape, less robust:** the alpha-vs-other_selective separation is significant at Rep 2/3a (Δ=+0.222, +0.196) but **loses significance at Rep 3b/3c** (Δ=+0.091, CI [−0.031, +0.203]). Given this dataset's strata are all n=6 (approximate coverage, flagged throughout), the most defensible reading is reduced statistical power at the smaller sample size, not a qualitatively different biological signal — the direction and rough magnitude are consistent with the 50-compound result at every rung, they just cross the significance threshold earlier as resolution increases.

## Action 4 — Multiplicity, stated plainly

6 ladder rungs × 3 pairwise contrasts × 2 datasets = **36 individual bootstrap difference-CIs** computed and reported (`docs/governance/GEOMETRY_LADDER_STATISTICS.json`, `action_4_multiplicity_disclosure`). No multiple-comparisons correction is pre-specified. Every one is reported; none is presented as an independent confirmatory test. The alpha-vs-other_selective finding above is the one result that holds up across the largest number of rungs and both datasets — that consistency, not any single CI, is what carries the weight here.

## Action 7 — Trajectory classification (five categories)

Applying the expanded taxonomy per contrast, 50-compound dataset (the more reliable one):

- **alpha vs other_selective: Stable, with mild monotonic attenuation.** Excludes zero at every meaningfully distinct rung; magnitude shrinks gradually (+0.224→+0.203→+0.147) but the effect does not disappear or reverse. This is the "stable" category with the caveat that it is not perfectly flat — a real, gentle geometry-resolution dependence exists alongside the persistent separation.
- **alpha vs intermediate: Progressive fragmentation.** Marginally significant at coarse resolutions, loses significance by intermediate. Consistent with a real but small effect that geometric strictness erodes.
- **alpha vs non_selective: Stable null.** No category applies beyond "no effect detected at any rung" — included for completeness, not because it fits one of the five categories describing a *changing* effect.
- No contrast showed single-resolution fragility (an effect appearing only at one arbitrary rung) or a fine-resolution reversal to the opposite sign, and no intermediate-resolution optimum (a peak stronger than both neighbors) was observed for any contrast — the trajectories are monotonic, not peaked, wherever an effect exists at all.

## Action 8 — Scientific boundary, restated

Not established by this analysis: a validated alpha-selectivity mechanism; that alpha-selective compounds are distinguishable from non-selective compounds (never significant); that the effect would survive a truly finer geometry rung than could be tested here (the real "fine" rung was a no-op, not evidence either way). Not done: no reward/penalty construction, no corpus scaling, no bin retuning after seeing results, no proceeding to ensemble docking on this basis alone.

## Next executable action

Per the mandate's own sequencing: the pre-registered combinatorial test (specificity-pocket occupancy × productive hinge interaction), with gamma analyzed separately per the standing specificity-pocket carve-out — the geometry ladder has now been completed as the prerequisite gate, with a result robust enough (persists, attenuated, across every meaningfully distinct rung in the larger dataset) to justify proceeding to that next step rather than stopping here.

# Phase 7 — Scientific Adjudication

Representation-3 Interaction Landscape Validation mandate. Consolidates
Phases 0–6. Applies the mandate's five-outcome framework (§22) honestly
— the result does not fit cleanly into one label, and is reported as
the blend it actually is rather than forced into a single bucket.

## A. What changed and what did not

| Comparison | Rep 0 (atom) | Rep 1 (residue) | Rep 2 (role-aware) | Rep 3 (role+geometry) |
|---|---|---|---|---|
| alpha_selective net score (50-cpd) | −0.750 | −0.833 | −1.167 | −2.417 |
| Stratum with the *best* (least negative) score | other_selective | other_selective | **alpha_selective** | **alpha_selective** |
| alpha vs other_selective, 95% CI overlap | overlap | overlap | **no overlap** | **no overlap** |
| alpha vs non_selective / intermediate, 95% CI overlap | overlap | overlap | overlap | overlap |

Full per-stratum values, both datasets, all four representations: `docs/governance/PHASE6_STATISTICAL_ANALYSIS.json`.

**What changed:** under Representations 2 and 3, alpha-selective compounds become the *best-ranked* of the four strata (previously they were not, under Rep 0/1 — this matches the originally reported null/inverted finding from commits eafe327/2f26c5c/7b3fe61). In the larger (50-compound) dataset, the separation between alpha-selective and other-isoform-selective compounds becomes statistically distinguishable (non-overlapping 95% bootstrap CIs) specifically under Rep 2/3, where it was not under Rep 0/1. This direction is consistent across both the 24- and 50-compound datasets, though only significant in the larger one (the 24-compound strata are all n=6, flagged approximate-coverage throughout).

**What did not change:** the net score never becomes positive in any representation or stratum — "least unfavorable to alpha" is not the same as "favors alpha." Alpha-selective compounds remain statistically indistinguishable from non_selective and intermediate compounds in every representation tested. No same-position rescue occurred anywhere (§13.1 = exactly 0 in both datasets, confirmed empirically, matching the mathematical necessity established before this analysis ran).

## B. Mechanism: pocket-level redundancy, not determinant conservation

§13.1 (same-position rescue): **0 / 0** in both datasets — zero instances in over 1,500 (24-cpd) and 3,100 (50-cpd) LOST-record × losing-isoform pairs examined. This is not a near-zero empirical result; it is the expected consequence of Representation 1 already excluding residue identity from its own key, confirmed rather than assumed.

§13.2 (pocket-level redundancy): **LOOSE ≈ 98–99%, STRICT ≈ 94–95%** in both datasets — almost every interaction lost at a specific mapped position is chemically fulfilled *somewhere else* in that isoform's own pocket for that compound.

**This is a real finding with a real limitation attached, and both must be reported together.** A PI3K ATP pocket contains on the order of 30–40 residues within contact range; "is this general interaction type present anywhere in a pocket that large" is a comparatively easy bar, and a near-ceiling redundancy rate is at least partly a description of ordinary pocket chemical richness rather than evidence of a specific, isoform-discriminating compensatory mechanism. The STRICT metric (94–95%, requiring the same residue functional class, not just the same interaction type) is somewhat more informative than LOOSE but is still close to ceiling. This caveat tempers, but does not erase, the ordering-separation finding in §A — the two results should be read together, not the second used to explain away the first, nor the first read as if the second caveat didn't exist.

## C. Gamma specificity-pocket carve-out (§20)

Per the standing Gate-1 evidentiary limitation (gamma FAIL, diagnosed to genuine incompleteness in `6AUD.pdb`'s specificity-pocket region), gamma's contribution to §13.2 within that specific region (canonical positions 780/772) is reported separately, never pooled:

| Isoform | Pairs examined (50-cpd) | Loose redundancy hits | Fraction |
|---|---:|---:|---:|
| alpha | 27 | 27 | 1.00 |
| beta | 26 | 26 | 1.00 |
| **gamma** | 19 | 19 | **1.00 (Gate-1-FAIL evidentiary tier)** |
| delta | 11 | 11 | 1.00 |

Gamma's 100% figure is numerically identical to the others but carries the standing Gate-1 caveat and must not be cited as equal-confidence structural evidence for this region. Full data: `docs/governance/PHASE5_RESCUE_ANALYSIS.json`.

## D. Decision (§22 five-outcome framework)

**No single outcome label fits cleanly, and forcing one would overstate or understate the result. The honest characterization is Outcome 3 (pocket-level redundancy dominates the mechanism) as the primary finding, with a real but narrow Outcome-2-shaped partial-ordering improvement layered on top:**

- **Outcome 3 is unambiguously supported as the mechanism**: §13.1=0 and §13.2 near-ceiling together establish that whatever apparent conservation exists is overwhelmingly pocket-level redundancy, not same-position determinant conservation. The mandate's own Outcome-3 text — "does not establish conservation of a specific selectivity determinant" — applies directly.
- **Layered on top, a real, narrower ordering effect exists**: alpha-selective compounds move from tied-with-or-worse-than other_selective (Rep 0/1) to statistically better-than other_selective (Rep 2/3, 50-compound dataset, non-overlapping CIs). This is Outcome-1/2-shaped but should not be called "robust" — it is one specific pairwise comparison, in one dataset size, that did not reach significance in the smaller dataset, and does not extend to the other two strata.
- **Outcome 5 (persistent null) is not the correct label either** — the null specifically for the alpha-vs-other_selective comparison was resolved by the representation change; calling the overall result "persistent null" would misrepresent that.

## E. What this does and does not establish

**Established:** the chemically role-aware representation reveals a real, statistically supported difference between alpha-selective and other-isoform-selective compounds that literal residue-identity-based representations did not show, in the larger of the two available datasets. The mechanism behind whatever conservation exists is overwhelmingly pocket-level functional redundancy, not conservation of a specific determinant at a specific position.

**Not established:** that alpha-selective compounds show net *favorable* (positive) alpha-preferring chemistry in any absolute sense; that alpha-selective compounds are distinguishable from non-selective or intermediate compounds; that the pocket-level redundancy reflects anything more specific than general pocket chemical richness; any claim involving gamma at full evidentiary confidence in the specificity-pocket region; a validated selectivity mechanism, reward signal, or generative-model training target (all explicitly out of scope for this phase, per §26, and still out of scope after this result).

## F. Limitations carried forward

Small n (24- and 50-compound corpora; smallest strata n=6, flagged approximate-coverage); prior knowledge of the Rep 0/1 result before this analysis ran (disclosed, not concealed, per §21); gamma's standing Gate-1 structural limitation; beta's weaker (chemical-plausibility-only) correspondence tier; ligand-side ionization state generally unverified in this docking pipeline (per the interaction detector's own long-standing documentation); the near-ceiling §13.2 redundancy rate as a limitation on interpreting *any* rescue mechanism, not just this one; and — not yet executed this phase, explicitly deferred rather than silently dropped — §11's full intermediate/fine geometry stress-test ladder beyond the Rep 2-vs-Rep 3 comparison already run, §19's pre-registered combinatorial Fisher's-exact test, and §13.3's optional intrinsic-residue-capacity metric.

## G. Next executable action

Given the ordering-separation finding is real but narrow (one pairwise comparison, one dataset size) and the pocket-redundancy mechanism raises a real ceiling-effect concern, the single highest-value next step is **§11's fuller geometry sensitivity ladder** (intermediate binning between Rep 2's no-geometry and Rep 3's coarse bins, plus the fine stress-test) — this is the cheapest remaining test (pure re-aggregation of already-computed per-pose data, no new parsing or docking) and directly tests whether the alpha-vs-other_selective separation is robust to geometry-resolution choice or fragile to it (§22 Outcome 4), which materially changes how much weight the Section D finding can bear.

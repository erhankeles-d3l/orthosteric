# Stage B — Summary and Verdict

Executes Stage B per Rev. 5's own binding sequence (SS0.5): β receptor due diligence + Gate 1 (SS3), then the 6XRL production-path bridge + smoke test (SS0.6.4). Both parts complete.

## Part 1 — β receptor due diligence: FOUR-ISOFORM ENDPOINT INVALIDATED

Full write-up: `docs/governance/STAGE_B_BETA_DUE_DILIGENCE.md`.

Four independent search angles found no human PIK3CB ATP-site experimental structure. Both candidates identified (2Y3A, 4BFR) are confirmed mouse, disqualified directly from their RCSB pages. Per SS3.1's binding rule, **the four-isoform confirmatory endpoint is invalidated** — not silently downgraded to three isoforms. SS1's power check is therefore **not run** against the four-isoform endpoint this session, per SS3.1's explicit dependency.

A real governance tension was found and flagged rather than silently resolved: an earlier project decision (GDR-006/SCI0-007) already accepted the AlphaFold beta model as admissible for prior comparative work. Rev. 5 sets a stricter, study-specific bar and its text is applied here as the more recent and specific instruction — but the divergence is recorded for the project owner, not adjudicated unilaterally.

## Part 2 — 6XRL production-path bridge + smoke test: PASS

Full data: `docs/governance/STAGE_B_6XRL_BRIDGE_SMOKE_TEST.json`.

Actually docked all 50 corpus compounds against 6XRL through the real production path (not a re-parse) — `cpu=1` throughout per SS4's reproducibility requirement, box center matching Gate 1's value exactly. **50/50 docked, 0 failures, 1543.8s. Interaction detection ran cleanly on all 50 pose sets, 0 errors.**

**The one number requiring interpretation, not a headline read:** hinge H-bond (Val882) recovered in only 18/50 top poses (36.0%), well below Gate 1's 4/5 (80%) on the single reference ligand. This gap is not directly interpretable on its own — Gate 1 tested one known, potent binder specifically engineered to engage that hinge; a scaffold-diverse corpus should show more heterogeneous engagement. Two checks were run before drawing any conclusion:

1. **Cross-reference against the already-committed alpha/delta rates on the identical corpus** (computed directly from `raw_interactions_50.json`, no new computation): alpha 27/50 (54.0%), delta 22/50 (44.0%), gamma-via-6XRL 18/50 (36.0%). Gamma is lower but in the same ballpark — not an order-of-magnitude gap, not near-zero. All three isoforms show a moderate, sub-100% rate across a chemically diverse corpus, consistent with real chemistry (not every compound is a potent hinge-binder) rather than a 6XRL-specific pipeline problem.
2. **Score-correlation check**: hinge-hit compounds show a more favorable mean Vina score (−8.83) than hinge-miss compounds (−8.27) — the chemically expected direction, since the hinge H-bond is an established major contributor to ATP-competitive affinity. This supports the hit/miss split reflecting real, differentiated binding chemistry, not noise.

**Verdict: PASS.** The production-path pipeline is confirmed working correctly at real corpus scale, and gamma-via-6XRL's behavior is continuous with, not an outlier from, the already Gate-1-validated alpha/delta receptors on the identical corpus.

## Stage B overall verdict

**Complete.** Part 2 passes cleanly. Part 1 does not "fail" in the sense of broken infrastructure — it returns a real, decisive, negative structural-biology finding (no human PIK3CB structure exists) that invalidates the frozen four-isoform endpoint per the mandate's own pre-registered rule. This is one of Rev. 5's own explicitly anticipated outcomes (SS15: *"β receptor inadequate → four-isoform confirmatory endpoint invalidated; receptor-limitation finding; SS1 not run against it"*), not a deviation from the plan.

## What this means for Stage C onward

SS1 (seal + power check) as specified cannot run against the four-isoform endpoint. Per SS3.1's permitted response, a three-isoform (α vs γ/δ) analysis remains available but requires its own separately pre-registered endpoint and its own power check — a substantive design task, not a same-session improvisation. This should be presented to the project owner as an explicit decision point before further work: either (a) design and pre-register that three-isoform endpoint as a new, separately-scoped mandate amendment, or (b) treat this finding itself as the deliverable and stop here, reporting the dataset/receptor limitation as the headline result — consistent with the mandate's own repeatedly-stated preference for an honest null over a manufactured positive.

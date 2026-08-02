# AUDITOR-2 Threshold Evidence: N_c, N_b, N_w, S4b (corrected)

**Status:** Evidence prepared | CANDIDATE RANGE — requires Auditor approval, with a
materially weakened confidence level after sensitivity analysis (see §4)

**Correction note:** an earlier draft of this document presented a single graph
simulation's result ("Lcc grows much more slowly than compound count") as if it were a
property of the actual ADR-0003 evidence graph. A sensitivity analysis across three
distinct, individually plausible graph-generation mechanisms shows this conclusion is
**not robust** — it depends heavily on an assumption about literature structure that
cannot be verified without the real corpus. This is reported honestly below rather than
carried forward as before.

---

## 1. Exact operational definitions (unchanged, extracted from governance documents)

**`N_c`:** minimum size of the largest connected component (Lcc) in the bipartite
compound×isoform evidence graph.

**`N_b`:** minimum number of bridging compounds linking study clusters.

**`N_w`:** minimum within-study four-isoform compound count for the evaluation stratum.

**S4b sharpness factor:** multiplier k such that mean predictive interval width ≤ k ×
σ_within_study.

**Ambiguity flagged (unchanged):** none of the governing documents states whether these
are measured on raw records or scaffold-deduplicated compounds.

---

## 2. Simulation methodology — full disclosure

**Mathematical definition of Lcc used:** the largest set of mutually-reachable compounds
under the relation "compound i and compound j are connected if they were measured in the
same study AND share at least one isoform with a recorded measurement." Computed via
union-find over all same-study compound pairs sharing ≥1 isoform.

**Missingness/coverage assumption:** varies by model (see §3) — this is exactly the
assumption identified as most consequential.

**Random seed:** 20260801, fixed throughout.

**Monte Carlo repetitions:** 300 per model per scenario (headline scenario), 150 per
scenario in the compound-count sweep.

**Parameter grid (headline scenario):** n_compounds=300, coverage_prob=0.5, n_studies=15.

**Confidence intervals:** reported as 95% percentile intervals across Monte Carlo
replicates, not analytic — appropriate given the non-Gaussian, right-skewed distribution
of Lcc observed under some models (see Model B below).

**Whether the simulation model resembles the actual ADR-0003 evidence graph:** **this is
explicitly unverifiable without the real corpus**, and is the central limitation of this
entire analysis. Three models were tested specifically to probe this.

---

## 3. Three graph-generation models tested

**Model A — uniform random.** Each compound assigned to one of `n_studies` uniformly at
random; each compound×isoform pair independently has a measurement with probability
`coverage_prob`. This was the only model in the prior draft.

**Model B — clustered/hub studies.** Study sizes follow a Dirichlet distribution with
concentration parameter favoring a few large "hub" studies — modeling the real-world
pattern where a handful of large multi-isoform screening panels (e.g., landmark papers
profiling many compounds across all four isoforms) contribute disproportionately to the
public record. Everything else identical to Model A.

**Model C — correlated per-compound coverage.** Each compound has an individual
"propensity to be broadly profiled" (Beta-distributed), rather than independent
per-isoform coin flips — modeling the pattern where some compounds are "panel compounds"
tested against most isoforms and others are tested against only one or two. Study
assignment as in Model A.

**None of these three models is asserted as correct.** They represent three
individually-plausible, mutually-inconsistent assumptions about how the real literature
is structured. The real ADR-0003 evidence graph's structure can only be determined by the
actual Stage 0 Q1 connectivity audit.

---

## 4. Sensitivity analysis results — the corrected headline finding

Same scenario (300 compounds, 50% coverage, 15 studies), same seed, three models:

| Model | mean Lcc | std Lcc | 95% CI | mean bridging compounds |
|---|---|---|---|---|
| A: uniform random | 26.4 | 2.3 | [23.0, 31.0] | 206.1 |
| **B: clustered/hub studies** | **96.8** | **31.4** | **[51.5, 174.5]** | 204.4 |
| C: correlated per-compound coverage | 24.7 | 2.3 | [21.0, 30.0] | 189.1 |

**This is the corrected central finding, replacing the prior draft's overconfident
claim:** Model B — arguably the *more* realistic assumption for a real literature corpus,
where landmark multi-isoform panels act as high-connectivity hubs — produces a mean Lcc
nearly **4× larger** than Models A and C, with an order-of-magnitude wider confidence
interval. The conclusion "Lcc grows much more slowly than compound count" is **not a
property of the ADR-0003 problem**; it is an artifact of assuming uniform random study
structure, which real scientific literature does not typically exhibit.

**Additional check — does Lcc/N shrinking with N hold across models?** The prior draft
observed Lcc/N shrinking from 0.088 to 0.025 as N grew from 300 to 1,200 under Model A.
This was **not re-tested under Model B** in this pass; given Model B's result above, this
additional claim from the prior draft should also be treated as unverified pending further
sensitivity testing, and is not repeated here as a finding.

---

## 5. Consequence for N_c and N_b — substantially weakened

**UNRESOLVED — evidence insufficient, corrected from the prior draft's CANDIDATE RANGE
claim.** No numeric range for `N_c` or `N_b` is proposed in this corrected document. The
prior draft's suggestion of a "relative threshold" and specific absolute ranges (e.g.,
"N_b in range 80–200") was downstream of the now-discredited Model-A-only result and is
withdrawn.

**What can still be said, honestly:**
- The *mechanism* by which N_c/N_b should be set — via the actual Stage 0 Q1
  connectivity audit's own structural output, rather than an a priori absolute number
  chosen before that structure is known — remains a reasonable methodological
  recommendation, independent of which graph model is correct.
- Whichever value is eventually chosen should be **stress-tested against multiple
  structural assumptions**, not derived from a single arbitrary model, precisely because
  this sensitivity analysis shows how much the answer can vary.

**RECOMMENDATION — not a governance decision:** the Auditor should treat any pre-Stage-0
numeric candidate for `N_c`/`N_b` as provisional at best, and should prioritize designing
the Stage 0 Q1 audit to directly measure the real graph's Lcc and bridging-compound count
rather than attempting to pre-specify a defensible number from simulation alone.

---

## 6. N_w and S4b — findings retained, with appropriate caveats

The N_w and S4b analyses do not depend on the graph-connectivity model above; they concern
single-compound or single-record statistical properties, not graph structure, and are
retained from the prior draft with their original caveats intact:

**N_w:** power to detect a 0.5 log effect at σ=0.3 (Constitution floor) is ≈1.0 already at
N_w=8 (4 families × 2 compounds/family). **Statistical power is not the binding constraint
for N_w** — this finding is robust regardless of graph-generation assumptions, since it
concerns a simple one-sample test, not connectivity. CANDIDATE RANGE (unchanged):
representativeness-based N_w in 24–40, contingent on Auditor's own choice of minimum
compounds/family — offered as a starting point, not a derived result.

**S4b:** null-model calibration showing a constant-width predictor's apparent coverage
depends on the assumed true-effect spread; k in [1.5, 2.0] denies the null model
plausible-looking coverage across the tested range. This finding is also independent of
the graph-connectivity question and is retained unchanged.

---

## 7. Limitations (expanded)

- The three-model sensitivity analysis is itself not exhaustive — real literature
  structure could differ from all three in ways not modeled here (e.g., isoform-specific
  study biases, where some isoforms are systematically under-profiled relative to others).
- N_w and S4b findings, while more robust than the N_c/N_b findings, still rest on the
  Constitution's stated 0.3 log noise floor and an assumed 0.5–1.5 log true-effect spread
  — both disclosed assumptions, not established facts.
- No amount of simulation substitutes for the actual Stage 0 Q1 connectivity audit against
  the real corpus.

**Independent Auditor decision still required: YES.**

---

## Addendum — empirical precedent search (published multi-target kinase datasets)

**Status: one genuine, disclosed tension identified between field practice and this
project's own pre-registration principle. No candidate number derived from it.**

### What was found

Established multi-target kinase drug-target-interaction benchmarks (KIBA, Davis, Metz —
the standard reference datasets in this exact modeling area) are curated using a
**post-hoc filtering threshold**: per the curation described in the DTI literature (e.g.,
"Multi-View Self-Attention for Interpretable Drug-Target Interaction Prediction," arXiv
2005.00397, citing the filtering methodology of an earlier curation), "a filter threshold
is applied to each dataset for which compounds and targets with a total number of samples
not above the threshold are removed."

**FACT — directly supported by source:** this describes filtering **after** inspecting
the raw dataset's actual structure, choosing a threshold that seems reasonable given what
the data actually look like — not a threshold fixed in advance of ever seeing the data.

**The exact numeric threshold values used by KIBA/Davis/Metz curators were not retrieved
in this pass** and are not reported here.

### The tension this creates, stated plainly rather than resolved

This project's own Constitution §1.4 requires thresholds to be **fixed before results are
seen** — precisely to prevent the kind of post-hoc, data-informed threshold-setting that
is standard practice in the field this project is drawing methodological precedent from.

This is not a reason to weaken the project's pre-registration requirement. It is a
disclosure that the field's typical practice does not provide a "these are the numbers
everyone uses" precedent that can be adopted directly — because the field's own numbers
were chosen with knowledge of the data they were applied to, which is exactly the
practice ADR-0003 §5 and Constitution §1.4 are designed to avoid repeating here.

**RECOMMENDATION — not a governance decision:** if the Auditor wants an externally
grounded floor for N_c/N_b/N_w, the more defensible route is not "what number did KIBA/
Davis/Metz use" (since that number was itself chosen post-hoc) but rather "what filtering
threshold, chosen before Stage 0 data are inspected, would a reasonable practitioner in
this field consider defensible" — which is a judgment call for the Auditor, informed by
but not derived from, the field's post-hoc precedents.

### What remains the Auditor's decision

Unchanged from the main document: no candidate range for N_c or N_b is proposed. This
addendum adds context (the field's typical practice is post-hoc, which is exactly the
practice this project's pre-registration rule exists to avoid) but does not supply a
number.

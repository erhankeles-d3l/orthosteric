# Stage C — Statistical Decision Record

## Frozen decision rule (restated verbatim, pre-registered before this curve was computed)

> If the curve shows the design has reasonable power (≥50%) at some effect size within the range this campaign's own prior work suggested plausible (~0.20–0.25, consistent with Rev. 5 §1.2's own anticipation), the decisive gate exists and Stage D is authorized. If even the largest tested effect (0.30) shows low power under both the independent and scaffold-correlated sensitivity checks, the decisive gate is not available at this n regardless of what the boundary-calibration number showed, and this is the headline dataset-limitation finding — not a re-run at a different sample size or a lowered margin.

## The full operating-characteristic curve

Real sealed-set composition, not idealized: **n = 44** (31 alpha_selective, 13 other_selective) — the frozen primary confirmatory contrast, out of a 2,069-compound sealed set (most of which lacks a complete four-isoform pAct panel and cannot enter this specific contrast — see `STAGE_C_STEP2_SUMMARY.md`). 33 distinct Bemis–Murcko scaffold families among the 44 (largest = 5 compounds, most singletons).

| True ΔAUC | P(CI₉₅,lower > 0.10) — independence | P(CI₉₅,lower > 0.10) — scaffold-correlated |
|---:|---:|---:|
| 0.10 (boundary calibration) | 3.6% | 4.3% |
| 0.15 | 8.0% | 7.8% |
| 0.20 | 12.4% | 15.4% |
| 0.25 | 28.6% | 28.6% |
| **0.30** | **47.0%** | **48.0%** |

Boundary calibration (0.10) is close to, but modestly above, the ~2.5% expected under a correctly-calibrated two-sided 95% CI at the boundary — a small liberal bias at n=44, disclosed as a property of the bootstrap procedure at this sample size, not a dataset-adequacy finding (per the frozen distinction between calibration and power).

## Decision

**Even at the largest tested effect (ΔAUC = 0.30), power is 47–48% — below the pre-registered 50% threshold — under both the independence-assumed and scaffold-correlated sensitivity models.** Within the 0.20–0.25 range this project's own prior work (Rev. 5 §1.2) anticipated as the plausible effect size, power is only 12–29%.

Per the frozen decision rule, both conditions for the dataset-limitation outcome are met:

1. The largest tested effect shows low power.
2. This holds under **both** sensitivity checks — scaffold correlation does not materially change the picture at either end of the curve (within ~1–3 percentage points at every effect size tested), meaning within-scaffold clustering is not the binding constraint here. Plain sample size is.

> ## STAGE C DECISION: POWER CHECK FAIL — THE DECISIVE GATE DOES NOT EXIST AT THE AVAILABLE n.

This is reported as the headline finding, not a preliminary result to be improved by any of the following — all explicitly prohibited by the pre-registered plan and not done here:

- **The 0.10 margin was not lowered.** It remains exactly as pre-registered.
- **The sealed set was not enlarged or redefined after seeing this result.** Its composition was frozen and hashed (Stage C Step 2) *before* this simulation ran; the simulation used that frozen composition's real counts, nothing more.
- **No corpus generation was undertaken to manufacture an alternative path.** Stage D (corpus assembly, motif discovery, the baseline ladder itself) is explicitly **not authorized** by this result.

## What this finding means, stated precisely

This is not a finding that the comparative structural signal is false, or that B7 would fail to beat B2 if the full Stage D/E pipeline were run. It is a finding that **the currently available sealed retrospective validation set cannot statistically distinguish a ≥0.10 AUC improvement from noise with the required 95%-confidence margin, even under generous assumptions about the true effect size.** The question Stage C was designed to ask — "does the decisive gate exist?" — has a clear answer: no, not with this dataset as sealed.

## What remains available, not executed here

Per Rev. 5's own repeated framing (a dataset-limitation finding is a legitimate, reportable result in its own right, not a failure requiring workaround): enlarging the underlying four-isoform panel corpus (more studies, more compounds with complete cross-isoform coverage) would be the principled way to increase n for a *future*, newly-registered validation attempt — explicitly a new effort, with its own fresh sealing and its own fresh pre-registration, not a re-run of this one.

## Reproducibility

- Script: `analysis/stage_c_step3_statistical_assessment.py` (fully reproducible from the frozen sealed-set composition counts alone; contains no reference to any individual compound's actual label).
- Results: `docs/governance/STAGE_C_STATISTICAL_ASSESSMENT.json`.
- Random seed: `20260808`, fixed and recorded.
- A real vectorization bug was caught and fixed before the full run: an earlier draft looped over each of the 10,000 inner bootstrap replicates individually in Python, which would have made the required outer-loop scale computationally intractable. Fixed by building the full pairwise-comparison tensor per chunk (fully vectorized numpy).

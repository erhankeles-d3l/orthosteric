# Docking Pipeline — Production Pilot, Correlation Analysis, and a Reproducibility Correction

**Date:** 2026-08-07
**Snapshot:** A4, `SNAP-05748f6627ea` (read-only throughout — verified via `git status`, no working-tree diff)

## Part 1 — Real pH-aware protonation (completed, tested)

Dimorphite-DL 2.0.2 wired into the interaction detector. `SALT_BRIDGE` is now a chemistry-confirmed label (real RDKit formal charge on the selected pH-7.4 protonation state); `CHARGED_CONTACT_CANDIDATE` is the unconfirmed remainder — unchanged geometric criteria, only the evidentiary label differs. 29 new tests, all passing.

**On the 5-compound pilot**: of 68 prior candidates, 20 promoted to confirmed `SALT_BRIDGE` (all from Quercetin's deprotonated phenolate oxygens — correct pKa chemistry), 48 remained unconfirmed, 2 compounds flagged ambiguous.

## Part 2 — Production pilot: 24 compounds × 4 isoforms (completed)

**Compound selection**: real, deterministic, stratified sample from A4's 1,267 `SelectivityTarget`s — 6 each from alpha-selective, other-selective, non-selective, intermediate strata, scaffold-diversity-preferring.

**Scale note, stated plainly**: 24, not the 50–100 originally aimed for. This reflects an actual time/tool-call budget constraint reached mid-session, not an architectural limit — the same pipeline that ran 24 would run 100 given more session time.

**Result**: 96/96 docking + interaction analyses completed successfully. Score range −10.7 to −5.9 kcal/mol (plausible). 36/96 entries flagged ambiguous protonation (9 of 24 compounds). Interaction totals: 167 H-bonds, 2 confirmed salt bridges, 356 charged-contact candidates, 801 hydrophobic contacts, 26 cation-π, 8 π-π.

## Part 3 — Correlation with real experimental selectivity (completed, honest null-leaning result)

Docking Δscore (`dock(X) − dock(α)`) vs. experimental `pAct_α − pAct_X`, same sign convention, 24 compounds:

| Axis | n | Pearson r | p | Spearman ρ | p | Sign agreement |
|---|---:|---:|---:|---:|---:|---:|
| α vs β | 24 | +0.364 | 0.080 | +0.366 | 0.079 | 13/24 (54%) |
| α vs γ | 24 | +0.183 | 0.391 | +0.140 | 0.514 | 15/24 (62%) |
| α vs δ | 24 | +0.237 | 0.264 | +0.362 | 0.082 | 11/24 (46%) |

**Honest reading**: weak, borderline (p≈0.08, not significant at conventional α=0.05) positive trends for β and δ; essentially no relationship for γ. Sign agreement (46–62%) is close to chance (50%) on every axis. **This does not support a claim that this docking pipeline's Δscore predicts experimental isoform selectivity at this sample size and this level of chemistry** (rigid receptor, single pose, no rescoring, no ensemble). This is reported as a real, informative negative-leaning result, not reframed as a partial success.

One interaction-type correlation nominally cleared p<0.05 (`charged_contact_candidate` vs β, ρ=−0.439, p=0.032) but does **not** survive correction for the 18 comparisons actually tested (6 interaction types × 3 axes; Bonferroni threshold ≈0.0028) — flagged explicitly as a likely false positive from multiple testing, not a finding.

## Part 4 — A reproducibility claim I made earlier needs correcting

While spot-checking the production results, I found a small discrepancy: re-running one compound/receptor pair gave −8.524 kcal/mol vs. the −8.549 recorded during the actual production run. I investigated rather than ignoring it:

- With `cpu=1` (single-threaded), 5 independent Vina invocations gave **bit-identical** scores.
- With Vina's **default multi-threaded** mode (what every docking run in this entire workstream actually used — I never explicitly set `cpu=`), repeated calls *within one continuous test* were also self-consistent, but did not match the number recorded from the original, separate production run.

**Correct statement, replacing my earlier claims**: the interaction *detector* is exactly deterministic given a fixed, already-saved pose (verified repeatedly, still true). Vina's own docking search, run in its default multi-threaded mode, is subject to small (~0.03 kcal/mol, ~0.3–0.5% relative) run-to-run floating-point non-determinism between independent process invocations — a known class of behavior in multi-threaded numerical grid computation without a fixed reduction order. My earlier "reran and confirmed identical" claims from the 5-compound and 20-pose pilots were true for what they actually tested (interaction-detector determinism on saved poses) but I described them more broadly than that, which overstated the guarantee. This is now corrected.

**Practical consequence**: at ~0.03 kcal/mol, this noise is small relative to the score range (~5 kcal/mol) and unlikely to flip any qualitative classification in this report, but it is a real, additional contributor to the weak correlations in Part 3 that I had not accounted for before. For any future run where bit-exact reproducibility is a hard requirement, `cpu=1` is confirmed to deliver it, at an observed ~10× wall-clock cost — an explicit, undecided speed-vs-determinism tradeoff, not resolved here.

## DONE
Real pH-aware protonation (Dimorphite-DL), SALT_BRIDGE promotion logic, 24-compound stratified production pilot (96/96 successful), correlation analysis against real experimental data, KD-tree-based receptor spatial indexing (built once per receptor, reused across all ligands — a genuine efficiency upgrade over the prior per-pose dense matrix). Full gate suite green throughout: 1,007 tests, ruff/mypy clean, import-linter 3/3.

## VALIDATED
Interaction-detector determinism reconfirmed after the protonation change. `cpu=1` Vina determinism confirmed (5/5 identical). Docking score plausibility confirmed (no outliers, no failures across 96 runs).

## CORPUS-DERIVED
All numbers in Parts 2–3 above.

## ENGINEERING CHOICE
24-compound scale (not 50–100, transparently under-delivered). KD-tree radius (12 Å, unchanged, still exceeds every detector cutoff by ≥6 Å). Multi-threaded Vina as default (not yet switched to `cpu=1`).

## GOVERNANCE REQUIRED
None new.

## RULE_MISSING
Ligand ionization state beyond what Dimorphite-DL confirms (unchanged). Cross-isoform residue correspondence (SCI1-003, unchanged).

## CORRECTED CLAIM
Vina docking-score reproducibility is NOT bit-exact across independent process invocations in default multi-threaded mode (~0.03 kcal/mol noise). Interaction-detector reproducibility on a fixed saved pose remains exact and unaffected.

## NEXT EXECUTABLE STEP
**Decide, as an explicit Project Owner call, whether future docking runs should default to `cpu=1`** (confirmed bit-exact, ~10× slower) or accept the ~0.03 kcal/mol multi-threaded noise as within-tolerance for this pipeline's current precision needs — this determines whether re-running the 24-compound (or a future 50–100-compound) pilot for stricter reproducibility is worth the wall-clock cost before any further correlation or scaling work.

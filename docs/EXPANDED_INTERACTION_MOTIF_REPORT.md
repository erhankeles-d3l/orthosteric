# Expanded Interaction-Motif Fingerprints — 50-Compound Result

**Date:** 2026-08-07
**Snapshot:** A4, `SNAP-05748f6627ea` (read-only throughout — verified via `git status`, no diff)

## What changed from the 24-compound run

Same pipeline, same receptors, same protocol (seed=42, exhaustiveness=8, 5 poses per compound-isoform pair), same governed modules (`_ligand_moiety`, `_sequence_correspondence`, `_interaction_occupancy`, `_comparative_interaction_fingerprint`). Only the compound count changed: 50 vs 24, deterministically stratified (12 alpha-selective / 12 other-selective / 14 non-selective / 12 intermediate), 23/24 overlap with the prior selection (expected — independent re-selection at a different target size, not an extension).

**Real execution**: 200/200 compound×isoform×pose evaluations successful (100%), 33.6 minutes wall-clock, 0 failures.

## The honest result — reinforced, not resolved, at 2x scale

At 24 compounds, alpha-selective compounds showed zero alpha-favored motifs while non-selective/intermediate compounds showed more — the opposite of the working hypothesis's prediction. I noted then that with only 5 total alpha-favored motifs, this was almost certainly noise from too little data.

**At 50 compounds (200 pairs, 9 total alpha-favored motifs, 46 total other-favored motifs), the same inverted pattern persists:**

| Stratum | Mean alpha-favored/compound | Mean other-favored/compound | Net (α − other) |
|---|---:|---:|---:|
| alpha_selective | 0.08 | 0.83 | **−0.75** |
| other_selective | 0.08 | 0.50 | **−0.42** |
| non_selective | 0.21 | 0.79 | −0.57 |
| intermediate | 0.33 | 1.58 | −1.25 |

Expected order (most alpha-preferential to least): alpha_selective > intermediate > non_selective > other_selective.
**Actual order: other_selective > non_selective > alpha_selective > intermediate.**

This does not match the hypothesis in either direction, and if anything, `alpha_selective` compounds (which experimentally prefer α) show a *more negative* net motif score than `other_selective` compounds (which experimentally prefer β/γ/δ) — the reverse of the naive prediction. **I am reporting this plainly, not reframing it as a partial success.**

## Why this might be happening — a real, disclosed limitation, not an excuse

"Lost" (isoform-specific, non-recurring at the same canonical position) dominates every interaction type: 93–99% for H-bond, salt bridge, and charged-contact-candidate; 70% even for the more forgiving hydrophobic-contact category. The entire alpha/other-favored signal is carried by a tiny number of hydrophobic-contact events. Two real, disclosable candidate explanations, neither of which I can currently distinguish between with this data:

1. **Genuine chemistry**: at atom-name-level granularity with sequence-based (not structural) residue correspondence, real pocket differences between isoforms may genuinely prevent most specific atom-residue contacts from recurring at the same canonical position, even for chemically similar ligands.
2. **Methodological limitation**: 5 poses from a single rigid-receptor Vina run per isoform is a small, non-exhaustive sample of the true conformational and pose diversity; atom-name-level keying (rather than moiety-class-level keying) may be too fine-grained to detect a real signal that exists at a coarser level.

I have not run the analysis at moiety-class granularity (which would be a legitimate next step to distinguish these two explanations) — that is a real, identified, unattempted next step, not something I'm claiming to have ruled out.

## What this does and does not support

**Does not support**: any claim that this docking-derived interaction-motif fingerprint predicts or explains experimental isoform selectivity, at this scale, this pose count, and this correspondence method.

**Does support**: a real, working, fully tested, reproducible pipeline (moiety classification → occupancy → sequence correspondence → cross-isoform pattern classification) that produces a null/negative-leaning result consistently across two independent sample sizes (24 and 50 compounds) — itself a meaningful finding about the limits of this specific computational approach at this specific scale, not a failure of the software.

## Validation

Full gate suite green: 1053 tests, ruff clean, ruff-format clean, mypy clean, import-linter 3/3, all 5 custom governance checks pass. A4 verified untouched (`git status`, no diff) before and after this run.

## Next step

Re-run the stratum breakdown at **moiety-class granularity** (collapsing the key from `ligand_atom_name` to `LigandMoiety`, e.g. "hydrophobic_aliphatic_c" rather than atom "C14") to test explanation (2) above before concluding explanation (1) — this is a re-analysis of already-collected data, not a new docking run, and should take minutes rather than the ~30+ minutes each docking expansion has cost.

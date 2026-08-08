# Structural Evidence: All Four Isoforms — Coverage Matrix and Viability Conclusion

**Date:** 2026-08-06
**Snapshot:** A4, `SNAP-05748f6627ea` (unmodified — verified before/after)
**Purpose:** expand structural evidence search from PI3Kγ-only to all four
isoforms, quantify actual modeling-relevant coverage, assess the governed
GDR-006 AlphaFold fallback, and determine empirically whether the
structural branch is viable — without prematurely changing the
skip-on-missing missingness architecture.

## Phase 1 — Search results, all four isoforms

| Isoform | UniProt | PDB entries (human) | Distinct ligand CCDs | Resolved InChIKeys | Exact corpus matches | Skeleton matches | Matched corpus compounds | Overlap w/ 1,267-compound modeling set |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| PI3Kα | P42336 | 135 | 95 | 95/95 | 25 | 0 | 25 | **11** |
| PI3Kβ | P42338 | **0** | — | — | — | — | **0** | **0** |
| PI3Kγ | P48736 | 107 | 102 | 102/102 | 66 | 2 | 68 | **28** |
| PI3Kδ | O00329 | 20 | 20 | 20/20 | 14 | 0 | 14 | **2** |

**PI3Kβ finding (verified, not a search failure):** two candidate hits
(`2Y3A`, `4BFR`) surfaced via full-text search but were directly verified
against RCSB polymer-entity metadata — both are **mouse** PIK3CB ortholog
structures (UniProt Q8BTI9), not human (P42338). Excluded as cross-species
evidence, consistent with never blending evidence tiers silently. Human
PIK3CB has genuinely zero PDB structures.

## Phase 2 — Modeling-relevant coverage matrix

### Exactly-N-isoform structural coverage (of 1,267 modeling compounds)

| N isoforms with evidence | 0 | 1 | 2 | 3 | 4 |
|---|---:|---:|---:|---:|---:|
| Compounds | 1,228 | 37 | 2 | **0** | **0** |

### Pairwise usable comparisons (compounds with evidence in BOTH isoforms)

| Pair | α−β | α−γ | α−δ | β−γ | β−δ | γ−δ |
|---|---:|---:|---:|---:|---:|---:|
| Count | 0 | 1 | 1 | 0 | 0 | 0 |

### Scaffold diversity of the 39-compound structurally-supported population

37 distinct scaffold families among 39 compounds — almost no scaffold
repeats. A scaffold-aware train/val/test split on this population would
be nearly degenerate: holding out one scaffold means holding out almost
exactly one compound, making any held-out evaluation statistically
meaningless regardless of the sample-size floor question.

## Phase 3 — Sufficiency reassessment (not applying the 50-floor blindly)

The mandate explicitly asked not to treat the documented 50-compound
floor as universal truth, and to report the underlying population
directly. Doing so:

- **39 compounds total** have any structural evidence overlapping the
  modeling set (up from 28 γ-only) — a real improvement from broadening
  the search, but the marginal gain (11 more) came almost entirely from
  α and δ compounds that **do not overlap** with the γ set (only 1-2
  compounds bridge any two isoforms).
- **Zero compounds have 3- or 4-isoform coverage.** No compound in the
  corpus can support a structural comparison across more than 2 isoforms,
  and even 2-isoform coverage is limited to 2 compounds total.
- **Every pairwise comparison except α−γ and α−δ has zero usable
  compounds.** A β-involving structural comparison (α−β, β−γ, β−δ) is
  categorically impossible — not sparse, impossible, because β has zero
  human structures.
- **Scaffold diversity (37/39) makes a trustworthy split infeasible
  independent of the sample-size floor.** Even if 39 exceeded 50, this
  population could not support a scaffold-held-out evaluation.

**Conclusion: experimental PDB evidence, now covering all four isoforms,
remains insufficient for a meaningful structural-vs-ligand-only
comparative experiment.** This is a stronger, more specific finding than
the prior session's γ-only result — it is not merely "not enough
compounds," it is "not enough compounds, and the ones that exist don't
share scaffolds, and most pairwise comparisons are structurally
impossible regardless of sample size."

## Phase 4 — GDR-006 AlphaFold fallback: inspected, not used (Outcome C)

GDR-006 (accepted, Option B) governs **how** AlphaFold-sourced structural
features are treated once they exist (include with an `is_alphafold`
indicator) — it does not itself generate compound-specific structural
evidence. AlphaFold predicts one static, ligand-agnostic receptor
structure per UniProt accession; it says nothing about where any specific
compound binds. Producing compound-level structural evidence from an
AlphaFold receptor requires **docking**, and per
`docs/governance/STAGE_D_STRUCTURAL_EVIDENCE_STATE.md`: *"All docking
parameters are RULE_MISSING... File GDRs for all docking RULE_MISSING
items before any docking proceeds."*

This is not a scope decision I made — it is a pre-existing, correctly
flagged governance gate from a prior session that this analysis simply
had to respect. Pursuing AlphaFold fallback further this session would
require either inventing docking parameters (explicitly prohibited) or
using a per-isoform receptor-existence flag that is constant across all
compounds for a given isoform and therefore adds no compound-specific
signal to the ligand-keyed model interface — not a meaningful multimodal
feature.

**Outcome: C** — even considering the governed AlphaFold route, compound-
level structural evidence remains insufficient, and this is a hard
architectural fact (docking ungoverned), not a search or effort gap.

## Phase 5 — Missingness architecture: not changed, per instruction

Per explicit instruction, skip-on-missing was **not replaced** this
session. The `StructuralFeatureMode.INDICATOR_ZERO_FILL` alternative
(built and tested in the immediately prior session, before this
mandate's explicit "do not change it yet" instruction arrived) remains
available, tested, and unused for any training run. No architectural
change was made in response to this session's findings; the findings are
reported for a future decision, not acted on unilaterally.

## Summary — what this milestone changed and did not change

| | Before this session | After this session |
|---|---|---|
| Isoforms searched | γ only | α, β, γ, δ (all four) |
| Modeling-set overlap | 28 (γ only) | 39 (any isoform) |
| 3+/4-isoform overlap | not measured | 0 / 0 |
| Pairwise usability | not measured | 2/6 pairs have >0, both =1 |
| Scaffold diversity of supported population | not measured | 37/39 (near-degenerate) |
| Missingness architecture | skip-on-missing | **unchanged** (per instruction) |
| Multimodal training run | not attempted | **not attempted** (data insufficient, quantified) |

## Reproducibility

`analysis/run_all_isoforms_structural_evidence_matching.py` (α/δ vs
modeling set, prior turn), `analysis/run_structural_coverage_matrix.py`
(this turn's exactly-N-isoform, pairwise, and scaffold-diversity
computation). Full data: `docs/governance/STAGE_D_COVERAGE_MATRIX_A4.json`.

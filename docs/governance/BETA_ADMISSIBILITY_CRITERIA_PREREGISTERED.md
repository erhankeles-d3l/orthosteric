# PRE-REGISTERED β-Receptor Homology-Dependent Admissibility Criteria

Frozen BEFORE any comparison between the selected experimental PI3Kβ ortholog
and human AF-P42338 is computed. No threshold below may be adjusted after
seeing results. Grounded in this project's existing Gate-1 logic (RMSD ≤2.0 Å
pose criterion, 3/5 seed pass threshold, hinge H-bond recovery requirement)
and correspondence-quality conventions already established (Gate 0's
anchor-verification discipline).

## Scope

This assessment is **structural and mechanistic only**. It must not read,
load, or reference: selectivity labels, the 24/50 label-informed corpora,
sealed validation labels, α-selective vs other-selective outcomes, B2/B7
performance, motif recurrence, Null A, Null B, ΔAUC, or any downstream
confirmatory result. Enforced by not importing any module from
`orthosteric.data.sealed_labels` or the label-informed corpus files in any
script written for this task.

## Dimension 1 — Global sequence correspondence

| Metric | PASS | CONDITIONAL | FAIL |
|---|---|---|---|
| Global sequence identity (ortholog vs human, full catalytic-domain-overlapping region) | ≥ 90% | 75–90% | < 75% |
| Alignment coverage (fraction of human AF sequence with a non-gap ortholog residue) | ≥ 95% | 85–95% | < 85% |

## Dimension 2 — ATP-pocket residue correspondence

Pocket defined per this project's existing convention: all residues with any heavy atom within 5.0 Å of any heavy atom of the bound ATP-site ligand (charter §2.1 pocket definition, applied to the ortholog's own co-crystallized ligand).

| Metric | PASS | CONDITIONAL | FAIL |
|---|---|---|---|
| Fraction of pocket residues with an identical (conservative or exact) residue at the corresponding human AF position | ≥ 90% | 75–90% | < 75% |
| Fraction of pocket residues with **any** correspondence (not aligned to a gap) | ≥ 95% | 85–95% | < 85% |
| Non-conservative substitutions at the three Gate-0-anchor-equivalent positions (hinge, affinity pocket, specificity pocket) | 0 | 1, with documented functional-class conservation | ≥ 2, or any position loses H-bond/aromatic/charge capability entirely |

## Dimension 3 — Ligand redocking / interaction recovery

Using the ortholog's own co-crystallized ATP-site ligand, redocked into (a) the ortholog itself (self-consistency check, same protocol as this project's existing Gate 1) and (b) the human AF-P42338 model (using AF's own established box, per `run_docking_pilot_four_isoform.py`'s G-loop-centroid convention).

| Metric | PASS | CONDITIONAL | FAIL |
|---|---|---|---|
| Ortholog self-redocking (Gate-1 style): seeds ≤2.0 Å RMSD | ≥ 3/5 | 2/5 | ≤1/5 (ortholog itself would be an inadequate comparator) |
| Hinge H-bond recovered in AF-P42338 redocking, at the human-AF-equivalent position of the ortholog's hinge anchor | Recovered in ≥ 3/5 seeds | Recovered in 1–2/5 seeds | 0/5 |
| Interaction-type overlap (H-bond/hydrophobic/charged categories detected in both receptors for the same ligand, at corresponding positions) | ≥ 70% of ortholog-detected interaction categories also detected in AF at the corresponding position | 40–70% | < 40% |

## Dimension 4 — β representation uncertainty vs. α/γ/δ

Compare the magnitude of β's AF-vs-ortholog discrepancy against the α/γ/δ receptors' own already-known structural uncertainty (Gate-1 RMSD spread; the 6AUD/6XRL completeness-driven sensitivity estimate already established in this project).

| Assessment | PASS | CONDITIONAL | FAIL |
|---|---|---|---|
| β's AF-vs-ortholog pocket discrepancy, relative to the α/γ/δ Gate-1 RMSD spread already observed (0.58–5.36 Å across all validated receptors) | Within the observed α/γ/δ range | Exceeds it but is localized to ≤1 non-anchor pocket region | Exceeds it and is diffuse across the pocket, or localized to an anchor position |

## Composite decision rule (frozen)

- **PASS**: all four dimensions PASS.
- **CONDITIONAL PASS**: no dimension is FAIL, and at least one is CONDITIONAL. The specific limitation(s) driving the CONDITIONAL rating must be named explicitly (e.g., "specificity-pocket region excluded from position-filtered analysis," "AF receptor retained but interaction confidence downgraded one tier").
- **FAIL**: any dimension is FAIL.

No dimension is weighted, averaged, or overridden by strong performance on another dimension — a single FAIL is disqualifying regardless of the other three.

This document is committed and hashed before any comparison in Sections 2–4 above is computed.

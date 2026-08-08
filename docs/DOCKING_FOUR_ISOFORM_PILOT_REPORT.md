# Four-Isoform Cross-Docking Pilot — Real Results

**Date:** 2026-08-06
**Snapshot:** A4, `SNAP-05748f6627ea` (read-only throughout — verified before/after)
**Toolchain:** RDKit 2026.03.5, Meeko 0.7.1, AutoDock Vina 1.2.7 (all installed and verified this session series)

## The central deliverable

Same 5-compound panel, docked against **all four** PI3K isoforms, with PI3Kβ resolved via the governed GDR-006 AlphaFold route rather than declared impossible.

## Receptor panel

| Isoform | Receptor | Source tier | Resolution / pLDDT | Box derivation |
|---|---|---|---|---|
| PI3Kα | 8EXL | EXPERIMENTAL_RECEPTOR (D1) | 1.989 Å | centroid of co-crystallized ligand 799 |
| PI3Kβ | AF-P42338 (AlphaFold v6) | ALPHAFOLD_RECEPTOR (D2) | global mean pLDDT 86.38; local (G-loop) 89.30 | centroid of UniProt-curated G-loop domain (residues 778–784) |
| PI3Kγ | 6AUD | EXPERIMENTAL_RECEPTOR (D1) | 2.015 Å | centroid of co-crystallized ligand BWY |
| PI3Kδ | 6PYR | EXPERIMENTAL_RECEPTOR (D1) | 2.21 Å | centroid of co-crystallized ligand P5J |

**PI3Kβ resolution, in detail:** no human PIK3CB PDB structure exists (confirmed, unchanged). Per SCI0-007's AlphaFold admissibility rules (mean pLDDT ≥ 70; UniProt accession match; only when no admissible PDB exists) and GDR-006 (include with `is_alphafold`/tier indicator), fetched the real AlphaFold model for P42338 — admissible (86.38 ≥ 70). For the box, rather than guessing or using a cross-species structure, I used UniProt's own curated domain annotation for P42338: the "G-loop" (776–784, part of the annotated "PI3K/PI4K catalytic" domain, 772–1053) — a real, independently-curated structural fact, not derived or guessed by this pipeline. AlphaFold's residue numbering matches UniProt canonical numbering exactly, so no alignment step was needed. Local pLDDT at the G-loop (89.30) exceeds the global mean, confirming high confidence exactly where the box is centered.

## Cross-docking result

**20/20 docking runs succeeded (100%). 5/5 compounds have complete four-isoform profiles.**

| Compound | α | β | γ | δ | α−β | α−γ | α−δ | Classification |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| LY294002 | −9.04 | −7.13 | −8.39 | −8.44 | +1.91 | +0.65 | +0.60 | intermediate/ambiguous |
| Quercetin | −8.77 | −6.73 | −8.77 | −8.30 | +2.03 | 0.00 | +0.46 | intermediate/ambiguous |
| Staurosporine-core | −8.87 | −8.49 | −11.26 | −9.26 | +0.38 | −2.38 | −0.39 | **other-isoform-selective** |
| Simple pyrimidine | −7.16 | −6.00 | −7.41 | −7.69 | +1.16 | −0.24 | −0.53 | intermediate/ambiguous |
| Morpholino-quinazoline | −6.99 | −5.45 | −7.50 | −6.46 | +1.55 | −0.51 | +0.54 | intermediate/ambiguous |

(Δdock convention: `dock(X) − dock(α)`; a positive value means α binds more strongly than isoform X, matching the project's `pAct_α − pAct_X` sign convention.)

**Reproducibility verified on both receptor source tiers**: identical scores to 3 decimal places across independent reruns with the same seed, for both an experimental receptor (8EXL) and the AlphaFold receptor (AF-P42338).

**Chemical sanity check**: staurosporine — a well-known broad-spectrum, exceptionally potent kinase inhibitor — scores strongest across the board and shows the largest isoform-differential signal (favoring γ by 2.38 kcal/mol over α), consistent with expectations for a compound whose potency is dominated by hinge-region interactions common across kinases, with the differential driven by pocket-specific contacts.

## What this pilot does and does not establish

**Does establish**: a real, working, reproducible, fully-provenanced four-isoform cross-docking pipeline, including the previously-blocked β isoform via a legitimate governed route. Scores are internally consistent, chemically plausible, and traceable to exact receptor/ligand/engine/seed/box provenance for every record.

**Does not establish**: that Vina score predicts experimental selectivity, that this 5-compound pilot generalizes to production scale, or any calibration between docking score and pAct. No such claim is made. `DockingComplexRecord.evidence_class` is `DOCKING_COMPLEX` on every record, never `EXPERIMENTAL_COMPLEX`, and `is_experimental` is `False` throughout — enforced by the dataclass itself, not just by convention.

## QC

15 tests across two files verify: every compound has all four isoforms represented; β is always `ALPHAFOLD_RECEPTOR`/tier D2, others always `EXPERIMENTAL_RECEPTOR`/tier D1; a compound's four-isoform profile is reconstructable and differential (not identical across isoforms — this is the pipeline's central capability, directly tested); comparative deltas are arithmetically consistent with raw scores; no non-`SUCCESS` record ever carries a score; every `SUCCESS` record carries complete provenance.

## Reproducibility

`analysis/run_docking_pilot.py` (α/γ/δ only, prior session) and `analysis/run_docking_pilot_four_isoform.py` (all four, this session, β resolved). Raw output: `data/structural_evidence/docking_pilot_four_isoform_A4.json` (20 records) and `docking_pilot_four_isoform_comparative_A4.json` (per-compound comparative summary). Source receptor PDBs (including the AlphaFold model): `data/structural_evidence/docking_pilot_receptors/`.

## Reward/penalty architecture — interface established, weights not invented

Per instruction, no numerical reward weights were chosen. What exists now: `DockingComplexRecord.docking_score` (raw, per isoform) and the comparative delta-dock computation (`α − X` per pair) give the exact quantities a future reward function would need — separable α-reward and β/γ/δ-penalty signals — without this session choosing how to combine them. That combination is exactly the kind of "scientifically consequential" decision this session was told not to invent.

## Governance classification

| | Class |
|---|---|
| `DOCKING_COMPLEX` evidence class, `DockingComplexRecord` schema | ENGINEERING CHOICE (this session), consistent with existing evidence-tier conventions |
| AlphaFold admissibility (pLDDT ≥ 70, UniProt match) | GOVERNED (SCI0-007, pre-existing) |
| AlphaFold treatment once features exist | GOVERNED (GDR-006, pre-existing) |
| Box derivation method (ligand centroid / UniProt domain centroid) | ENGINEERING CHOICE, documented per-record |
| Docking engine/version/seed/exhaustiveness | ENGINEERING CHOICE, versioned (`docking_pipeline_v1_vina1.2.7_meeko0.7.1`) |
| Reward/penalty combination weights | NOT DECIDED — explicit remaining decision, not invented |
| Docking-score-to-pAct calibration | NOT DECIDED — explicit remaining decision, not invented |

## Next milestone

**Scale from 5 to ~50–100 chemically diverse compounds drawn from the real A4 corpus** (not synthetic examples), stratified across the selective/non-selective/intermediate categories per the mandate's Phase 7 design, and check whether the resulting four-isoform docking-derived comparative signal correlates directionally with the existing experimental selectivity labels for the subset of compounds where both exist — the first real test of whether this computational layer adds information beyond what's already known experimentally, before any larger production run.

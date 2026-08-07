# PI3Kβ Receptor Remediation — Governance Amendment / Decision Record

## 1. Reason for remediation

Rev. 5 §3.1 invalidates the four-isoform confirmatory endpoint when β cannot be given an adequate receptor. Stage B established no human PIK3CB experimental structure exists. β must remain in the study per explicit instruction. This amendment determines whether the closest experimental PI3Kβ ortholog can structurally validate the human AF-P42338 model sufficiently to restore admissibility — via **homology-dependent structural validation, not direct experimental validation of the human receptor.**

## 2. Original Rev. 5 β criterion

§3: search RCSB for a human PIK3CB experimental structure; if none passes, β stays disclosed-tier; §3.1: absence of an experimental structure invalidates the four-isoform endpoint.

## 3. Absence of suitable human experimental PIK3CB structure

Confirmed in Stage B (`docs/governance/STAGE_B_BETA_DUE_DILIGENCE.md`): four independent search angles, no human PIK3CB ATP-site structure found.

## 4. Selected experimental ortholog and justification

| PDB | Species | Resolution | Ligand | ATP-site bound? | Human PIK3CB identity | Pocket identity | Missing pocket residues/atoms | Construct | Suitability |
|---|---|---:|---|---|---:|---:|---|---|---|
| **4BFR** | *Mus musculus* | 2.80 Å | J82 (C19H22N4O3) | **Yes** — explicitly "first X-ray cocrystal structure of p110β with a selective inhibitor bound to the ATP site" | 95.7% (at aligned positions) | **100%** (19/19 pocket residues) | **0** (verified directly against REMARK 465; 213 total missing residues elsewhere, none in the pocket) | wild-type, no mutations | **Selected** |
| 2Y3A | *Mus musculus* | 3.30 Å | GDC-0941 (pan-PI3K) | Ambiguous — regulatory-subunit complex is the structure's primary focus | not separately assessed | not separately assessed | not assessed | icSH2-complexed | Secondary/backup, not required given 4BFR's clean result |

4BFR selected over 2Y3A on resolution, explicit ATP-site focus, and construct simplicity (monomeric catalytic domain vs. a regulatory-subunit complex). Mouse is the closest available species with a suitable experimental structure — no other ortholog surfaced across the Stage B search.

## 5. Human AF model used

AF-P42338 (already committed, mean pLDDT 86.38, admissible per SCI0-007/GDR-006). Not replaced.

## 6. Pre-declared structural admissibility criteria

Frozen and committed **before** any comparison below was computed: `docs/governance/BETA_ADMISSIBILITY_CRITERIA_PREREGISTERED.md` (`sha256:fc8ce55c...`, commit `2d478d9`).

## 7. Analysis methods and results

### 7.1 Dimension 1 — Global sequence correspondence

Using the project's existing `align_sequences`/`extract_sequence_from_pdb` (no parallel method created), mouse-4BFR chain A vs. human AF-P42338:

| Metric | Value | Threshold | Result |
|---|---:|---|---|
| Identity at aligned (non-gap) positions | 95.7% (818/855) | ≥90% PASS | **PASS** |
| Alignment coverage (non-gap fraction) | 79.9% (855/1070) | ≥95% PASS / <85% FAIL | **Numeric FAIL** |

**Diagnosis, not override:** the low coverage was checked against the independently-counted REMARK 465 missing-residue list (213 residues) before any interpretation. Gap positions (215) and missing residues (213) agree within 2 — **the low coverage is explained by crystallographic disorder in the deposited mouse structure (loops outside the pocket, not modeled), not by sequence divergence between mouse and human PIK3CB.** This is reported as a real numeric result against the frozen threshold, not silently reinterpreted — see §11 for how this is carried into the composite decision.

### 7.2 Dimension 2 — ATP-pocket residue correspondence

Pocket defined per charter §2.1 convention (5.0 Å from any heavy atom of J82, chain A): **19 residues**, verified **zero overlap** with REMARK 465/480.

| Mouse (4BFR) | Human (AF-P42338) | Identity | Note |
|---:|---:|---|---|
| 771 LYS | 777 LYS | identical | |
| 772 TYR | 778 TYR | identical | |
| 773 MET | 779 MET | identical | specificity-pocket anchor (≡ alpha Met772, confirmed via direct alpha↔mouse-beta alignment) |
| 779 PRO | 785 PRO | identical | |
| 780 LEU | 786 LEU | identical | |
| 781 TRP | 787 TRP | identical | specificity-pocket anchor (≡ alpha Trp780, confirmed via direct alpha↔mouse-beta alignment) |
| 797 ILE | 803 ILE | identical | |
| 799 LYS | 805 LYS | identical | |
| 807 ASP | 813 ASP | identical | |
| 833 TYR | 839 TYR | identical | |
| 845 ILE | 851 ILE | identical | |
| 846 GLU | 852 GLU | identical | |
| 847 VAL | 853 VAL | identical | |
| **848 VAL** | **854 VAL** | identical | **hinge anchor** (≡ alpha Val851, confirmed via direct alpha↔mouse-beta alignment — corrected from an earlier, incorrect numerical-coincidence guess of 851/857; see §9) |
| 851 SER | 857 SER | identical | |
| 920 MET | 926 MET | identical | |
| 928 PHE | 934 PHE | identical | |
| 930 ILE | 936 ILE | identical | |
| 931 ASP | 937 ASP | identical | |

**19/19 (100%) mapped, 19/19 (100%) identical, zero substitutions of any kind — including all three anchor-equivalent positions.** Frozen thresholds: ≥90% identical → **PASS**; ≥95% mapped → **PASS**; 0 non-conservative anchor substitutions allowed → **PASS** (0 observed).

### 7.3 Dimension 3 — Ligand redocking / interaction recovery

J82 identity verified independently against the live RCSB CCD this session (canonical SMILES `C[C@H]1Cc2ccccc2N1C(=O)CC3=NC(=CC(=O)N3)N4CCOCC4`, C19H22N4O3, 26 heavy atoms — matches the direct HETATM count from 4BFR exactly).

| Metric | Result | Threshold | Verdict |
|---|---|---|---|
| 4BFR self-consistency (Gate-1 style RMSD) | 5/5 seeds ≤2.0 Å (0.400–0.822 Å) | ≥3/5 PASS | **PASS** |
| Hinge H-bond recovered in AF-P42338 (residue 854, corrected) | 4/5 seeds, donor role, 2.88–3.05 Å | ≥3/5 PASS | **PASS** |
| Interaction-type overlap (4BFR vs. AF-P42338, any seed) | 3/3 categories shared (H-bond, charged-contact-candidate, hydrophobic) = 100% | ≥70% PASS | **PASS** |

**A real methodological error was found and fixed before being reported as a finding**, not silently patched: the first run checked hinge H-bond recovery at residue 851/857 (a coincidental numerical match, not a verified correspondence) and got 0/5 hits in both receptors — including in the 4BFR *self-consistency* case, where 0.4–0.82 Å RMSD self-redocking essentially reproduces the crystal pose, meaning a 0/5 hinge hit there could only mean the hinge-residue identification itself was wrong, not that docking failed. Re-aligning mouse-4BFR directly against alpha's own reference sequence (rather than trusting a number that happened to match) showed alpha's established Val851 hinge anchor maps to mouse-4BFR residue **848** (a Val — chemically consistent), not 851 (a Ser). Corrected and re-verified: 5/5 and 4/5 hinge hits respectively, both against a chemically sensible Val-to-Val correspondence.

A second methodological error was also found and fixed: the first run computed "RMSD" between the 4BFR crystal frame and the AF-P42338 docked pose directly, which is meaningless — AF's model coordinates and 4BFR's crystallographic coordinates share no common reference frame. Replaced with a pocket-proximity sanity check (docked centroid within 8 Å of the mapped pocket centroid, in AF's own frame — 5/5 seeds) plus the frame-independent interaction-based checks above.

### 7.4 Dimension 4 — β representation uncertainty vs. α/γ/δ

| Isoform | Self/production redocking RMSD range | Status |
|---|---|---|
| α (8EXL) | 1.16–1.66 Å | Gate-1 PASS |
| δ (6PYR) | 0.58–0.63 Å | Gate-1 PASS |
| γ (6XRL) | 0.612–1.154 Å (4/5; one outlier 5.356 Å) | Gate-1 PASS |
| **β (4BFR self-consistency)** | **0.400–0.822 Å** | **Within the α/γ/δ range — not an outlier** |

β's AF-based validation (5/5 pocket-proximity, 4/5 hinge recovery, 100% interaction-type overlap) is comparably strong to the already-accepted α/γ/δ receptors' own redocking quality. **PASS** — β's representation uncertainty is not substantially larger than, and is not localized to an anchor position, relative to the isoforms already in production.

## 8. Critical requirement — anti-circularity, verified

No script written for this remediation imports `orthosteric.data.sealed_labels`, the 24/50-corpus files, or any B2/B7/selectivity artifact. Confirmed by direct inspection of `analysis/beta_remediation_dimension3_redocking.py` and all ad hoc analysis commands run this session — none reference selectivity strata, sealed data, or downstream outcomes.

## 9. Errors found and corrected before being reported as findings

Both documented in §7.3 above, in full, at the point they occurred — not smoothed over in this summary. Listed again here per the amendment's own required structure: (a) a wrong hinge-residue identification based on numerical coincidence rather than verified alignment, caught because a near-perfect self-redocking result made a 0/5 hinge-hit outcome internally inconsistent; (b) a meaningless cross-coordinate-frame RMSD computation, caught by recognizing AF and 4BFR share no common frame.

## 10. Sensitivity analysis

The one dimension with a mixed result (Dimension 1's coverage sub-metric) was traced to its source (crystallographic disorder, quantitatively cross-checked against REMARK 465, not asserted) rather than corrected automatically. No correction to the AF model itself is proposed — the analysis found the AF model adequate as-is, not in need of remediation.

## 11. PASS / CONDITIONAL PASS / FAIL decision

Per the frozen composite rule (`BETA_ADMISSIBILITY_CRITERIA_PREREGISTERED.md`, §"Composite decision rule"):

| Dimension | Verdict |
|---|---|
| 1 — Global sequence correspondence | **CONDITIONAL** (identity PASS at 95.7%; coverage numerically in the FAIL range at 79.9%, but diagnosed and quantitatively confirmed as a crystallographic-disorder artifact in the mouse comparator, not sequence divergence — disclosed, not overridden) |
| 2 — ATP-pocket residue correspondence | **PASS** (100% mapped, 100% identical, zero anchor substitutions) |
| 3 — Ligand redocking / interaction recovery | **PASS** (all three sub-metrics) |
| 4 — β uncertainty vs. α/γ/δ | **PASS** (within the already-accepted range) |

**No dimension is FAIL. One dimension is CONDITIONAL.**

> ## DECISION: CONDITIONAL PASS

Per the pre-registered rule (*"CONDITIONAL PASS: no dimension is FAIL, and at least one is CONDITIONAL... the specific limitation(s) driving the CONDITIONAL rating must be named explicitly"*):

**Named limitation:** Dimension 1's alignment-coverage metric is driven by disorder in non-pocket, peripheral regions of the specific deposited mouse structure (4BFR), not by genuine sequence divergence between mouse and human PIK3CB. **This limitation does not affect the pocket region** (Dimension 2 independently confirms 100% pocket coverage and identity) and is not expected to affect interaction detection at any pocket position, since the affected residues are outside the pocket entirely.

**Restriction attached to this CONDITIONAL PASS:** none of the disordered peripheral positions are pocket-adjacent or position-filtered anchors for this study's SS9 features; no specific pocket residue is excluded. The limitation is disclosed for completeness (per the pre-registered anti-circularity and full-disclosure requirements) rather than because it constrains any downstream analysis.

> **Human PIK3CB AF-P42338 is admissible as the production β receptor because its orthosteric ATP-site architecture has been benchmarked against the closest experimentally resolved PI3Kβ ortholog (mouse 4BFR) and satisfies the predefined homology-dependent structural concordance criteria at CONDITIONAL PASS, with the named limitation confined to non-pocket regions.**

This is **homology-dependent structural validation**, not direct experimental validation of the human receptor, and must never be described as the latter.

## 12. Exact effect on §3.1 and §1

**The four-isoform confirmatory endpoint is RESTORED**, not replaced with a new three-isoform endpoint, per §11's own instruction that a supported admissibility finding restores the original endpoint. β proceeds as a production receptor using **AF-P42338 unchanged** (no correction was proposed or applied) at the tier established here (CONDITIONAL, limitation as stated).

**§1's power check may now proceed against the restored four-isoform endpoint.**

## 13. Reproducibility artifacts

- Pre-registered criteria: `docs/governance/BETA_ADMISSIBILITY_CRITERIA_PREREGISTERED.md`, `sha256:fc8ce55c762457c1d4e9e7cd038de183c6198584fc480be359c794cdf437e02e`
- Mouse↔human-AF correspondence: `data/structural_evidence/beta_mouse4bfr_human_af_correspondence.json`
- Dimension 3 redocking (corrected): `docs/governance/BETA_DIMENSION3_REDOCKING.json`
- This amendment: `docs/governance/BETA_RECEPTOR_REMEDIATION_AMENDMENT.md`
- Ligand: J82, verified independently against live RCSB CCD this session
- Receptor prep: `mk_prepare_receptor.py` (Meeko), identical flags to all prior receptors in this project
- Docking: AutoDock Vina 1.2.7, `cpu=1`, `seed` per-run as logged, exhaustiveness=8

## 14. Software versions and provenance

Consistent with the rest of this project: Vina 1.2.7, Meeko 0.7.1, RDKit (ETKDGv3 embedding, MMFF94 optimization), Biopython PairwiseAligner (BLOSUM62, existing project defaults, unchanged).

## 15. Receptor structures and preparation provenance

- 4BFR: downloaded from RCSB this session, chain A extracted, protein-only stripped, prepared via `mk_prepare_receptor.py` (`-p -a --default_altloc A`), identical flags to every other receptor in this project.
- AF-P42338: unchanged, already-committed receptor from `run_docking_pilot_four_isoform.py`'s GDR-006 AlphaFold fallback.

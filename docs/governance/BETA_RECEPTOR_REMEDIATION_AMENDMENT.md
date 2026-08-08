# PI3Kβ Receptor Remediation — Governance Amendment / Decision Record

**Status: FROZEN.** This document, and the decision it records, is not modified after commit except by a new, separately-dated amendment. Nothing in Stage C or later may reinterpret this result.

## 1. Reason for remediation

Rev. 5 §3.1 invalidates the four-isoform confirmatory endpoint when β cannot be given an adequate receptor. Stage B established no human PIK3CB experimental structure exists. β must remain in the study per explicit instruction. This amendment determines whether the closest experimental PI3Kβ ortholog can structurally validate the human AF-P42338 model sufficiently to restore admissibility — via **homology-dependent structural validation, not direct experimental validation of the human receptor.**

## 2. Original β failure (documented, not glossed over)

Per `docs/governance/STAGE_B_BETA_DUE_DILIGENCE.md`: four independent search angles (general, human-specific, recency-focused, cryo-EM-specific) all converged on the same negative finding — no human PIK3CB ATP-site experimental structure exists. Both candidates surfaced (2Y3A, 4BFR) are confirmed *Mus musculus* (mouse), disqualified directly from their RCSB structure pages under the original human-only criterion. This is a genuine structural-biology fact, not a search failure, and is consistent with the documented history that human p110β has long resisted crystallization where the mouse ortholog has not. Per Rev. 5 §3.1's literal rule, this invalidated the four-isoform confirmatory endpoint at the close of Stage B.

## 3. Mouse experimental PDB → human AF structural concordance strategy

Because β must remain in the study, this task asks a different, narrower question than "does a human structure exist": **does the closest available experimental ortholog (mouse) provide sufficient structural support for the already-committed human AlphaFold model (AF-P42338) to serve as an adequate production receptor for this study's specific structural comparisons?** This is homology-dependent structural validation — bounded, falsifiable, pre-registered before any comparison ran — not a claim that the human receptor has been experimentally solved.

## 4. Selected experimental ortholog and justification

| PDB | Species | Resolution | Ligand | ATP-site bound? | Human PIK3CB identity | Pocket identity | Missing pocket residues/atoms | Construct | Suitability |
|---|---|---:|---|---|---:|---:|---|---|---|
| **4BFR** | *Mus musculus* | 2.80 Å | J82 (C19H22N4O3) | **Yes** — explicitly "first X-ray cocrystal structure of p110β with a selective inhibitor bound to the ATP site" | 95.7% (at aligned positions) | **100%** (19/19 pocket residues) | **0** (verified directly against REMARK 465; chain-A-only count is 97, none overlapping the pocket) | wild-type, no mutations | **Selected** |
| 2Y3A | *Mus musculus* | 3.30 Å | GDC-0941 (pan-PI3K) | Ambiguous — regulatory-subunit complex is the structure's primary focus | not separately assessed | not separately assessed | not assessed | icSH2-complexed | Secondary/backup, not required given 4BFR's clean result |

4BFR selected over 2Y3A on resolution, explicit ATP-site focus, and construct simplicity. Mouse is the closest available species with a suitable experimental structure — no other ortholog surfaced across the Stage B search.

## 5. Human AF model used

AF-P42338 (already committed, mean pLDDT 86.38, admissible per SCI0-007/GDR-006). **Not replaced. Not modified in any way as a result of this remediation** (§14).

## 6. Pre-declared structural admissibility criteria

Frozen and committed **before** any comparison below was computed: `docs/governance/BETA_ADMISSIBILITY_CRITERIA_PREREGISTERED.md`, `sha256:fc8ce55c762457c1d4e9e7cd038de183c6198584fc480be359c794cdf437e02e`, committed at `2d478d9`.

## 7. Analysis methods and results

Fully reproducible from `analysis/beta_remediation_dimensions_1_2.py` (Dimensions 1–2) and `analysis/beta_remediation_dimension3_redocking.py` (Dimension 3) — no result below depends on an un-committed calculation.

### 7.1 Dimension 1 — Global sequence correspondence

Using the project's existing `align_sequences`/`extract_sequence_from_pdb` (no parallel method created), mouse-4BFR chain A vs. human AF-P42338:

| Metric | Value | Threshold | Result |
|---|---:|---|---|
| Identity at aligned (non-gap) positions | 95.7% (818/855) | ≥90% PASS | **PASS** |
| Alignment coverage (non-gap fraction) | 79.9% (855/1070) | ≥95% PASS / <85% FAIL | **Numeric FAIL** |

**Diagnosis, not override — corrected during this closure pass, not smoothed over.** An interactive, ad hoc check during the live session counted 213 REMARK 465 missing residues and compared this to 215 gap positions, calling the two "consistent within 2." That count did not filter by chain and combined **both** protein chains in the 4BFR asymmetric unit — an invalid comparator, since the alignment (and the identity/coverage numbers above) concerns chain A alone. Rebuilt as a committed, reproducible script (`beta_remediation_dimensions_1_2.py`), the correct chain-A-only REMARK 465 count is **97**, not 213.

The corrected, more rigorous diagnosis: of the 215 total gap positions, **125 fall outside the mouse crystallization construct's own range (residues 117–1061) entirely** — never part of the expressed protein, not disorder, not divergence — and **90 fall inside the construct range**, consistent with the corrected 97-residue REMARK 465 count within 7 residues. **Neither factor is sequence divergence between mouse and human PIK3CB.** The conclusion is unchanged from the (flawed) original check; the supporting arithmetic is now correct and independently reproducible.

### 7.2 Dimension 2 — ATP-pocket residue correspondence

Pocket defined per charter §2.1 convention (5.0 Å from any heavy atom of J82, chain A): **19 residues**, verified **zero overlap** with the corrected chain-A REMARK 465 list.

| Mouse (4BFR) | Human (AF-P42338) | Identity | Note |
|---:|---:|---|---|
| 771 LYS | 777 LYS | identical | |
| 772 TYR | 778 TYR | identical | |
| **773 MET** | **779 MET** | identical | specificity-pocket anchor (≡ alpha Met772, confirmed via direct alpha↔mouse-beta alignment) |
| 779 PRO | 785 PRO | identical | |
| 780 LEU | 786 LEU | identical | |
| **781 TRP** | **787 TRP** | identical | specificity-pocket anchor (≡ alpha Trp780, confirmed via direct alpha↔mouse-beta alignment) |
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

No script written for this remediation imports `orthosteric.data.sealed_labels`, the 24/50-corpus files, or any B2/B7/selectivity artifact. Confirmed by direct inspection of `analysis/beta_remediation_dimensions_1_2.py`, `analysis/beta_remediation_dimension3_redocking.py`, and all ad hoc analysis commands run this session — none reference selectivity strata, sealed data, or downstream outcomes.

## 9. Errors found and corrected before being reported as findings

Three, in total, all disclosed at the point they occurred rather than smoothed over in this summary:

1. **Wrong hinge-residue identification** (§7.3) — based on a numerical coincidence (851/857) rather than a verified correspondence, caught because a near-perfect self-redocking result made a 0/5 hinge-hit outcome internally inconsistent.
2. **Meaningless cross-coordinate-frame RMSD** (§7.3) — AF-P42338 and 4BFR share no common frame; replaced with pocket-proximity and interaction-based checks.
3. **Invalid REMARK 465 comparator** (§7.1) — the first ad hoc count combined both protein chains in the asymmetric unit; corrected to a chain-A-only, script-verified count of 97, with a full construct-boundary-vs-disorder breakdown replacing the original coincidental "213 ≈ 215" comparison.

## 10. Sensitivity analysis

The one dimension with a mixed result (Dimension 1's coverage sub-metric) was traced to its source twice — once informally during the session, and again rigorously while closing Stage B — rather than corrected automatically. No correction to the AF model itself is proposed — the analysis found the AF model adequate as-is, not in need of remediation.

## 11. PASS / CONDITIONAL PASS / FAIL decision

Per the frozen composite rule (`BETA_ADMISSIBILITY_CRITERIA_PREREGISTERED.md`, §"Composite decision rule"):

| Dimension | Verdict |
|---|---|
| 1 — Global sequence correspondence | **CONDITIONAL** (identity PASS at 95.7%; coverage numerically in the FAIL range at 79.9%, but diagnosed and quantitatively confirmed — twice, the second time rigorously — as a construct-boundary and crystallographic-disorder artifact in the mouse comparator, not sequence divergence — disclosed, not overridden) |
| 2 — ATP-pocket residue correspondence | **PASS** (100% mapped, 100% identical, zero anchor substitutions) |
| 3 — Ligand redocking / interaction recovery | **PASS** (all three sub-metrics) |
| 4 — β uncertainty vs. α/γ/δ | **PASS** (within the already-accepted range) |

**No dimension is FAIL. One dimension is CONDITIONAL.**

### CRITICAL GOVERNANCE STATEMENT (binding)

> Stage-B β remediation restores the pre-registered four-isoform endpoint conditionally. The conditional status is retained because global sequence coverage of the experimental ortholog is 79.9%, below the pre-specified 85% threshold, despite 95.7% sequence identity. Independent residue-level analysis shows that the coverage deficit corresponds to peripheral crystallographic disorder rather than divergence of the evaluated ATP-site pocket. Pocket correspondence, redocking, and structural-consistency criteria pass. This limitation is therefore carried forward as a disclosed representation limitation and is not silently reclassified as a threshold pass.

**Named limitation, and why it is non-disqualifying:** the coverage deficit is confined to non-pocket, peripheral regions of the specific deposited mouse structure — 125 of 215 gap positions fall outside the crystallized construct entirely, and the remaining 90 are ordinary loop disorder consistent with the independently-counted REMARK 465 list. **Dimension 2 independently confirms 100% pocket coverage and identity** — the exact region this study's structural comparisons depend on is untouched by the Dimension 1 limitation. No pocket residue, and no position-filtered anchor this study's future §9 features would use, is affected. The limitation is disclosed for completeness and governance transparency, not because it constrains any downstream analysis.

> **Human PIK3CB AF-P42338 is admissible as the production β receptor because its orthosteric ATP-site architecture has been benchmarked against the closest experimentally resolved PI3Kβ ortholog (mouse 4BFR) and satisfies the predefined homology-dependent structural concordance criteria at CONDITIONAL PASS, with the named limitation confined to non-pocket regions.**

This is **homology-dependent structural validation**, not direct experimental validation of the human receptor, and must never be described as the latter.

## 12. Exact effect on §3.1 and §1 — the freeze

- **The four-isoform confirmatory endpoint is RESTORED**, not replaced with a new three-isoform endpoint, per the task's own instruction that a supported admissibility finding restores the original endpoint.
- **AF-P42338 is retained, unmodified**, as the production β receptor. No correction was proposed or applied to the receptor structure itself — only to this analysis's own supporting arithmetic (§9).
- **This decision is not reinterpreted after Stage C begins.** Any future finding (including any result from the §1 power check, the sealed retrospective set, or the baseline ladder) does not retroactively alter this amendment's PASS/CONDITIONAL/FAIL determination. A different concern about β discovered later requires a **new**, separately-dated amendment — not a revision of this one.
- **§1's power check may now proceed** against the restored four-isoform endpoint.

## 13. Reproducibility artifacts, hashes, and provenance

All hashes computed and recorded in `docs/governance/BETA_REMEDIATION_HASHES.json`, generated at Stage-B closure. Summary:

| Artifact | Path | Role |
|---|---|---|
| Pre-registered criteria | `docs/governance/BETA_ADMISSIBILITY_CRITERIA_PREREGISTERED.md` | Frozen before any comparison (commit `2d478d9`) |
| Mouse↔human sequence correspondence | `data/structural_evidence/beta_mouse4bfr_human_af_correspondence.json` | Dimension 1 raw alignment |
| Dimensions 1+2, reproducible script | `analysis/beta_remediation_dimensions_1_2.py` | Regenerates all Dimension 1/2 numbers from committed inputs only |
| Dimensions 1+2, results | `data/structural_evidence/beta_remediation_dimensions_1_2.json` | Corrected, reproducible output |
| Dimension 3, reproducible script | `analysis/beta_remediation_dimension3_redocking.py` | Regenerates all redocking numbers |
| Dimension 3, results | `docs/governance/BETA_DIMENSION3_REDOCKING.json` | Corrected redocking/hinge/interaction-overlap output |
| This amendment | `docs/governance/BETA_RECEPTOR_REMEDIATION_AMENDMENT.md` | Consolidated decision record |
| Mouse receptor source | `4BFR`, downloaded from RCSB this session | Ligand J82, chain A |
| Human receptor source | `AF-P42338`, already-committed (GDR-006 fallback), unmodified | — |

Ligand identity verified independently against the live RCSB CCD (J82). Software: AutoDock Vina 1.2.7, Meeko 0.7.1, RDKit (ETKDGv3/MMFF94), Biopython PairwiseAligner (BLOSUM62, existing project defaults, unchanged) — all identical to the versions already used throughout this project.

## 14. Receptor structures and preparation provenance

- 4BFR: downloaded from RCSB this session, chain A extracted, protein-only stripped, prepared via `mk_prepare_receptor.py` (`-p -a --default_altloc A`), identical flags to every other receptor in this project.
- AF-P42338: unchanged, already-committed receptor from `run_docking_pilot_four_isoform.py`'s GDR-006 AlphaFold fallback. **Not modified by this remediation in any way.**

---

## STAGE B CLOSURE

> **STAGE B: CONDITIONAL PASS — FOUR-ISOFORM ENDPOINT RESTORED.**

Stage C is authorized only after this amendment, its evidence artifacts, hashes, and validation state are committed as one closure commit (see `docs/governance/BETA_REMEDIATION_HASHES.json` and the closure commit this amendment ships with).

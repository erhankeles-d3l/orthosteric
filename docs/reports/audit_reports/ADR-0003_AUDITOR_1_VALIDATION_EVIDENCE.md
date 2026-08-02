# AUDITOR-1 Validation Evidence: Train/Evaluation Split

**Status:** Evidence prepared | CANDIDATE POLICY — requires Auditor approval

**Search log:**
- Query: "scaffold split vs random split QSAR benchmark leakage molecular machine learning Wallach Sheridan"
  Date: 2026-08-01 | Sources screened: 8 | Selected: 6
- Query: "proteochemometrics multi-target selectivity validation split cross-study confounding kinase panel"
  Date: 2026-08-01 | Sources screened: 8 | Selected: 4

---

## 1. Evidence table — split strategies in molecular ML

| Split type | Leakage mode | Claim supported | Primary evidence | Limitation |
|---|---|---|---|---|
| Random record-level | Compound, scaffold, study-level leakage all present | Assay reproducibility only | Sheridan 2004 (cited in Guo et al.); confirmed by multiple benchmark studies | Overestimates prospective performance; unsuitable as sole criterion |
| Scaffold (Bemis-Murcko) | Scaffold-family leakage; near-analogues with distinct scaffolds can still appear on both sides | Scaffold-level generalization | Guo et al. 2024 (arxiv 2406.00873); Pubs ACS JCIM 2025 (acs.jcim.5c00475) | Shown to *overestimate* VS performance; may underestimate when scaffold diversity is low |
| Scaffold-family / cluster | Reduced analogue leakage | Series-level generalization | Guo et al. 2024; UMAP-based clustering comparison in same study | More demanding; Pearson r ≈ 0.4 between in-distribution and out-of-distribution performance |
| Temporal | Concept drift, prospective simulation | Real-world deployment estimation | Sheridan 2013; Stärk et al. 2022 (cited in arxiv 2504.09481) | Requires timestamps; many datasets lack them |
| Study/assay-level (within-study stratum) | Minimizes systematic assay-effect leakage | Assay-robustness and biological signal separation | ADR-0003 §3 design rationale; Wymann 2010 (proteochemometric double-CV) | Does not measure novel-scaffold generalization |
| Subject-disjoint (for non-molecular analogy) | Group-level leakage | Group-level generalization | Leakage ablation paper (arxiv 2606.24944): +0.039 AUROC inflation from image-level vs subject-disjoint splitting | Molecular analogue: study-disjoint |

## 2. Proteochemometrics-specific evidence

**FACT — directly supported by source:** Kauvar et al. / Ding et al. (BMC Bioinformatics 2010, PMCID PMC2910025) showed that a proteochemometric double cross-validation on 317 kinases yielded P² = 0.67–0.73 for new compound-kinase pairs and P²_kin = 0.65–0.70 for new kinases. This used double cross-validation — an unbiased estimate closely analogous to the within-study evaluation stratum design.

**FACT — directly supported by source:** Lindström et al. (BMC Bioinformatics 2004, PMCID PMC555743) showed that *standard* CV with variable subset selection (no double-CV) yields misleading estimates for proteochemometric models; the double-CV is required for unbiased estimates.

**RECOMMENDATION — not a governance decision:** For a multi-isoform comparative selectivity model, the ADR-0003 §3 design (train on graph, gate on within-study stratum) correctly isolates systematic assay effects. The double-CV structure from proteochemometric literature provides direct precedent for using a high-reliability within-study stratum as the gate evaluation set.

## 3. Six leakage modes, with evidence for each

1. **Record-level:** same measurement in train and eval. **Prevented trivially by construction.** No additional safeguard needed.
2. **Compound-level:** same compound, different study, in both train and eval. **Permitted by the ADR-0003 §3 design as stated.** This is intentional — it enables assay-robustness measurement. Must be stated explicitly in any claims.
3. **Scaffold-family:** near-analogue from same chemical series in train, evaluation compound in eval. **NOT explicitly excluded by ADR-0003 §3.** This is the leakage mode identified in Guo et al. 2024 as causing virtual-screening overestimation.
4. **Study-level:** if a study appears in both training and eval strata because its compounds span both. **Structure of the within-study stratum design should prevent this naturally**, but this should be verified by the Auditor.
5. **Cross-study calibration:** cross-study noise is ~0.5–0.7 log (Constitution §2.4) vs within-study ~0.3 log. Evaluating S2 and S4 on within-study avoids this. **Handled by §3 design.**
6. **Assay-design leakage:** model trained on cross-study data could learn assay-condition patterns rather than biology. **The within-study gate mitigates this for gating criteria specifically.**

## 4. Candidate safeguard

**CANDIDATE POLICY — requires Auditor approval:**
> Exclude compounds from the within-study evaluation stratum at the scaffold-family level from any training data — not merely the record. Require completion reports to state explicitly which generalization claim (assay-robustness vs. novel-scaffold) each S2/S4/S5 figure supports.

Evidence for this safeguard: Guo et al. 2024 demonstrated that scaffold splits overestimate VS performance because near-analogues with distinct scaffolds leak. Scaffold-family exclusion is a stronger variant of this safeguard.

## 5. What remains the Auditor's decision

- Accept the §3 design as-is (assay-robustness claim, explicitly labelled);
- Accept with the scaffold-family exclusion modification;
- Require a fully disjoint split (limits measurable corpus);
- Reject and require re-design.

**Independent Auditor decision still required: YES.**

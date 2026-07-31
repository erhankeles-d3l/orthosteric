# Constitution Amendment Set — v4.6 → v4.7

**Authority:** `ADR-0003` [Scientific] — Public Knowledge-Only Training Policy
**Status:** Proposed. **Not applicable until ADR-0003 is Accepted** by the Independent Scientific Auditor (Constitution §7.7). Until then the Constitution remains at v4.6 and this document has no force.

**Scope.** Eleven loci, located by repository-wide audit. No other section of v4.6 references user-supplied data, homogeneous corpora, or continual learning. Part A is untouched, so §A.8 re-derivation review is **not** triggered.

**Unresolved before acceptance.** `N_c`, `N_b`, `N_w` and the S4 sharpness factor are sealed thresholds and must be set by the Auditor and sealed **before** the Stage 0 audit runs (Constitution §1.4). They are left as `[SEALED AT STAGE 0]` here rather than invented.

---

## A1 · §1.4 — S4 gains a sharpness criterion

**Rationale.** Under a heterogeneous corpus, target σ rises to roughly 0.5–0.7 log. A model reporting wide uncertainty everywhere becomes well-calibrated and uninformative, so ECE alone no longer discriminates.

**Was**
> | S4 | Per-target calibration | Tier 1 | ECE ≤ 0.10 for each of α, β, γ, δ **separately** |

**Becomes**
> | S4a | Per-target calibration | Tier 1 | ECE ≤ 0.10 for each of α, β, γ, δ **separately**, on the within-study evaluation stratum (§2.3) |
> | S4b | Per-target sharpness | Tier 1 | Mean predictive interval width per target ≤ the within-study label noise floor (§3.1 Q4) × `[SEALED AT STAGE 0]`. Calibration achieved by uniformly wide intervals fails |

## A2 · §1.4 — S5 restricted to within-study pairs

**Rationale.** A matched pair spanning two studies can flip on assay variance alone, so cross-study pairs test the corpus rather than the model.

**Was**
> | S5 | MMP selectivity switching | Tier 1 | ≥ 60% correct direction on held-out matched pairs known to flip selectivity |

**Becomes**
> | S5 | MMP selectivity switching | Tier 1 | ≥ 60% correct direction on held-out matched pairs known to flip selectivity, **both members measured within one study and assay** |

## A3 · §1.4 — kill criteria sentence

**Was**
> If Stage 0 yields fewer than 300 four-isoform panel compounds across fewer than 8 scaffold families, the project stops and is redesigned as a physics-only orthosteric study.

**Becomes**
> If the Stage 0 public comparative evidence audit (§3.1 Q1) fails the connectivity thresholds of R1, the project stops and is redesigned as a physics-only orthosteric study.

## A4 · §2.3(1) — corpus definition

**Rationale.** The core amendment. Training uses the connected public evidence graph; the criteria that gate the project are evaluated where the target is trustworthy.

**Was**
> 1. Selectivity computed **only from within-study, within-assay panels.** Cross-study ratios excluded from primary targets; admissible only as low-reliability auxiliary evidence.

**Becomes**
> 1. **Training corpus:** the connected public evidence graph — a content-hashed snapshot of public databases and peer-reviewed literature (ADR-0003 §2). **Evaluation of S2, S4a, S4b and S5:** the **within-study, within-assay stratum** only. Cross-study ratios may inform training with modelled study effects; they are never the ground truth against which a gating criterion is scored. Both strata are reported separately, never pooled.

## A5 · §2.3(2) — ATP concentration as normalization

**Was**
> 2. Every record carries assay ATP concentration, format, substrate, construct. Records lacking ATP concentration are flagged and excluded from primary targets.

**Becomes**
> 2. Every record carries assay ATP concentration, format, substrate, construct, publication or accession, and curation confidence. Where assay [ATP] and the isoform ATP Km are both known, IC50 is converted to Ki by the Cheng–Prusoff relation before use — a normalization, not a learned covariate. Records lacking [ATP] cannot be normalized: they are flagged, excluded from primary targets, and admissible only as low-reliability auxiliary evidence. Assay type, endpoint, organism and publication are recorded as metadata and may serve as covariates or stratification variables; **[ATP] is not among them**, being upstream of the target's definition.

## A6 · §2.4 — two noise floors

**Was**
> - Distinguish epistemic from aleatoric uncertainty. Assay uncertainty is estimable from replicate and inter-lab variance, typically ≥ 0.3 log units. No model may claim precision below the noise floor of its labels.

**Becomes**
> - Distinguish epistemic from aleatoric uncertainty. Assay uncertainty is estimable from replicate and inter-lab variance, typically ≥ 0.3 log units per measurement. **Two floors are recorded and used separately** (§3.1 Q4): the within-study floor, against which S4b sharpness is judged, and the cross-study floor, which applies to any quantity derived from cross-study differences. Because the primary target is a *difference*, cross-study targets carry roughly 0.5–0.7 log. No model may claim precision below the floor applicable to the stratum it is reporting on.

## A7 · §3.1 Q1 — the audit question

**Was**
> 1. Compounds with **all four** Class I isoforms measured **within a single study and assay**, by Bemis–Murcko scaffold family.

**Becomes**
> 1. **Public comparative evidence audit.** Report: total compounds and activity records per isoform; per-isoform coverage and pairwise isoform overlap; **connectivity of the compound × isoform measurement graph** — largest connected component, bridging-compound count, study-cluster structure; the **within-study four-isoform compound count** constituting the evaluation stratum (§2.3); scaffold diversity within the connected component; publication diversity and per-publication concentration; assay-type diversity, the fraction with recorded [ATP] and the fraction normalizable to Ki; duplicate and conflicting measurement rates with the resolution policy applied; and the curation-confidence distribution.

## A8 · §3.1 Q4 — noise floors

**Was**
> 4. Inter-lab reproducibility for compounds in ≥ 3 independent studies — sets the label noise floor and the ceiling on reportable accuracy.

**Becomes**
> 4. Inter-lab reproducibility for compounds in ≥ 3 independent studies. Report **both** the within-study and cross-study noise floors (§2.4). The within-study floor sets the S4b sharpness reference and the ceiling on reportable accuracy for gating criteria.

## A9 · §3.3 — data policies gain the corpus policy

**Insert as the first bullet of §3.3**

> - **Public knowledge only.** Training and evaluation corpora consist exclusively of publicly available scientific knowledge — ChEMBL, BindingDB, PubChem BioAssay, RCSB PDB, and peer-reviewed publications with their supplementary data. User-run assays, laboratory notebooks, unpublished screening, proprietary datasets and continual or online learning are excluded (ADR-0003 §2). Each corpus is a **content-hashed snapshot**; new evidence enters only as a new snapshot producing a new model generation (§0.4). **Prospective validation and E4 evidence (§2.5) may come from newly generated experiment and are never fed back into training.**

## A10 · Part VIII — R1 replaced

**Was**
> | R1 | Insufficient four-isoform panel data | Fatal | Stage 0 | < 300 cmpds / < 8 families |

**Becomes**
> | R1 | Insufficient **connected** public evidence for comparative learning | Fatal | Stage 0 §3.1 Q1 connectivity audit | Largest connected component < `N_c` compounds, **or** bridging compounds < `N_b`, **or** within-study four-isoform compounds < `N_w`, **or** < 8 scaffold families in the connected component. All four sealed before the audit runs |

## A11 · Part VIII — R5 mitigation reference

**Was**
> | R5 | ATP-concentration / assay heterogeneity dominates signal | High | §2.3 within-study-only | Assay covariates explain > 50% of variance |

**Becomes**
> | R5 | ATP-concentration / assay heterogeneity dominates signal | High | §2.3 Cheng–Prusoff normalization; within-study evaluation stratum; modelled study effects | Assay covariates explain > 50% of variance **on the within-study stratum** |

---

## Not amended, and why

| Section | Why it stands |
|---|---|
| Part A | Untouched. The founding hypothesis concerns correspondence between binding sites, not corpus provenance. §A.8 re-derivation is **not** triggered |
| §0.4 Tier 2 barrier | Unaffected. Tier 2 remains public data held out; the query budget is independent of corpus policy |
| §2.5 evidence classes | Unaffected. E4 remains experimental; ADR-0003 clarifies that E4 may be newly generated without entering training |
| §5.4 promotion rules | Unaffected. Design Rules still require an E4 edge, which the three-channel policy preserves |
| §6.3, §9.7 | Wording stands; ADR-0003 §Decision clarifies that Stage 5 experiment is channel 3 |
| §1.4 S2, S3, S6, S7, S8a–c, S9, S10 | Unaffected. S2 survives as a relative comparison (ADR-0003 §3) |

## Application

On acceptance: apply A1–A11, bump to **v4.7**, record the version and authorizing ADR in `docs/GOVERNANCE_VERSIONS.md`, add a row to Appendix B (Defects corrected), and re-verify protocol compatibility ranges (`>=4.6, <5.0` — v4.7 remains inside both).

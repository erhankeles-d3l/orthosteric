# ADR-0003 [Scientific] — Public Knowledge-Only Training Policy

**Status:** Active — computational evidence-adjudication framework adopted under AMENDMENT-ADR-0003-COMPUTATIONAL-ADJUDICATION (commit 7e607e9, Project Owner authorization 2026-08-02).  The mandatory independent human Auditor gate is replaced by a pre-specified deterministic decision procedure implemented in `src/orthosteric/data/adjudication.py` (procedure version 1.0).  ADR-0003 §3–§10 remain unchanged; the amendment governs the *resolution mechanism* only.
**Date:** —
**Supersedes:** nothing
**Numbering note:** assumes `ADR-0001` authorizes Foundation and `ADR-0002` closes the governance-hierarchy and PROJECT_SPECIFICATION items.

---

## Decision

The platform learns exclusively from **publicly available scientific knowledge**. Training corpora are curated, content-hashed snapshots of public databases and peer-reviewed literature. Models are immutable after training; new evidence enters only as a new snapshot producing a new model generation.

Three data channels are defined and are **not interchangeable**:

| Channel | Sources | May influence model parameters? |
|---|---|---|
| **Training** | Public only (§2 below) | Yes |
| **Evaluation** | Public only | No — evaluation never tunes |
| **Prospective validation / E4 evidence** | Public **or** newly generated experiment | **Never.** Feeding these back into training is prohibited |

The third channel is what preserves Constitution §5.4: Design Rule promotion requires an E4 edge, and Stage 5 (§9.7) generates new experimental measurements. A blanket exclusion of non-public data would make E4 unobtainable and Design Rules unreachable. The policy therefore bans *retraining* on new experiment, not the existence of new experiment.

## 1. Rationale

- **Reproducibility.** Any third party can reconstruct the training corpus from a snapshot hash and the public record. A corpus containing proprietary or unpublished data cannot be independently reproduced, which is incompatible with ENG §6.
- **Provenance.** Every activity record traces to a publication or database accession (Constitution §3.3), which the knowledge layer already requires (§5.3).
- **Immutability.** Constitution §0.4 already defines a model generation as frozen architecture + data + hyperparameters. This ADR states the corollary explicitly: there is no prediction → experiment → retraining loop.
- **Feasibility.** The prior policy admitted only compounds with all four Class I isoforms measured within a single study and assay. That is a small fraction of the public record and creates a real risk of triggering R1 on a data-curation artefact rather than a genuine absence of evidence.

## 2. Accepted and rejected sources

**Accepted for training and evaluation:** ChEMBL · BindingDB · PubChem BioAssay · RCSB PDB · peer-reviewed publications and their supplementary data.

**Rejected for training and evaluation:** user-run assays · laboratory notebooks · unpublished screening decks · proprietary or licensed corporate datasets · any continual or online learning from deployment.

**Accepted for prospective validation and E4 evidence only:** newly generated experiment under Constitution §6.3, and independent external benchmarks. These never enter a training corpus.

## 3. Consequences for the criteria — the part that must not be skipped

Relaxing the within-study constraint changes the statistical properties of the learning target, and two success criteria are affected. **This section is the reason this ADR cannot be a documentation-only refactor.**

The target is a *difference*, `pAct_α − pAct_β`. Within a single study and assay, systematic effects (protocol, reagent lot, operator, detection) largely cancel in the difference. Across studies they do not. Inter-lab σ per measurement is typically ≥ 0.3 log (Constitution §2.4), so a cross-study difference carries σ of roughly 0.5–0.7 log, against selectivity signals often of 1–2 log.

| Criterion | Effect | Resolution |
|---|---|---|
| **S2** — beat ligand-only baseline by ≥ 0.3 log RMSE | **Survives.** It is a *relative* comparison; both model and baseline face the same label noise | Unchanged, but evaluated on the within-study stratum (§4) |
| **S4** — ECE ≤ 0.10 per isoform | **Breaks.** With inflated target noise, a model reporting wide uncertainty everywhere is well-calibrated and useless | **Add a sharpness criterion.** Calibration alone is insufficient; mean predictive interval width must be reported alongside ECE and must not exceed the within-study label noise floor by more than a pre-registered factor |
| **S5** — MMP direction | Sensitive: matched pairs spanning studies may flip on assay variance alone | Restrict to within-study matched pairs |
| **§2.4** — no precision below the label noise floor | Now binding at two different floors | Record within-study and cross-study noise floors separately (Stage 0 Q4) |

**Recommended resolution, for the Auditor to accept or reject:**

> **Train on the connected public evidence graph; evaluate the gating criteria on the within-study stratum.**

This unlocks the data volume without treating cross-study differences as trustworthy ground truth for the criteria that decide whether the project proceeds. Within-study records become a high-reliability evaluation stratum rather than the entire corpus.

## 4. ATP concentration is a normalization, not a covariate

All Tier 1 and Tier 2 targets are engaged ATP-competitively and differ in ATP Km, so IC50 depends on assay [ATP] through the Cheng–Prusoff relation.

- Where [ATP] **and** the isoform ATP Km are known, convert IC50 → Ki. This is a principled normalization and is preferred to learning an assay effect.
- Where [ATP] is **unknown**, the record cannot be normalized. It remains excluded from the primary target and is admissible only as low-reliability auxiliary evidence, as Constitution §2.3(2) already provides.

Assay *type*, endpoint, organism, construct, publication and curation confidence are recorded as metadata and may serve as covariates or stratification variables. **[ATP] is not in that group** — it is upstream of the target's definition, not a nuisance variable alongside it.

## 5. R1 is replaced

**Current R1:** insufficient four-isoform panel data — kill trigger under 300 compounds across under 8 scaffold families.

**Replacement R1:** *insufficient connected public evidence for comparative learning.*

The relevant structure is the bipartite measurement graph of compounds × isoforms. Comparative learning needs a large connected component with enough **bridging compounds** — those measured on overlapping isoform subsets across studies — to identify the between-isoform offsets.

Kill trigger, to be finalized at Stage 0 with the Auditor:

- fewer than **N_c** compounds in the largest connected component, **or**
- fewer than **N_b** bridging compounds linking study clusters, **or**
- fewer than **N_w** within-study four-isoform compounds for the evaluation stratum (§3), **or**
- fewer than 8 scaffold families in the connected component

`N_c`, `N_b` and `N_w` are sealed at Stage 0 before the audit is run (Constitution §1.4: thresholds fixed before results are seen). `N_w` is the criterion that most directly replaces the old 300.

## 6. Propagation map — what Steps 2–6 must change

Recorded here so the amendment set is auditable rather than discovered incrementally.

**Constitution**

| Section | Change |
|---|---|
| §2.3(1) | Within-study-only becomes: training on the connected graph; **primary evaluation targets computed within-study** |
| §2.3(2) | Retained. [ATP] absence remains disqualifying for the primary target; add the Cheng–Prusoff normalization (§4) |
| §3.1 Q1 | Four-isoform single-study census → public comparative evidence audit (§7) |
| §3.1 Q4 | Record **two** noise floors: within-study and cross-study |
| §3.3 | Add: training corpus is a content-hashed public snapshot; three-channel policy (Decision) |
| §1.4 S4 | Add the sharpness criterion (§3) |
| §1.4 S5 | Restrict to within-study matched pairs |
| §6.3, §9.7 | Clarify that Stage 5 experiment is channel 3 — E4 evidence, never training |
| Part VIII R1 | Replace per §5 |

**Scientific Protocol** — no invariant is removed. Add: no training corpus contains a non-public record; no prospective or E4 measurement enters a training snapshot.

**Backlog** — `SCI0-004`, `SCI0-008`, `SCI0-011`, `SCI0-015` rewritten; ingestion, harmonization and connectivity-analysis objectives added (§7).

**`data/` package** — sub-modules per source (`chembl/`, `bindingdb/`, `pubchem/`, `pdb/`, `literature/`) plus `harmonization/`, `provenance/`, `snapshots/`. **Harmonization becomes a scientific component**, not plumbing: it performs the Cheng–Prusoff normalization, duplicate resolution and confidence assignment, and therefore requires its own tests and documentation under ENG §2.

**Knowledge layer** — every Interaction Evidence Record carries publication or accession, assay, confidence and evidence class. No record is sourced to "user experiment" except at E4 in channel 3.

**Completion report** — "Experimental arm" becomes "Prospective validation," which may be satisfied by published validation studies or independent external benchmarks **without retraining**.

## 7. Replacement Stage 0 audit questions

`SCI0-008` becomes the **public comparative evidence audit**, answering:

1. Total compounds and activity records per Class I isoform.
2. Coverage per isoform; pairwise isoform overlap per compound.
3. **Connectivity** of the compound × isoform measurement graph: largest component, bridging compound count, study-cluster structure.
4. Within-study four-isoform compound count — the evaluation stratum (§3).
5. Scaffold diversity within the connected component; propeller vs. flat counts.
6. Publication diversity and per-publication record concentration.
7. Assay-type diversity; fraction with recorded [ATP]; fraction normalizable to Ki.
8. Duplicate and conflicting measurement rate; resolution policy.
9. Curation confidence distribution.

## 8. Alternatives considered

| Alternative | Rejected because |
|---|---|
| Retain within-study-only for training | Likely triggers R1 on a curation artefact rather than absent evidence; discards most of the public record |
| Pool all sources with no within-study stratum | Cross-study differences become the gating ground truth at σ ≈ 0.5–0.7 log, below which S2's 0.3 log margin is not credible; violates §2.4 |
| Treat [ATP] as a learned covariate | Discards a known physical relation (Cheng–Prusoff) in favour of estimating it from noisy data |
| Ban all non-public data including Stage 5 | Makes E4 unobtainable and Design Rules unreachable (§5.4) |
| Permit continual learning from deployment | Incompatible with model-generation immutability (§0.4) and the Tier 2 query budget |

## 9. Reversibility and review

**Reversibility:** costly. The corpus definition, harmonization layer and R1 formulation all depend on it; reversing after Stage 0 seals would invalidate the audit.

**Review trigger:** the Stage 0 gate. If the connectivity audit shows the connected component is dominated by a single publication or assay format, the effective evidence base may be narrower than the record count suggests, and the Auditor reconsiders the S4 sharpness factor and the `N_b` threshold before modelling begins.

## 10. Open items requiring Auditor decision before Accepted

1. Accept or reject the train-on-graph / evaluate-within-study split (§3).
2. Set `N_c`, `N_b`, `N_w` and the S4 sharpness factor — **sealed before the audit runs**.
3. Confirm the duplicate-resolution policy (§7.8): median, most-recent, or highest-confidence.
4. Confirm whether BindingDB and PubChem records lacking a primary publication are admissible.

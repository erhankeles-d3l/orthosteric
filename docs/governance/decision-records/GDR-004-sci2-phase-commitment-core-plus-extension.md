# Governance Decision Record GDR-004 — SCI-2 Phase Commitment: Core + Extension

**Category:** Scope governance — phase commitment per Constitution §1.6, §9.0.  
**Status:** Accepted.  
**Date:** 2026-08-06.  
**Decided by:** Project Owner, direct instruction (2026-08-06). Implemented
by the computational pipeline as a governance artefact with no model code.  
**Resolves:** SCI2-001 GGR-001 ("Phase commitment not recorded — BLOCKING").  
**Companion documents:** SCI2-001-specification.md, ADR-0010, Constitution §9.0.

---

## Decision

**Phase commitment = Core + Extension (Phase 1 + Phase 2 in Constitution §9.0 terminology).**

The project is committed to Phase 1 (Core) and Phase 2 (Extension).  
The project is NOT committed to Phase 3 (Full).  
Full scope may not be entered without a separate gate-level Decision Record.

---

## Core scope (Phase 1) — twelve items, all FROZEN

These items are authorized for implementation once the Core-blocking
Stage 0 prerequisites are sealed (see §4 below).

1. Joint comparative representation across PI3Ka/b/g/d. Never four
   independent isoform models. Never compound→activity.
2. Direct pairwise log-selectivity prediction (Delta_alpha_x = pAct_alpha -
   pAct_x). Not absolute-activity-then-subtraction.
3. Symmetric comparative objective: PI3Ka-productive and spared-isoform
   evidence enter the objective with equal weight (Constitution §4.2(2)).
4. Per-target applicability-domain assessment: one AD flag per isoform and
   per selectivity axis, never a single molecule-level flag (§4.2(4)).
5. Proper censored-measurement treatment: inactives modelled with a censored
   likelihood, never discarded or imputed to threshold (§3.3).
6. Calibrated per-target uncertainty: ECE <= 0.10 per isoform (S4a); mean
   interval width per target <= within-study noise floor * [sealed multiplier]
   (S4b). Never aggregated across isoforms (§2.4).
7. Scaffold-aware train/validation/test evaluation: whole scaffolds held out;
   model-selection folds respect the same boundaries (§3.4; SCI1-017).
8. Required degeneracy/ablation battery: pocket shuffle (S3), ligand-only
   ablation (S2), Delta-prediction comparison, MMP switch set (S5),
   scaffold holdout (S1), apo ablation (S6).
9. Evaluation gates S2, S3, S4a, S4b, S6. All pass/fail thresholds from
   the Constitution and Amendment A1; no invented thresholds.
10. Experimental structural evidence overrides governed AlphaFold fallback
    per SCI0-007 rules AF-1 through AF-5. Source preserved throughout.
11. Full provenance and deterministic execution: every ComparativePrediction
    carries training_snapshot_sha, model_generation_id, feature_config_version,
    training_split_id, structural sources per isoform (ADR-0010 §5 inv.2/3).
12. Decision Policy selectivity tiers (Tier A >=10x; Tier B >=30x; Tier C >=100x;
    Tier D >=300x; Tier E >=1000x) remain downstream of model inference and
    MUST NOT be training targets. These belong to policy/. (ADR-0008.)

---

## Extension scope (Phase 2) — three conditional items

These items are authorized for development ONLY after their own prerequisite
governance decisions are explicitly sealed, as specified below.

13. **S7 / cross-family transfer** may be developed where its prerequisites
    are governed: the second family must be sealed at Stage 0 (§3.1 Q16),
    and the sealing must predate Tier 1 modelling (Constitution §9.6). S7
    is NOT committed by this record alone; it becomes available when Q16 is
    sealed and S7 is confirmed live at Stage 0.

14. **S9 mechanistic extension** (explanation interface §4.7, rule extraction
    S9a/S9b/S9c, scrambled-label control) may be developed ONLY after the
    following Stage 0 items are explicitly sealed:
    - S9 reference rule set (§3.6, §3.1 Q13) — sealed and hashed.
    - Empirical S9b precision floor (§3.6.5) — calibrated and recorded.
    - Sealed correspondence ordering and S8c covariate list (§2.1, §1.4.1).
    None of these may be treated as engineering assumptions or invented.

15. **S10 in-silico mutation analysis** (S10a determinant knockout; S10b
    null-mutation control) may be developed ONLY after the following items
    are explicitly preregistered and sealed:
    - S10 mutation sites (§3.1 Q14) — the specific residue positions to mutate.
    - S10 null-control sites (§3.1 Q14) — conserved distal positions for S10b.
    - S10 evaluation protocol — criteria for "abolishes or significantly attenuates."
    The S10b null control is mandatory alongside S10a; S10a alone is
    insufficient (Constitution §1.4 S10b).

---

## Full scope (Phase 3) — NOT committed

The following capabilities are NOT authorized by this record and require
a separate gate-level Decision Record before any implementation begins:

- Knowledge layer (Part V).
- Stage 0.5 mutation-propagation dynamics (§3.2).
- L4 alchemical/FEP mutation to E3 evidence class.
- Prospective experimental test (Stage 5, §9.7).
- Option B election (orthosteric mutant discrimination, §1.3).

---

## Claim ceilings

Per Constitution §9.0, the following claim limits apply to Core+Extension:

**Core (Phase 1) claim ceiling:**
- No determinant claims (no perturbational evidence exists in Phase 1).
- No generality claims (no cross-family transfer in Phase 1).
- No Candidate Determinant claims.
- May claim: comparative selectivity learning with degeneracy controls.

**Extension (Phase 2) claim ceiling:**
- Candidate Determinant claims become available (class E1/E2 evidence).
- Correspondence-floor finding becomes available (S8c).
- Knowledge-extraction claims become available (S9, subject to §14 prerequisites).
- Does NOT support: Design Rules, generality claims, therapeutic framing.
- Does NOT support: Determinant promotion to class E3 or E4.

**Claim ceiling promotion requires a Full scope commitment** (Phase 3):
Design Rules, generality claims, E3/E4 evidence, therapeutic framing.

---

## GGR-002 through GGR-010 disposition (required by task)

Each item from SCI2-001 §14 is classified. No item is silently resolved.

| GGR | Description | Classification | Rationale | SCI2-002 consequence |
|---|---|---|---|---|
| GGR-002a | MMP switch set (§3.1 Q6) | CORPUS_REQUIRED | Real activity data needed; cannot be constructed from synthetic fixtures | Core BLOCKED until sealed |
| GGR-002b | S4b sharpness multiplier (Amendment A1) | CORPUS_REQUIRED | "[SEALED AT STAGE 0]" in the Constitution; must be set by governance once within-study noise floor is characterized from real data | Core S4b gate BLOCKED |
| GGR-002c | Correspondence ordering / S8c covariates (§2.1, §1.4.1) | PHASE_CONDITIONAL | Required for Extension (S8c); NOT required for Core | Blocks Extension Stage 3 only |
| GGR-002d | S9 reference rule set + S9b floor (§3.6, §3.1 Q13) | PHASE_CONDITIONAL | Required for Extension S9 only (item 14 above) | Blocks Extension S9 only |
| GGR-002e | S10 mutation/null-control sites (§3.1 Q14) | PHASE_CONDITIONAL | Required for Extension S10 only (item 15 above) | Blocks Extension S10 only |
| GGR-002f | Second family (§3.1 Q16) | NOT_IN_SCOPE | Requires Full scope; not committed | Does not affect Core+Extension |
| GGR-003 | Loss function | PARTIALLY_GOVERNED + GDR_REQUIRED | Structure: GOVERNED (direct log-ratio, Constitution §4.2(1); symmetric equal weighting, §4.2(2); censored likelihood, §3.3). Specific parametric form, pAct_alpha/Delta joint-vs-separate optimization, and INDETERMINATE handling in the loss: GDR_REQUIRED before first training run | Structured model code may proceed; no training until residual GDR is filed |
| GGR-004 | Applicability domain algorithm | GDR_REQUIRED | Different AD algorithms (k-NN, conformal, Mahalanobis) have materially different S8b behaviour and leakage implications (conformal calibration set); scientific meaning changes | AD implementation BLOCKED |
| GGR-005 | AlphaFold model-level treatment | GDR_REQUIRED | Option A (exclude from training) vs B (include with source indicator) affects which compounds can be predicted and what the model learns; scientifically consequential | AlphaFold handling code BLOCKED |
| GGR-006 | Missingness encoding | ENGINEERING_CHOICE | Ordinal + boolean UNAVAILABLE mask preserves UNAVAILABLE != ABSENT without changing scientific meaning; consistent with Constitution §2.2, §4.2(5); working assumption in SCI2-001 §6 is confirmed here | May proceed |
| GGR-007 | Uncertainty representation | GDR_REQUIRED | S4a/S4b compliance depends on calibration quality of the chosen method; conformal prediction requires a calibration set (leakage); deep ensemble has training-cost implications | Uncertainty module BLOCKED |
| GGR-008 | Censored likelihood form | GDR_REQUIRED | Constitution §3.3 mandates the category ("censored likelihood") but not the parametric form; task instruction explicitly prohibits choosing without governance | Censored likelihood BLOCKED |
| GGR-009 | Model selection / validation protocol | ENGINEERING_CHOICE | Constitution §3.4 governs scaffold-aware splitting; the specific fold structure (scaffold-aware k-fold on training families, held-out test set) is an implementation of that requirement without altering its scientific meaning | May proceed; protocol documented in Implementation Spec |
| GGR-010 | Dual-inhibitor census | CORPUS_REQUIRED | Requires real data collection from the corpus (ChEMBL/BindingDB/PubChem mTOR records) to identify dual PI3K/mTOR compounds; cannot be resolved by engineering decision | Extension S8a/S8c BLOCKED until census performed |


---

## Items still requiring GDR (summary)

The following GDRs are required before the indicated capabilities can be implemented:

| GDR needed | Governs | Blocks |
|---|---|---|
| GDR-005 (to be filed) | AD algorithm (GGR-004) | Per-target AD implementation |
| GDR-006 (to be filed) | AlphaFold model-level treatment (GGR-005) | AlphaFold handling in model |
| GDR-007 (to be filed) | Uncertainty representation (GGR-007) | Uncertainty module |
| GDR-008 (to be filed) | Censored likelihood form (GGR-008) | Loss function (censored term) |
| GDR-009 (to be filed) | Loss function specific form + pAct_alpha/Delta weighting (GGR-003 residual) | First training run |

Filing these GDRs is the responsibility of the Project Owner. The computational
pipeline may prepare draft proposals but may not file them unilaterally.

---

## Items requiring real corpus evidence

| Item | What is needed | When needed |
|---|---|---|
| GGR-002a MMP switch set | Activity data for matched molecular pairs known to flip selectivity | Before Core Stage 2 (SCI-2 model evaluation) |
| GGR-002b S4b sharpness multiplier | Within-study noise floor from actual corpus (Stage 0 Q4) | Before Core S4b gate evaluation |
| GGR-010 Dual-inhibitor census | ChEMBL/BindingDB/PubChem search for dual PI3K/mTOR inhibitors | Before Extension S8a/S8c evaluation |

---

## Items Claude may decide autonomously

| Item | Decision | Governing basis |
|---|---|---|
| GGR-006 missingness encoding | Ordinal integer (0=UNAVAILABLE/NOT_APPLICABLE, 1=ABSENT, 2=CANDIDATE, 3=OBSERVED) + boolean UNAVAILABLE mask | Engineering implementation of Constitution §2.2, §4.2(5); preserves UNAVAILABLE != ABSENT without changing scientific meaning |
| GGR-009 validation protocol structure | Scaffold-aware k-fold: training families used for k-fold cross-validation; whole scaffold families held out for test; no test-set leakage | Engineering implementation of Constitution §3.4 scaffold-aware splitting requirement |

---

## Relationship to ADR-0010 and SCI2-001

**ADR-0010** defines the Phase C architecture and import-layer order. It is
unaffected by this record. The learning/ package remains below eval/ and
interpretation/ in the layer order.

**SCI2-001** (docs/specifications/SCI2-001-specification.md) identified GGR-001
through GGR-010. This record resolves GGR-001 and classifies GGR-002 through
GGR-010. SCI2-001 remains the authoritative specification; this record amends
its blocking-items table for GGR-001 and the classifications in §14.

---

## Authorization point for SCI2-002

SCI2-002 (the first SCI-2 implementation milestone) becomes authorized when:

1. This GDR-004 is accepted. [Accepted by this record — 2026-08-06]
2. GGR-002a (MMP switch set) is sealed with real corpus data.
3. GGR-002b (S4b sharpness multiplier) is sealed with real corpus data.
4. GDR-005 (AD algorithm) is filed and accepted.
5. GDR-006 (AlphaFold treatment) is filed and accepted.
6. GDR-007 (uncertainty representation) is filed and accepted.
7. GDR-008 (censored likelihood form) is filed and accepted.
8. GDR-009 (loss function specific form) is filed and accepted.

Items 2--8 must be completed before any model training code is written.
Model architecture code (defining ComparativeInput/ComparativePrediction
consumption, interface compliance verification) may proceed once item 1
is complete, provided it introduces no training implementation.

**The next authorized milestone is SCI2-002 scoping and task definition**,
to be created once items 2--8 are resolved. SCI2-002 must be defined in
IMPLEMENTATION_BACKLOG.md by a separate authorized task.

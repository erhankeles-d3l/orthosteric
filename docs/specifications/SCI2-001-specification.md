# SCI2-001 — SCI-2 Comparative Representation Learning Specification

**Status:** In Progress — SCI2-001 planning milestone  
**Date:** 2026-08-06  
**Authority:** Constitution v4.6 Parts I, IV; ADR-0010; SCI0-007 amendment;
Amendment Set v4.7; ADR-0008; GDR-001/002/003  
**Supersedes:** SCI-2 backlog skeleton in `IMPLEMENTATION_BACKLOG.md`

---

## 0. Executive summary and blocking items

SCI-2 is the comparative representation learning stage. Its central
scientific obligation (FROZEN — Constitution §4.1, §4.2, ADR-0010 §5 inv.4):

```
compound
+ PI3Ka structural evidence
+ PI3Kb structural evidence
+ PI3Kg structural evidence
+ PI3Kd structural evidence
        |
JOINT COMPARATIVE REPRESENTATION
        |
SELECTIVITY PREDICTION
        |
UNCERTAINTY / APPLICABILITY DOMAIN
        |
SCI-3 MECHANISTIC INTERPRETATION
```

**SCI-2 implementation is currently BLOCKED.** Stage 0 pre-registration
items required before any model code may be written (Constitution §3.1, §9.1, §9.3):

| Item | Status |
|---|---|
| Phase commitment (Core / Extension / Full) | NOT RECORDED — GOVERNANCE_DECISION_REQUIRED |
| Correspondence ordering for Tier 2 (S8c) | Not sealed — Constitution §2.1, §1.4.1 |
| S8c covariate list | Not sealed |
| S9 reference rule set | Not sealed — Constitution §3.6 |
| Second family for S7 | Not sealed — Constitution §3.1 Q16 |
| MMP switch set | Not sealed — Constitution §3.1 Q6 |
| S10 mutation/null-control sites | Not sealed (Phase 2 dependency) |
| S4b sharpness threshold multiplier | "[SEALED AT STAGE 0]" in Amendment A1; not sealed |
| SCI1-022 gate on real data | Not yet executed |
| Dual-inhibitor census | Not yet performed — Constitution §3.5, §3.1 Q12 |

SCI2-001 maps these gaps, freezes what is already governed, and documents
the remaining decisions legibly. It does not resolve GOVERNANCE_DECISION_REQUIRED
items unilaterally.


## 1. SCI-2 dependency map

```
SCI0 -- immutable public evidence corpus (content-hashed snapshot)
  data/snapshots/   -- SnapshotManifest, content SHA
  data/activity.py  -- ActivityRecord with full provenance
  data/strata.py    -- WithinStudyStratum (§2.3(1))
  data/graph.py     -- MeasurementGraph (connectivity for R1)
        |
SCI0 harmonization
  data/harmonization/ -- chem standardizer, scaffold, deduplicator
        |
SCI1 pocket representation
  pocket/_structure_record.py  -- StructureRecord, StructureProvenance
  pocket/_pocket_definition.py -- PocketResidueSet (ligand-ensemble union)
  pocket/_residue_mapping.py   -- ResidueCorrespondenceTable (Trp780/Met772/859)
  pocket/_rotamer_state.py     -- RotamerState (included in pocket, not noise)
  pocket/_pocket_geometry.py   -- PocketGeometry
        |
SCI1 features
  features/_interaction_fingerprint.py  -- InteractionFingerprint
  features/_contact_map.py              -- PocketContactMap
  features/_structural_graph.py         -- PocketGraph
  features/_pocket_descriptor.py        -- PocketDescriptor
  features/_comparative_feature.py      -- ComparativeFeatureSet (joint 4-isoform)
  features/_md_interface.py             -- MDFeaturePlaceholder (NOT_COMPUTED Phase 3)
  features/_feature_config.py           -- FeatureConfig (all RULE_MISSING)
  features/_pipeline.py                 -- FeaturePipelineResult (Path A entry point)
        |
SCI1 evaluation scaffold
  eval/_metrics.py          -- log_selectivity_ratio, per_target_rmse
  eval/_calibration.py      -- ece_per_target (per target; never aggregated)
  eval/_uncertainty.py      -- compose_selectivity_confidence (conjunction, not min)
  eval/_productive_binding.py -- BindingClassification (INDETERMINATE is distinct)
  eval/_splitting.py        -- scaffold_split (whole scaffold held out)
  eval/_stratum.py          -- load_within_study_stratum (§2.3(1))
  eval/_baselines.py        -- LigandOnlyBaseline, NNBaseline, PCMBaseline
  eval/_gate.py             -- s1_gate_evaluation (GO/STOP/INSUFFICIENT_DATA)
        |
SCI-2 comparative representation learning  [THIS SPEC]
  learning/                 -- ComparativeInput, ComparativePrediction, et al.
        |
SCI-3 mechanistic interpretation
  interpretation/           -- attribution, counterfactuals, discrete rules
        |
eval/ (criteria scoring: S2, S3, S4, S6)
policy/ (Decision Policy: potency floors, selectivity tiers)
generation/ (deferred until SCI-3 complete)
```

---

## 2. The comparative learning invariant (FROZEN)

**Source:** Constitution §4.1, §4.2(1), ADR-0010 §5 invariant 4.

SCI-2 MUST implement: `compound + alpha + beta + gamma + delta -> joint representation -> selectivity`

SCI-2 MUST NOT implement:
- `compound -> activity` (scalar predictor)
- `compound + isoform -> activity` (four independent models)

**Parameter sharing alone does NOT satisfy this requirement** (Constitution §A.4).
Four encoders with shared weights consuming one isoform each independently is
not comparative learning. The comparative relationship must be representable
within the forward pass, not only at the output.

---

## 3. The learning target (FROZEN)

**Source:** Constitution §4.1, §2.3(4).

```
S_1 = (pAct_alpha, Delta_alpha_beta, Delta_alpha_gamma, Delta_alpha_delta) +/- CI
  where Delta_alpha_x = pAct_alpha - pAct_x    (positive = alpha-selective)
```

Per-isoform binding classification: PRODUCTIVE / NON_PRODUCTIVE / INDETERMINATE.
INDETERMINATE contributes ZERO to selectivity claims (Constitution §2.2).

Training corpus: connected public evidence graph.
Evaluation of S2, S4a, S4b, S5: within-study, within-assay stratum only.
The two are reported separately; never pooled (Amendment A4).

Tier 2 ratios are predicted but NEVER trained on (Constitution §4.1).


---

## 4. Architecture invariants

### 4.1 Path A (FROZEN) — Constitution §4.6

The model input interface MUST accept any ATP site without alignment to
Class I residue positions. `features/_pipeline.py` is the Path A entry point.
Path B requires a gate-level Decision Record (§4.6). Not elected here.

### 4.2 Symmetric evidence (FROZEN) — Constitution §4.2(2)

Alpha-productive and beta/gamma/delta-sparing evidence enter the objective
with equal weight. NOT: affinity model + selectivity penalty.

### 4.3 Pocket conformational states as inputs (FROZEN) — Constitution §4.2(3), C6

Rotamer states are model inputs. Apo-structures alone are prohibited for
pocket definition (§2.1 ligand-ensemble union).

### 4.4 Per-target applicability domain (FROZEN architecture; algorithm RULE_MISSING)

**Source:** Constitution §4.2(4). "Target" = per isoform (alpha, beta, gamma, delta).
A single molecule-level AD is non-compliant. AD algorithm: GOVERNANCE_DECISION_REQUIRED (GGR-004).

### 4.5 Indeterminate expressibility (FROZEN) — Constitution §4.2(5), §2.2

The model MUST output "I don't know" per target. INDETERMINATE carries no
sparing information and contributes ZERO to selectivity claims.

### 4.6 Evidence independence (FROZEN) — Constitution §4.2(6)

Repeated observations from one method count as one observation.

### 4.7 Experimental > AlphaFold (FROZEN) — ADR-0010 §5 inv.1; SCI0-007

Experimental PDB overrides AlphaFold (rules AF-1 through AF-5).
AlphaFold source survives all transformations as `StructureSource.ALPHAFOLD`.
Model-level treatment: GOVERNANCE_DECISION_REQUIRED (GGR-005).

### 4.8 Provenance preservation (FROZEN) — ADR-0010 §5 inv.2

Every `ComparativePrediction` MUST carry: training_snapshot_sha (SCI0-011
content hash), feature_config_version, model_generation_id (frozen:
architecture + training data + hyperparameters), training_split_id, and
structural source per isoform (PDB ID or AlphaFold accession).

### 4.9 Determinism (FROZEN) — ADR-0010 §5 inv.3

Same input + configuration + software -> same output hash.
Random seeds forbidden in model evaluation; permitted in training only when
seeded and recorded in the model generation record.

### 4.10 No learned pocket detection (FROZEN) — ADR-0010 §5 inv.6; Constitution §2.1

Pocket boundaries come from `pocket/_pocket_definition.py` (ligand-ensemble
union) and must not be modified or replaced by model predictions.

---

## 5. Learning target formulation

### 5.1 Formulation (FROZEN) — Constitution §4.2(1)

Direct log-ratio prediction from joint 4-isoform representation:

```
Delta_alpha_beta  = model_output_1(compound, alpha, beta, gamma, delta)
Delta_alpha_gamma = model_output_2(compound, alpha, beta, gamma, delta)
Delta_alpha_delta = model_output_3(compound, alpha, beta, gamma, delta)
```

Not: predict absolute potencies per isoform and subtract.

### 5.2 Loss function (GOVERNANCE_DECISION_REQUIRED — GGR-003)

Constrained by §4.2(1)(2) and §3.3 but not fully specified. Exact parametric
form, weighting between axes, treatment of INDETERMINATE in the loss, and
treatment of pAct_alpha vs Delta axes jointly or separately are all unresolved.

### 5.3 Censored measurement treatment (GOVERNANCE_DECISION_REQUIRED — GGR-008)

Constitution §3.3: "modelled with a censored likelihood -- never discarded,
never imputed to the threshold." The parametric form (Tobit, interval-censored,
other) is not governed. Do not choose without a Decision Record.

---

## 6. Missingness semantics (PARTIALLY FROZEN)

**Source:** Constitution §4.2(5), §2.2.

| State | Ordinal | Model meaning |
|---|---|---|
| OBSERVED | 3 | Positive evidence present |
| CANDIDATE (RULE_MISSING) | 2 | Geometry present; threshold ungoverned |
| ABSENT | 1 | Structure available; interaction not present |
| UNAVAILABLE | 0 | Structure unavailable; NOT negative evidence |
| NOT_APPLICABLE | 0 | Chemistry incompatible; NOT negative evidence |

FROZEN: UNAVAILABLE and NOT_APPLICABLE MUST NOT be treated as equivalent
to ABSENT. INDETERMINATE binding MUST NOT contribute to selectivity claims.

Missingness encoding into model tensor: GOVERNANCE_DECISION_REQUIRED (GGR-006).
Working assumption (engineering, reversible): ordinal integer + boolean
UNAVAILABLE mask. This preserves the distinction without altering scientific meaning.


---

## 7. Degeneracy battery specification

**Source:** Constitution §4.3.

### T1 — Pocket shuffle (S3, HARD GATE)
- Perturbation: permute isoform pocket features at evaluation; compound unchanged
- Invariant: RMSE degrades >= 0.3 log units
- Threshold: RULE_AVAILABLE (Constitution §1.4 S3)
- Kill criterion: S3 failure means comparative learning did not occur

### T2 — Ligand-only ablation (S2, HARD GATE)
- Perturbation: train/evaluate with no structural features
- Invariant: full model beats ligand-only by >= 0.3 log RMSE
- Threshold: RULE_AVAILABLE (Constitution §1.4 S2)
- Kill criterion: S2 failure means the learned component is unjustified

### T3 — Delta-prediction test (diagnostic)
- Perturbation: compare direct log-ratio vs. independent-then-subtract
- Invariant: direct prediction is better calibrated (§4.2(1))
- Threshold: RULE_MISSING — report direction and effect size only
- Not a hard gate; governs architectural justification

### T4 — MMP selectivity switch set (S5)
- Perturbation: held-out within-study MMP pairs known to flip selectivity
- Invariant: >= 60% correct direction
- Threshold: RULE_AVAILABLE (Constitution §1.4 S5, Amendment A2)
- DEPENDENCY: MMP switch set NOT YET SEALED (Stage 0 §3.1 Q6)

### T5 — Scaffold-family holdout (S1)
- Perturbation: withhold entire families; retrain; check determinant recovery
- Invariant: position-859 determinant recovered in >= 4 of 5 held-out families
- Threshold: RULE_AVAILABLE (Constitution §1.4 S1)
- DEPENDENCY: Phase 2 (explanation interface) must be committed

### T6 — Apo ablation (S6, HARD GATE)
- Perturbation: remove induced-pocket and rotamer-state features
- Invariant: propeller-compound beta/delta ranking collapses
- Threshold: RULE_AVAILABLE structure; collapse = drops below ligand-only
- Kill criterion: S6 failure means C6 is violated; pocket is apo-degenerate

### T7 — Scrambled-label control (S9c)
- Perturbation: retrain on permuted selectivity labels; run full explanation pipeline
- Invariant: chance-level recall against sealed reference rule set
- Gate: kills S9a/S9b if it fails (Constitution §1.4 S9c)
- DEPENDENCY: S9 rule set not sealed; Phase 2 must be committed

### T8 — In-silico mutation / S10 (PHASE 2 ONLY, NOT COMMITTED)
- Do not implement until Phase 2 is recorded as committed
- S10b null control required alongside S10a (Constitution §1.4 S10b)

---

## 8. Gate definitions: S2, S3, S4, S6

| Gate | Metric | Threshold | Source | Status |
|---|---|---|---|---|
| S2 | log-RMSE improvement over ligand-only, within-study stratum | >= 0.3 log units | RULE_AVAILABLE: Constitution §1.4 S2 | Awaits real data |
| S3 | RMSE degradation under pocket shuffle | >= 0.3 log RMSE | RULE_AVAILABLE: Constitution §1.4 S3 | Awaits model |
| S4a | ECE per target (alpha, beta, gamma, delta separately) | ECE <= 0.10 | RULE_AVAILABLE: §1.4 S4a (Amendment A1) | Awaits model |
| S4b | Mean interval width per target <= noise floor * [multiplier] | SEALED AT STAGE 0 | Multiplier NOT YET SEALED | Blocked |
| S6 | Propeller-compound beta/delta ranking, apo-ablation | Collapses under apo-ablation | RULE_AVAILABLE: Constitution §1.4 S6 | Awaits model |

**S4b is structurally sound but numerically incomplete.** The sharpness
multiplier is "[SEALED AT STAGE 0]" in Amendment A1 and cannot be
manufactured. S4b gates only after Stage 0 completion.

---

## 9. Leakage control contract

| Path | Control | Status |
|---|---|---|
| Scaffold leakage | scaffold_split (SCI1-017): whole scaffold held out | Implemented |
| Within-study / cross-study | Within-study stratum for S2, S4a, S4b, S5 | Implemented |
| Tier 2 barrier | import-linter contract 3; data/tier2_gate.py | Implemented |
| Model selection | Scaffold-aware validation fold | GOVERNANCE_DECISION_REQUIRED (GGR-009) |
| Hyperparameter tuning | Training + validation only | GOVERNANCE_DECISION_REQUIRED (GGR-009) |
| Preprocessing normalization | Statistics from training data only | RULE_MISSING — no normalization currently specified |
| Dual-inhibitor (mTOR Tier 2) | Tier 2 stratified: known dual agents vs others | NOT YET IMPLEMENTED (§3.5) |
| Structural-state leakage | Conformational state not inferred from activity labels | RULE_MISSING |

---

## 10. AlphaFold handling in SCI-2

FROZEN (SCI0-007, rules AF-1 through AF-5):
- AlphaFold only when no admissible experimental PDB exists.
- Source always labeled StructureSource.ALPHAFOLD throughout.
- AlphaFold-derived pocket definitions prohibited (no bound ligand).
- AlphaFold features must not be presented as experimental evidence.

Model-level treatment: GOVERNANCE_DECISION_REQUIRED (GGR-005).
Options: (A) exclude from training; (B) include with source indicator.
Option (C) downweighting requires an invented factor — prohibited.

---

## 11. Selectivity tiers and Decision Policy (FROZEN separation)

The 10x/30x/100x/300x/1000x tiers are Decision Policy Layer parameters
(ADR-0008). They MUST NOT appear in SCI-2 loss functions, training targets,
or evaluation criteria (S2, S3, S4, S6 use RMSE/ECE, not tier counts).
This separation is enforced by the import-layer order (policy/ above learning/).

---

## 12. Uncertainty requirements

FROZEN (Constitution §2.4, Amendment A6):
- Uncertainty is per-target; never aggregated across isoforms.
- Joint selectivity confidence = conjunction product, NOT min() (§2.4).
- Two noise floors: within-study and cross-study (Amendment A6).
- S4b sharpness: mean interval width <= noise floor * [SEALED AT STAGE 0].
- No precision claim below the applicable stratum's noise floor.

Uncertainty representation: GOVERNANCE_DECISION_REQUIRED (GGR-007).


---

## 13. Phase commitment and scope (GOVERNANCE_DECISION_REQUIRED — BLOCKING)

**Source:** Constitution §9.0, §1.6. Phase commitment NOT YET RECORDED.

| Phase | Scope additions | Claim ceiling |
|---|---|---|
| Phase 1 — Core | Comparative model + degeneracy battery + S1/S2/S3/S4a/S6 | No determinant or generality claims |
| Phase 2 — Extension | + Explanation interface (§4.7), S9 rule extraction, S10, Tier 2 | Candidate Determinant; correspondence-floor |
| Phase 3 — Full | + Knowledge layer, Stage 0.5 dynamics, L4 alchemical, S7 transfer | Design Rules; generality claims |

Until phase commitment is recorded:
- S10 in-silico mutation: NOT IN SCOPE
- S9 scrambled-label control: NOT IN SCOPE
- §4.7 explanation interface: NOT IN SCOPE
- S7 cross-family transfer: NOT IN SCOPE

---

## 14. Governance gap report (GGR-001 through GGR-010)

### GGR-001: Phase commitment not recorded (BLOCKING)

Decision: Core / Core+Extension / Full?  
Required: Constitution §1.6, §9.0 — determines scope and claim ceilings.  
Status: NOT RECORDED. Record as a Decision Record before any model code.

### GGR-002: Stage 0 pre-registration incomplete (BLOCKING)

Multiple Stage 0 items unsealed (§3.1 Q6, Q11, Q12, Q13, Q14, Q16;
sharpness multiplier; S9 rule set). Constitution §9.1 blocks modelling.
Action: Audit Phase 1 prerequisites; seal those items.

### GGR-003: Loss function not specified

Constrained by §4.2(1)(2) and §3.3 but not fully determined.
Required: exact parametric form, weighting between axes, treatment of
INDETERMINATE in the loss, censored term.

### GGR-004: Applicability domain algorithm not specified

Per-target AD required by §4.2(4) but algorithm not governed.
Required before AD implementation. Test-set AD calibration risks leakage.

### GGR-005: AlphaFold model-level treatment

SCI0-007 governs use conditions; model representation is not governed.
Options: (A) exclude from training — AlphaFold isoforms marked UNAVAILABLE;
(B) include with source indicator. Option (C) downweighting requires an
invented weight — prohibited. Record a Decision Record.

### GGR-006: Missingness encoding not specified

Five-state vocabulary must enter the model tensor preserving UNAVAILABLE != ABSENT.
Working assumption (reversible): ordinal + boolean UNAVAILABLE mask.
Confirm in Implementation Specification before training.

### GGR-007: Uncertainty representation not specified

S4a/S4b require calibrated per-target confidence.
Options: Gaussian CI, deep ensemble, conformal prediction, Monte Carlo dropout.
Each has different calibration properties and S4b testability implications.

### GGR-008: Censored measurement treatment

Constitution §3.3 mandates censored likelihood but does not specify form.
Options: Tobit-1 (left/right censored normal), interval-censored, other.
Record as a Decision Record with statistical justification.

### GGR-009: Model selection and validation protocol

Test-set model selection contaminates S2/S4. The protocol must precede training
and be specified as a leakage-control artefact in the Implementation Specification.
Must be scaffold-aware (§3.4) and must not permit test-set selection.

### GGR-010: Dual-inhibitor stratification for mTOR Tier 2

Constitution §3.5 mandates dual-inhibitor census. mTOR Tier 2 evaluation
must be stratified (known dual agents vs. others). Census not yet performed.

---

## 15. Explicitly prohibited SCI-2 behaviors

SCI-2 MUST NOT:
1. Train a compound -> activity model or four independent isoform models.
2. Treat UNAVAILABLE as zero (same as ABSENT).
3. Treat INDETERMINATE as weak evidence of sparing.
4. Use Tier 2 data for training, model selection, or feature engineering.
5. Use test-set performance for model selection or hyperparameter tuning.
6. Use selectivity tiers (10x/30x/100x/300x/1000x) as training targets.
7. Use Decision Policy thresholds in loss functions.
8. Claim mechanistic causality — that belongs to SCI-3.
9. Treat AlphaFold structures as experimental evidence.
10. Pool within-study and cross-study measurements as equivalent ground truth.
11. Invent a scientific threshold not in any governing document.
12. Create synthetic measurements to fill structural gaps.
13. Modify pocket boundary definitions — those are fixed by pocket/ layer.
14. Change scaffold assignments from SCI0-012.
15. Change SCI0-011 harmonization rules.
16. Change SCI1 feature definitions without a separately authorized task.
17. Implement S10, S9, or §4.7 explanation interface before Phase 2 is committed.
18. Use parameter sharing alone as proof of comparative representation.

---

## 16. SCI-2 artifact interfaces

Defined in `src/orthosteric/learning/_interfaces.py`. Frozen dataclasses
sealing the SCI-2 input/output contract without model implementation.

---

## 17. Next authorized milestone

1. **GOVERNANCE_DECISION_REQUIRED (GGR-001):** Record phase commitment.
2. After phase commitment: complete Stage 0 pre-registrations required for
   the committed phase (GGR-002 dependent items).
3. After Stage 0 + GDRs for GGR-003 through GGR-009: SCI2-002 (first
   implementation milestone, to be defined after SCI2-001 gates).

SCI-2 model code begins ONLY after all three steps are complete.

# Implementation Backlog

**Operational document, not governance.** It is expected to change constantly; the governance chain above it is expected to be stable. It adds no rule and overrides nothing.

| Field | Value |
|---|---|
| **Owns** | The ordered list of objectives, and each objective's status |
| **Does not own** | Any rule, policy, sequence definition, or scientific requirement |
| **Governed by** | Scientific Protocol v1.2 (`SI18`, §5 granularity, §16 package ownership) |
| **Consumed by** | The §10 execution loop, at step 9 |
| **Data policy** | `ADR-0003` — public knowledge only; contingent on its acceptance |

**Relationship to SI16.** SI16 forbids new *governance* documents. This is not one: governance answers what must be true and in what order; this answers which objective is next. It is mutable by the procedure in §3 rather than by ADR.

---

## 1. Objective identity

Format `SCI<state><nnn>`, zero-padded, never renumbered, never reused — including for superseded objectives. Gaps are normal.

| State | Prefix |
|---|---|
| `SCI-0` | `SCI0-001` … |
| `SCI-0.5` | `SCI05-001` … |
| `SCI-1` … `SCI-5` | `SCI1-001` … `SCI5-001` … |

IDs are the form used in task reports, commit bodies and ADR references. A commit body cites exactly one.

## 2. Status vocabulary

`Pending → Active → Done`, plus `Blocked` and `Superseded`.

| Status | Meaning |
|---|---|
| `Pending` | Specified, not started |
| `Active` | In progress. **At most one objective is `Active` project-wide** (Protocol P2) |
| `Done` | Committed, CI green, task report written |
| `Blocked` | Cannot proceed; records the blocking condition and what would unblock |
| `Superseded` | Replaced by a later objective, which is cited. Never deleted |

Deliberately distinct from Constitution §7.2 (`Provisional/Validated/Retired`) and the Protocol §6 maturity ladder (`Scaffolded … Frozen`), which describe concepts and modules rather than work items.

**This document owns per-objective status.** `docs/SCIENTIFIC_STATE.md` records only the pointer to the `Active` objective — it does not restate the list.

## 3. Two tiers, and who may add objectives

**Committed objectives** are fully specified and ordered. They are **frozen at state entry**: once a state becomes active, its committed list does not change.

**Provisional objectives** are named for later states but not specified, because their content depends on outcomes not yet available — which determinants emerge at `SCI-3`, whether S7 is live, whether an experimental arm exists.

**Refining a state's provisional objectives into committed ones is itself an objective**, always numbered `…-001` for that state, executed at state entry with its own task report. This is the only authorized way objectives are added.

**Discovered work** during an active objective is routed, never appended:

| Discovery | Route |
|---|---|
| Defect in the objective under construction | Fix within it; no new objective |
| Defect in a `Done` objective of the current state | New objective, appended after the current one, cited in the task report |
| Work belonging to a later state | Record as provisional under that state; **do not execute** |
| Work requiring an architecture decision | STOP; ADR (Protocol §11) |
| Anything else | STOP — do not invent an objective (`SI18`) |

## 4. Granularity

Per Protocol §5, an objective is the smallest change that is independently testable, leaves CI green, and advances exactly one Exit-gate item.

**Objectives are vertical slices, not horizontal phases.** Each carries its own tests, written first, and its own documentation. There is no separate "write the tests" or "write the docs" objective — Protocol §10 steps 10 and 12 put both inside every objective. A backlog that lists tests as a later objective licenses untested implementation until it is reached.

```
Wrong:  001 schema · 002 serialization · 003 tests · 004 documentation
Right:  001 schema + its tests + docstrings
        002 serialization + its tests + docstrings
```

**Gate objectives carry no code.** They invoke the Protocol §15.4 procedure and are marked `[procedure]`.

---

## SCI-0 — Data, audit, pre-registration · **committed**

Derived from Constitution §3.1 Q1–Q16, §2.3, §3.3 **as amended by ADR-0003**. Creates `data/` (Protocol §16).

**`data/` sub-structure** (ADR-0003 §6). Harmonization is a scientific component, not plumbing: it performs Cheng–Prusoff normalization, duplicate resolution and confidence assignment, and carries its own tests and documentation under ENG §2.

```
data/  chembl/  bindingdb/  pubchem/  pdb/  literature/
       harmonization/  provenance/  snapshots/
```

| ID | Objective | Notes |
|---|---|---|
| `SCI0-001` | Refine `SCI-0` backlog; confirm Q1–Q16 coverage under ADR-0003 | §3 |
| `SCI0-002` | `data/` package scaffold — README with Constitution sections served | maturity `Scaffolded` |
| `SCI0-003` | Provenance record schema + writer — publication or accession mandatory | ENG §7; §3.3; every record traces to public source |
| `SCI0-004` | Activity record schema — **assay metadata mandatory**: type, [ATP], endpoint, organism, construct, publication, curation confidence | §2.3(2) as amended |
| `SCI0-005` | Censored-data representation and censored likelihood interface | §3.3; never imputed to threshold |
| `SCI0-006` | Source adapters — ChEMBL, BindingDB, PubChem BioAssay | ADR-0003 §2 accepted sources |
| `SCI0-006b` | **Literature mining** — CrossRef, PubMed, PMC OA; table-first extraction priority; **binding span-verification gate**; OA coverage bias quantified | ADR-0003 §2; unanchored values discarded, not down-weighted |
| `SCI0-007` | Source adapters — PDB structures + **structured construct descriptor**; UniProt sequence metadata. **AlphaFold excluded** | §2.1; predicted structures cannot support §2.1(1) |
| `SCI0-008` | **Harmonization: Cheng–Prusoff IC50 → Ki** where [ATP] and isoform ATP Km are known; **BAO assay-ontology mapping** with measured-quantity and interference-susceptibility fields | §2.3(2); a normalization, not a covariate |
| `SCI0-008b` | **Chemical standardization (RDKit)** — salt stripping, charge normalization, canonical tautomer, stereochemistry preserved, canonical SMILES, InChI, InChIKey. **No descriptors** | descriptors are features → SCI-1 (Protocol §16) |
| `SCI0-008c` | **Identifier harmonization** — internal ID, cross-references across sources; conflicting structures surfaced, never silently merged | prerequisite for deduplication |
| `SCI0-009` | Harmonization: duplicate and conflict resolution; **different stereoisomers never merged**; policy recorded | requires `SCI0-008b` — deduplication without canonical structures is unsound |
| `SCI0-010` | Harmonization: curation-confidence assignment — **additive and inspectable; no learned model** | audit Q9; a learned scorer would breach SI3 and make the corpus depend on a model trained on it |
| `SCI0-011` | Snapshot builder — content-hashed, immutable; manifest includes **full software provenance** (RDKit, Python, lock hash, git SHA, OS, pipeline version) | §3.3 as amended; ENG §13. RDKit version affects InChIKey, so the toolchain is part of corpus identity |
| `SCI0-011` | `Done` | — | feature/sci0-011 | immutable snapshot; SHA-256 over records+policy+SW; PDB vs AF tracking; RULE_MISSING manifest |
| `SCI0-012` | `Done` | — | feature/sci0-012 | Bemis–Murcko scaffold family assignment | audit Q5 |
| `SCI0-013` | `Done` | — | feature/sci0-013 | **Within-study / within-assay stratum extraction** | §2.3(1) as amended — the evaluation stratum |
| `SCI0-014` | `Done` | — | feature/sci0-014 | **Compound × isoform measurement graph construction** | connectivity substrate for R1 |
| `SCI0-014b` | `Done` | — | feature/sci0-014b | **Dataset characterization** — descriptive only; never modifies the snapshot; may not inform split, stratum or threshold selection | attached to snapshot hash |
| `SCI0-014c` | `Done` | `GDR-002` | feature/gdr-002-corpus-derived-engineering-parameters | **Corpus profile freezing** (`data/snapshots/_profile.py`) — `N_c`, `N_b`, `N_w` computed deterministically from an already-frozen `SCI0-011` snapshot's `SCI0-014`/`SCI0-014b` characteristics; content-hashed, immutable | `GDR-002`; not sealed a priori — corpus-derived |
| `SCI0-015` | **Public comparative evidence audit** — Q1 as amended, all nine sub-questions | **R1 evaluated here**; replaces the old four-isoform census |
| `SCI0-016` | Q4 audit — **both** noise floors, within-study and cross-study | §2.4 as amended; sets the S4b reference |
| `SCI0-017` | Q3 audit — right-censored fraction and handling | |
| `SCI0-018` | Q5 audit — ATP-site structure inventory: resolution, construct, open specificity pocket | inventory only; derivation is `SCI-1` |
| `SCI0-019` | Q6 — MMP selectivity-switch set, **within-study pairs only** | S5 as amended |
| `SCI0-020` | Q7 — evaluation-set size after scaffold-aware splitting | §3.4 |
| `SCI0-021` | Q8–Q10 — Tier 2 census, per-target evaluation mode, structural quality | **no Tier 2 record enters any training path** (SI1) |
| `SCI0-022` | Q12 — dual-inhibitor census | §3.5 |
| `SCI0-023` | Seal: correspondence ordering + weighting + S8c covariate list | Auditor-owned; §2.1, §1.4.1 |
| `SCI0-024` | Seal: S9 reference rule set | Auditor-owned; §3.6.3 |
| `SCI0-025` | Q15 — empirical S9b precision floor calibration | §3.6.5 |
| `SCI0-026` | Seal: S10 mutation and null-control sites | Q14 |
| `SCI0-027` | Seal: second-family selection | Q16; before any Tier 1 modelling |
| `SCI0-028` | `Revised scope, 2/3 remaining items closed` | `docs/governance/SCI0-028-GOVERNANCE-GAP-REPORT.md`, `GDR-001`, `GDR-002` | feature/gdr-002-corpus-derived-engineering-parameters | **Verify** `_profile.py` computation is deterministic, reproducible, and provenanced (`N_c`/`N_b`/`N_w` reclassified as corpus-derived, `GDR-002` — no longer sealed here); duplicate-resolution policy resolved (`GDR-001`); S4b relocated to `policy/` (`ADR-0008`, `GDR-002`) | **no longer sealed before `SCI0-015` runs** — reclassification removes that dependency (`GDR-002` §6); per-isoform ATP Km source remains `RULE_MISSING`, does not block `SCI0-015`'s connectivity portions |
| `SCI0-029` | Seal: pre-registered thresholds for all criteria | `sealed/config/`; non-composable loader |
| `SCI0-030` | Phase commitment — record in `CLAUDE.md` header | §1.6 |
| `SCI0-031` | `[procedure]` `SCI-0` gate evaluation | §15.4; proceed / redesign / stop |

*`SCI0-023` through `SCI0-029` are `Scientific` ADR category and may not be authored by the model developer alone (ENG §1; Constitution §7.7).*

**Ordering constraint.** `SCI0-028` must be `Done` before `SCI0-015` begins. Running the connectivity audit before its thresholds are sealed would let the kill criterion be chosen after seeing the data — a Constitution §1.4 violation and the exact failure R23 describes.

**Revision (2026-08-05, `GDR-002`).** This constraint applied specifically because `N_c`/`N_b`/`N_w` needed pre-sealing before `SCI0-015` ran. Under `GDR-002`, those three are corpus-derived engineering parameters computed *from* the audit's own output, not pre-sealed floors compared against it — the reason for the ordering constraint no longer applies to them. `SCI0-015` is **no longer blocked by `SCI0-028`**. It remains blocked by the separate, standing requirement that real corpus acquisition be explicitly authorized before it begins, which `GDR-002` does not authorize and is unaffected by it.

## Corpus Quality Assessment Layer (`quality/`) · **architectural layer, not a stage**

Authorized by `ADR-0009` [Architectural]; dimension rules governed by `GDR-003`
[Scientific]. Not an `SCI-N` stage. Interposes between the descriptive
`CorpusProfile` (`GDR-002`) and the Decision Policy Layer (`ADR-0008`):

```
SCI0-011 Immutable Snapshot -> SCI0-014b Characterization -> CorpusProfile
   -> CorpusQualityAssessment (quality/) -> CorpusQualityGatePolicy (policy/)
   -> PROCEED / WARNING / REDESIGN / STOP
```

| ID | Status | Record | Branch | Objective |
|---|---|---|---|---|
| `CQA-001` | `Done` | `ADR-0009`, `GDR-003` | feature/adr-0009-corpus-quality-assessment | `quality/` package: `QualityDimensionEvaluator` ABC, `CorpusQualityAssessor`, 7 dimension evaluators (connectivity, coverage, scaffold diversity, publication concentration, confidence, missingness, structural coverage); `policy/`'s `CorpusQualityGatePolicy` consuming only the assessment |

**Closes the remaining R1 threshold dependency.** `GDR-002` retired R1's
automatic numeric kill-switch for `N_c`/`N_b`/`N_w` but left open exactly how
the resulting `SCI0-031` human decision would be informed. `GDR-003` closes
that: every rule touching `N_c`/`N_b`/`N_w` is a structural zero/non-zero
check, never a magnitude comparison. No fixed-threshold dependency on those
three quantities remains anywhere in the interpretation pipeline.

**A defect discovered and fixed during implementation.** `GraphStats.
within_study_four_isoform` (`SCI0-014`) was found to count compounds in a
panel where all four isoforms are collectively represented *somewhere*, not
compounds *individually* measured across all four — a materially weaker
quantity than the Constitution's actual `N_w`. `CorpusProfile.engineering_
parameters` gained a corrected field, `n_complete_compounds` (`StratumReport.
total_complete_compounds`, verified correct by direct construction), which
`quality/`'s `CoverageEvaluator` uses instead. `n_w` is retained for
continuity and documented with the discovered gap; `SCI0-014`'s `graph.py`
itself is not modified in this change (out of scope; flagged for a future
pass).

**Structural coverage extension point prepared, not implemented** (`ADR-0009`
§4): `CorpusProfile.structural_coverage` (reserved, `None` by default) and a
`StructuralCoverageEvaluator` stub (`NOT_YET_AVAILABLE`, always) demonstrate
the mechanism `SCI0-018` will eventually populate. No PDB or AlphaFold record
is read anywhere in this change.

## Decision Policy Layer (`policy/`) · **architectural layer, not a stage**

Authorized by `ADR-0008` [Architectural]. Not an `SCI-N` stage: `SCI-4` is
Cross-family transfer (Constitution §9.6, criterion S7) and is untouched. See
`ADR-0008` for why this is a layer rather than a stage.

| ID | Status | Record | Branch | Objective |
|---|---|---|---|---|
| `DPL-001` | `Done` | `ADR-0008` | feature/adr-0008-decision-policy-layer | `policy/` package: `Policy` ABC, `PolicyEngine`, `PolicyConfig`, configurable `SelectivityTierTable`, selectivity/potency/confidence/uncertainty policies, `DecisionRecord` provenance |

Operates exclusively on model outputs. Never modifies evidence, harmonized
data, features, or learned models — enforced by the `.importlinter` layer order
(`policy/` is highest, so no lower layer may import it). No policy output is
criterion-eligible (Constitution §1.4 firewall).

Deliberately **not** implemented, because no evidence layer exists to support
them and no threshold would be anything but invented: `ADMETPolicy`,
`DevelopabilityPolicy`. The `Policy` ABC admits them without changes to
existing code when such an evidence layer is added.

Open, and blocking one policy from classifying rather than abstaining:
`UncertaintyPolicy` requires the label-noise floor from `SCI0-016`, which has
not run; it abstains and raises `RULE_MISSING/SCI0-016` until then.

## Phase C · **Comparative Structural Learning Platform** — `ADR-0010`

Phase B (evidence engineering, SCI0-001..SCI0-031) is complete (modulo
corpus acquisition authorization). Phase C begins structural representation
learning. New package taxonomy (ADR-0010): `pocket/`, `features/`,
`learning/`, `interpretation/`, `generation/`. Old stubs `model/`, `train/`,
`explain/` retired. Layer order: `generation/` → `policy/` → `eval/` →
`interpretation/` → `learning/` → `features/` → `pocket/` → `quality/` →
`data/` → `runtime/`.

## SCI-1 — Structural Feature Generation · **Phase C, committed**

Populates `pocket/` (preprocessing + extraction) then `features/`
(representation construction). Every module: deterministic, provenanced,
fully tested.

| ID | Status | Record | Objective |
|---|---|---|---|
| `SCI1-000` | `Done` | `ADR-0010` | Phase C architecture spec + package stubs + layer order. **This PR.** |
| `SCI1-001` | **Next** | — | `pocket/` data models: `StructureRecord`, `StructureProvenance`, `PocketDefinitionPolicy`, `PocketResidueSet` (pure-Python, no external deps) |
| `SCI1-002` | **Done** | — | `pocket/` geometry + rotamer: `_pocket_geometry`, `_rotamer_state`, `_solvent_accessibility` (BioPython/numpy) |
| `SCI1-003` | **Done** | — | `pocket/` residue mapping: `_residue_mapping` (cross-isoform correspondence data model, Constitution §2.1) |
| `SCI1-004` | **Done** | — | `features/` interaction fingerprints: `_interaction_fingerprint` (8 evidence classes, RULE_MISSING-by-default thresholds, canonical-position alignment) |
| `SCI1-005` | **Done** | — | `features/` contact maps + graph: `_contact_map`, `_structural_graph` |
| `SCI1-006` | **Done** | — | `features/` descriptors + comparative set: `_pocket_descriptor`, `_comparative_feature` |
| `SCI1-007` | **Done** | — | `features/` MD interface stubs: `_md_interface` |
| `SCI1-008` | **Done** | — | `features/` governed config: `FeatureConfig`, versioned |

## SCI-2 — Comparative Representation Learning · **Phase C, provisional**

Populates `learning/`. Constitution §4.1–§4.7.

| ID | Objective |
|---|---|
| `SCI2-001` | Refine `SCI-2` backlog; comparative encoder; direct log-ratio prediction head; degeneracy battery |

## SCI-3 — Mechanistic Interpretation · **Phase C, provisional**

Populates `interpretation/`. Constitution §4.7, §2.5, §5.3–§5.4.

| ID | Objective |
|---|---|
| `SCI3-001` | Refine `SCI-3` backlog; discrete-rule interface; counterfactual perturbation |

## SCI-4 — Molecular Design · **Phase C, deferred**

Populates `generation/`. Deferred until SCI-3 complete.

| ID | Objective |
|---|---|
| `SCI4-001` | Refine `SCI-4` backlog after SCI-3 outcomes |

## SCI-0.5 — Mutation propagation · **provisional** (Phase 3, Option B only)

| ID | Objective |
|---|---|
| `SCI05-001` | Refine `SCI-0.5` backlog — only if Option B is elected and Phase 3 committed |

## SCI-1 — Pocket, representation, baselines · **committed**

Derived from Constitution §2.1, §4.6, §9.3. Creates `pocket/`, `features/`, `eval/` (metrics, calibration).

| ID | Objective | Notes |
|---|---|---|
| `SCI1-001` | Refine `SCI-1` backlog against `SCI-0` audit outcomes | §3 |
| `SCI1-002` | `pocket/` scaffold — README with Constitution sections served | **DONE** |
| `SCI1-003` | Reference structure loader; construct and resolution recording | §2.1 |
| `SCI1-004` | Ligand-ensemble union pocket builder — **rejects apo input** | §2.1(1); R4 |
| `SCI1-005` | Rotamer-state ensemble representation | §2.1(2); sequence/backbone-only is non-compliant |
| `SCI1-006` | Ordered-water retention and flagging | §2.1 |
| `SCI1-007` | Pocket version hashing; per-prediction reference | §5.4; SI9 immutability |
| `SCI1-008` | Point-mutation input support; pocket re-derivation | §2.1, for S10 |
| `SCI1-009` | `features/` scaffold | |
| `SCI1-010` | Path A representation — correspondence-free, accepts an arbitrary ATP site | §4.6; SI4 |
| `SCI1-011` | Path A verification on a mutated structure and an unseen ATP site | forfeits S7/S8/S10 if unmet |
| `SCI1-012` | `eval/` scaffold — metrics and calibration only | battery is `SCI-2` |
| `SCI1-013` | Log-selectivity-ratio metric; per-target RMSE | §2.3(4) |
| `SCI1-014` | Per-target calibration (ECE) + **sharpness** reporting — never aggregated | S4a, S4b; SI12 |
| `SCI1-015` | Uncertainty composition as explicit conjunction | §2.4; no `min()` |
| `SCI1-016` | Indeterminate branch per target | §2.2; SI13 |
| `SCI1-017` | Scaffold-aware / series-aware splitting | §3.4; whole series held out |
| `SCI1-017b` | Within-study evaluation stratum loader; stratum reporting separated from pooled | §2.3(1) as amended |
| `SCI1-018` | Baseline 1 — ligand-only | §9.3 |
| `SCI1-019` | Baseline 2 — nearest-neighbour Tanimoto | §3.4 |
| `SCI1-020` | Baseline 3 — proteochemometric | §1.2 prior art |
| `SCI1-021` | Baseline evaluation against sealed S2 threshold, **on the within-study stratum** | §15.3; §2.3(1) as amended |
| `SCI1-022` | `[procedure]` `SCI-1` gate evaluation | **if any baseline meets S2, STOP** — the learned component is unjustified |

*No `model/` or `train/` code may exist until `SCI1-022` is `Done` (SI3).*

## SCI-2 — Learning · **provisional**

Creates `model/`, `train/`, `eval/` (degeneracy battery, seals); `explain/` if Phase 2 committed.

| ID | Objective |
|---|---|
| `SCI2-001` | Refine `SCI-2` backlog against `SCI-1` outcomes and the committed phase |

Skeleton, to be specified at `SCI2-001`: model interface and configuration · comparative encoder · direct log-ratio prediction head (§4.2(1)) · symmetric objective (§4.2(2)) · training loop and checkpointing · per-target applicability domain (§4.2(4)) · degeneracy battery per §4.3 (pocket shuffle, ligand-only ablation, Δ-prediction, MMP switch, scaffold holdout, apo-ablation) · scrambled-label control and S10 in-silico mutation if Phase 2 · generation freeze (§15.1) · `[procedure]` gate evaluation for S2, S3, S4, S6.

## SCI-3 — Knowledge extraction and first Tier 2 query · **provisional**

| ID | Objective |
|---|---|
| `SCI3-001` | Refine `SCI-3` backlog; requires the `SCI-2` gate record |

Skeleton: `explain/` discrete-rule interface (§4.7) if not built at `SCI-2` · rule extraction against the sealed reference set · blinded adjudication support (§3.6.4) · S1 determinant recovery across held-out families · dual-inhibitor stratification (§3.5) · covariate-adjusted S8c gradient reporter **with no significance test** (SI15) · `[procedure]` Tier 2 query per §15.2 — prediction committed before the query executes · `[procedure]` gate evaluation.

## SCI-4 — Cross-family transfer · **provisional**

| ID | Objective |
|---|---|
| `SCI4-001` | Refine `SCI-4` backlog; requires `SCI-3` outcomes and a new frozen generation |

Skeleton: sealed second-family evaluation without retuning (S7) · `kg/` within the Constitution §5.2 caps · the three §5.1 justifying queries · promotion rules (§5.4) · L4 alchemical residue mutation to E3 · combined-gradient S8c · `[procedure]` second Tier 2 query against a **new** generation · `[procedure]` gate evaluation.

## SCI-5 — Experimental validation · **provisional**

| ID | Objective |
|---|---|
| `SCI5-001` | Refine `SCI-5` backlog; **requires the §6.3 experimental arm** |

Not entered if the project is computation-only; the limitation is recorded in the completion report. Skeleton: §6.2 four-field hypothesis record per molecule · assay result ingestion at E4 · Design Rule promotion requiring ≥2 series and an E4 edge · `[procedure]` gate evaluation.

---

## Ledger

Updated at every task. One row per objective; `Superseded` rows retained.

| ID | Status | Commit | Task report | Notes |
|---|---|---|---|---|
| `SCI0-001` | `Done` | — | feature/sci0-001-sci0-002 | refinement document at docs/specifications/SCI0-001-refinement-data-acquisition.md adopted |
| `SCI0-002` | `Done` | — | feature/sci0-001-sci0-002 | data/ scaffold: config, exceptions, models, tier2_gate, README, subpackage stubs |
| `SCI0-003` | `Done` | — | feature/sci0-003 | provenance schema + writer; ActivityRecord in models.py; 34 tests |
| `SCI0-004` | `Done` | — | feature/sci0-004-sci0-005 | BiochemicalRecord/CellularRecord schema; CensoredValue |
| `SCI0-005` | `Done` | — | feature/sci0-004-sci0-005 | censored_fraction; no code path discards censored records |
| `SCI0-006` | `Done` | — | feature/sci0-006 | source connectors: ChEMBL, BindingDB, PubChem; tier-at-ingestion; 20 tests |
| `SCI0-006b` | `Done` | — | feature/sci0-006b | literature adapters: CrossRef, PubMed, PMC OA; span-verification gate; OA bias report |
| `SCI0-007` | `Done` | — | feature/sci0-007 | PDB+UniProt+AlphaFold fallback; §2.1 admissibility; construct descriptor; 9 AF rules |
| `SCI0-008b` | `Done` | — | feature/sci0-008b | RDKit chemical standardization; stereo preserved; no descriptors; deterministic |
| `SCI0-008c` | `Done` | — | feature/sci0-008c | identifier harmonization; InChIKey internal ID; cross-refs; conflict detection; fail-closed |
| … | | | | `SCI0-006`–`SCI0-031` `Pending` |

**At most one `Active` row at any time.** If none is `Active` and none is `Pending` in the current state, the state's Exit gate is evaluated; if it passes, the FSM advances. **If no unfinished objective exists anywhere in the committed phase, the protocol is complete — do not invent work (`SI18`).**

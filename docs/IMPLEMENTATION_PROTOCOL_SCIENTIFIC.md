# Implementation Protocol — Scientific Development

**Version 1.2** · First-class governance document · `docs/IMPLEMENTATION_PROTOCOL_SCIENTIFIC.md`

| Field | Value |
|---|---|
| **Owns** | The sequence in which scientific capability is added to the repository |
| **Does not own** | Scientific rules · engineering policy · architecture · coding standards |
| **Compatible Constitution** | `>=4.6, <5.0` — verified against `docs/GOVERNANCE_VERSIONS.md` |
| **Entered from** | Foundation Protocol `COMPLETE` → lifecycle transition ADR → Research |
| **Covers** | Constitution Stages 0–5, as states `SCI-0` … `SCI-5` |
| **Terminates at** | The phase-dependent terminus of §17, producing `SCIENTIFIC_COMPLETION_REPORT.md` |
| **Lifecycle stage throughout** | Research (ENG §16) |

**Identifiers.** States are `SCI-0`, `SCI-0.5`, `SCI-1` … `SCI-5`. They are immutable and are the form used in ADR cross-references. They deliberately avoid the Constitution's crowded namespace — `S1`–`S10` are success criteria, `E1`–`E4` evidence classes, `C1`–`C6` corollaries, `R1`–`R33` risks, `I1`–`I10` Foundation invariants.

---

## 0. Orientation

**Governance is finished. The repository now gains scientific capability.**

At any moment there is exactly one question:

> **What is the next unfinished objective of the current state?**

Not future work. Not optimization. Not publication. Only the current state's Exit gate.

### Mental model

```
Repository
├── Governance ................ finished; do not extend (SI16)
├── Scientific state .......... SCI-0 … SCI-5 (§16)
├── Current objective ......... from IMPLEMENTATION_BACKLOG.md (SI18)
├── Current module ............ §6
└── Current commit ............ one objective, one commit, one report
```

Everything below the current objective is implementation detail. Everything above it is governance. **Never mix the two in one change.**

### Layer map

The repository grows in layers. Earlier layers never depend on later ones (SI17).

| State | Layer | Gate that matters |
|---|---|---|
| `SCI-0` | Data, audit, pre-registration | R1 kill criterion; six seals; phase commitment |
| `SCI-1` | Pocket, representation, **baselines** | **A baseline meeting S2 disqualifies the learned component** |
| `SCI-2` | Learning | S2, S3, S4, S6 — comparative learning occurred or it did not |
| `SCI-3` | Knowledge extraction **and the first Tier 2 query** | S9c voids S9a/S9b; one logged query |
| `SCI-4` | Cross-family transfer (builds `kg/`) | S7 without retuning |
| `SCI-5` | Experimental validation | E4 edges; Design Rule promotion |

Two labels are easy to get wrong. Knowledge extraction is `SCI-3`, not `SCI-4` — `SCI-4` is *transfer*, which happens to build the knowledge layer. And `SCI-1` is baselines *and* representation: dropping "baselines" hides the gate most likely to stop the project.


## 1. Ownership and conflict resolution

```
Constitution  →  Accepted ADR  →  CLAUDE.md  →  Foundation Protocol
  →  Scientific Protocol  →  Engineering Standards  →  Project Specification
```

| Document | Owns |
|---|---|
| Constitution v4.6 | Scientific rules, criteria, evidence classes, stage gates |
| `CLAUDE.md` | Agent execution rules |
| Foundation Protocol | Repository establishment sequence (terminated before this protocol begins) |
| **Scientific Protocol** | **Scientific implementation sequence** |
| `ENGINEERING_STANDARDS.md` | Engineering policy, ADR policy and categories |
| `PROJECT_SPECIFICATION.md` | Functional requirements |
| `GOVERNANCE_VERSIONS.md` | Document versions and compatibility ranges |
| `IMPLEMENTATION_BACKLOG.md` | The ordered objective list and per-objective status. Operational, not governance |

**A conflict with the Constitution is always resolved by the Constitution and indicates a defect here.** Report it and request an ADR (`CLAUDE.md` §5); never reconcile silently.

## 2. Version compatibility (verify before execution)

Before the first task of any session, verify that `docs/GOVERNANCE_VERSIONS.md` records a Constitution version inside `>=4.6, <5.0`. Outside that range this protocol is invalid and work stops.

**Why the major bound.** Constitution §A.8 makes any Part A amendment trigger re-derivation review of the tier architecture, Tier 3 exclusions, pocket definition and representation decision. A major bump means the states mapped to those may no longer hold and must be re-verified, not assumed.

## 3. Relationship to Constitution stages and phases

**This protocol adds no sequence of its own.** Its states *are* the Constitution's stages (Part IX). It adds only which packages each state creates, what verifies a state complete, and the procedures of §15.

**The state machine is not linear.** Constitution §1.6 commits a phase at the `SCI-0` gate, and that fixes the terminus:

| Committed phase | States executed | Terminus |
|---|---|---|
| Phase 1 — Core | `SCI-0`, `SCI-1`, `SCI-2` | after `SCI-2` |
| Phase 1+2 — Extension | + `SCI-3` | after `SCI-3` |
| Full | + `SCI-4`, `SCI-5` (+ `SCI-0.5` if Option B elected) | after `SCI-5` |

Claim ceilings per phase are Constitution §9.0 and are not restated. Descoping is a Decision Record, not an amendment.

## 4. Domain boundary

Where a state cites "Constitution §n" or "ENG §n," that section is authoritative and complete; this document adds ordering only. A **Sequencing note** is protocol content: it states why work happens at that point rather than later, and appears nowhere else.

## 5. Task granularity

An **objective** is the smallest change that simultaneously:

1. is independently testable,
2. leaves CI green on completion, and
3. advances exactly one item of the current state's Exit gate.

If a proposed change advances two Exit-gate items, it is two objectives. If it cannot be tested alone, it is too small and belongs inside a larger one. One objective, one commit, one task report (P5).

## 6. Module maturity

Progress is tracked per module, not per package. A package's maturity is the **minimum** of its modules'.

| Level | Meaning |
|---|---|
| `Scaffolded` | Directory, `__init__.py`, README exist; no logic |
| `Implemented` | Logic present; type-checks strictly |
| `Tested` | Unit tests pass; tests preceded implementation |
| `Gate-verified` | The owning state's Exit gate has been satisfied with this module in place |
| `Frozen` | Part of a frozen model generation (§15.1); no change without a new generation |

An empty scaffold is `Scaffolded`, never a completed deliverable. A state's Exit gate is met only when every module it owns is at least `Gate-verified`.

*The term `Gate-verified` is used rather than "Validated" to avoid collision with Constitution §7.2's status vocabulary (`Provisional → Validated → Retired`).*

## 7. Scientific invariants

Verified after **every** task (§10 step 14). Violation is a protocol halt (§13).

| # | Invariant | Owned by |
|---|---|---|
| SI1 | Tier 2 never enters training, tuning, model selection, feature engineering or threshold setting. Read **once per model generation**, at the `SCI-3` and `SCI-4` gates only, through the gate module, logged | Constitution §0.4 |
| SI2 | No model trained before every `SCI-0` seal exists — otherwise thresholds are not pre-registered | Constitution §1.4, §3.1 |
| SI3 | No learned component built before the `SCI-1` baseline gate is evaluated and recorded | Constitution §9.3 |
| SI4 | Representation is correspondence-free (Path A). Path B requires the §4.6 gate-level Decision Record and forfeits S7, S8a–c, S10 | Constitution §4.6 |
| SI5 | No explanation module before a predictive model exists and passes its gate | Constitution §4.7 |
| SI6 | The knowledge layer only consumes outputs; it never influences training, features or model selection | Constitution §5.3 |
| SI7 | The **model** never authors a Determinant or Design Rule. Model output enters as Candidate Determinant at E1; promotion requires E3 or E4. *(The Auditor's manual curation of the sealed reference rule set is required, not forbidden — §3.6.)* | Constitution §2.5, §5.4 |
| SI8 | The model never consumes Design Rules, rule annotations or selectivity labels as supervision for rule recovery | Constitution §1.3, S9 |
| SI9 | Pocket definitions, dataset snapshots, model generations, thresholds, evidence classifications and correspondence orderings are never modified in place | `CLAUDE.md` §8 |
| SI10 | No metric compared against a threshold before that threshold is sealed | Constitution §1.4 |
| SI11 | No gate evaluation before the model generation is frozen | Constitution §0.4 |
| SI12 | Tier 2 results reported per target, never aggregated into a single off-target score | Constitution §2.3(5) |
| SI13 | Every per-target output can express Indeterminate | Constitution §2.2 |
| SI14 | No Tier 3 target enters any module | Constitution §0.2 |
| SI15 | No significance test on the S8c correspondence gradient | Constitution §1.4.1, §7.6 |
| SI16 | **No new governance document is written.** The governance chain is complete (Constitution, `CLAUDE.md`, ENG, both protocols, `GOVERNANCE_VERSIONS.md`). Extending it requires an explicit instruction plus a `Process` ADR — writing governance is the standing substitute for writing code | ENG §18; Constitution §7.5 |
| SI18 | **Objectives are never invented.** Every implementation task corresponds to exactly one objective in `docs/IMPLEMENTATION_BACKLOG.md`. If no unfinished objective exists in the current state, evaluate the Exit gate; if none exists in the committed phase, the protocol is complete. **Do not create work** | Backlog §3 |
| SI17 | **Layer dependency direction.** Earlier layers never import later ones: `data/` ← `pocket/` ← `features/` ← `model/` ← `train/`; `eval/`, `explain/` and `kg/` consume, never feed | ENG §2 contract 4 |

## 8. Invariant verification mapping

What can be checked mechanically, and what requires review. Only the first group belongs in CI.

| Invariant | Verified by | Automatable |
|---|---|---|
| SI1 | Import-graph contract 3 (ENG §2) + `logs/tier2_queries.jsonl` entry count per generation hash | **Yes** |
| SI2 | `sealed/MANIFEST.md` completeness vs. first commit touching `src/<pkg>/train/` | **Yes** |
| SI3 | Baseline results recorded in `docs/SCIENTIFIC_STATE.md` before the first `model/` commit | **Yes** |
| SI4 | Absence of residue-indexed features; Path B ADR presence | Partial — presence check yes, semantics no |
| SI5 | `explain/` creation commit postdates the `SCI-2` gate record | **Yes** |
| SI6 | Import-graph contract: nothing under `train/`, `features/`, `model/` imports `kg/` | **Yes** |
| SI7 | Knowledge-layer write path: Design Rule nodes accept only Auditor-sealed or E4-backed sources | Partial |
| SI8 | Training data schema contains no rule or Design Rule field | **Yes** |
| SI9 | Git history + `sealed/MANIFEST.md` + snapshot content hashes | **Yes** |
| SI10 | Seal verification recorded in every evaluation task report | **Yes** |
| SI11 | Generation freeze record precedes the gate record in commit order | **Yes** |
| SI12 | Report generator emits no aggregate off-target field | **Yes** |
| SI13 | Model interface exposes an Indeterminate branch per target; tested | **Yes** |
| SI14 | Tier declaration on every artefact (Constitution §7.6); grep for Tier 3 terms | Partial |
| SI15 | CI grep for significance tests in the gradient reporter | **Yes** |
| SI16 | No file added under `docs/` matching the governance set without a `Process` ADR | **Yes** |
| SI17 | Import-graph contract 4 (ENG §2) | **Yes** |
| SI18 | Commit body cites exactly one backlog objective ID; the ledger has at most one `Active` row | **Yes** |

**The three partial rows are review obligations, not gaps to be automated away.** SI4's semantics, SI7's provenance judgement and SI14's scope judgement require a human — they belong in the ENG §21 PR checklist and the Auditor's remit (Constitution §7.7).

## 9. Protocol invariants and stop conditions

**Protocol invariants.** P1 exactly one active state · P2 one logical objective · P3 one module under construction · P4 one frozen generation per gate evaluation · P5 one commit and one task report per objective · P6 one satisfied Exit gate per transition; **no state skipped within the committed phase** — states beyond the phase terminus (§3) are *not entered*, which is not a skip — and none revisited without §12 · P7 one owning document per requirement · P8 one state creates each package (§16).

**Stop conditions**, in addition to `CLAUDE.md` §2 — **stop immediately**:

- state does not match observed repository state
- `GOVERNANCE_VERSIONS.md` records a Constitution version outside §2's range
- a required seal is absent or its hash does not verify
- a threshold is needed that is not sealed
- representation undefined, or Path A/B unresolved
- a pocket definition would change (SI9)
- a new evidence class, determinant, assay type, or dataset schema field is required
- the task would train on, tune against, or select using Tier 2
- the Tier 2 budget for the current generation is exhausted
- gate evaluation requested against an unfrozen generation
- the knowledge layer would require an interpretation no evidence class authorizes
- a Constitution section is ambiguous for the case at hand
- the committed phase does not authorize the state
- a stage gate has failed and a Constitution kill criterion applies

## 10. Execution algorithm

```
 1  Read CLAUDE.md. Verify governance versions (§2).
 2  Read docs/SCIENTIFIC_STATE.md; verify against observed state. Mismatch → STOP.
 3  Read the Constitution sections the current state cites.
 4  Classify the task (§11). STOP → report. §15 procedure → follow it instead.
 5  Read the ENGINEERING_STANDARDS sections cited.
 6  Search docs/adr/ for an Accepted decision covering it.
 7  Verify the committed phase authorizes the state (§3).
 8  Verify the current state owns the task and the package (§16). If not → STOP.
 9  Take the next Pending objective from docs/IMPLEMENTATION_BACKLOG.md for this
    state and mark it Active. If none is Pending → evaluate the Exit gate; do not
    invent an objective (SI18). Confirm it satisfies §5 granularity (P2, P3).
10  Write tests first (CLAUDE.md §9).
11  Implement.
12  Update documentation in the owning document only (ENG §18).
13  Run make ci-local. Red → §12.2.
14  Verify the Exit gate, then all §7 and §9 invariants via §8.
15  Update module maturity (§6); write the task report (§14); update state file.
16  Commit.
17  Advance state only when the Exit gate is fully satisfied and every module the
    state owns is at least Gate-verified (§6) — existence is not completion.
    Otherwise take the next task in the same state.
```

## 11. Task classification

| Class | Action |
|---|---|
| Module implementation owned by the current state | Continue |
| Test or documentation of an existing module | Continue |
| Refactor | Continue **only if package ownership is unchanged** (§16). A refactor moving code across a package boundary is architecture |
| Bug in a scientific module | Continue; no ADR |
| Architecture, schema, or dependency change | **ADR before implementing**; category per ENG §1 |
| Anything touching a §7 invariant | **STOP** |
| Work owned by a later state, or by an unauthorized phase | **STOP** |
| Tier 2 access, seal read, generation freeze, gate evaluation | **§15 procedure**, not a normal task |
| Unclassifiable | **STOP** |

## 12. Recovery

**12.1 After interruption.** Read `docs/SCIENTIFIC_STATE.md`; verify HEAD against the recorded last green CI; verify CI green; verify recorded against observed state; verify recorded seal hashes still verify; verify the Tier 2 query log matches the recorded count. Resume the current state's outstanding objectives.

**Never infer progress from the presence of files.** If state file and repository disagree — or the Tier 2 log has more entries than recorded — **STOP**, report both, request instruction. An unexplained Tier 2 entry is a Constitution §0.4 barrier event: recorded, not corrected (§7.7).

**12.2 After red CI — decision criterion.**

| Condition | Action |
|---|---|
| More than one module affected | **Revert** |
| Root cause uncertain | **Revert** |
| Failure localized to the current state, cause understood, fix does not weaken any guarantee | Fix forward |
| Fix forward attempted once and CI still red | **Revert** — no second attempt |

Then: `make ci-local` → re-verify Exit gate and all invariants → resume. **Never** weaken a check to restore green (`CLAUDE.md` §3). Revisiting a completed state requires recording the corrective change (P6).

## 13. Violation classes

| | **Implementation failure** | **Protocol violation** | **Constitutional violation** |
|---|---|---|---|
| Examples | test red, mypy error, convergence failure | state skipped, missing task report, two objectives in one commit, restated requirement | Tier 2 in a training path, threshold adjusted after results, unlogged Tier 2 query, Candidate Determinant reported as Determinant |
| Response | §12.2; fix; continue | **halt**; record; corrective change; re-verify Exit gate | **halt**; record as a barrier event (§7.7); **not quietly corrected**; Auditor notified; the affected result is invalid |

A constitutional violation is never downgraded because it was accidental.

## 14. Task report

**Extends** the six-line audit of `CLAUDE.md` §17:

```
--- Scientific extension ---
Objective:                       backlog ID → Done | Blocked + reason
Next objective:                  backlog ID
State (before → after):
Modules changed + maturity (§6):
Constitution sections implemented:
Evidence classes touched:        [expected: none unless the state owns them]
Candidate Determinants created:
Determinants promoted:           + evidence class justifying promotion
Design Rules promoted:           + E4 edge reference
Tier boundaries touched:         [expected: none]
Model generation:                hash | unchanged | newly frozen
Tier 2 queries consumed:
Seals read:                      artefact + verification result
Exit gate:                       met | outstanding
Invariants:                      SI1–SI15 · P1–P8, per §8
Violation class:                 none | implementation | protocol | constitutional
Next objective / blocking issues:
```

## 15. Protocol-owned procedures

Sequences, not policies. These exist nowhere else.

### 15.1 Model generation freeze

Required before any gate evaluation (SI11) and any Tier 2 query (SI1).

```
1  Confirm architecture, training data snapshot and hyperparameters are final.
2  Compute the generation hash (Constitution §0.4 definition).
3  Record it in docs/SCIENTIFIC_STATE.md and the experiment record (ENG §6).
4  Set every module in the generation to maturity Frozen (§6).
5  Commit. The freeze commit is the generation's identity.
```

A change after freezing creates a **new** generation with a fresh Tier 2 budget; it never extends the old one.

### 15.2 Tier 2 query

Permitted only at the `SCI-3` and `SCI-4` gates, once per frozen generation.

```
1  Verify the generation is frozen (§15.1) and its budget unused.
2  Write the pre-registered prediction, before observing any Tier 2 data.
3  Commit the prediction. This commit must precede the query.
4  Execute through the gate module; it appends to the query log.
5  Verify the log entry matches the frozen generation hash.
6  Record results per target — never aggregated (SI12).
7  Do not iterate on the result within this generation.
```

Step 3 is what makes the prediction pre-registered rather than asserted afterwards, and it is verifiable in commit order. A query executed before its prediction is committed is a constitutional violation (§13).

### 15.3 Seal consumption

```
1  Read only at evaluation time, through the evaluation seal module.
2  Verify the hash against sealed/MANIFEST.md before use; mismatch → STOP.
3  Record artefact and verification result in the task report.
4  Compute the metric first, then compare against the seal — never the reverse.
```

Step 4 removes the opportunity to anchor an analysis choice on the threshold it will be judged against.

### 15.4 Gate evaluation

```
1  Freeze the generation (§15.1).
2  Verify every seal the gate consumes (§15.3).
3  Evaluate all criteria the Constitution names for the state — all of them, once.
4  Record each outcome, pass or fail, in docs/SCIENTIFIC_STATE.md.
5  If a Constitution kill criterion is met, STOP. A failed gate is a finding,
   not a retry: re-running it on a tuned model is a new generation and must be
   declared as such.
```

## 16. State machine

```
RESEARCH_START → SCI-0 → [phase commitment] → SCI-1 → SCI-2
  → SCI-3 → SCI-4 → SCI-5 → RESEARCH_COMPLETE
                ↘ SCI-0.5 (Phase 3, Option B only)
```

### Package ownership (P8)

Each package is created by exactly one state. Creating it elsewhere is a protocol violation.

| Package | Created by | Never contains |
|---|---|---|
| `data/` | `SCI-0` | features, model logic |
| `pocket/` | `SCI-1` | featurization, prediction |
| `features/` | `SCI-1` | I/O, training |
| `eval/` — metrics, calibration | `SCI-1` | training |
| `model/` | `SCI-2` | training loop, I/O |
| `train/` | `SCI-2` | model mathematics |
| `eval/` — degeneracy battery, seals | `SCI-2` | training |
| `explain/` | `SCI-2` if Phase 2 committed, else `SCI-3` | model definition |
| `kg/` | `SCI-4` (Phase 3 only) | anything outside Constitution §5.2 |

`eval/` is deliberately split: metrics score the `SCI-1` baselines; the degeneracy battery tests the `SCI-2` model. This is the one authorized exception to one-package-one-state.

---

| | |
|---|---|
| **SCI-0** | Owner: Constitution §3.1, §9.1 · Data audit, pre-registration, phase commitment |

*Sequencing note.* Blocking. `data/` is created here because the audit requires provenanced loading, censoring and assay filtering. Structure *inventory* for Q5 is in scope; pocket *derivation* is not — that is `SCI-1`. All six sealed artefacts are produced here into the infrastructure Foundation built.

**Creates.** `data/`.
**Validation.** Q1–Q16 answered. Six artefacts sealed and hash-verified. Phase committed and recorded in the `CLAUDE.md` header.
**Failure.** A seal created after any model code exists; an audit number without provenance.
**Exit gate.** ✓ Q1–Q16 ✓ seals verified ✓ phase committed ✓ gate outcome recorded ✓ R1 not triggered ✓ `data/` modules `Gate-verified`

---

| | |
|---|---|
| **SCI-0.5** | Owner: Constitution §3.2 · Orthosteric mutation-propagation test |

*Sequencing note.* Phase 3, Option B only. Independent of the model, so may run in parallel with later states.

**Validation.** Five replicates per condition; §3.2.3 controls satisfied; outcome A, B or C recorded.
**Failure.** A conclusion from effects inside the within-condition null; a 100-ns negative reported as a true negative.
**Exit gate.** ✓ outcome recorded ✓ Option B live, conditionally live, or retired

---

| | |
|---|---|
| **SCI-1** | Owner: Constitution §9.3, §4.6, §2.1 · Pocket derivation, representation, baselines, scoring metrics |

*Sequencing note.* Baselines and the metric layer precede any learned component (SI3). The Constitution gate here can disqualify the learned component entirely, so building the model first risks unjustifiable work.

**Creates.** `pocket/`, `features/`, `eval/` (metrics, calibration).
**Validation.** Pocket definitions are ligand-ensemble unions with rotamer states, never apo. Path A implemented. Three baselines evaluated: ligand-only, nearest-neighbour Tanimoto, proteochemometric.
**Failure.** An apo-derived pocket; a sequence- or backbone-only representation; Path B without the §4.6 record.
**Exit gate.** ✓ pocket definitions versioned ✓ Path A accepts an arbitrary ATP site and a mutated structure ✓ baselines recorded ✓ **no baseline meets S2** — if one does, the learned component is unjustified and this is a STOP

---

| | |
|---|---|
| **SCI-2** | Owner: Constitution §9.4, Part IV · Comparative model, training, degeneracy battery |

*Sequencing note.* Full §4.3 battery excluding Tier 2 and transfer. `explain/` and S10 are built here **only if Phase 2 is committed**; otherwise `SCI-3` owns them.

**Creates.** `model/`, `train/`, `eval/` (battery, seals); `explain/` if Phase 2.
**Validation.** S2, S3, S4, S6 against sealed thresholds via §15.3. Plus S9c, S10a, S10b if Phase 2.
**Failure.** Any §1.4 kill criterion — S2 or S3 failure means comparative learning did not occur; S6 failure means apo-degeneracy requiring rebuild.
**Exit gate.** ✓ generation frozen ✓ S2, S3, S4, S6 pass ✓ battery complete ✓ (Phase 2: S9c, S10a, S10b)

**Phase 1 terminus** (§17).

---

| | |
|---|---|
| **SCI-3** | Owner: Constitution §9.5 · Knowledge extraction and the first Tier 2 query |

*Sequencing note.* The first Tier 2 access in the project's life. Follows §15.2 exactly; the pre-registered prediction is committed before the query executes.

**Creates.** `explain/` if not created at `SCI-2`.
**Validation.** S1 across held-out families; S9a/S9b against the sealed rule set with blinded adjudication; one logged Tier 2 evaluation with the covariate-adjusted gradient report.
**Failure.** S9c failure voids S9a/S9b; an unlogged query is a constitutional violation.
**Exit gate.** ✓ S1, S5, S9a, S9b ✓ S8a, S8b, S8c reported ✓ exactly one query logged against the frozen generation ✓ S8c descriptive, no significance test (SI15)

**Phase 2 terminus** (§17).

---

| | |
|---|---|
| **SCI-4** | Owner: Constitution §9.6 · Cross-family transfer, knowledge layer, E3 promotion |

*Sequencing note.* Requires a **new** frozen generation — `SCI-3`'s budget is spent. `kg/` is created here, after the evidence it stores exists; built earlier it would hold nothing and risk influencing training (SI6).

**Creates.** `kg/`.
**Validation.** Sealed second family evaluated with no retuning (S7); second logged query; L4 alchemical mutation promoting Candidate Determinants to E3; S8c over the combined gradient.
**Failure.** Retuning voids S7; a Determinant promoted on E1/E2 alone violates §5.4.
**Exit gate.** ✓ S7 without retuning ✓ second query logged against a new generation ✓ promotions carry E3 or E4 ✓ §9.6 honesty clause satisfied

---

| | |
|---|---|
| **SCI-5** | Owner: Constitution §9.7, §6.2, §6.3 · Prospective experimental test |

*Sequencing note.* Requires the §6.3 experimental arm. Without it the project is computation-only, cannot reach Design Rule status, and this state is not entered — the limitation is recorded in the completion report.

**Validation.** Every molecule carries the four §6.2 fields before evaluation. Synthesis and assay against the Class I panel plus mTOR. E4 edges recorded.
**Failure.** A molecule evaluated without a pre-registered falsifying observation; a Design Rule claimed without an E4 edge.
**Exit gate.** ✓ predictions committed before assay ✓ results recorded with provenance ✓ Design Rule promotions carry E4

---

## 17. Termination and completion artifact

`RESEARCH_COMPLETE` is reached at the terminus the committed phase fixes (§3), with every executed state's Exit gate satisfied and all §7, §9 invariants holding.

**Completion produces `docs/SCIENTIFIC_COMPLETION_REPORT.md`**, without which the protocol is not complete:

```
Protocol version:              1.0
Constitution version:          from GOVERNANCE_VERSIONS.md
States executed:               + gate outcome for each
States not executed:           + reason (phase, Option B, no experimental arm)
Achieved phase:                Phase 1 | 1+2 | Full
Claim ceiling:                 per Constitution §9.0 for the achieved phase
Criteria met / not met:        S1–S10, each with evidence reference
Model generations:             every hash, with its Tier 2 queries
Final seal verification:       every artefact, hash, verification result
Evidence inventory:            Candidate Determinants · Determinants + class · Design Rules + E4
Remaining limitations:         explicitly including any §9.6 honesty-clause obligation
Publication readiness:         yes/no + what is outstanding
```

**On completion this protocol terminates.** No further state may be entered; `docs/SCIENTIFIC_STATE.md` records `RESEARCH_COMPLETE` and is not subsequently modified.

```
RESEARCH_COMPLETE + completion report
  ↓
Publication lifecycle ADR (ENG §16) — thresholds freeze; deprecation policy begins
  ↓
Publication → Reference Implementation → Maintenance → Archive
```

**A terminus reached by descoping is a legitimate outcome, not a failure.** Constitution §9.0: a Phase 1 result honestly described is worth more than three phases attempted and none completed. The claim ceiling for the achieved phase is binding, and §9.6's honesty clause governs how the deliverable is described.

---

## Appendix A — Artifact traceability

The canonical dependency graph. It is a **DAG, not a chain**: pocket version and dataset snapshot converge on a model generation, and a Determinant requires both a Candidate and a perturbational edge.

```
        Dataset snapshot ──┐
     (content hash, ENG §13)│
                            ├──→  Model generation  ──→  Evaluation record
        Pocket version  ────┤      (hash, §15.1)          (+ sealed threshold
     (Constitution §5.2 node)│                              verification, §15.3)
                            │            │                        │
      Hyperparameters ──────┘            │                        ▼
                                         │              Selectivity Prediction
                                         │              (Constitution §5.2 node)
                                         ▼                        │
                              Tier 2 query record ────────────────┤
                          (frozen generation + committed          │
                           pre-registration, §15.2)               ▼
                                                        Candidate Determinant
                                                        (class E1, §5.3)
                                                                  │
                                          + perturbationally_tested_by edge
                                            E2 (§15 S10) → still Candidate
                                            E3 (alchemical) or E4 (experiment)
                                                                  ▼
                                                            Determinant
                                                     (Constitution §5.4)
                                                                  │
                                     + ≥2 independent series + ≥1 E4 edge
                                                                  ▼
                                                            Design Rule
```

**Constraints on this graph.**

- **Node types are capped.** Only the eight types of Constitution §5.2 exist in the knowledge layer. There is no "representation version" node — representation is part of the model generation (architecture + data + hyperparameters). Adding a node type requires the §5.1 fourth-query test, an ADR, and a retirement.
- **Non-graph artefacts** — dataset snapshots, model generations, experiment records, Tier 2 query log lines — live in ENG §6, §12 and §13. They are referenced by graph nodes, not stored as nodes.
- **Every edge is directional and append-only.** A contradicting edge is added; the original is never removed (Constitution §5.4).
- **Every prediction references the pocket-definition and model-generation versions that produced it** (Constitution §5.4). A prediction without both is unattributable and, per ENG §7, is deleted rather than archived.
- **The E1 → Determinant path cannot be shortened.** E1 and E2 in combination do not reach E3 (Constitution §2.5). S10 provides E2 only, which is why passing it promotes nothing.

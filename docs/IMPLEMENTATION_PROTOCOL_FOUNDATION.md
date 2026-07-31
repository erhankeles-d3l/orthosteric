# Implementation Protocol — Repository Foundation

**Version 1.0** · First-class governance document · `docs/IMPLEMENTATION_PROTOCOL_FOUNDATION.md`

**This is not Constitution Stage 0.** Constitution §3.1 and §9.1 reserve "Stage 0" for the scientific feasibility audit and pre-registration. This protocol uses no Constitution stage or phase number.

| Field | Value |
|---|---|
| **Owns** | The sequence in which the repository is established |
| **Does not own** | Any engineering policy, any scientific rule |
| **Authority** | `ADR-0001` (§2) |
| **Inputs** | Constitution v4.6 · `CLAUDE.md` · `ENGINEERING_STANDARDS.md` · `ADR-0001` |
| **Outputs** | Reproducible repository · Phase 1 CI · configuration framework · seal infrastructure · one production module |
| **Constitution phase** | Not committed; Foundation does not commit it |
| **Succeeded by** | Lifecycle transition ADR, then Constitution Stage 0 |

---

## 1. Ownership and conflict resolution

```
Constitution  →  Accepted ADR  →  CLAUDE.md  →  Foundation Protocol
  →  Engineering Standards  →  Project Specification
```

| Document | Owns |
|---|---|
| Constitution v4.6 | Scientific rules |
| `CLAUDE.md` | Agent execution rules |
| **Foundation Protocol** | **Repository implementation sequence** |
| `ENGINEERING_STANDARDS.md` | Engineering policy |
| `PROJECT_SPECIFICATION.md` | Functional requirements |

**A conflict between this protocol and ENGINEERING_STANDARDS should be impossible.** This document states *when* and *in what order*; that one states *what* and *how*. A genuine conflict is evidence the domain boundary was breached, and the correct response is to fix the boundary — not to apply precedence and continue. The ordering above is a backstop.

## 2. Authority (blocking)

Constitution §3.1 forbids infrastructure work before the data audit. **Foundation requires `ADR-0001` before any work begins.**

**Why an exception is defensible.** Constitution Stage 0 produces artefacts requiring infrastructure that already exists: an audit report needing provenance (§3.3), six sealed artefacts whose integrity must be independently verifiable, an append-only query log. A seal-timestamp check added after seals exist cannot distinguish a legitimate seal from a backdated one.

**Why it must be capped.** R1 is a fatal kill risk. The exception authorizes only infrastructure that survives a physics-only redesign — configuration, provenance, seals, CI, documentation and testing all remain necessary in that outcome. That argument belongs in ADR-0001's Evidence field in those terms.

**ADR-0001 must also record**, under Review trigger: what happens if R1 fires. Foundation is enterable once (§14, `Any → Foundation` illegal), so a physics-only redesign requiring infrastructure changes is not a return to Foundation and needs its own protocol or an amendment. Decide that path in the ADR rather than under pressure.

**Cap (binding).** ADR-0001 authorizes only the states of §14. Anything else requires its own ADR.

## 3. Domain boundary

This protocol states **sequence and process**. It restates no requirement owned elsewhere.

Where a state says "per ENG §n," the owning section is authoritative and complete; this document adds only ordering. Where a state carries a **Sequencing note**, that note is protocol content — it explains why the work happens at that point rather than later, and appears nowhere else.

## 4. Repository invariants

Verified after **every** task (§9 step 13). Any violation is a protocol halt (§12).

| # | Invariant |
|---|---|
| I1 | No scientific code — no model, featurization, pocket, descriptor or algorithm |
| I2 | No data processing; no dataset in the repository |
| I3 | No Tier 2 handling; `data/tier2/` empty |
| I4 | No training, inference or evaluation metrics |
| I5 | No scientific or ML dependency added. Foundation pins only what Foundation uses; RDKit, PyTorch and CUDA are added later by the stage that needs them, each per ENG §9 |
| I6 | No GPU, HPC, container, DVC or MLflow configuration |
| I7 | No experiment executed; `logs/runs/` empty |
| I8 | No knowledge-layer code; `kg/` absent |
| I9 | Constitution phase uncommitted |
| I10 | No unresolved `<FILL` marker in any document |

## 5. Protocol invariants

Properties of execution rather than of the repository. Violation is a protocol halt (§12).

| # | Invariant |
|---|---|
| P1 | Exactly one active FSM state |
| P2 | Exactly one logical objective in progress |
| P3 | Exactly one commit per completed objective |
| P4 | Exactly one task report per objective |
| P5 | Exactly one satisfied Exit gate per state transition; no state skipped, none revisited without §11 |
| P6 | Exactly one owning document per requirement; this protocol restates none |

## 6. Foundation stop conditions

In addition to `CLAUDE.md` §2. **Stop immediately; do not continue.**

- FSM state in `docs/FOUNDATION_STATE.md` does not match observed repository state
- `ADR-0001` absent or not Accepted
- an ADR required by the current task is absent or not Accepted
- the current state's Exit gate is unmet and the task would advance state
- CI is red
- any invariant in §4 or §5 is violated
- the task lies outside Foundation scope (§7 classification returns STOP)
- a document required by the current state is absent or unreadable
- the previous objective has no task report

On stopping: state which condition fired, the observed versus expected state, and what is required to resume.

## 7. Task classification

Classify before implementing. Exhaustive; no fall-through.

| Class | Action |
|---|---|
| Repository · Environment · Tooling · Configuration · Testing · CI · Documentation · Infrastructure | Continue, if the current state owns the work |
| Bug in a Foundation artefact | Continue; no ADR |
| Refactor | Continue; `CLAUDE.md` §10 applies |
| Architecture — new abstraction, dependency, top-level directory, `Makefile` contract change | **ADR before implementing** |
| Scientific — anything touching §4 | **STOP** |
| Unclassifiable | **STOP** — report and request clarification |

## 8. Command and state-inspection policy

**Commands.** Only `make` targets (ENG §22). Foundation permits no exception, including for diagnosis. A broken target is fixed in the `Makefile` in the same change.

**Never infer repository state.** Before acting on the existence of a directory, module, ADR, `Makefile` target, CI workflow, config key or test, **verify it by inspection.** A document describing an artefact is not evidence the artefact exists. This is `CLAUDE.md` §1 applied to the filesystem: an assumed path is an invented path.

## 9. Execution algorithm

```
 1  Read CLAUDE.md.
 2  Read docs/FOUNDATION_STATE.md; verify it matches observed state (§8). Mismatch → STOP.
 3  Classify the task (§7). STOP → stop and report.
 4  Read the ENGINEERING_STANDARDS sections the current state cites.
 5  Search docs/adr/ for an Accepted decision covering it (CLAUDE.md §5).
 6  Verify authorization by ADR-0001 and that the task lies within the §2 cap.
 7  Verify the current state owns the task. If not → STOP.
 8  Confirm exactly one logical objective (P2).
 9  Write tests first (CLAUDE.md §9).
10  Implement.
11  Update documentation in the owning document only (ENG §18).
12  Run make ci-local. Red → §11.
13  Verify the state's Exit gate, then all §4 and §5 invariants.
14  Write the task report (§13); update docs/FOUNDATION_STATE.md.
15  Commit (P3).
16  Advance state only if the Exit gate is fully satisfied (P5); else take the next task in the same state.
```

Steps 12–14 are never deferred to the end of a batch.

## 10. Execution state

`docs/FOUNDATION_STATE.md`, committed with every task.

```
FSM state:            <one of §14>
Current objective:
Completed states:
Blocked objectives:   objective + blocking condition + what would unblock
Pending ADRs:         number + status
Pending validation:   Exit-gate items outstanding in the current state
Last green CI:        commit SHA
```

**Lifecycle stage is not recorded here.** The `CLAUDE.md` header owns it (ENG §18); this file does not restate it.

## 11. Recovery

### 11.1 After interruption

```
Read docs/FOUNDATION_STATE.md
  ↓
Verify HEAD matches the recorded Last green CI, or a later commit with a task report
  ↓
Verify CI green at HEAD
  ↓
Verify the recorded FSM state against observed repository state (§8)
  ↓
Resume the current state's outstanding objectives
```

**Never infer previous progress** from the presence of files. If the state file and the repository disagree, **STOP** — do not decide which is correct. Report both and request instruction.

### 11.2 After red CI

```
Stop progression — start no new objective
  ↓
Restore green: revert, or fix forward only if the fix is smaller than the revert
and touches no other state
  ↓
make ci-local
  ↓
Re-verify the current Exit gate and all §4, §5 invariants
  ↓
Resume
```

**Never** disable, skip or weaken a check to restore green (`CLAUDE.md` §3). Revisiting a completed state requires recording the corrective change under Blocked objectives (P5).

## 12. Violation classes

Treated differently; do not conflate.

| | **Implementation failure** | **Protocol violation** |
|---|---|---|
| Examples | test red, mypy error, import failure, docs build warning | state skipped, raw `pytest`, tests written after implementation, missing task report, two objectives in one commit, requirement restated from another document |
| Meaning | the artefact is wrong | the execution process is wrong |
| Response | §11.2 rollback; fix; continue | **halt**; record in `FOUNDATION_STATE.md`; corrective change; re-verify the affected Exit gate before any new objective |
| Reportable | task report CI field | task report Blocking issues, and named explicitly |

An implementation failure is normal. A protocol violation means subsequent work cannot be trusted until corrected.

## 13. Task report

**Extends** the six-line audit of `CLAUDE.md` §17 — that audit is written as specified, then:

```
--- Foundation extension ---
FSM state (before → after):
Files modified:
Tests added:
CI status:            green | red + reason
Exit gate:            met | items outstanding
Invariants:           I1–I10 pass/fail · P1–P6 pass/fail
Violation class:      none | implementation | protocol (§12)
Next objective:
Blocking issues:
```

## 14. State machine

Deterministic. No state skipped; no completed state revisited without §11.2.

Each state records **Owner** (the section defining the work), **Objective**, **Validation**, **Failure**, **Outputs**, **Exit gate**, and a **Sequencing note** only where the ordering is non-obvious. Implementation detail lives in the Owner section.

**`make ci-local` obligation.** Created at FND-3, initially running only the checks that exist. **Every later state adding a check registers it in `ci-local`** — carried in each Outputs line. By FND-11, `ci-local` and CI are identical, which the FND-7 Exit gate verifies.

```
UNINITIALIZED → FND-1 REPOSITORY → FND-2 ENVIRONMENT → FND-3 MAKEFILE
  → FND-4 SEALS → FND-5 CONFIG → FND-6 TESTS → FND-7 CI → FND-8 DOCS
  → FND-9 BOUNDARIES → FND-10 FIRST_MODULE → FND-11 VALIDATED → COMPLETE

State identifiers `FND-n` are immutable and are the form used in ADR cross-references.
They deliberately avoid the Constitution's `S1`–`S10` success-criteria namespace.
```

**Legal transitions.** Sequential only, on Exit gate satisfaction. `COMPLETE → lifecycle ADR → Constitution Stage 0` (§15). Illegal: skipping a state; `Any → Foundation`; `Foundation → Stage 1` or beyond.

---

| State | Owner | Objective |
|---|---|---|
| **FND-1 REPOSITORY** | `CLAUDE.md` §15; ENG §3 | Create the canonical tree, limited to directories FND-2–FND-11 require |

*Sequencing note.* `sealed/` and `logs/` are created here because FND-4 depends on them. `src/<pkg>/` is created without sub-packages — FND-10 owns package creation. `kg/` is not created (I8).
**Validation.** Tree conforms; no directory present that ENG §3 would require an ADR for.
**Failure.** An invented path; a directory with no consuming state.
**Outputs.** Tree · `README.md` stub · `.gitignore` · empty `docs/adr/`.
**Exit gate.** ✓ tree conforms ✓ no ADR-requiring directory ✓ invariants pass

---

| State | Owner | Objective |
|---|---|---|
| **FND-2 ENVIRONMENT** | ENG §4, §9 | Configure the pinned, reproducible environment |

**Validation.** `make install` reproduces from the lockfile alone on a clean checkout. I5 holds.
**Failure.** A Python version range; uncommitted or hand-edited lockfile.
**Outputs.** `pyproject.toml` · lockfile · `.pre-commit-config.yaml`.
**Exit gate.** ✓ reproducible from lockfile ✓ Python exactly pinned ✓ I5 holds

---

| State | Owner | Objective |
|---|---|---|
| **FND-3 MAKEFILE** | ENG §22 | Implement all seven target contracts |

*Sequencing note.* Built before any tooling is invoked by hand, so no invocation is ever discovered rather than declared. `ci-local` runs the checks existing now and is extended by each later state.
**Validation.** Each target satisfies its ENG §22 contract; only `format` modifies source.
**Failure.** A weakened contract (`CLAUDE.md` §3); any tooling invoked outside `make` from this point (§8).
**Outputs.** `Makefile`.
**Exit gate.** ✓ seven targets ✓ contracts satisfied ✓ `make ci-local` green ✓ no raw invocation used

---

| State | Owner | Objective |
|---|---|---|
| **FND-4 SEALS** | `CLAUDE.md` §7; ENG §8 | Seal directory, manifest, timestamp check, log tree, audit logger |

*Sequencing note.* Built before Constitution Stage 0, which creates the artefacts these protect. The timestamp check is written while `src/<pkg>/train/` does not exist, so it is correct for every seal thereafter; added later it could not distinguish a legitimate seal from a backdated one. The sealed-config **loader** is not built here — it belongs to FND-5.
**Validation.** Timestamp check correct on an empty `sealed/` and once `train/` exists. Audit logger appends, cannot truncate. `logs/tier2_queries.jsonl` present and empty (I3, I7).
**Failure.** A seal created before the check exists; a truncating handler.
**Outputs.** `sealed/MANIFEST.md` · logging module · tests · **timestamp check registered in `ci-local`**.
**Exit gate.** ✓ check passes on empty `sealed/` ✓ logger append-only under test ✓ registered

---

| State | Owner | Objective |
|---|---|---|
| **FND-5 CONFIG** | ENG §5 | Configuration framework and the non-composable sealed-config loader |

*Sequencing note.* The sealed loader is built now, not when thresholds first exist. Deferred, the first pre-registered thresholds would be read through an overridable path and Constitution §1.4 would be unenforceable for exactly the seals that matter most.
**Validation.** Unknown key raises; CLI override against a sealed config raises; resolved config hashes deterministically.
**Failure.** Any hardcoded path, threshold or hyperparameter in `src/`; a sealed config reachable through normal composition.
**Outputs.** `configs/` · schema module · sealed loader · tests · **hardcoded-value lint registered in `ci-local`**.
**Exit gate.** ✓ unknown keys rejected ✓ sealed override rejected ✓ hash deterministic ✓ registered

---

| State | Owner | Objective |
|---|---|---|
| **FND-6 TESTS** | ENG §3, §4 | Test framework, coverage, `tests/` mirror |

**Validation.** `make test` green; mirror check passes.
**Failure.** A scientific test, or one asserting a scientific numerical value (I1).
**Outputs.** `tests/` mirror · coverage config · **mirror check registered in `ci-local`**.
**Exit gate.** ✓ `make test` green ✓ mirror passes ✓ no scientific test

---

| State | Owner | Objective |
|---|---|---|
| **FND-7 CI** | ENG §20 (Phase 1 table); ENG §17 | Implement the complete Phase 1 CI and branch protection |

*Sequencing note.* The S8c-no-significance-test grep is written now although no reporter exists — it costs nothing here and cannot then be forgotten when the reporter is built.
**Validation.** Every Phase 1 check runs, and a deliberately introduced violation of each is caught. Nothing from Phase 2 or 3 present (I6).
**Failure.** A check that only warns; a Phase 2 or 3 check added early.
**Outputs.** `.github/workflows/` · branch protection · **all Phase 1 checks registered in `ci-local`**.
**Exit gate.** ✓ complete ENG §20 Phase 1 set present and failing correctly when violated ✓ `make ci-local` equals CI ✓ no Phase 2/3 check

---

| State | Owner | Objective |
|---|---|---|
| **FND-8 DOCS** | ENG §18, §19 | Documentation infrastructure and changelog |

*Sequencing note.* `CHANGELOG.md` starts here and is maintained from this commit onward rather than retrofitted.
**Validation.** `make docs` green under strict mode; `docs/api/` generated; no normative content duplicated across documents.
**Failure.** A hand-edited `docs/api/`; a tolerated strict-mode warning.
**Outputs.** `mkdocs.yml` · `docs/` structure · `CHANGELOG.md` · **strict build registered in `ci-local`**.
**Exit gate.** ✓ `make docs` green ✓ nav complete ✓ no duplicated normative content ✓ CHANGELOG live

---

| State | Owner | Objective |
|---|---|---|
| **FND-9 BOUNDARIES** | ENG §2 (contracts) | Implement contracts 1, 2, 4; write contract 3 inert |

*Sequencing note.* Contracts are implemented before production code — retrofitting them onto an existing import graph means discovering violations that then get negotiated. Contract 3 is written but inert because `data/tier2/` and `train/` do not exist; verify here that it activates without restructuring, since it is expressed over module paths the canonical tree already fixes.
**Validation.** Contracts 1, 2, 4 pass and catch deliberate violations. Contract 3 present and provably activatable.
**Failure.** A contract expressed over paths that would need layout changes to enable.
**Outputs.** Contract configuration · **contracts registered in `ci-local`**.
**Exit gate.** ✓ 1, 2, 4 enforced ✓ 3 activatable ✓ deliberate violations caught

---

| State | Owner | Objective |
|---|---|---|
| **FND-10 FIRST_MODULE** | ENG §2 (package standard), §7 (provenance) | One minimal production module validating the architecture |

*Sequencing note.* Create only the sub-package the module needs; a package whose Constitution-section README cannot be honestly written is not created. Recommended module: the provenance-record writer in `data/` — it exercises config → typed object → provenanced output → audit log, and Constitution §3.3 requires provenance on the audit's first record, so it is used immediately rather than being scaffolding. A synthetic no-op validates the toolchain and nothing else.

**This state does not change lifecycle stage.** The transition is a separate governance act (§15).

**Validation.** Type checks strictly; tests preceded implementation; documented per ENG §2; emits every ENG §7 field.
**Failure.** A package without an honest Constitution-section README; `kg/` created (I8); scientific logic (I1).
**Outputs.** One module · its tests · package README.
**Exit gate.** ✓ green under all targets ✓ tests preceded implementation ✓ only needed packages exist ✓ lifecycle stage unchanged

---

| State | Owner | Objective |
|---|---|---|
| **FND-11 VALIDATED** | — | Verification only; no implementation |

**Validation.** From a clean checkout: `make install`, `test`, `lint`, `typecheck`, `docs` all pass; CI green on a PR into `develop`; config loads and the sealed loader rejects an override; imports and all contracts pass; audit logger and provenance writer produce complete records; every §4 and §5 invariant holds.
**Failure.** Any check passing only on a warm environment; any invariant violated.
**Outputs.** Validation record in the task report; state set to `VALIDATED`.
**Exit gate.** ✓ every item verified from a clean checkout

---

## 15. Termination and exit

`COMPLETE` is reached when: state is `VALIDATED`, every Exit gate FND-1–FND-11 is satisfied, `ADR-0001` is Accepted, and all §4 and §5 invariants hold.

**On reaching `COMPLETE` this protocol terminates.** No further Foundation task may begin. `docs/FOUNDATION_STATE.md` records `COMPLETE` and is not subsequently modified.

**Exit sequence** — lifecycle change is a governance act, isolated from implementation:

```
Foundation COMPLETE
  ↓
Lifecycle transition ADR (ENG §16) — updates the CLAUDE.md header to Research
  ↓
Constitution Stage 0 — data audit and pre-registration (§3.1)
  ↓
gate: proceed / redesign / stop
```

**Foundation completion is not a scientific gate.** It authorizes no scientific claim and does not satisfy Constitution Stage 0, whose gate may still invoke R1 and retire much of what Foundation built. `ADR-0001` accepts that risk explicitly.

The only legal successor to `COMPLETE` is the lifecycle transition ADR, and after it, Constitution Stage 0.

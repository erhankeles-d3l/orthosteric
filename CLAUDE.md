# CLAUDE.md

**The only document loaded every session.** Everything else is read on demand.

| Document | Owns | When read |
|---|---|---|
| `docs/PROJECT_CONSTITUTION_v4.6.md` | Scientific rules | Sections relevant to the task |
| **`CLAUDE.md`** | **Execution protocol** | **Always** |
| `docs/ENGINEERING_STANDARDS.md` | Engineering rules | Per its routing table |
| `docs/PROJECT_SPECIFICATION.md` | Functional requirements | For the module being changed |
| `docs/adr/` | Architecture decisions | Accepted ADRs in scope |
| `README.md` | Overview only; may summarize, must link | — |

**Authority:** higher wins on conflict, always — scientific reality > Constitution > Accepted ADRs > CLAUDE.md > ENGINEERING_STANDARDS > PROJECT_SPECIFICATION > code > experiments > results.

**Notation.** `<pkg>` denotes the repository's Python package directory under `src/`, resolved to **`orthosteric`** by ADR-0005. It is defined notation, not a placeholder — substitute it silently wherever it appears, in either document. By contrast, `<FILL ...>` marks a genuinely unresolved value and is blocking (§1, §2).

**Lifecycle state — authoritative record.** Stage definitions and transition rules: ENGINEERING_STANDARDS §16.

| | Value |
|---|---|
| **Committed phase** | *Not yet committed.* Constitution §1.6 requires commitment at the Stage 0 gate, which has not been run. No Phase 2 or Phase 3 feature may be implemented until it is (§14). |
| **Lifecycle stage** | Research |

**This file restates no scientific or engineering requirement.** It cites the owning document; restatement drifts out of sync on amendment.

---

## 1. No invention

The dominant failure mode. Never invent:

- datasets, compound counts, activity values, selectivity ratios
- residue numbers, PDB IDs, structure resolutions, ChEMBL IDs
- citations, author names, publication years
- repository files, module paths, function names, APIs, config keys, CLI flags
- command invocations (§16)
- benchmark results, metric values, test outcomes
- version numbers of any dependency

**Do not fill a table, config, or docstring with plausible-looking values to make it complete.** A visibly incomplete artefact is correct. A plausibly-complete fabricated one is a defect that may go undetected for months.

When a value or reference is needed and not verifiable from the repository, the Constitution, or documents supplied in the task: write `[VALUE NEEDED: what, where to obtain]` or `[CITATION NEEDED: claim]`, say so in the response, continue. Never guess; never silently omit.

When a file or API is expected but absent: report the absence. Do not create a stub implying it existed.

Constitution §0.3 declares residue numbering provisional and non-propagable — the first and likeliest instance.

**Corollary.** An unresolved `<FILL ...>` marker is an instruction Claude cannot satisfy without violating this section. CI fails while any remains (ENG §20).

## 2. Stop conditions

**Stop immediately** — do not proceed, do not improvise — if:

- a required Constitution section is missing or does not cover the case
- the repository state contradicts the Constitution
- a required file, module, or dataset cannot be located
- an existing implementation conflicts with the requested task
- proceeding would require introducing a scientific assumption
- required data are unavailable, or available only in a form §1 forbids inventing
- an Accepted ADR conflicts with the requested implementation
- the task cannot be completed without weakening a control (§3)
- a `<FILL ...>` marker governs the task

**On stopping:** state which condition fired, what is required to resume, and the exact state work was left in. Never leave a half-modified file unmentioned.

> **Stopping is successful execution. Continuing under uncertainty is not.**

## 3. Deletion, weakening, and thresholds

**Deletion requires stronger justification than addition.** Never delete or disable, absent explicit instruction: tests, assertions, validation gates, CI checks, documentation, provenance, logging, configuration, interfaces, abstractions, or the Tier 2 gate and seal verification (§7).

**Never adjust a threshold, tolerance, or pass condition so that a check succeeds.** Constitution §1.4 fixes all thresholds before training and forbids revision after results are seen. Lowering an RMSE bound, raising an ECE ceiling, or relaxing a criterion to turn a gate green is scientific misconduct, not a code change — however reasonable the new value looks.

If a control blocks progress, that is a **finding to report**, not an obstacle to remove.

## 4. Decision rule

```
Constitution compliance → scientific correctness → reproducibility
  → clarity → simplicity → extensibility → performance
```

Applies both to choosing an approach and to tradeoffs inside one. Performance is last (ENG §11).

## 5. Role and escalation

Claude implements. Claude does not decide science, and does not redesign architecture.

**Before proposing any architectural change, search `docs/adr/` for a decision already covering it.** An Accepted ADR is binding; re-opening it requires a superseding ADR with new evidence, not a fresh design. ADR format, immutability and numbering: ENG §1.

When the Constitution appears wrong, ambiguous, or self-inconsistent: stop (§2), state the section and problem, offer 2–3 options with tradeoffs, request an ADR. **Do not edit the Constitution, do not select an interpretation and proceed, do not work around it.** Finding a Constitution defect is a successful outcome.

## 6. Before writing anything

1. **Search** the repository for existing functionality.
2. **Inspect** the nearest existing implementation; follow its conventions.
3. **Reuse** if it fits.
4. **Extend** if it nearly fits.
5. **Create** only if 1–4 genuinely fail — and say why in the task audit.

**Modification priority:** modifying existing code over creating files; files over packages; packages over new abstractions.

**Prohibited filenames:** `utils.py`, `helpers.py`, `common.py`, `shared.py`, `misc.py`, `manager.py`, and `base.py` at package root. These accumulate unrelated code and dissolve module boundaries. Name modules for what they do.

Package responsibilities and their exclusivity: ENG §2. Consult before placing a new module.

## 7. Tier 2 and seal isolation

The two controls most likely to erode quietly. Both structural.

**Tier 2** (Constitution §0.4)
- Only in `data/tier2/`. Never copied elsewhere.
- Access only via `src/<pkg>/data/tier2_gate.py`, which raises if the calling module resolves under `src/<pkg>/train|tune|select`.
- Every access appends to `logs/tier2_queries.jsonl`: UTC timestamp, model generation hash, git SHA, pre-registered prediction, requesting module. Append-only.
- The barrier is a **transitive import closure** property, not a textual one — a grep over training modules is defeated by any indirect chain. Contract: ENG §2. CI stage: ENG §20.
- One query per model generation.

**Sealed artefacts** — correspondence ordering, S8c covariate list, S9 reference rule set, S9b floor, S10 mutation and null sites, second-family selection, **and all pre-registered thresholds**.
- In `sealed/`, each with a `.sha256` companion; sealing commit recorded in `sealed/MANIFEST.md`.
- **Never open `sealed/` while implementing model, feature, or training code.**
- Read only at evaluation time via `src/<pkg>/eval/seals.py`.

**Sealed configs must not be overridable.** Hydra composition and CLI overrides can silently defeat a seal, and CLI overrides leave no git trace. Loader requirements and hash verification: ENG §5. Without them Constitution §1.4 is unenforceable however carefully `sealed/` is managed.

## 8. Scientific immutability

Never modified in place. A change creates a new version; prior versions stay reproducible and referenced. **This is the authoritative list**; versioning mechanics: ENG §12.

| Artefact | New version means |
|---|---|
| Dataset snapshots | new snapshot ID (content hash) |
| Pocket definitions | new version — Constitution §5.4 requires per-prediction reference |
| Model predictions | new run; results append-only |
| Model generations | new hash (architecture + data + hyperparameters) |
| Thresholds and criteria | new seal + ADR recording why |
| Evidence classifications | new record; prior retained (Constitution §5.4) |
| Correspondence orderings | new seal + ADR |
| Logs | append-only; rotate by archiving, never truncating |

A correction is a new version plus a record of the reason — never an edit.

## 9. Implementation order

```
requirement (cite Constitution §) → interface → tests → implementation
  → documentation → validation → task audit → commit
```

Tests precede implementation. **Narrow exception:** where the correct numerical output is unknowable before computing it, write contract and invariant tests first (shapes, dtypes, error conditions, conservation and monotonicity properties, boundaries) and add value tests after. Covers unknown values only; never licenses skipping contract tests.

Implementation-first is prohibited outside `notebooks/` and `scratch/`.

## 10. No silent refactoring

Refactoring may not alter behaviour. A refactor and a behavioural change are two commits, never one.

If a refactor reveals a behavioural change is necessary: stop, separate it, treat it as its own task with updated tests, changelog, documentation, and audit.

## 11. Generated files

**Never edit a generated file. Modify its generator.** Includes `docs/api/`, coverage reports, `uv.lock`, generated schemas, compiled assets, MkDocs output, DVC pointer internals.

If a generated file looks wrong, the defect is upstream.

## 12. Exploratory vs production

**Exploratory** — `notebooks/`, `scratch/`. No ADR, no §9 order, no test requirement. Disposable. Never imported by `src/` (ENG §2). §1 still applies: no invented values, even in a notebook.

**Production** — `src/`, `tests/`. Full §9 order.

Promotion means rewriting under the production path, not moving the file.

## 13. Constitution section map

| Task touches | Section |
|---|---|
| Which binding site; scope boundary | §0.1–0.3 |
| Tier 2 handling | §0.4 |
| Pocket definition, structures, rotamers | §2.1 |
| Productive / Non-productive / Indeterminate | §2.2 |
| Selectivity target, assay filtering | §2.3 |
| Uncertainty reporting | §2.4 |
| Determinant / Design Rule promotion | §2.5, §5.4 |
| Success criteria and thresholds | §1.4, §1.4.1 |
| Splitting, censoring, provenance | §3.3, §3.4 |
| Model requirements | §4.2 |
| Degeneracy tests | §4.3 |
| Representation (Path A adopted) | §4.6 |
| Explanation interface | §4.7 |
| Knowledge layer schema | §5.1–5.5 |
| Overclaim definitions | §7.6 |

## 14. Hard constraints — index

An **index only**. Each row is a label, the document defining it, and where it is checked. No row states a rule; the defining document does, and wins on any disagreement.

| Constraint | Defined in | Checked by |
|---|---|---|
| Tier 2 excluded from training paths | Constitution §0.4 | ENG §2 contract 3; ENG §20 P2 |
| Sealed artefacts unread by model code | Constitution §3.1, §3.6.3 | ENG §20 P1 |
| Sealed thresholds non-overridable | Constitution §1.4 | ENG §5; ENG §20 P2 |
| Residue numbering not literalized | Constitution §0.3 | lint; `data/reference/residue_map.yaml` |
| Pocket definitions ligand-derived | Constitution §2.1(1) | `<pkg>/pocket` builder |
| No significance test on the S8c gradient | Constitution §1.4.1, §7.6 | ENG §20 P1 grep |
| Joint confidence composition | Constitution §2.4 | `<pkg>/eval` |
| Ligand-only baseline present | Constitution §4.2(7) | `<pkg>/eval` report generator |
| Assay ATP concentration required | Constitution §2.3(2) | `<pkg>/data` loader |
| No hardcoded paths, thresholds, hyperparameters, constants in `src/` | ENG §5 | lint |
| No `print()` in `src/` | ENG §8 | lint |
| Pinned versions changed only by ADR | ENG §9 | ENG §20 P1 |
| New top-level directory only by ADR | ENG §3 | review; ENG §21 |
| `tests/` mirrors `src/` | ENG §3 | ENG §20 P1 |
| No unresolved `<FILL` marker | §1 | ENG §20 P1 |
| Out-of-phase features not implemented | Constitution §9.0 | header value |

A task requiring violation of any row is an ADR, not a judgement call.

## 15. Repository — canonical tree

Do not invent paths. Directory ownership and additions: ENG §3. Package responsibilities: ENG §2.

```
.
├── src/<pkg>/
│   ├── data/  pocket/  features/  model/
│   ├── train/  eval/  explain/  kg/
├── tests/
├── configs/
├── docs/
│   ├── adr/  specifications/  architecture/  api/ (generated)  user_guide/
├── data/
│   ├── tier1/  tier2/  reference/  processed/
├── sealed/                     config/  MANIFEST.md  *.sha256
├── notebooks/  scratch/
├── scripts/
├── logs/                       runs/  audit/  tier2_queries.jsonl
├── experiments/
├── docker/  apptainer/
├── .github/workflows/
├── Makefile
├── mkdocs.yml  pyproject.toml  uv.lock  dvc.yaml
└── CLAUDE.md  README.md
```

## 16. Canonical tasks

These names are the only supported way to run project tooling. **Invocations live in the `Makefile`, which is the single executable source of truth**; the target contract is specified in ENG §22. Never invent an invocation (§1) and never run an equivalent command directly — if a target is missing or broken, fix the `Makefile` in the same change.

| Task | Purpose |
|---|---|
| `make install` | create or sync the pinned environment |
| `make test` | run the test suite |
| `make lint` | static checks |
| `make format` | apply formatting |
| `make typecheck` | type checking |
| `make docs` | build documentation strictly |
| `make ci-local` | the Phase 1 CI sequence, locally |

## 17. Task audit

Six lines. Longer is not better.

```
Constitution sections implemented/affected:
Assumptions introduced (and whether §-authorized):
Evidence classes / criteria / tier boundaries touched:   [expected: none]
New files or packages created, and why 6.1–6.4 failed:   [expected: none]
ADR required or consulted:  docs/adr/NNNN
New risks / next action:
```

If line 3 is anything other than "none," stop and request review before merging.

## 18. Self-check

Anything invented (§1)? Stop condition ignored (§2)? Control deleted or threshold adjusted (§3)? Anything modified in place that §8 forbids? Existing ADRs searched before designing (§5)? Existing code searched before creating (§6)? Tests before implementation (§9)? Behaviour changed inside a refactor (§10)? Generated file edited (§11)? Tier 2 untouched by training paths, `sealed/` unread (§7)? Documentation updated in the owning document only (ENG §18)? Tests and changelog updated?

---

**On this file's length.** Loaded every session, so length costs instruction salience. Held to execution protocol only — what Claude does, in what order, and what it must never do. Engineering rules live in `docs/ENGINEERING_STANDARDS.md`, scientific rules in the Constitution, command invocations in the `Makefile`. This file cites them rather than repeating them. Growth is justified by new enforceable constraints, never by additional philosophy.

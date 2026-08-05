# Engineering Standards

**Authority:** below `CLAUDE.md`, above `PROJECT_SPECIFICATION.md`. **Read on demand.**

**Scope.** Engineering rules applying to anyone writing code here, human or agent. Agent execution protocol is in `CLAUDE.md`; scientific requirements are in Project Constitution v4.6. This document contains neither.

**Notation** (`<pkg>`) and **current lifecycle state** are defined in the `CLAUDE.md` header.

| If the task involves | Read |
|---|---|
| An architectural decision | §1 |
| Package structure, responsibilities, import boundaries | §2 |
| Repository layout; adding a directory | §3 |
| Coding style, typing, docstrings | §4 |
| Configuration | §5 |
| Running or recording an experiment | §6 |
| Writing any output file | §7 |
| Logging | §8 |
| Dependencies and pinned versions | §9 |
| Public API changes or removals | §10 |
| Optimizing anything | §11 |
| Versions and schemas | §12 |
| Data storage and snapshots | §13 |
| Experiment tracking | §14 |
| Containers and HPC | §15 |
| Project stage | §16 |
| Branches and commits | §17 |
| Documentation ownership | §18 |
| Documentation build | §19 |
| CI configuration | §20 |
| Opening a PR | §21 |
| Makefile targets | §22 |

---

## 1. Architecture Decision Records

**Every irreversible or costly architectural decision requires an ADR, written and Accepted before implementation begins.** Constitution §7.1 sets the threshold: irreversible or costly gets a record; reversible gets a commit message.

**Format** — reuses the Constitution §7.1 field set, so the project has one decision-record schema rather than two:

```
# ADR-NNNN — <title>
Status:        Proposed | Accepted | Superseded by ADR-MMMM | Rejected
Decision:
Date:
Alternatives:
Evidence:
Reversibility:  reversible | costly | irreversible
Review trigger:
```

**Rules**

- **ADRs are immutable except for the Status line.** Content is never edited after Acceptance. A changed decision is a new ADR superseding the old one and citing it.
- **Numbers are never reused**, including for Rejected ADRs. Gaps are normal.
- Superseded ADRs remain in the repository. Deleting one destroys the reasoning that justifies current architecture.
- **Search before designing** (`CLAUDE.md` §5).

**Categories.** Every ADR declares one, in its title line as `[Category]`:

| Category | Scope |
|---|---|
| `Architectural` | module boundaries, abstractions, persistence, schemas, dependencies |
| `Scientific` | anything touching Constitution criteria, evidence classes, tiers, thresholds — requires Auditor review (Constitution §7.7) |
| `Process` | protocol exceptions, `Makefile` contracts, CI policy, tooling |
| `Deprecation` | public API removal (§10) |
| `Lifecycle` | stage transitions (§16) |

A `Scientific` ADR may not be authored by the model developer alone.

**ADR required for:** a new runtime dependency or any change to a pinned version (§9); a new top-level directory (§3); a persistence or schema choice; anything affecting reproducibility (seeding, splitting, snapshot policy); any deviation from Constitution §4; a knowledge-layer schema change (Constitution §5.2 requires naming the justifying query **and** a retirement); optimization that changes numerical results (§11); a lifecycle stage transition (§16); a `Makefile` target contract change (§22).

**No ADR for:** file layout within an existing package, behaviour-preserving refactors, test additions, docstrings, dev-only tooling.

## 2. Package structure, responsibilities, and import boundaries

**Authoritative definition of package responsibilities.** Each package under `src/<pkg>/` has exactly one, and they are mutually exclusive:

| Package | Responsibility | Must not contain |
|---|---|---|
| `data/` | loading, provenance, censoring, tier gating | feature construction, model logic |
| `pocket/` | structure handling, ensemble union, rotamer states | featurization, prediction |
| `features/` | feature construction | I/O, training, prediction |
| `model/` | prediction | training loops, I/O, evaluation metrics |
| `train/` | training orchestration | model mathematics, metric definitions |
| `eval/` | evaluation, calibration, degeneracy battery, seal reading | training, feature construction |
| `explain/` | Constitution §4.7 discrete-rule interface | model definition, training |
| `kg/` | knowledge layer (Phase 3) | anything outside Constitution §5.2 schema |
| `policy/` | Decision Policy Layer — classify predictions against configurable project objectives (`ADR-0008`) | evidence loading, harmonization, featurization, model definition, training, criterion evaluation |

A module performing two of these belongs in neither and must be split.

**Every package contains:** `README.md` (purpose, public API summary, Constitution sections served); `__init__.py` declaring `__all__`; `_`-prefixed internal modules; complete type annotations on public functions and classes; module docstrings stating purpose, Constitution section served, inputs, outputs, assumptions, limitations, references; and a matching directory under `tests/` (§3).

If "Constitution section served" cannot be written, the package's necessity is unclear.

**Import contracts, enforced mechanically** via `import-linter` or equivalent:

**Layer order (highest → lowest)**, as enforced in `.importlinter`:
`policy/` → `eval/` → `explain/` → `train/` → `model/` → `features/` →
`pocket/` → `data/` → `runtime/`. `policy/` sits at the top by `ADR-0008` so
that no lower layer can import it — mechanically preventing a project
prioritization threshold from influencing evidence, features, training,
prediction, or criterion evaluation.

1. no cross-package imports of `_`-prefixed internal modules
2. no `src/` import from `notebooks/` or `scratch/`
3. **no path from any training entry point to `data/tier2_gate` or `data/tier2`** — transitive closure, not direct imports
4. no import from a package into one above it in the responsibility order above

Contract 3 is what protects Constitution §0.4. Because these contracts also enforce §10 API boundaries and notebook isolation, the import linter is a Phase 1 dependency, and far cheaper to adopt before the import graph exists than to retrofit onto one.

## 3. Repository layout

The canonical tree is in `CLAUDE.md` §15 — always loaded, because path invention is an every-task failure mode. This section governs it.

- **Directory ownership is exclusive.** Production code only in `src/`; experiment outputs only in `experiments/`; exploratory work only in `notebooks/` and `scratch/`; Hydra configuration only in `configs/`; immutable datasets only in `data/`; specifications only in `docs/specifications/`; decisions only in `docs/adr/`.
- **A new top-level directory requires an ADR.** Directories inside an existing package do not.
- **`tests/` mirrors `src/` exactly.** A test file with no corresponding source module, or a source module with no test file, is a defect. Enforced by the mirror check in §20.
- `data/processed/` must be regenerable from `data/tier1|tier2|reference` plus a recorded config. If it is not, it is source data and belongs elsewhere.

## 4. Coding standards

| Concern | Standard |
|---|---|
| Formatting | Ruff format; no competing formatter |
| Linting | Ruff; rule set in `pyproject.toml` is the single source of truth |
| Typing | mypy `strict`; 100% annotation coverage on public APIs |
| Python | exact minor version pinned in `pyproject.toml` (§9) — **not** a `>=` range |
| Docstrings | Google style, on every public symbol |
| Imports | absolute within the package; no wildcard imports |
| Line length | as configured in `pyproject.toml`; not restated here |

Rationale for the exact Python pin: a version *range* is incompatible with the reproducibility guarantee of §6. If the environment can resolve to more than one interpreter minor version, two runs of the same commit may differ.

Configuration for all of the above lives in `pyproject.toml`. Values are not duplicated here, which would create a second source of truth that drifts.

## 5. Configuration management

Hydra with Pydantic-validated structured configs.

**Composition order** (later overrides earlier):
```
defaults → phase → environment → experiment → CLI overrides
```

- **No duplication.** A key is defined in exactly one layer; lower layers override, never redefine.
- **Every key documented** in its structured-config class docstring.
- **Unknown keys forbidden** — Pydantic `extra="forbid"`. A typo'd override fails loudly rather than passing silently.
- **Every configurable value originates in Hydra.** No `epochs = 100`, `lr = 1e-4`, threshold, or path literal in `src/`.
- **The resolved config is hashed** into the experiment record — the resolved object, not the template.

**Sealed configuration is exempt from composition.** Pre-registered thresholds (Constitution §1.4) load through a dedicated non-composable loader that rejects override keys and CLI overrides. CLI overrides leave no git trace, so an overridable threshold makes the seal unenforceable. Resolved threshold values are hashed into the experiment record (§6) and verified against `sealed/*.sha256` at evaluation time. Isolation rules: `CLAUDE.md` §7.

## 6. Experiment reproducibility

> **Every published figure, table, metric, and model artifact must be reproducible from a single recorded experiment ID.**

For aggregate artefacts this is satisfied by a **manifest run**: an experiment whose record references the constituent run IDs and whose output is the figure or table. A comparison plot spanning three model generations is one manifest run referencing three underlying runs — so the rule holds without exception, and every published artefact has one ID resolving to everything beneath it.

Every experiment writes `logs/runs/<run_id>.json` **before** producing results. A run without a complete record is not an experiment; its outputs are not citable.

| Field | Notes |
|---|---|
| `run_id` | ULID or UUID |
| `utc_started` / `utc_finished` | |
| `git_sha` | dirty tree → refuse to run outside `notebooks/` |
| `config_hash` | fully-resolved config |
| `sealed_threshold_hash` | verified against `sealed/` (§5) |
| `data_snapshot_ids` | content hashes; never mutable paths |
| `model_generation_hash` | architecture + training data + hyperparameters (Constitution §0.4) |
| `seeds` | every stochastic component, explicitly passed; no implicit global seeding |
| `python_version`, `dependency_lock_hash` | |
| `cuda_version`, `driver_version`, `hardware` | GPU model and count, host, scheduler job ID |
| `container_digest` | digest, not tag (§15) |
| `constitution_version`, `adr_versions` | |
| `phase`, `lifecycle_stage` | values per `CLAUDE.md` header |
| `tool_versions` | protonation, docking, MD engines — Constitution §2.1 requires these |
| `tier2_query_ref` | log line reference if Tier 2 accessed, else `null` |
| `constituent_run_ids` | manifest runs only |

## 7. Output provenance

Every produced file carries provenance. No orphan outputs.

- **Text / CSV / JSON:** header comment or top-level `_meta` object.
- **Binary / figures / models:** sidecar `<name>.meta.json`.

Minimum fields: `run_id`, `git_sha`, `config_hash`, `model_generation_hash`, `utc_created`, `constitution_version`, Constitution Part IX `stage`, and the `tier` of any data used.

Outputs found without provenance are **deleted, not archived**. An unattributable result is worse than no result, because it may be cited.

## 8. Logging

No `print()` in `src/`. Levels: `ERROR`, `WARNING`, `INFO`, `DEBUG`.

Plus a dedicated **scientific audit logger** writing to `logs/audit/` — a separate named logger, not a syslog level, because retention and immutability requirements differ. It records anything a reviewer would need to reconstruct why a number came out as it did: threshold applications, records dropped by filters and why, censored-data handling decisions, seal reads, Tier 2 gate invocations, applicability-domain flags fired, and every Indeterminate classification (Constitution §2.2).

Append-only; rotated by archiving, never truncating.

## 9. Dependencies and version pinning

**The authoritative location for every version is `pyproject.toml` plus the lockfile.** Version numbers are deliberately not listed in this document — a prose list becomes a second source of truth and drifts on the first bump.

Pinned components, values in `pyproject.toml`: Python (exact minor), RDKit, PyTorch, CUDA toolkit, plus every runtime dependency and its transitive lock.

**Any change to a pinned version requires an ADR.** The lockfile-diff check in §20 fails CI on a lockfile change without a linked ADR. Spontaneous upgrades are the failure mode this prevents.

A new runtime dependency requires an ADR establishing all five:

1. **Necessity** — nothing existing or in the stdlib provides it. State what was searched.
2. **Maintenance** — active releases, resolved issues, non-trivial contributor base. A dormant package is a deferred migration.
3. **License compatibility** — recorded explicitly; copyleft flagged.
4. **Reproducibility** — pinnable to an exact version with a hash. Unpinnable, GPU-architecture-locked, or closed-source is disqualifying unless the ADR argues the exception.
5. **Cost of removal** — how deeply it would embed.

Preference order: stdlib → mature scientific stack (numpy/scipy/pandas/rdkit/scikit-learn class) → domain package → niche package. Dependency count is minimized as a standing objective; two packages doing similar work is a defect. Dev-only tooling is exempt from the ADR requirement, not from pinning.

## 10. Public API stability

- **Only symbols exported through `__all__` are public.** Everything else is internal regardless of naming.
- Internal APIs may change freely, at any stage.
- **Public APIs require deprecation before removal**, from the Publication stage onward (§16): a `DeprecationWarning`, a changelog entry, and at least one minor version in which both old and new exist.
- During Prototype and Research, interfaces may churn without deprecation — the §16 table permits it, and deprecation cycles during exploratory work are ceremony without benefit.
- Removing a public symbol without deprecation at or after Publication is a breaking change requiring a major version bump and an ADR.

## 11. Performance

Ordering per `CLAUDE.md` §4 — performance is last.

No optimization before a measured bottleneck exists. Optimization reducing clarity requires a benchmark in the PR showing the gain. **Optimization that changes numerical results requires an ADR** — changed results are a scientific change, not an engineering one.

## 12. Versioning

The immutable artefacts, and the rule that changes create new versions rather than edits, are defined in `CLAUDE.md` §8. This section gives increment mechanics only.

Semantic versioning, independently, for:

| Artefact | Increments when |
|---|---|
| Repository | public API of `src/` changes (§10) |
| Configuration schema | a key is added, removed, or retyped |
| Documentation | released with repository version |

For the artefacts in `CLAUDE.md` §8, identifiers are content hashes or seal references rather than SemVer. Knowledge-graph schema changes additionally require the ADR conditions of §1.

## 13. Data storage (DVC)

- **No dataset committed to Git.** Only DVC pointer files.
- Snapshots are **immutable**; a change produces a new snapshot ID.
- **Content hash mandatory**, recorded in the experiment record (§6).
- Remote storage versioned; retention policy documented.
- `data/tier2/` is DVC-tracked like any other data and additionally governed by `CLAUDE.md` §7. DVC provides no access control, so the import contracts of §2 remain the enforcing mechanism.

## 14. Experiment tracking (MLflow)

Every run logs parameters, metrics, artifacts, **and the complete experiment record of §6** — MLflow stores those fields rather than re-deriving them, so §6 remains the single definition.

- Run name includes the model generation hash.
- Metric logging is append-only; no metric overwritten within a run.
- Tier 2 metrics tagged `tier=2` and cross-referenced to the `logs/tier2_queries.jsonl` line.
- Artifacts carry the provenance metadata of §7; MLflow storage does not substitute for it.
- Manifest runs (§6) link constituent run IDs as tags.

## 15. Containers and HPC

```
Docker (development, CI) → Apptainer (HPC execution) → CI verification → versioned images
```

- Development and CI run the Docker image; HPC runs the Apptainer image built from it.
- CI verifies both build, and that a smoke test yields identical results in each.
- **Images referenced by digest, not tag,** in the experiment record. Tags are mutable; digests are not.
- Image version bumps on any dependency or base-image change; the digest is recorded.
- HPC job scripts live in `scripts/`; scheduler job IDs recorded in the experiment record (§6).
- Archived stages (§16) require the image to remain buildable or the digest deposited.

## 16. Project lifecycle

Standards tighten as the project matures rather than being uniformly maximal from day one. **The current stage is recorded in the `CLAUDE.md` header**; this section defines the stages and their transitions.

**Naming note:** *Reference Implementation* replaces the usual "Production". Constitution §1.5 disclaims a general-purpose platform and any clinical deliverable, so a stage named Production would invite the scope creep §7.6 guards against.

| Stage | Permitted changes | Review | Docs | Validation | Reproducibility |
|---|---|---|---|---|---|
| **Prototype** | Anything, in `notebooks/`/`scratch/` | None | Notebook narrative | None required | Seeds recorded |
| **Research** | `src/` under the production path; interfaces may churn | Self-review + task audit | Module docstrings; ADRs for costly choices | Unit tests + degeneracy battery | Full experiment record (§6) |
| **Publication** | Bug fixes and clarity only; **no threshold or criterion changes**; deprecation policy begins (§10) | Named reviewer per PR | Full MkDocs; methods traceable to code | All committed-phase criteria evaluated and reported | Every published artefact resolvable to one experiment ID (§6) |
| **Reference Implementation** | Additive only; deprecation cycle for removals | Two reviewers | Public API docs + tutorials | Regression suite over published results | Container digest pinned and archived |
| **Maintenance** | Security and dependency updates; no scientific change | One reviewer | Changelog only | Regression suite stays green | Archived environment still builds |
| **Archive** | None | — | Frozen; final state documented | Final validation report | Snapshot + container deposited with a DOI |

**Transitions.** Prototype → Research on completion of the Foundation Protocol (`docs/IMPLEMENTATION_PROTOCOL_FOUNDATION.md` §15), not on creation of the first production module — Foundation creates one during its own validation, and the transition is a governance act isolated from implementation. Every transition requires an ADR recording the stage entered, the standards now in force, and what is frozen. The `CLAUDE.md` header is updated in the same change.

Entering **Publication freezes thresholds.** After that point a threshold change in git history is evidence of a Constitution §7.6 overclaim violation, not a routine edit.

## 17. Branches and commits

| Branch | Purpose | Gate |
|---|---|---|
| `main` | stable; every commit reproducible | full phase-appropriate CI (§20); no direct pushes; reviewer sign-off from Publication onward (§16) |
| `develop` | integration | full CI |
| `feature/<short-name>` | implementation | lint, typecheck, tests |
| `hotfix/<short-name>` | urgent fixes off `main` | full CI; ADR if architectural |
| `experiment/<run-topic>` | throwaway exploration | none |

- One logical change per branch. A branch that both refactors and changes behaviour violates `CLAUDE.md` §10 and is split.
- Commit subject: `<area>: <imperative summary>`, ≤ 72 characters. Body states why, not what. Reference `ADR-NNNN` and Constitution sections where applicable.
- A commit touching `sealed/` states in its body which artefact is sealed and why — these commits are audited (§5, `CLAUDE.md` §7).
- **`experiment/*` branches may produce experiment records but never published artefacts.** They are deleted after harvest, so a run record on such a branch would reference an unreachable commit and break the §6 guarantee. Promotion means re-running on `develop`.

## 18. Documentation ownership

One home per kind of content. Duplication across documents is a defect; the second copy will drift.

| Document | Owns |
|---|---|
| `README.md` | Project overview and orientation. The only document permitted to summarize others, and only with links. |
| `docs/PROJECT_CONSTITUTION_v4.6.md` | Scientific rules, scope, criteria, evidence classes |
| `CLAUDE.md` | Execution protocol; notation; current lifecycle state; canonical repository tree; immutable-artefact list; hard-constraint index; canonical task names |
| `docs/IMPLEMENTATION_PROTOCOL_FOUNDATION.md` | The sequence in which the repository is established; Foundation invariants, stop conditions and state machine. States sequence only — never engineering policy |
| `docs/IMPLEMENTATION_PROTOCOL_SCIENTIFIC.md` | The sequence in which scientific capability is added; scientific invariants; model-generation, Tier 2 query, seal-consumption and gate procedures. States sequence only |
| `docs/ENGINEERING_STANDARDS.md` | Engineering rules; package responsibilities; lifecycle definitions; CI; Makefile contract; this table |
| `docs/PROJECT_SPECIFICATION.md` | Functional requirements; requirement-to-module traceability (Constitution §7.9) |
| `docs/adr/` | Architecture decisions and their reasoning |
| `docs/architecture/` | Design notes and diagrams; no requirements, no decisions |
| `docs/api/` | Generated API reference; never hand-edited (`CLAUDE.md` §11) |
| `docs/user_guide/` | How to run things |
| `docs/GOVERNANCE_VERSIONS.md` | Document versions and per-protocol Constitution compatibility ranges. No other document restates a version |
| `Makefile` | Command invocations — the executable source of truth (§22) |
| Module docstrings | What a module does and its assumptions |

When content could plausibly live in two places, it goes in the higher-authority document and the other links to it.

## 19. Documentation build

MkDocs. Every public class, public function and configuration schema appears automatically — no hand-maintained API lists, which rot.

`mkdocs build --strict` runs in CI; failure fails the build. Broken cross-references and undocumented public symbols are errors, not warnings.

## 20. CI, staged by project phase

The full pipeline is substantial infrastructure. Building it before there is code to run through it repeats the constitution-before-construction inversion. Stage it.

**Phase 1 — build now**

| Check | Enforces |
|---|---|
| pre-commit | hygiene |
| `ruff check` | §4 |
| `ruff format --check` | §4 |
| `mypy --strict` | §4 |
| `pytest` + coverage | §4 |
| import-graph contracts | §2 contracts 1, 2, 4; §10 |
| tests-mirror-src | §3 |
| lockfile-diff-requires-ADR | §9 |
| seal-timestamp | `CLAUDE.md` §7 |
| no-unresolved-`<FILL`-marker — matches `<FILL` **literally**, never any angle-bracket token, or it fires permanently on the `<pkg>` notation | `CLAUDE.md` §1, header |
| S8c-no-significance-test grep | Constitution §1.4.1, §7.6 |
| governance-version-compatibility — each protocol's declared range is satisfied by `GOVERNANCE_VERSIONS.md`, and every version row cites an Accepted ADR | `GOVERNANCE_VERSIONS.md` |
| `mkdocs build --strict` | §19 |

**Phase 2 — add when Tier 2 work begins**

| Check | Enforces |
|---|---|
| Tier 2 transitive-import contract | §2 contract 3; Constitution §0.4 |
| Tier 2 query-log validation | Constitution §0.4 |
| sealed-threshold hash verification | §5; Constitution §1.4 |
| experiment-record schema | §6 |
| DVC snapshot integrity | §13 |

**Phase 3 — add when results must be portable or shared**

| Check | Enforces |
|---|---|
| MLflow schema | §14 |
| Docker build | §15 |
| Apptainer build | §15 |
| cross-image result equivalence | §15 |
| release | §12 |

Every stage that can fail must fail loudly. A check that only warns is not a check.

## 21. Pull request checklist

Distinct from the task audit in `CLAUDE.md` §17: that is the agent's self-check at task end; this is the human review gate.

1. Why is this needed?
2. Which Constitution section does it serve?
3. Which ADR authorizes it? Was `docs/adr/` searched for an existing decision (§1)?
4. What scientific capability changed?
5. What evidence, criteria, or tier boundary changed? *(Expected: none. Otherwise named reviewer sign-off.)*
6. Any control deleted, or threshold adjusted? *(Expected: no. `CLAUDE.md` §3.)*
7. New files, packages, or top-level directories — why did reuse and extension fail (`CLAUDE.md` §6; §3 here)?
8. Any pinned version changed? Linked ADR (§9)?
9. Backward compatible? If not, which versions bump (§12), and was deprecation observed (§10)?
10. Tests added or updated, written before implementation (`CLAUDE.md` §9)?
11. Documentation updated in the owning document only (§18)? Changelog entry?

## 22. Makefile target contract

The `Makefile` is the **single executable source of truth for command invocations.** Task names are listed in `CLAUDE.md` §16; the actual command strings exist only here, so tooling changes touch one file. No document restates an invocation.

Each target must satisfy its contract:

| Target | Contract |
|---|---|
| `install` | Creates or syncs the environment from the lockfile, without resolving new versions. Fails if the lockfile and `pyproject.toml` disagree. |
| `test` | Runs the full test suite over `tests/`. Non-zero exit on any failure. Deterministic — no network, no wall-clock dependence. |
| `lint` | Runs all static checks that do not require type information. Read-only; never rewrites files. |
| `format` | Applies formatting in place. The only target permitted to modify source. |
| `typecheck` | Runs strict type checking over `src/` and `tests/`. |
| `docs` | Builds documentation in strict mode; warnings are failures (§19). |
| `ci-local` | Runs the complete Phase 1 CI sequence of §20 in order, stopping at the first failure. Must be runnable offline. |

Rules:

- Targets are **idempotent** except `format` and `install`.
- A target's contract may not be weakened to make it pass — that is a `CLAUDE.md` §3 violation.
- Adding a target requires no ADR; **changing an existing target's contract does** (§1), because CI and `CLAUDE.md` §16 depend on the contract rather than the implementation.
- If a target is missing or broken, fix the `Makefile` in the same change rather than running an equivalent command directly.

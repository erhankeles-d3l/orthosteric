# ADR-0006 [Architectural] — Repository Structure Revisions

**Status:** Proposed
**Date:** 2026-07-31
**Reversibility:** costly after SCI code lands — decide before `feature/SCI0-001`

---

## Context

A revised repository structure has been proposed. Parts of it are improvements the built tree lacks. Three parts would break barriers the Foundation exists to establish, and two would reintroduce a pattern `CLAUDE.md` §6 prohibits by name.

Structure changes are cheap now and expensive once objectives are merged, so this ADR settles them before `SCI0-001`.

## Decision — adopt

| Change | Rationale |
|---|---|
| `docs/reports/objective_reports/` | Task reports (Protocol §14) currently have no home and would accumulate loose in `docs/` |
| `docs/reports/audit_reports/` | Stage 0 audit outputs (`SCI0-015`) need a versioned location, attached to the snapshot hash |
| `docs/reports/foundation/` | Foundation publication and validation reports |
| `docs/architecture/package_map.md` | Renders the ENG §2 responsibility table as a diagram; no new authority |
| `docs/architecture/state_machine.md` | Renders the FND and SCI state machines; no new authority |
| `docs/architecture/dependency_graph.md` | Generated from the import contracts, so it cannot drift from what CI enforces |
| `.github/PULL_REQUEST_TEMPLATE.md` | Encodes the ENG §21 checklist at the point of use — the single highest-value addition in the proposal |
| `.github/ISSUE_TEMPLATE/` | One template per objective class, citing backlog IDs |

## Decision — reject

### R1 · `configs/thresholds/`

**Rejected. This would defeat the seal.**

Pre-registered thresholds live in `sealed/config/`, loaded through the non-composable loader built at `FND-5`. `configs/` is the Hydra composition root: anything under it is override-able from the command line, and a CLI override leaves no git trace. Placing thresholds there makes Constitution §1.4 unenforceable for precisely the values that decide whether the project proceeds.

### R2 · `sealed/` and `logs/` omitted

**Rejected — both are load-bearing.**

The proposal has no `sealed/` and no `logs/`. Without `sealed/` there is no pre-registration and `SCI0-023`…`SCI0-029` have nowhere to write. Without `logs/tier2_queries.jsonl` the Constitution §0.4 query budget is unauditable. Both must remain at root.

### R3 · `datasets/{raw,processed,snapshots,tier2}` replacing `data/{tier1,tier2,reference,processed}`

**Rejected — it loses the tier structure.**

`tier1/` and `reference/` disappear, and `raw/` is not a tier. Tier separation is what `CLAUDE.md` §7 and SI1 depend on; a directory layout that cannot express "this is Tier 1 data" removes the filesystem-level expression of the barrier. If a rename to `datasets/` is wanted for taste, the tier subdirectories must survive intact — but the canonical tree in `CLAUDE.md` §15 already says `data/`, and renaming it means amending that too.

### R4 · `common/` and `utils/`

**Rejected on the same grounds as the prohibited filenames.**

`CLAUDE.md` §6 prohibits `utils.py`, `helpers.py`, `common.py`, `shared.py`, `misc.py` and `manager.py` by name, because they accumulate unrelated code and dissolve module boundaries. A `common/` or `utils/` **package** is the identical failure one level up, and harder to unwind because imports spread across it. Shared code goes in the package that owns the responsibility, or gets an ADR naming a new responsibility.

### R5 · `foundation/` as a package

**Rejected — superseded by `ADR-0004`.**

Foundation's production code lives in `runtime/`, which `ADR-0004` added to the ENG §2 responsibility table with a stated responsibility and exclusions. A second Foundation package would give the same work two homes.

### R6 · `tests/integration/`

**Rejected as located.** ENG §3 requires `tests/` to mirror `src/` exactly, and the mirror check in CI would fail on a test package with no source counterpart. Cross-package tests belong under the package whose behaviour they assert, or need an ADR amending the mirror rule with a stated exemption.

### R7 · `.github/workflows/quality.yml` and `release.yml`

**Rejected as premature.** `quality.yml` duplicates checks already in `ci.yml`. `release.yml` is a Phase 3 concern under the ENG §20 staging, and building it before there is anything to release repeats the constitution-before-construction inversion.

### R8 · Moving `CLAUDE.md` to `docs/protocol/`

**Rejected.** It is the file an agent loads at session start and conventionally sits at repository root. ENG §18's ownership table references it by that path, as do the CI marker check and several cross-references.

### R9 · `reports/` at root alongside `docs/reports/`

**Rejected — one home per content class** (ENG §18). Reports go under `docs/reports/`.

### R10 · `tools/`

**Rejected as undefined.** Its purpose overlaps `scripts/`. If a distinction is wanted, it needs a stated responsibility.

## Defect found in the proposed state-ownership table

The proposal maps SCI2 → `model/` and omits **`train/`** entirely. Protocol §16 assigns both `model/` and `train/` to `SCI-2`, with `eval/` split across `SCI-1` (metrics, calibration) and `SCI-2` (degeneracy battery, seals). The authoritative mapping is Protocol §16 and is unchanged by this ADR.

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| Adopt the proposal wholesale | Three barrier breaks (R1, R2, R3) and two boundary dissolutions (R4, R5) |
| Reject it wholesale | Loses eight genuine improvements, including the PR template |
| Defer until after SCI-0 | Structure changes get costlier with every merged objective; `docs/reports/` is needed by the first task report |

## Evidence

`CLAUDE.md` §6 (prohibited names), §7 (seal and Tier 2 isolation), §15 (canonical tree); ENG §2 (package responsibilities), §3 (tests mirror src), §5 (composition root), §18 (documentation ownership), §20 (CI staging), §21 (PR checklist); Constitution §0.4, §1.4; `ADR-0004`.

## Review trigger

Any proposal to add a top-level directory, or to relocate `sealed/`, `logs/` or `data/`.

## Adopted repository philosophy

The framing offered with the proposal is sound and worth recording, since it maps the git history onto the Constitution:

| Stage | Establishes |
|---|---|
| Foundation | **how** the project is built |
| `SCI-0` | **what data** it uses |
| `SCI-1` | **how** proteins and ligands are represented |
| `SCI-2` | **how** learning is performed |
| `SCI-3` | **what knowledge** is extracted |
| `SCI-4` | **whether** the method generalizes |
| `SCI-5` | **whether** computational hypotheses are experimentally supported |

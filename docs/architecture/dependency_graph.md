# Dependency Graph

**Derived, explanatory document. Not a source of governance authority.**

This page renders the import contracts already defined and mechanically enforced by the files below. It is a manually maintained transcription for readability, not a generated artefact — no generator or additional CI job was introduced to produce it. If it drifts from `.importlinter`, `.importlinter` and the CI check that runs it are authoritative; this page is stale and must be corrected by hand to match.

**Authoritative sources:**

- `.importlinter` (repository root) — the enforced contracts
- `.github/workflows/ci.yml`, step "Import-graph contracts" (`PYTHONPATH=src lint-imports --config .importlinter`) — where they are checked
- `docs/ENGINEERING_STANDARDS.md` §2 — the four import-contract rules these contracts implement

Established by `ADR-0006` (A6).

## Contract 2 — `src/` never imports `notebooks/` or `scratch/`

```
orthosteric  ──forbidden──▶  notebooks
orthosteric  ──forbidden──▶  scratch
```

Type: `forbidden`. Enforces ENG §2 rule 2 and `CLAUDE.md` §12 (production/exploratory isolation).

## Contract 3 — no training path reaches Tier 2

```
orthosteric.train  ──forbidden──▶  orthosteric.data.tier2_gate
```

Type: `forbidden`, transitive closure (not just direct imports). Enforces ENG §2 rule 3 and Constitution §0.4. Currently **inert**: `orthosteric.data.tier2_gate` does not exist yet (`data/` is still a scaffold), so the contract has nothing to violate until `SCI-0` builds it.

## Contract 4 — layer dependency direction (SI17)

Declared layer order, highest to lowest (a layer may depend only on layers below it):

```
orthosteric.eval
orthosteric.explain
orthosteric.train
orthosteric.model
orthosteric.features
orthosteric.pocket
orthosteric.data
orthosteric.runtime
```

Type: `layers`, `exhaustive = false` (packages not listed are unconstrained by this contract). Enforces ENG §2 rule 4 — no import from a package into one above it in the responsibility order.

## Current enforcement status

All three contracts run in CI (`ci.yml`, step "Import-graph contracts") on every push and pull request to `main`/`develop`. Contract 3 is structurally present but inert pending `SCI-0`, exactly as recorded in `docs/FOUNDATION_STATE.md` (invariant table, `FND-9 BOUNDARIES`).

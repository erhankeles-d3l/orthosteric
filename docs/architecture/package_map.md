# Package Map

**Derived, explanatory document. Not a source of governance authority.**

This page renders the package-responsibility mapping already defined by the documents below. If anything here appears to conflict with one of those documents, the source document wins (`CLAUDE.md` authority order) and this page is stale and must be corrected to match it — never the other way round.

**Authoritative sources:**

- `docs/ENGINEERING_STANDARDS.md` §2 — package responsibilities and import boundaries (base table)
- `docs/adr/ADR-0004-fnd10-first-module.md` (Accepted) — adds `runtime/` to the ENG §2 table
- `docs/IMPLEMENTATION_PROTOCOL_SCIENTIFIC.md` §16, P8 — which lifecycle state creates each package

Established by `ADR-0006` (A4).

## Responsibility table (ENG §2, as amended by ADR-0004)

| Package | Responsibility | Must not contain | Created by (Protocol §16, P8) |
|---|---|---|---|
| `data/` | loading, provenance, censoring, tier gating | feature construction, model logic | `SCI-0` |
| `pocket/` | structure handling, ensemble union, rotamer states | featurization, prediction | `SCI-1` |
| `features/` | feature construction | I/O, training, prediction | `SCI-1` |
| `model/` | prediction | training loops, I/O, evaluation metrics | `SCI-2` |
| `train/` | training orchestration | model mathematics, metric definitions | `SCI-2` |
| `eval/` | evaluation, calibration, degeneracy battery, seal reading | training, feature construction | split: metrics/calibration at `SCI-1`; degeneracy battery/seals at `SCI-2` |
| `explain/` | Constitution §4.7 discrete-rule interface | model definition, training | `SCI-2` if Phase 2 committed, else `SCI-3` |
| `kg/` | knowledge layer (Phase 3) | anything outside Constitution §5.2 schema | `SCI-4` (Phase 3 only) |
| `runtime/` | run identity, experiment records, scientific audit logging (`ADR-0004`) | domain schemas, scientific logic | Foundation (`FND-10`) |

**Currently populated:** `runtime/` (Foundation, `FND-10`). All other packages under `src/orthosteric/` exist only as empty scaffolds (`__init__.py`) pending their owning lifecycle state — see `state_machine.md` in this directory.

## Notes

- `eval/` is the one authorized exception to one-package-one-state (Protocol §16).
- A module performing two of these responsibilities belongs in neither and must be split (ENG §2).
- Import contracts enforcing this layering are rendered in `dependency_graph.md`, not here.

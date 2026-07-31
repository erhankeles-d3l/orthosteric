# Foundation State

**FSM state: COMPLETE**

Foundation Protocol v1.0 terminated. `docs/FOUNDATION_STATE.md` is not modified after this
point (Foundation Protocol §15).

| Field | Value |
|---|---|
| FSM state | `COMPLETE` |
| Completed states | `FND-1` … `FND-11` |
| Blocked objectives | none |
| Pending ADRs | `ADR-0003` (Proposed — awaits Independent Scientific Auditor) |
| Pending validation | none |
| Authorizing ADR | `ADR-0001` |
| Package name | `orthosteric` (`ADR-0007`, superseding `ADR-0005`) |

Lifecycle stage is recorded in the `CLAUDE.md` header, not here (ENG §18).

## Exit gates

| State | Delivered | Gate |
|---|---|---|
| `FND-1` REPOSITORY | Canonical tree, git, `main`/`develop`, `.gitignore`, LICENSE, README | ✅ |
| `FND-2` ENVIRONMENT | `pyproject.toml`, Python `==3.12.*`, dev extras | ✅ |
| `FND-3` MAKEFILE | Seven ENG §22 targets | ✅ |
| `FND-4` SEALS | `sealed/MANIFEST.md`, seal-timestamp check, `logs/{runs,audit}`, empty `logs/tier2_queries.jsonl`, audit logger | ✅ |
| `FND-5` CONFIG | Config schema, **non-composable sealed threshold loader** | ✅ |
| `FND-6` TESTS | pytest, coverage, `tests/` mirrors `src/` | ✅ |
| `FND-7` CI | GitHub Actions, complete ENG §20 Phase 1 set | ✅ |
| `FND-8` DOCS | MkDocs strict, documentation tree, `CHANGELOG.md` | ✅ |
| `FND-9` BOUNDARIES | Import contracts 1, 2, 4 enforced; 3 inert | ✅ |
| `FND-10` FIRST_MODULE | `runtime/` run-metadata writer (`ADR-0004`) | ✅ |
| `FND-11` VALIDATED | Clean-checkout verification | ✅ |

## Invariants at completion

| Invariant | Status |
|---|---|
| I1 no scientific code | ✅ `data/`…`explain/` are scaffolds only |
| I2 no data processing, no dataset | ✅ |
| I3 no Tier 2 handling; `data/tier2/` empty | ✅ |
| I4 no training, inference, evaluation metrics | ✅ |
| I5 no scientific or ML dependency | ✅ dev tooling only; no RDKit, PyTorch, CUDA |
| I6 no GPU, HPC, container, DVC, MLflow config | ✅ `docker/`, `apptainer/` empty |
| I7 no experiment executed; `logs/runs/` empty | ✅ |
| I8 no knowledge layer; `kg/` absent | ✅ |
| I9 Constitution phase uncommitted | ✅ |
| I10 no unresolved `<FILL` marker | ✅ |

## Next

```
lifecycle transition ADR (recorded: CLAUDE.md header reads Research)
  → SCI0-001  refine the SCI-0 backlog
  → SCI0-002  data/ package scaffold
  → SCI0-003  import the verified provenance package
```

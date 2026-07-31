# Changelog

Maintained from the first commit, never retrofitted (ENG §8).

## [0.1.0] — 2026-07-31

### Foundation (`FND-1` … `FND-11`)

Authorized by `ADR-0001` as a capped exception to Constitution §3.1.

- `FND-1` Canonical repository tree; `main` and `develop`; `.gitignore`; LICENSE; README
- `FND-2` `pyproject.toml`; Python pinned to `==3.12.*`; ruff, mypy, pytest, coverage
- `FND-3` `Makefile` with the seven ENG §22 target contracts
- `FND-4` `sealed/MANIFEST.md`; seal-timestamp check; `logs/{runs,audit}`; empty
  `logs/tier2_queries.jsonl`; scientific audit logger
- `FND-5` Configuration schema; **non-composable sealed threshold loader**
- `FND-6` pytest, coverage, `tests/` mirroring `src/`
- `FND-7` GitHub Actions running the complete ENG §20 Phase 1 set
- `FND-8` MkDocs strict; documentation tree; this changelog
- `FND-9` Import-graph contracts 1, 2 and 4 enforced; contract 3 written inert
- `FND-10` Run-metadata writer in `runtime/` (per `ADR-0004`)
- `FND-11` Clean-checkout validation

### Decisions

- `ADR-0001` Foundation authorization
- `ADR-0002` Governance closure — authority ordering; `PROJECT_SPECIFICATION` v0.1
- `ADR-0003` Public knowledge-only training policy (**Proposed**, awaiting Auditor)
- `ADR-0004` `FND-10` first module is the run-metadata writer, not the provenance writer
- `ADR-0005` Package name `orthosteric`

### Not implemented

No scientific capability. `data/`, `pocket/`, `features/`, `model/`, `train/`, `eval/`,
`explain/` and `kg/` are scaffolds owned by later objectives.

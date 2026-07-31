# orthosteric

Comparative evidence learning for mechanistic orthosteric selectivity, benchmarked on
Class I PI3Ks.

**This repository is at lifecycle stage Research and Constitution phase is not yet
committed.** No scientific capability is implemented. See
`docs/IMPLEMENTATION_BACKLOG.md` for the next objective.

## What this is

A framework for learning *why* a ligand discriminates between homologous orthosteric ATP
pockets, with the founding hypothesis stated and tested rather than assumed. PI3K is the
benchmark, not the discovery target — orthosteric α-selectivity over β/γ/δ is a solved
medicinal chemistry problem, and recovering it is method validation.

## Documentation

| Document | Owns |
|---|---|
| `docs/PROJECT_CONSTITUTION_v4.6.md` | Scientific rules, criteria, evidence classes |
| `CLAUDE.md` | Execution protocol; canonical tree; hard-constraint index |
| `docs/ENGINEERING_STANDARDS.md` | Engineering policy, lifecycle, CI |
| `docs/IMPLEMENTATION_PROTOCOL_FOUNDATION.md` | Repository establishment sequence |
| `docs/IMPLEMENTATION_PROTOCOL_SCIENTIFIC.md` | Scientific implementation sequence |
| `docs/IMPLEMENTATION_BACKLOG.md` | The ordered objective list |
| `docs/PROJECT_SPECIFICATION.md` | Functional requirements |
| `docs/GOVERNANCE_VERSIONS.md` | Document versions and compatibility |
| `docs/adr/` | Architecture decisions |

## Working here

```bash
make install     # sync the pinned environment
make ci-local    # the complete Phase 1 CI sequence, offline
```

`make` targets are the only supported way to invoke tooling (ENG §22). The `Makefile` is
the single executable source of truth for invocations.

## Licence

Software: MIT (`LICENSE`) — **provisional, requires confirmation.** Software,
documentation and public-data licensing are three independent questions; see `NOTICE`.

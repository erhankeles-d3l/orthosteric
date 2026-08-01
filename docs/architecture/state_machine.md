# State Machine

**Derived, explanatory document. Not a source of governance authority.**

This page renders the Foundation and Scientific state machines already defined by the documents below. If anything here appears to conflict with one of those documents, the source document wins and this page is stale.

**Authoritative sources:**

- `docs/IMPLEMENTATION_PROTOCOL_FOUNDATION.md` §14 — Foundation state machine
- `docs/FOUNDATION_STATE.md` — Foundation's current, terminal state record
- `docs/IMPLEMENTATION_PROTOCOL_SCIENTIFIC.md` §16 — Scientific state machine and package ownership (P8)
- `docs/ENGINEERING_STANDARDS.md` §16 — project lifecycle stages (Prototype/Research/Publication/…)

Established by `ADR-0006` (A5).

## Foundation state machine (terminated — `COMPLETE`)

```
UNINITIALIZED → FND-1 REPOSITORY → FND-2 ENVIRONMENT → FND-3 MAKEFILE
  → FND-4 SEALS → FND-5 CONFIG → FND-6 TESTS → FND-7 CI → FND-8 DOCS
  → FND-9 BOUNDARIES → FND-10 FIRST_MODULE → FND-11 VALIDATED → COMPLETE
```

Current record (`docs/FOUNDATION_STATE.md`): FSM state `COMPLETE`, all `FND-1`…`FND-11` exit gates satisfied, `ADR-0001` Accepted. This file is not modified after `COMPLETE` (Foundation Protocol §15) — this rendering does not modify it, only cites it.

## Scientific state machine (current: `Research`, pre-`SCI-0`)

```
RESEARCH_START → SCI-0 → [phase commitment] → SCI-1 → SCI-2
  → SCI-3 → SCI-4 → SCI-5 → RESEARCH_COMPLETE
                ↘ SCI-0.5 (Phase 3, Option B only)
```

| State | Owner (Constitution) | Creates | Phase terminus |
|---|---|---|---|
| `SCI-0` | §3.1, §9.1 | `data/` | — |
| `SCI-0.5` | §3.2 | — (test only) | Phase 3, Option B only |
| `SCI-1` | §9.3, §4.6, §2.1 | `pocket/`, `features/`, `eval/` (metrics, calibration) | — |
| `SCI-2` | §9.4, Part IV | `model/`, `train/`, `eval/` (battery, seals); `explain/` if Phase 2 | Phase 1 |
| `SCI-3` | §9.5 | `explain/` if not built at `SCI-2` | Phase 2 |
| `SCI-4` | §9.6 | `kg/` | — |
| `SCI-5` | §9.7, §6.2, §6.3 | — | — |

## Lifecycle stage (ENG §16) — orthogonal axis

`Prototype → Research → Publication → Reference Implementation → Maintenance → Archive`

Current stage, per the `CLAUDE.md` header: **Research**. Every transition requires its own ADR (`Lifecycle` category, ENG §1) recording the stage entered and what is frozen; this page does not perform or authorize a transition.

## Governance note

As of this document's creation, no `SCI-0` objective has started (`SCI0-001`…`SCI0-003` remain `Pending`; see `docs/IMPLEMENTATION_BACKLOG.md`). This page describes the state machine that governs future work — it does not itself advance any state.

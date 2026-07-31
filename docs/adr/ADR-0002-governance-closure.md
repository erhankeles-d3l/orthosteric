# ADR-0002 [Process] — Governance Closure

**Status:** Accepted
**Date:** 2026-07-31
**Reversibility:** reversible

## Decision

Two closure items on the v1.0 governance freeze.

**1. Authority ordering.** The canonical hierarchy is the one written into every governance
document:

```
Scientific reality → Constitution → Accepted ADRs → CLAUDE.md
  → Foundation Protocol → Scientific Protocol → Engineering Standards
  → Project Specification → code → experiments → results
```

`CLAUDE.md` sits **above** Engineering Standards, not below.

**2. `PROJECT_SPECIFICATION.md`** exists at v0.1 with §1 (Data sources and exclusions)
complete and §2–8 explicitly deferred with named objectives, which Constitution §7.9
permits: *"Every charter requirement must map to at least one specification item or be
explicitly marked deferred with a phase."*

## Alternatives

For item 1: place Engineering Standards above `CLAUDE.md`. **Rejected.** `CLAUDE.md` holds
the no-invention rule, the stop conditions, and the prohibition on weakening a control or
adjusting a threshold. If engineering policy outranked it, an engineering argument could
license a control weakening — ENG §10 permits interface churn during Research while
`CLAUDE.md` §3 forbids weakening guarantees, and the ordering decides which wins.

## Evidence

Six governance documents were written with the ordering above; a single later message
proposed the inverse. Consistency plus the safety argument favours the written form.

## Review trigger

Any amendment to `CLAUDE.md` §3 or ENG §10.

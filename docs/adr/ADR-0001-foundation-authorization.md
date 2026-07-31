# ADR-0001 [Process] — Foundation Authorization

**Status:** Accepted
**Date:** 2026-07-31
**Reversibility:** costly

## Decision

Authorize scientifically neutral repository infrastructure prior to Constitution Stage 0,
as a capped exception to Constitution §3.1 (*"No modelling, architecture or infrastructure
work begins until complete and reviewed"*).

Scope is limited to the states of `IMPLEMENTATION_PROTOCOL_FOUNDATION.md` §14
(`FND-1` … `FND-11`). Nothing scientific is authorized: no model, featurization, pocket
code, descriptors, training, evaluation metrics, Tier 2 handling, or knowledge layer.

## Alternatives

1. **Complete the Stage 0 audit with no tooling.** Rejected — audit artefacts would be
   unversioned and unprovenanced, and the six sealed artefacts would have no integrity
   mechanism.
2. **Full platform build first.** Rejected — maximal R1 exposure.
3. **Capped exception (adopted).**

## Evidence

Constitution Stage 0 produces artefacts requiring infrastructure that already exists: an
audit report needing provenance (§3.3), six sealed artefacts whose integrity must be
independently verifiable, and an append-only Tier 2 query log. A seal-timestamp check
added *after* seals exist cannot distinguish a legitimate seal from one backdated after
the audit, so the check must pre-date what it validates.

The exception is defensible because every authorized item survives an R1 outcome:
configuration, provenance, seals, CI, documentation and testing all remain necessary in a
physics-only orthosteric study. Nothing built under this ADR is wasted if comparative
learning proves infeasible.

## Review trigger

The Constitution Stage 0 gate (`SCI0-031`).

**If R1 fires.** Foundation is enterable once (Foundation Protocol §14: `Any → Foundation`
is illegal). A physics-only redesign requiring infrastructure change is therefore not a
return to Foundation and requires either its own protocol or an amendment. That decision
is deferred to the gate, and this clause exists so it is not discovered under pressure.

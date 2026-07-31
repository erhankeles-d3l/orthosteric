# ADR-0004 [Process] — FND-10 First Production Module

**Status:** Accepted
**Date:** 2026-07-31
**Reversibility:** reversible

## Decision

Foundation's first production module (`FND-10`) is the **run-metadata writer** in
`src/orthosteric/runtime/`, not the provenance-record writer in `data/`.

`runtime/` is added to the Engineering Standards §2 responsibility table:

| Package | Responsibility | Must not contain |
|---|---|---|
| `runtime/` | Run identity, experiment records, scientific audit logging | domain schemas, scientific logic |

`data/` remains untouched by Foundation and is created by `SCI0-002`.

## Alternatives

1. **Provenance writer in `data/` (original recommendation).** Rejected — it is
   `SCI0-003`, so one module would have two owning states, breaching Protocol P8; and
   Foundation invariants I1/I2 forbid Foundation creating anything in `data/`.
2. **A synthetic no-op module.** Rejected — validates the toolchain and nothing else, and
   is never used again.
3. **Run-metadata writer in `runtime/` (adopted).** Exercises config → typed object →
   deterministic serialization → audit log, and ENG §6 requires an experiment record
   before any run produces results, so it is used immediately.

## Evidence

Protocol §16 package ownership assigns every `data/` sub-package to a SCI state.
Foundation Protocol §4 invariants I1 and I2 prohibit scientific code and data processing.
ENG §6 requires `logs/runs/<run_id>.json` written **before** results, which is
infrastructure rather than science.

## Review trigger

Any change to the ENG §2 responsibility table.

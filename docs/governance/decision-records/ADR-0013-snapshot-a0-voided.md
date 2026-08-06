# ADR-0013 — Activity Snapshot A0 Voided (Immutability Violation)

**Date:** 2026-08-06
**Status:** Accepted
**Category:** Corpus integrity — snapshot lineage correction
**Affects:** Activity Snapshot A0 (`SNAP-2b8f5ce6f236`), ADR-0012 references
**Related:** GDR-010 (DRAFT), Constitution Invariant 4

---

## Finding

Activity Snapshot A0, as committed in `8e1b49a`, is **internally inconsistent**
and is hereby **VOIDED**.

### What happened

1. A0 was frozen by `SnapshotBuilder`, producing
   `snapshot_sha256 = 2b8f5ce6f236344b6e7d5ca67729a7fae77d3cb47a9fca2f9e36d4f3a9599493`
   over records that did **not** contain an `isoform` field.

2. A field-name defect was then discovered: `build_graph_stats_from_records()`
   reads `isoform`, but the harmonizer emitted `gene`. This produced degenerate
   graph statistics (`N_c = 0`, `N_b = 0`).

3. The defect was repaired by **mutating the already-frozen
   `records.json.gz` in place** to add the `isoform` field, without re-freezing.

4. The manifest was not regenerated. The stored `snapshot_sha256` therefore
   describes a record set that no longer exists on disk.

### Verification

```
Committed manifest SHA:            2b8f5ce6f236344b…
Committed records with 'isoform':  14331 / 14331
```

The manifest hash was computed before those 14,331 fields existed. The manifest
does not describe its own records.

---

## Why this is a governance matter, not a bug fix

This violated **Invariant 4 — Snapshot immutability**:

> Once a model generation is trained, its corpus cannot change underneath it.

A frozen snapshot was edited in place. No model generation was bound to A0, so
no downstream scientific result is affected — but the invariant was breached and
the breach is recorded here rather than silently corrected.

---

## Decision

1. **A0 (`SNAP-2b8f5ce6f236`) is VOID.** It must not be cited as a corpus
   identity, used as a `parent_snapshot_sha256`, or bound to any Model
   Generation. Prior references to it (ADR-0012 commit message,
   `STAGE_D_STRUCTURAL_EVIDENCE_STATE.md`) are superseded by this record.

2. **A0 is not re-frozen.** A0 was a two-isoform (β/γ) checkpoint that
   **failed** the corpus quality gate (`coverage` and `missingness`
   structurally degenerate, `n_complete_compounds = 0`). It has no standalone
   scientific value, and re-freezing it would produce an identity that is
   itself unstable pending GDR-010.

3. **The four-isoform corpus is frozen as A1 with
   `parent_snapshot_sha256 = None`,** and this record documents why the lineage
   does not begin at A0.

4. **Corrective control:** the harmonizer now emits `isoform` at record
   construction time (`scripts/stage_bc_freeze_activity_snapshot.py`), so the
   field is present *before* the hash is computed. No post-freeze mutation.

---

## Prevention

The underlying enabler was that a frozen snapshot's records file is writable and
its manifest hash is not re-verified on read. A verification helper that
re-computes the content hash on load, and fails closed on mismatch, is
recommended — but its exact semantics depend on the outcome of **GDR-010**
(which fields define snapshot identity), so it is deferred rather than
implemented now.

---

## Reversibility

Not reversible: A0 never validly described its records. Nothing is lost, since
A0 failed its quality gate and was never used for training.

## Review trigger

At GDR-010 decision, to add the load-time hash verification control.

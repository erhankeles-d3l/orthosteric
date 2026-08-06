# Governance Decision Record GDR-010 — Snapshot Identity vs Build Provenance

**Category:** Scientific-infrastructure (definition of snapshot identity; touches
SCI0-011 snapshot semantics and therefore corpus/model lineage).
**Status:** **ACCEPTED — Option A. Implemented.**
**Date raised:** 2026-08-06.
**Date accepted:** 2026-08-06 (Project Owner decision).
**Raised by:** Computational pipeline during Phase 1 audit.
**Affects:** SCI0-011 `SnapshotManifestV2`, ADR-0009, GDR-002 (precedent), all
snapshot lineage and Model Generation binding.
**Blocking:** Stage 0 sealing; stable Activity Snapshot identity. RESOLVED.

---

## 1. Problem

`SnapshotBuilder.build()` computes:

```
snapshot_sha256 = SHA256( stable_json(records)
                        + stable_json(policy)
                        + stable_json(software) )
```

where `software` is `SoftwareProvenance`, containing among other fields:

| Field | Volatility |
|---|---|
| `git_sha` | changes on **every commit**, including documentation-only commits |
| `git_dirty` | changes on **any uncommitted edit** in the working tree |
| `os_platform`, `os_version` | differ between Linux / macOS / CI runners |
| `python_version` | changes on any interpreter patch bump |

### Consequence

The same scientific corpus, curated under the same policy, produces a
**different snapshot identity** when:

- a typo is fixed in a README (git_sha changes);
- the snapshot is frozen from a dirty working tree (git_dirty = True);
- the identical pipeline is re-run on a different machine or CI runner;
- Python is upgraded from 3.12.3 to 3.12.4.

This was observed empirically during the Phase 1 audit: re-running the freeze
script over byte-identical input records produced
`a0160ec9ab46e3b7…` where the committed manifest recorded
`2b8f5ce6f236344b…`.

### Why this matters scientifically

Constitution Invariant 4 requires that a Model Generation remain reproducible
from its recorded snapshot lineage. If `snapshot_sha256` is not a function of
the data alone, then:

- a snapshot's integrity **cannot be independently verified** — a third party
  re-running the pipeline on the same data gets a different hash and cannot
  distinguish "data changed" from "environment changed";
- `SnapshotDiff(N, N+1)` reports a difference when nothing scientific changed;
- `parent_snapshot_sha256` lineage becomes an artefact of commit history
  rather than of data descent.

---

## 2. Tension with existing governance

GDR-002 §2 establishes the precedent that provenance metadata must not
destroy determinism:

> `profile_sha256` — content hash over every field above **except** the freeze
> timestamp … a timestamp is provenance metadata and must never make
> otherwise-identical profiles non-deterministic.

The same paragraph, however, states that the software toolchain **should**
affect the hash:

> any change to the corpus, the software toolchain, or the profile algorithm
> produces a different `profile_sha256`

These two statements are in tension for `git_sha` specifically. The intent
("a toolchain change must be detectable") is sound; the implementation via
`git_sha` is too coarse, because it fires on changes that provably cannot
affect the records.

---

## 3. Options

### Option A — Two-hash separation (proposed)

Split identity from environment:

```
content_sha256           = SHA256( stable_json(records) + stable_json(policy) )
build_provenance_sha256  = SHA256( stable_json(software) )
snapshot_id              = "SNAP-" + content_sha256[:12]
```

Both are stored in the manifest. Lineage, `SnapshotDiff`, and Model Generation
binding key on `content_sha256`. `build_provenance_sha256` is recorded and
reportable but is not identity-defining.

**Rationale.** The records are the scientific output. If a toolchain change
alters the science — e.g. an RDKit standardization change producing different
canonical SMILES — then the *records themselves differ* and `content_sha256`
changes accordingly. A toolchain change that does not alter any record cannot
have altered the science, and should not alter the corpus identity.

- Preserves GDR-002's detectability intent: environment drift remains visible
  via `build_provenance_sha256`.
- Makes snapshot integrity independently verifiable from data + policy alone.
- Cross-platform and cross-commit reproducible.

**Cost.** Changes `SnapshotManifestV2` schema; existing snapshots must be
re-frozen or migrated; `ADR-0009` and `GDR-002` text needs a consistency pass.

### Option B — Restrict `SoftwareProvenance` inside the hash

Keep one hash but include only scientifically-load-bearing software fields
(e.g. `rdkit_version`, `orthosteric_version`, `lockfile_hash`), excluding
`git_sha`, `git_dirty`, `os_platform`, `os_version`, `python_version`.

- Smaller schema change.
- Still not verifiable by a third party who pins different OS/Python.
- Requires a governed judgement on which fields are load-bearing — itself a
  scientific decision.

### Option C — Status quo, with documented limitation

Accept that `snapshot_sha256` identifies "this data built in this environment",
and add a governed statement that cross-environment reproduction is out of
scope.

- No code change.
- Contradicts Invariant 4 in practice; blocks independent verification.
- Not recommended.

---

## 4. Recommendation

**Option A**, on the grounds that it is the only option under which snapshot
identity is a property of the science rather than of the build machine, which
is what Invariant 4 and Invariant 5 jointly require.

---

## 5. What was NOT done

Per Constitution §36, the pipeline did **not**:

- change the hashing implementation;
- re-define snapshot identity;
- migrate or silently re-freeze existing snapshots to mask the issue;
- select which `SoftwareProvenance` fields are scientifically load-bearing.

This record raises the question only. No hashing behaviour has been altered.

---

## 6. Interim consequence

Until this is decided:

- Activity Snapshot identity is **environment-dependent** and must be quoted
  together with its `software.git_sha`.
- Stage 0 **cannot be sealed**, because sealing asserts a stable corpus
  identity that the current implementation does not provide.
- Acquisition, harmonization, characterization and QC are unaffected and may
  proceed; only the *identity semantics* of the resulting snapshot are in question.

## 7. Review trigger

Project Owner decision required before Stage 0 sealing or Model Generation 1.

---

## 8. ACCEPTANCE ADDENDUM (2026-08-06)

**Decision: Option A, approved as follows (verbatim from the Project Owner):**

> Snapshot scientific identity shall be `content_sha256 =
> SHA256(records + scientific policy)`. Build/environment provenance shall
> be separately represented as `build_provenance_sha256` and must not
> alter scientific snapshot identity. Retrieval timestamps are provenance,
> not identity-defining content. Existing A0 remains void; A1–A3 must be
> migrated/re-frozen under the approved identity model rather than mutated.

### 8.1 Implementation

`src/orthosteric/data/snapshots/_builder.py`:

```
content_sha256 = SHA256( stable_json(content_view(sorted_records))
                        + stable_json(policy.to_canonical_dict()) )

build_provenance_sha256 = SHA256( stable_json(software.to_canonical_dict()) )

snapshot_sha256 := content_sha256   # scientific identity
snapshot_id = "SNAP-" + content_sha256[:12]
```

`content_view()` strips `retrieval_timestamp` from each record before
hashing (`_PROVENANCE_ONLY_RECORD_FIELDS`); the field remains stored, just
not identity-defining. `SnapshotManifestV2` carries a new
`build_provenance_sha256` field, reportable but never identity-defining.

### 8.2 Empirical verification (post-implementation)

Re-running the §3 reproducibility experiment against the new code
(`analysis/gdr010_reproducibility.py`, `analysis/validate_a4.py`) confirms:

| Perturbation | `snapshot_sha256` | `build_provenance_sha256` |
|---|---|---|
| git_sha, git_dirty, python_version, os_platform, os_version, rdkit_version, orthosteric_version, lockfile_hash | unchanged | changed |
| `retrieval_timestamp` inside records | unchanged | n/a |
| genuine record edit (activity_value) | changed | n/a |
| policy edit | changed | n/a |

### 8.3 Migration

A0 remains VOID (ADR-0013). A1, A2, A3 are retained on disk, unmutated, as
the historical record of how the corpus reached its current isoform
vocabulary and scaffold assignment — they were frozen under the pre-GDR-010
single-hash scheme and are not retroactively rehashed.

The migration to the approved identity model is Activity Snapshot **A4**:
built from A3's exact harmonization output plus the GDR-011 fields
(§ GDR-011 below), frozen under the new `SnapshotBuilder`, with
`parent_snapshot_sha256` = A3's `snapshot_sha256` as recorded in A3's own
manifest (i.e. under the scheme in effect when A3 was frozen — lineage
records history as it happened, not as it would look under the current
scheme).

### 8.4 Tests

`tests/data/snapshots/test_snapshot_builder.py`: 9 parametrized environment-
invariance tests, 3 `build_provenance_sha256` sensitivity tests, 1
reproducibility test, 1 `retrieval_timestamp`-invariance test. The
pre-existing test that asserted the now-rejected behaviour
(`rdkit_version` change → different `snapshot_sha256`) was rewritten to
assert the approved behaviour.

### 8.5 Residual, unresolved observation (not decided here)

`CorpusProfile.profile_sha256` (GDR-002) still includes `SoftwareProvenance`
in its own hash, independently of this decision — GDR-010's scope was
snapshot identity, not profile identity. This tension is noted but not
resolved by this GDR; a future GDR may need to extend the Option A split to
`_profile.py` if profile identity is found to have the same problem.

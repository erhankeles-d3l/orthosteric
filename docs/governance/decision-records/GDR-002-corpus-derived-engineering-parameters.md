# Governance Decision Record GDR-002 — `N_c`, `N_b`, `N_w` Reclassified as Corpus-Derived Engineering Parameters

**Category:** Scientific (methodology; changes the *kind* of object `N_c`,
`N_b`, `N_w` are, and — as a necessary consequence, made explicit in §4 —
changes R1's function for these three quantities).
**Status:** Accepted.
**Date:** 2026-08-05.
**Decided by:** Project Owner, direct instruction (2026-08-05), implemented by
the computational pipeline. This is not a literature-review resolution under
the pipeline's standing authorization (unlike `GDR-001`) — it is an explicit
governance instruction, executed and documented here for auditability.
**Amends (in effect, additively — not by deleting prior text):**
`docs/specifications/CONSTITUTION_AMENDMENT_SET_v4.7.md` Amendments A1 (S4b)
and A10 (R1); `docs/IMPLEMENTATION_BACKLOG.md` `SCI0-028`'s scope and its
ordering constraint relative to `SCI0-015`;
`docs/governance/SCI0-028-GOVERNANCE-GAP-REPORT.md`'s classification of items
1–3.

---

## Decision

`N_c` (largest connected component), `N_b` (bridging-compound count), and
`N_w` (within-study four-isoform compound count) are **corpus-derived
engineering parameters**, not literature-derived scientific thresholds.

1. Each is computed **deterministically** from the frozen `SCI0-011` immutable
   snapshot — never before it exists, never from partially curated data.
2. None is **optimized during model development** and none is **fitted to
   model performance**. They are graph-theoretic and set-counting properties
   of the assembled evidence corpus, computed once per snapshot, independent
   of anything downstream of `SCI-1`.
3. None is **estimated from the literature**. `docs/governance/SCI0-028-
   GOVERNANCE-GAP-REPORT.md` §3–4 already established why no literature
   source can supply a defensible number: `N_c`/`N_b`'s own sensitivity
   analysis (`ADR-0003_AUDITOR_2_THRESHOLD_EVIDENCE.md`) showed roughly 4×
   variation across three individually-plausible, mutually-inconsistent
   assumptions about literature structure — the correct value depends on the
   specific corpus assembled, not on a property PI3K biology or the
   scientific literature could specify in advance.
4. They become part of an **immutable corpus profile**, itself content-hashed
   and attached to the `SCI0-011` snapshot it was computed from — see §2.

## Rationale

The Project Owner's stated scientific rationale is adopted in full: these
quantities describe the corpus, not the organism. `N_c` is "the size of the
largest connected component of the finalized evidence graph" — a fact about
which compounds happened to be co-assayed across the public record this
project draws on, not a fact about PI3K. Treating it as a pre-registerable
scientific constant was a category error inherited from the original R1
formulation, which asked the Independent Scientific Auditor to "determine
these from first principles" (`ADR-0003_INDEPENDENT_AUDITOR_BRIEF.md`,
AUDITOR-2) — but there are no first principles for the connectivity of one
specific, contingent literature corpus. `GDR-002` corrects the category, not
merely the number.

## 1. Two governance categories, made explicit

| | Corpus-derived engineering parameters | Scientific parameters |
|---|---|---|
| **Examples** | `N_c`, `N_b`, `N_w`, corpus statistics, graph characteristics, scaffold distributions, publication distributions | ATP Km, Cheng-Prusoff normalization, biological assay interpretation, biochemical conversion rules, mechanistic assumptions |
| **Nature** | Deterministic outputs of the evidence corpus | Claims about biology or methodology that could be right or wrong independent of which corpus was assembled |
| **Source of value** | Computed from the frozen snapshot | Established by evidence about the organism, the assay chemistry, or the modelling methodology |
| **Governance** | Reclassified here; verified for determinism/reproducibility, not sealed as a priori numbers | Continue to require scientific governance (Governance Decision Record or Governance Amendment) and must **not** become corpus-derived |
| **This record's authority over them** | Full — this is exactly what `GDR-002` reclassifies | None — AUDITOR-5 / ATP Km is explicitly *not* touched by this record (§5) |

This distinction is binding on future work: a parameter is corpus-derived only
if its correct value is a mathematical or statistical fact about whichever
corpus was assembled, verifiable by recomputation, and would legitimately
change if the corpus changed. A parameter whose correct value is a claim
about PI3K biology, independent of which papers happened to get curated,
is scientific and must not be reclassified this way no matter how
inconvenient sourcing it proves.

## 2. The corpus profile

**Workflow** (implemented in `src/orthosteric/data/snapshots/_profile.py`):

```
Raw evidence
      |
Corpus acquisition                 (SCI0-006, SCI0-006b, SCI0-007)
      |
Corpus harmonization               (SCI0-008b/c, SCI0-009, SCI0-010, SCI0-012)
      |
Immutable snapshot (SHA-256)       (SCI0-011)
      |
Compute corpus characteristics     (SCI0-014 graph.py, SCI0-014b audit.py)
      |
Freeze corpus profile              (this record: _profile.py)
      |
Model development                  (SCI-1 onward)
```

**`CorpusProfile`** is a frozen dataclass referencing an `SCI0-011` snapshot by
its SHA-256 (a foreign key, not an embedded mutation of the snapshot object —
`SCI0-011`'s already-merged, tested code is not reopened by this record). It
bundles:

- `engineering_parameters` — `N_c`, `N_b`, `N_w`, and a small set of
  closely-related counts recorded alongside them (see §3, "the `N_w`
  ambiguity" and "the scaffold-diversity gap").
- The full `SCI0-014b` `CharacterizationReport` for that snapshot — dataset
  statistics, graph connectivity, scaffold statistics, and publication
  concentration statistics, exactly the four categories the Project Owner's
  instruction requires and exactly what `SCI0-014b` already computes.
- `software` — `SoftwareProvenance`, reused from `SCI0-011` (not redefined).
- `policy` — the full `PolicyManifest`, reused from `SCI0-011` (dedup,
  scaffold, confidence, and adjudication policy versions).
- `profile_algorithm_version` — a version identifier for *how* the profile
  itself is computed, distinct from the policy versions above: this changes
  if the connectivity or aggregation *method* changes, even if no upstream
  policy does.
- `profile_sha256` — content hash over every field above **except** the
  freeze timestamp, following the `SCI0-011` precedent exactly: a timestamp
  is provenance metadata and must never make otherwise-identical profiles
  non-deterministic.

**Freeze policy**, as instructed and implemented without exception:

- A profile is computed only from an already-frozen `SCI0-011` snapshot.
  `freeze_corpus_profile()` takes pre-computed `GraphStats` and
  `CharacterizationReport` as inputs; it does not read raw records or
  re-derive them, so it cannot be run against partially curated data by
  construction — there is no code path in this module that accepts anything
  earlier in the pipeline than an already-built characterization.
- Values cannot change without a new snapshot: `profile_sha256` is a pure
  function of `snapshot_sha256` plus the computation inputs, so any change to
  the corpus, the software toolchain, or the profile algorithm produces a
  different `profile_sha256`, never a mutated one.
- Every prior corpus profile remains independently reproducible from its
  snapshot hash, exactly as `SCI0-011` snapshots already are.

## 3. Two definitional issues, flagged rather than silently resolved

**The `N_w` ambiguity.** The Project Owner's instruction defines `N_w` as "the
number of complete within-study four-isoform **strata**" — a count of
`(study, assay)` panels. The Constitution's original wording (Amendment A10,
`CONSTITUTION_AMENDMENT_SET_v4.7.md`) and the field already implemented in
`SCI0-014`'s `GraphStats.within_study_four_isoform` define it as a count of
**compounds** measured across all four isoforms within a qualifying stratum —
a different unit. Rather than silently picking one, `EngineeringParameters`
records both under distinct names: `n_w` (compounds; the Constitution's
original unit, preserved for continuity with the already-merged `SCI0-014`
field) and `n_complete_strata` (panels; `SCI0-013`'s `StratumReport.
usable_strata`, matching the Project Owner's phrasing exactly). Both are
frozen into every profile. If the Project Owner intends `N_w` to be redefined
to the strata count going forward, that is a one-line follow-up — the value
is already computed and named, just not yet promoted to be *the* `N_w`.

**The scaffold-diversity gap.** R1's fourth disjunct — "< 8 scaffold families
in the connected component" — is **not reclassified by this record**. It was
fixed in the Constitution's original text (not left as
`[SEALED AT STAGE 0]`), so it was never one of the outstanding placeholders
`SCI0-028` was blocking on, and §4 below leaves it untouched. However, no
existing module computes scaffold-family diversity *restricted to the largest
connected component specifically* — `SCI0-014b`'s `ScaffoldStats` is
corpus-global. `CorpusProfile` does not fabricate this number; it is recorded
as a known gap (`scaffold_families_in_largest_component: None`, with a
docstring explaining why) rather than silently substituted with the
corpus-global count, which would answer a different question.

## 4. Consequence for R1 (Part VIII, Amendment A10) — stated explicitly, not implied

R1's original form compares measured connectivity against pre-sealed floors:
"Largest connected component < `N_c` compounds, or bridging compounds < `N_b`
... All four sealed before the audit runs." Under this record, `N_c` and `N_b`
are no longer pre-sealed floors — they **are** the measured quantities. A
condition of the form "measured value < measured value" is vacuous, so R1's
kill-switch function for these two disjuncts cannot survive unchanged, and
this record does not pretend otherwise.

**What replaces it.** `SCI0-031` ("`[procedure]` `SCI-0` gate evaluation... 
proceed / redesign / stop") already exists in the backlog as a human decision
point. Under this record, the connectivity-adequacy judgment that R1's `N_c`/
`N_b`/`N_w` disjuncts used to make automatically is made **there**, by the
Project Owner, informed by the frozen `CorpusProfile` — an explicit, recorded,
qualitative gate decision rather than an automatic numeric comparison against
a number no literature could have defensibly supplied anyway. This is not a
weakening of rigor relative to the status quo: the status quo was three
`[SEALED AT STAGE 0]` placeholders that `SCI0-028`'s own evidence review
(`ADR-0003_AUDITOR_2_THRESHOLD_EVIDENCE.md`) found could not be filled with a
defensible number at all. An informed human gate decision, made against a
fully reproducible frozen profile with recorded provenance, is a real
control; a numeric comparison against an arbitrarily-chosen or
unfillable placeholder was not.

**What is unchanged.** The scaffold-family disjunct ("< 8 scaffold families")
remains a pre-sealed numeric floor exactly as originally written — it was
fixed at the Constitution's original authorship, not one of the outstanding
placeholders, and this record does not touch it. `SCI0-031`'s gate decision
therefore still includes one genuine automatic numeric check (scaffold
diversity, once the component-restricted count is computed — see §3) alongside
the newly-qualitative connectivity review.

**Formal amendment status.** This record amends Amendment A10 additively:
`CONSTITUTION_AMENDMENT_SET_v4.7.md` retains its original "Was/Becomes" text
for A10 verbatim (ADRs and amendment drafts are not rewritten in place;
see `ENGINEERING_STANDARDS.md` §1), with a dated revision note appended
directly beneath it pointing here. The Constitution itself remains at v4.6
(`docs/GOVERNANCE_VERSIONS.md`); this record modifies the *proposed, not yet
Accepted* v4.7 amendment draft, which is the correct locus for a change of
this kind before that draft is ever adopted.

## 5. What this record does not do

- It does **not** touch AUDITOR-5 (ATP Km, Cheng-Prusoff normalization). Per
  the Project Owner's explicit constraint, scientific parameters "continue to
  require scientific governance and must not become corpus-derived."
  `adjudication.py`'s `INSUFFICIENT_EVIDENCE` status for AUDITOR-5 is
  unchanged.
- It does **not** convert S4b into a corpus-derived parameter. Per the
  Project Owner's explicit instruction, S4b is a methodological/model-design
  parameter and is relocated to the Decision Policy Layer (`ADR-0008`,
  `policy/`), where it is versioned, held fixed for a given experiment, and
  revisable only through a future Governance Decision Record. Concretely: a
  future `SharpnessPolicy` (or an addition to the existing policy module) will
  read `label_noise_floor_log_units` (already a `PolicyConfig` field, `SCI0-
  016`-sourced) and a configured multiplier — not a Constitution-sealed
  scientific threshold. This record documents the relocation decision; the
  policy class itself is not implemented here, since no `SCI0-016` noise
  floor exists yet for it to operate against (`UncertaintyPolicy` already
  abstains for exactly this reason).
- It does **not** compute any parameter from partially curated data — enforced
  by `freeze_corpus_profile()`'s signature, which accepts only already-built
  `GraphStats` and `CharacterizationReport` objects, themselves obtainable
  only from an already-frozen `SCI0-011` snapshot.
- It does **not** invent a value for the scaffold-diversity gap identified in
  §3.

## 6. Effect on `SCI0-028` and its ordering constraint relative to `SCI0-015`

`docs/IMPLEMENTATION_BACKLOG.md`'s `SCI0-028` row is revised (see that file)
from "seal `N_c`, `N_b`, `N_w`, S4b sharpness factor, duplicate-resolution
policy, per-isoform ATP Km source" to a verification-scoped objective:

- **Duplicate-resolution policy** — resolved (`GDR-001`). Unchanged by this
  record.
- **`N_c`, `N_b`, `N_w`** — reclassified (this record). `SCI0-028`'s
  remaining responsibility for these three is to verify `_profile.py`'s
  computation is deterministic, reproducible, and correctly provenanced —
  which is exactly what `tests/data/snapshots/test_profile.py` (this change
  set) already does against synthetic inputs, since no real snapshot exists
  yet to verify it against real data.
- **S4b** — relocated to `policy/` (this record, §5). No longer an `SCI0-028`
  scope item.
- **Per-isoform ATP Km source** — **unchanged, still `RULE_MISSING`**. This
  record does not resolve it and does not claim to.

**Ordering consequence.** The backlog's ordering constraint — "`SCI0-028`
must be `Done` before `SCI0-015` begins" — existed specifically because
`N_c`/`N_b`/`N_w` needed pre-sealing before the connectivity audit ran, to
prevent choosing the kill criterion after seeing the data (`Constitution
§1.4`; risk `R23`). That reason no longer applies to those three items: they
are now computed *from* the audit's own output, not compared against a
pre-sealed floor set before it. The ATP Km item does not gate the
connectivity portions of `SCI0-015` either — `SCI0-015`'s Q1 sub-questions
about `[ATP]` coverage (Amendment A7) are descriptive census questions, not
dependent on AUDITOR-5 being resolved. **`SCI0-015` is therefore no longer
blocked by `SCI0-028`.** It remains blocked by the separate, standing
requirement that real corpus acquisition be explicitly authorized before it
begins — unaffected by this record, and not authorized here.

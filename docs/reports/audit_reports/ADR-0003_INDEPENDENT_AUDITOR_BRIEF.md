# ADR-0003 Independent Scientific Auditor Brief

**Prepared:** governance/audit-preparation task, on `feature/adr-0003-auditor-brief`, off `main` @ `3c55960cdc3ba06ed12eb878c5bc56711291925e`.
**Filed under:** `docs/reports/audit_reports/` (established by `ADR-0006`, A2).

---

## 1. Purpose and scope

This document assembles, in one place, everything an Independent Scientific Auditor needs to review and decide on `ADR-0003` (`docs/adr/ADR-0003-public-knowledge-only-training-policy.md`). It is a **briefing package, not a decision**. It makes no scientific choice, proposes no numerical threshold, and does not alter `ADR-0003` in any way. Its only job is to separate, cleanly:

1. established project rules (already binding, not open for this Auditor to relitigate),
2. evidence already available in the repository,
3. unresolved scientific decisions,
4. proposed options that are explicitly **not** decisions,
5. evidence gaps,
6. decisions reserved exclusively for the Independent Scientific Auditor.

## 2. Repository baseline (verified at preparation time)

| Item | Value |
|---|---|
| `main` | `3c55960cdc3ba06ed12eb878c5bc56711291925e` |
| `develop` | `b73bdb33af0a87d2e2a5cef5d30a6667f80beeaa` |
| `v0.1.0-foundation` | → `795a7dc0a862f75a77b730bb732ba34c4f03de4d` |
| `ADR-0006` | Accepted |
| `ADR-0003` | Proposed |
| `SCI0-001` / `SCI0-002` / `SCI0-003` | Pending — no implementation exists |

`ADR-0003` is byte-identical to its state at the Foundation baseline commit `795a7dc0a862f75a77b730bb732ba34c4f03de4d` (`git diff 795a7dc..main -- docs/adr/ADR-0003-*.md` is empty).

## 3. ADR-0003 status

```
Status: Proposed — requires Independent Scientific Auditor sign-off
        (Constitution §7.7; ENG §1: a Scientific ADR may not be
        authored by the model developer alone)
```

`ADR-0003` is `[Scientific]` category (ENG §1). It has not been Accepted, Rejected, or Superseded. No content in it has been edited since the Foundation baseline.

## 4. Scientific governance boundary

This section states, explicitly, what this document is **not**:

- This document has **no authority over `ADR-0003`**. It cannot accept, reject, modify, or reinterpret it.
- No scientific threshold, numerical value, or dataset is proposed, invented, or selected anywhere in this document.
- Nothing here constitutes SCI-0 work. `SCI0-001`/`SCI0-002`/`SCI0-003` remain `Pending`.
- Per `CLAUDE.md` §5 and Constitution §7.7 / ENG §1: a `Scientific` ADR may not be authored, resolved, or effectively pre-decided by the model developer (or an agent acting for them) alone. Every open item below is reserved for the Independent Scientific Auditor.
- Where this document lists "options," they are drawn **verbatim from governance documents already in the repository** — never invented — and are presented as alternatives for the Auditor to choose among, not recommendations.

## 5. Auditor decision matrix

| ID | Exact scientific question | ADR-0003 §§ | Constitution §§ | ENG/Protocol §§ | Backlog objectives affected | Existing evidence | Evidence missing | Downstream consequence if unresolved | Earliest dependent objective | Must be sealed before that objective? | What the Auditor must decide |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **AUDITOR-1** | Accept or reject: train on the full connected public evidence graph, but evaluate gating criteria (S2, S4a, S4b, S5) only on the within-study, within-assay stratum | §3 | §2.3(1) as amended (Amendment A4, `CONSTITUTION_AMENDMENT_SET_v4.7.md`); §1.4 | — | `SCI0-013` (within-study stratum extraction), `SCI0-014`/`SCI0-015` (measurement graph, R1 audit), `SCI1-017b`, `SCI1-021` | ADR-0003 §3 gives the full statistical rationale: inter-lab σ ≥ 0.3 log (Constitution §2.4), cross-study σ ≈ 0.5–0.7 log vs. a 1–2 log selectivity signal; a table of which criteria (S2/S4/S5/§2.4) survive vs. break under pooling | No empirical connectivity-audit data exists yet — `SCI0-015` is itself gated behind this decision and `SCI0-028` | `SCI0-013`/`SCI0-014` | Yes — `SCI0-028` "sealed before `SCI0-015` runs" (explicit backlog ordering constraint) | Accept, reject, or modify the split (§3, recommended resolution offered but not adopted) |
| **AUDITOR-2** | Seal `N_c` (min. compounds in largest connected component), `N_b` (min. bridging compounds), `N_w` (min. within-study four-isoform compounds), and the S4 sharpness factor | §5, §10 item 2 | §1.4 (thresholds fixed before results seen) | `SCI0-028` (backlog); `sealed/MANIFEST.md` expected artefacts | `SCI0-015` (R1 evaluated here), `SCI0-028` | ADR-0003 §5 defines the *structure* of the replacement R1 (bipartite compound×isoform graph, bridging-compound requirement, ≥8 scaffold families) and states these four are "finalized at Stage 0 with the Auditor." **No candidate numerical value for any of the four exists anywhere in the repository** — confirmed by full-text search | All four values — this is a "determine," not a "select among existing values," decision | `SCI0-015` | Yes — explicit backlog note: "`SCI0-028` must be `Done` before `SCI0-015` begins" | Determine `N_c`, `N_b`, `N_w`, sharpness factor from first principles / the connectivity structure — **no existing authoritative source contains these values; this task does not propose any** |
| **AUDITOR-3** | Duplicate-resolution policy for conflicting measurements of the same compound/isoform: median / most-recent / highest-confidence / other | §7.8 (referenced), §10 item 3 | — | `SCI0-009` (requires `SCI0-008b` first), `SCI0-010` (confidence scoring, "additive and inspectable; no learned model") | `SCI0-009`, `SCI0-010` | `SCI0-010`'s one hard constraint: the confidence score must be additive/inspectable, never a learned model (governance-imposed limit on *how* any policy may use confidence, not which policy to pick) | No default or candidate policy text exists anywhere; ADR-0003 §7.8 is referenced by number but the referenced content is the open item itself, not a resolution | `SCI0-009` | Yes — implicitly, since `SCI0-009` "requires `SCI0-008b`" and both precede any snapshot with the corpus's final shape | Select or justify a policy among median / most-recent / highest-confidence / another explicitly justified alternative, consistent with `SCI0-010`'s additive-and-inspectable constraint |
| **AUDITOR-4** | Are BindingDB and PubChem BioAssay records lacking a primary publication admissible to the training/evaluation corpus? | §10 item 4 | §2 (accepted sources, generic) | `SCI0-006` (source adapters), `SCI0-011` (snapshot builder) | `SCI0-006`, `SCI0-011` | ADR-0003 §2 lists ChEMBL · BindingDB · PubChem BioAssay · RCSB PDB · peer-reviewed literature as accepted sources **in general**, with no carve-out for records inside those sources that lack a citable publication | No repository text addresses this sub-case at all | `SCI0-006` | Not explicitly stated as a seal, but affects corpus definition before any snapshot (`SCI0-011`) is built | Decide admissibility, and if admissible, under what confidence/tier treatment |
| **AUDITOR-5** | Define the authoritative ATP Km source, construct scope, version/seal policy, and conflict-resolution rule for Cheng–Prusoff normalization | §4 (silent on this) | §2.3(2) as amended (Amendment A5) — same silence | `SCI0-008` (`docs/specifications/SCI0-001-refinement-data-acquisition.md` §`SCI0-008`); `sealed/MANIFEST.md` line 23 lists "per-isoform ATP Km source" under expected `SCI0-028` artefacts | `SCI0-008`, `SCI0-028` | The Cheng–Prusoff formula itself is specified precisely (`Ki = IC50 / (1 + [ATP]/Km_ATP)`, `SCI0-001` spec line 132). `sealed/MANIFEST.md` already anticipates a "per-isoform ATP Km source" as an artefact to be sealed under `SCI0-028`. `SCI0-001`'s spec requires the source be "cited, not assumed" (line 142) | **No authoritative ATP Km value, source, database, or reference table exists anywhere in the repository.** No construct-scope definition (e.g., full-length vs. kinase-domain-only Km). No version/date policy. No conflict-resolution rule for disagreeing published values. No stated precedence between sources | Any record with known [ATP] but no cited Km is non-normalizable under the current spec, silently shrinking the usable corpus in an unaudited way | `SCI0-008` | Yes, per `sealed/MANIFEST.md`'s own listing — but **`ADR-0003` §10 does not list this as an Auditor open item, even though the sealed-artefact manifest already expects it from `SCI0-028`.** This is the confirmed discrepancy (§8 below) | Define the authoritative Km source(s), construct scope, version/seal policy, and the conflict-resolution rule when multiple published values exist for one isoform/construct |

**Evidence vs. recommendation, made explicit:** every "Existing evidence" cell above quotes or cites text already in the repository. No cell in "What the Auditor must decide" contains a number, named source, or policy choice supplied by this task — those columns state the *shape* of the decision required, never its content.

## 6. Evidence available (consolidated)

- `docs/adr/ADR-0003-public-knowledge-only-training-policy.md` — full decision rationale, §1–§10, including its own four explicit open items (§10) and the "Recommended resolution, for the Auditor to accept or reject" in §3 (a recommendation, explicitly not an adopted decision).
- `docs/PROJECT_CONSTITUTION_v4.6.md` §1.4, §2.3, §2.4, §2.5, §3.1, §3.6, §5.4 — the criteria, evidence-class, and thresholding rules ADR-0003 amends or is constrained by.
- `docs/ENGINEERING_STANDARDS.md` §1 (ADR categories, Scientific-ADR authorship restriction), §2 (package responsibilities for `data/`).
- `docs/specifications/CONSTITUTION_AMENDMENT_SET_v4.7.md` — the exact proposed Constitution amendments (A4, A5, A6, A11, R5) that would take effect if `ADR-0003` is Accepted, given as "Was" → "Becomes" diffs.
- `docs/specifications/SCI0-001-refinement-data-acquisition.md` — implementation-level detail for `SCI0-002`…`SCI0-014b`, contingent on `ADR-0003` Accepted per its own text ("Until then this is proposed work, not authorized work").
- `docs/specifications/EXECUTION_PLAN_bootstrap-to-stage0-gate.md` — objective sequencing through the Stage 0 gate.
- `docs/PROJECT_SPECIFICATION.md` §1.5–1.6 — normalization/admissibility rules and requirement→module→backlog traceability table.
- `docs/IMPLEMENTATION_BACKLOG.md` — objective definitions, statuses (all `SCI0-002`…`SCI0-031` `Pending`), and the explicit `SCI0-023`…`SCI0-029` "Scientific ADR category, may not be authored by the model developer alone" restriction.
- `sealed/MANIFEST.md` — "Nothing is sealed yet"; expected-artefact table naming `SCI0-028`'s scope, including "per-isoform ATP Km source."
- `docs/FOUNDATION_STATE.md`, `docs/IMPLEMENTATION_PROTOCOL_FOUNDATION.md`, `docs/IMPLEMENTATION_PROTOCOL_SCIENTIFIC.md` — confirm Foundation is `COMPLETE`, lifecycle stage is `Research`, and the `SCI-0` state machine has not been entered.

## 7. Evidence gaps

1. **No candidate values for `N_c`, `N_b`, `N_w`, or the S4 sharpness factor** exist anywhere in the repository (AUDITOR-2). This is expected under Constitution §1.4 (thresholds fixed before results are seen) — the Auditor is meant to determine these from first principles, not select among pre-supplied candidates.
2. **No candidate duplicate-resolution policy draft** exists (AUDITOR-3) beyond the single hard constraint that any scoring involved must be additive and non-learned (`SCI0-010`).
3. **No text addresses BindingDB/PubChem admissibility without a primary publication** at all (AUDITOR-4) — a true blank, not merely an unresolved choice among stated options.
4. **No ATP Km source, construct-scope definition, version policy, or conflict-resolution rule exists anywhere** (AUDITOR-5) — see §8 for the full focused audit.
5. **No `supplementary/` ADR-0003 review package exists** — see §9. This gap is procedural (a referenced artifact absent) rather than scientific, but it means the Auditor package handed over here is the totality of what this repository currently contains; there is no separate deeper analysis document to consult.

No evidence gap listed above was filled by this task. Each is reported as-is.

## 8. ATP Km policy gap — focused audit

**Search performed** (current tree, all tracked file types): `ATP Km`, `Km`, `Cheng-Prusoff` / `Cheng–Prusoff`, `Ki conversion`, `ATP concentration`, `isoform ATP`, `PI3Kα/β/γ/δ Km`.

**Every occurrence found**, with what each one does and does not say:

| Location | What it says | What it does NOT say |
|---|---|---|
| `docs/PROJECT_CONSTITUTION_v4.6.md:368` | Targets are ATP-competitive and differ in ATP Km; IC50 depends on assay [ATP] | No source, value, or policy |
| `docs/adr/ADR-0003-public-knowledge-only-training-policy.md:60,62` | Where [ATP] and isoform ATP Km are known, convert IC50→Ki (Cheng–Prusoff) | No source, version, or conflict-resolution rule |
| `docs/specifications/CONSTITUTION_AMENDMENT_SET_v4.7.md:57` (Amendment A5) | Same normalization rule, proposed Constitution text | Same silence, carried into the proposed amendment |
| `docs/PROJECT_SPECIFICATION.md:61` | Same rule, restated | Same silence |
| `docs/specifications/SCI0-001-refinement-data-acquisition.md:132,142,205` | Gives the exact formula (`Ki = IC50 / (1 + [ATP]/Km_ATP)`); requires the per-isoform Km source be "cited, not assumed"; notes the isoform ATP Km table is "PI3K-specific" and a precondition for `SCI-4` cross-family transfer | Does not name the source, does not define construct scope, does not define what happens when published Km values disagree |
| `docs/IMPLEMENTATION_BACKLOG.md:100` (`SCI0-008`) | Backlog objective performs the conversion "where [ATP] and isoform ATP Km are known" | Same silence |
| `docs/specifications/EXECUTION_PLAN_bootstrap-to-stage0-gate.md:73,97` | Restates `SCI0-008`'s scope; `SCI0-028`'s seal scope includes "per-isoform ATP Km source" | Does not itself supply a source |
| `sealed/MANIFEST.md:23` | Lists "per-isoform ATP Km source" as an artefact **expected** to be sealed under `SCI0-028` | Nothing is sealed yet; no source is named |

**Search for specific isoform values** (`PI3Kα Km`, `PI3Kβ Km`, `PI3Kγ Km`, `PI3Kδ Km`): **zero matches**. No numeric Km value for any PI3K isoform, and no named literature/database source for one, exists anywhere in the tracked repository.

**Conclusion: no authoritative ATP Km source exists in this repository at present.** This is stated as fact, not proposed as a gap to be filled by this task. **No source, value, or policy is chosen here.**

**Auditor decision item (verbatim, as instructed):**

> Define the authoritative ATP Km source, construct scope, version/seal policy, and conflict-resolution rule for Cheng–Prusoff normalization.

This is **AUDITOR-5** in the matrix above (§5).

**The precise discrepancy this brief surfaces:** `sealed/MANIFEST.md` already anticipates this decision as part of `SCI0-028`'s sealed scope ("per-isoform ATP Km source"), and `SCI0-001`'s implementation spec already requires the source be cited rather than assumed — yet **`ADR-0003` §10's own numbered Auditor open-items list (items 1–4) does not include it.** The plumbing downstream expects this decision to be made and sealed; the ADR's own open-items enumeration does not ask the Auditor for it. This is an internal inconsistency in the governance chain, not a resolution — the Auditor (or the ADR's owner) should decide whether to add it as `ADR-0003`'s fifth explicit open item, or fold it into item 2 (since it will materially be sealed alongside `N_c`/`N_b`/`N_w`/sharpness factor at `SCI0-028`).

## 9. Missing supplementary-package finding

**Read-only search performed:**
- `git branch -a` — all local and remote branches enumerated (`main`, `develop`, `feature/adr-0006-repository-structure`, plus their remotes)
- `git log --all --diff-filter=A --name-only` — every file ever *added* in any commit, on any branch, filtered for "supplement" in its path: **zero matches**
- `git rev-list --all | xargs git grep -il "supplementary"` — every commit, on any branch, searched for the word "supplementary" in file contents: matches found only inside `ADR-0003`, `PROJECT_SPECIFICATION.md`, `CONSTITUTION_AMENDMENT_SET_v4.7.md`, `EXECUTION_PLAN_bootstrap-to-stage0-gate.md`, `SCI0-001-refinement-data-acquisition.md`, and `NOTICE` — in every case as ordinary prose (e.g., "peer-reviewed publications and their supplementary data"), never as a directory or package name
- Full enumeration of every file ever committed on any branch (84 unique paths, listed in the search output) — no `supplementary/` prefix appears among them

**Finding, stated explicitly:** a `supplementary/` ADR-0003 review package **has never existed in this repository's history, on any branch, at any commit.** It was not deleted, moved, or lost — it was never created. No historical version exists to identify or restore. This brief does not recreate one, and does not claim any such package was reviewed in preparing this brief — this brief itself, together with the documents cited in §6, is the complete evidentiary basis currently available.

## 10. SCI objective dependency map

```
ADR-0003 Accepted (blocking, all of SCI-0)
  │
  ├─ AUDITOR-1 (train/eval split) ──▶ SCI0-013 ─▶ SCI0-014 ─▶ SCI0-015 (R1 evaluated here)
  │                                                              ▲
  ├─ AUDITOR-2 (N_c,N_b,N_w,sharpness) ──▶ SCI0-028 (seal) ──────┘  [SCI0-028 must be Done before SCI0-015]
  │
  ├─ AUDITOR-3 (duplicate-resolution) ──▶ SCI0-008b ─▶ SCI0-009 ─▶ SCI0-010
  │
  ├─ AUDITOR-4 (BindingDB/PubChem admissibility) ──▶ SCI0-006 ─▶ SCI0-011 (snapshot builder)
  │
  └─ AUDITOR-5 (ATP Km policy) ──▶ SCI0-008 (Cheng–Prusoff conversion)
                                       and SCI0-028 (per sealed/MANIFEST.md expected artefact)

SCI0-001 ("refine SCI-0 backlog; confirm Q1–Q16 coverage under ADR-0003")
  requires ADR-0003 Accepted per its own spec's Contingency clause.
```

All five Auditor items sit upstream of `SCI0-001`'s own stated contingency. None has been resolved by this task.

## 11. Exact questions for the Independent Scientific Auditor

**AUDITOR-1.** Accept, reject, or modify: train on the connected public evidence graph; evaluate S2, S4a, S4b, S5 only on the within-study, within-assay stratum (ADR-0003 §3; Amendment A4).

**AUDITOR-2.** Determine and seal `N_c`, `N_b`, `N_w`, and the S4 sharpness factor (ADR-0003 §5, §10 item 2). No existing authoritative source in this repository contains candidate values — these must be determined, not selected.

**AUDITOR-3.** Confirm the duplicate-resolution policy: median, most-recent, highest-confidence, or another explicitly justified policy consistent with `SCI0-010`'s additive/inspectable, non-learned constraint (ADR-0003 §7.8, §10 item 3).

**AUDITOR-4.** Confirm whether BindingDB and PubChem BioAssay records lacking a primary publication are admissible to the corpus, and if so, under what tier/confidence treatment (ADR-0003 §10 item 4).

**AUDITOR-5.** Define the authoritative ATP Km source, construct scope, version/seal policy, and conflict-resolution rule for Cheng–Prusoff normalization (not currently an ADR-0003 §10 item; surfaced by this brief; already expected as a `SCI0-028` sealed artefact per `sealed/MANIFEST.md`).

## 12. Explicit statement — no decisions have been made

No scientific decision, threshold, value, source, or policy has been selected, adopted, or implied as preferred anywhere in this document. Every "recommended resolution" quoted from `ADR-0003` §3 is quoted as an existing proposal within `ADR-0003` itself, not endorsed or adopted by this brief. Where this brief lists options (e.g., AUDITOR-3's median/most-recent/highest-confidence), they are presented neutrally, without ranking or recommendation.

## 13. Explicit statement — this document has no authority over ADR-0003

This brief is an audit-preparation artifact under `docs/reports/audit_reports/` (ADR-0006, A2). It does not amend, supersede, reinterpret, or bind `ADR-0003`. `ADR-0003`'s status (`Proposed`), its substantive text, and its own §10 open-items list remain exactly as they were before this document was written. Only the Independent Scientific Auditor's own review, followed by a change to `ADR-0003`'s Status line (or a superseding ADR), can move `ADR-0003` toward `Accepted`.

## 14. Independent Scientific Auditor sign-off (to be completed by the Auditor — left blank)

| Item | Auditor determination |
|---|---|
| **AUDITOR-1** (train/eval split) | ☐ Accepted ☐ Rejected ☐ Modified — details: __________ |
| **AUDITOR-2** (`N_c`, `N_b`, `N_w`, sharpness factor) | Values and seal specification: __________ |
| **AUDITOR-3** (duplicate-resolution policy) | ☐ Accepted ☐ Rejected ☐ Modified — details: __________ |
| **AUDITOR-4** (BindingDB/PubChem admissibility) | ☐ Accepted ☐ Rejected ☐ Modified — details: __________ |
| **AUDITOR-5** (ATP Km source/scope/version/conflict-resolution) | ☐ Accepted ☐ Rejected ☐ Modified — details: __________ |
| **Auditor name / affiliation** | __________ |
| **Date** | __________ |
| **Signature / attestation** | __________ |

*Fields above are intentionally left blank. Completing them is the Independent Scientific Auditor's exclusive prerogative (Constitution §7.7; ENG §1).*

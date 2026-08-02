# ADR-0003 Gate-Readiness Evidence Plan

**Prepared by:** the implementation developer, as a companion to the existing
`ADR-0003_INDEPENDENT_AUDITOR_BRIEF.md`. **Not a decision document.** Nothing in this
plan resolves a question; it exists to show what evidence is available, what is missing,
and how the missing evidence could be generated without ever inspecting the eventual
scientific corpus to tune the answer.

**Governing constraint:** Constitution §1.4 — thresholds are pre-registered before the
audit that they gate. This plan exists precisely so that thresholds can be set *before*
`SCI0-015` runs, per `SCI0-028`.

---

## Evidence matrix

| # | Question | Governing section | Existing evidence | Missing evidence | Proposed evidence-generation method | Numerical value required? | Sealing eventually required? | Downstream objectives affected | Exclusively an Auditor decision |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Train-on-graph vs. evaluate-within-study | ADR-0003 §3; Constitution §2.3(1) | Full qualitative argument already in ADR-0003 and the Auditor Brief | A concrete leakage-prevention rule (scaffold-family exclusion) is proposed but not adopted | Technical analysis — see `ADR-0003_METHODOLOGICAL_CONSIDERATIONS.md` §AUDITOR-1 | No — this is a policy choice, not a threshold | No | `SCI0-004` schema; `SCI0-013` stratification; `SCI0-014` graph construction | **Yes** — accept / reject / accept-with-modification |
| 2 | `N_c`, `N_b`, `N_w`, S4 sharpness factor | ADR-0003 §5, §10; `SCI0-028` | Operational definitions extracted from governance docs (below); a reproducible power/null-model analysis — see `ADR-0003_THRESHOLD_ANALYSIS.md` | Real corpus characterization (Stage 0 Q1–Q9) does not exist yet — cannot exist yet, since it's downstream of this seal | Power analysis for `N_w` (done, see companion doc); structural/graph-theoretic reasoning for `N_c`/`N_b` (done, partial); null-model calibration for S4b (done) | **Yes**, eventually — but the analysis here shows per-compound power is satisfied at small `n`, so the true constraint is representativeness, not power | **Yes** — this is precisely what `SCI0-028` seals | `SCI0-015` audit; every criterion gated by R1 | **Yes** — final numbers |
| 3 | Duplicate-resolution policy | ADR-0003 §10(3); Constitution §3.3 | Existing project confidence-scoring framework (deterministic, additive, non-learned) | None outstanding at the policy level | Comparative technical analysis — see `ADR-0003_METHODOLOGICAL_CONSIDERATIONS.md` §AUDITOR-3 | No | Yes — the chosen policy is recorded, not "sealed" as a number, but is immutable once adopted (Constitution §7.2) | `SCI0-009` deduplication; `SCI0-008` normalization ordering | **Yes** — final policy choice |
| 4 | BindingDB/PubChem admissibility without primary publication | ADR-0003 §10(4); Constitution §2.5 (evidence classes) | Existing E1–E4 evidence-class framework already in the Constitution | None outstanding at the policy level | Provenance-tier mapping — see `ADR-0003_METHODOLOGICAL_CONSIDERATIONS.md` §AUDITOR-4 | No | No | `SCI0-006` connector tiering; `SCI0-015` Q8 corpus size | **Yes** — admissible / restricted / excluded |
| 5 | ATP Km policy (source, scope, versioning, conflicts, sealing) | ADR-0003 §4; review package item 4 — **absent from ADR-0003's own §10 list**, see finding below | Constitution §4 states the normalization *method* (Cheng–Prusoff) but not the Km *source* | A verified, citable numeric Km(ATP) per isoform/construct — see `ADR-0003_ATP_KM_EVIDENCE_REVIEW.md` for what was and was not found | Literature search (performed — see companion doc); the search surfaced one strong candidate paper but could not verify its numeric value due to an access barrier | **Yes**, per-isoform/construct | Yes — `SCI0-028`, time-critical, before `SCI0-008` | `SCI0-008` normalization; every Cheng–Prusoff-converted record | **Yes** — final source hierarchy and values |

## Finding carried forward from the existing Auditor Brief

`ADR-0003 §10` ("Open items requiring Auditor decision before Accepted") lists four
items and omits the Km policy as a numbered item, even though `§4` of the same document
states the normalization method without specifying the Km source. This plan treats Km as
a fifth, equally live question — consistent with the review package and the task that
requested this evidence plan — but flags that `§10` itself should probably be corrected
to include it, which is an ADR-text change and therefore outside developer authority
(Constitution: ADRs are immutable except the Status line).

## What this plan does not do

- It does not set `N_c`, `N_b`, or `N_w` to final values.
- It does not choose a duplicate-resolution policy.
- It does not rule on BindingDB/PubChem admissibility.
- It does not select an ATP Km source or value.
- It does not change ADR-0003's Status line.

Every one of those remains the Independent Scientific Auditor's decision.

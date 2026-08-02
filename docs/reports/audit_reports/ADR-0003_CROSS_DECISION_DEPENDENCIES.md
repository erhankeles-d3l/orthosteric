# ADR-0003 Cross-Decision Dependencies

**Status of this document: developer evidence-gathering output — informs, does not
resolve, any Auditor decision.** No item below is a decision. Companion to
`ADR-0003_INDEPENDENT_AUDITOR_BRIEF.md`, `ADR-0003_GATE_READINESS_EVIDENCE_PLAN.md`,
`ADR-0003_THRESHOLD_ANALYSIS.md`, `ADR-0003_METHODOLOGICAL_CONSIDERATIONS.md`, and
`ADR-0003_ATP_KM_EVIDENCE_REVIEW.md`. This document does not repeat their analysis;
it examines only the *interactions* among the five Auditor questions.

---

## 1. ATP Km ↔ duplicate resolution

Different Km(ATP) values for the same isoform (the PI3Kδ 118 μM vs. 37 ± 3 μM conflict
documented in `ADR-0003_ATP_KM_EVIDENCE_REVIEW.md` §C is now a concrete, in-hand instance
of this, not a hypothetical) produce different Ki values for every IC50 record converted
via Cheng–Prusoff before duplicate resolution runs. **Consequence:** whichever Km the
Auditor selects changes every downstream Ki value that duplicate-resolution then
aggregates — the two decisions cannot be made independently and expect the resulting
corpus to be reproducible if either changes later without re-running the other. This is
a re-statement, in concrete terms, of why Order A (normalize-then-aggregate) is the only
sound ordering (`ADR-0003_METHODOLOGICAL_CONSIDERATIONS.md` §AUDITOR-3) — a Km change
under Order A requires re-normalizing before re-aggregating; under the rejected Order B
it would silently corrupt an already-aggregated value.

## 2. ATP Km ↔ isoform selectivity

Constitution §2.4 requires reporting per-target confidence and uncertainty separately,
and forbids claiming precision below the label noise floor. If the *uncertainty* on
Km(ATP) differs meaningfully across isoforms — which the current evidence already
suggests, since three isoforms have no reported error at all (Table 1, TR-FRET) while
PI3Kδ's competition-assay value carries an explicit ± 3 μM — then the normalized Ki
values inherit asymmetric additional uncertainty across isoforms **before** any assay or
inter-lab noise is even considered. An apparent selectivity signal between two isoforms
could be partly or wholly an artefact of one isoform's Km being better- or worse-
characterized than another's, not a real potency difference. This is a risk to flag for
the Auditor's threshold-setting (AUDITOR-2) and normalization-policy (AUDITOR-5)
decisions jointly, not a claim that the current evidence proves such an artefact exists.

## 3. BindingDB/PubChem admissibility ↔ threshold selection

Already identified in `ADR-0003_METHODOLOGICAL_CONSIDERATIONS.md`'s cross-question note:
a stricter admissibility policy (AUDITOR-4) shrinks the corpus, which makes `N_c`/`N_b`/
`N_w` (AUDITOR-2) harder to clear. This document adds one refinement: because
`ADR-0003_THRESHOLD_ANALYSIS.md` recommends `N_c`/`N_b` be specified as *relative*
quantities (e.g., "≥ X% of total compounds," "≥ Y compounds per identified study
cluster") rather than fixed absolute counts, the interaction is not purely one-directional
— a relative threshold partially self-adjusts to whatever corpus size AUDITOR-4 produces,
whereas an absolute threshold does not. This means the *form* of the AUDITOR-2 threshold
(absolute vs. relative) changes how sensitive the whole gate is to the AUDITOR-4 decision,
which is itself a consideration for the Auditor, not a resolution of either.

## 4. Duplicate resolution ↔ graph topology

Aggregating records (however AUDITOR-3 resolves) collapses multiple raw measurements into
one node-defining record. Depending on *when* aggregation happens relative to graph
construction (`SCI0-014`), it can change: node count (multiple raw records → one compound
node either way, so this is usually neutral), but **edge count and bridging-compound
identification are not neutral** — if two studies both measured the same compound against
overlapping isoform subsets, whether that compound counts as a "bridging compound" for
`N_b` depends on whether its measurements from both studies survive as distinguishable
evidence or get silently merged into a single aggregate before the graph is built. This is
a direct, mechanical dependency: `SCI0-009`/`SCI0-010` (duplicate resolution) must run in
a way that graph construction (`SCI0-014`) can still see per-study provenance, or `N_b`
becomes uncountable in the sense the Auditor intends it.

## 5. Train/evaluation split ↔ N_w

`ADR-0003_METHODOLOGICAL_CONSIDERATIONS.md` §AUDITOR-1 proposes (as a candidate, not a
decision) excluding the within-study evaluation stratum from training at the
**scaffold-family** level rather than the record level, to protect the novel-scaffold
generalization claim. `ADR-0003_THRESHOLD_ANALYSIS.md` observes that `N_w`'s real
constraint is representativeness, i.e., breadth across scaffold families. **These two
considerations pull in opposite directions on corpus size**: the stricter the leakage
exclusion (whole scaffold families removed from training whenever their family appears
anywhere in the evaluation stratum), the smaller both the training pool *and* the
achievable evaluation-stratum diversity become. A very strict AUDITOR-1 split could make
an ambitious AUDITOR-2 `N_w` target harder to reach, or vice versa. Neither analysis
decided this trade-off; it is named here as a joint consideration.

## 6. Threshold selection ↔ admissibility — the anti-circularity constraint

Restated because it is the single most important interaction structurally: Constitution
§1.4 requires all thresholds fixed **before** the audit that they gate is run. This means
`N_c`, `N_b`, `N_w`, and the S4 sharpness factor must **not** be set by looking at the
actual corpus that results from whatever AUDITOR-4 admissibility policy is chosen — the
ordering must be: AUDITOR-4 admissibility policy decided → `SCI0-028` seals `N_c`/`N_b`/
`N_w`/S4 → `SCI0-015` connectivity audit runs. `ADR-0003_THRESHOLD_ANALYSIS.md`'s own
anti-circularity statement (its synthetic-data-only power analysis) demonstrates the
correct pattern for the developer-evidence stage; the same ordering constraint continues
to bind at the Auditor's own sealing step (`SCI0-028`) and is not satisfied merely because
this evidence-gathering pass respected it.

## Interaction summary table

| Interaction | Direction | Governance section | Must be resolved jointly, or can be sequenced? |
|---|---|---|---|
| ATP Km ↔ duplicate resolution | Km value changes every Ki duplicate-resolution aggregates | ADR-0003 §4, §7.8 | Sequenced — Km (AUDITOR-5) must be fixed before duplicate-resolution (AUDITOR-3) is applied to Ki values, though the *policy* for AUDITOR-3 can be decided independently |
| ATP Km ↔ isoform selectivity | Asymmetric Km uncertainty risks artefactual selectivity | Constitution §2.4 | Must be considered jointly with AUDITOR-2's threshold/uncertainty treatment |
| BindingDB/PubChem admissibility ↔ threshold form | Stricter admissibility shrinks corpus, interacts with absolute vs. relative threshold form | ADR-0003 §5, §10 | Auditor should resolve AUDITOR-4 before finalizing AUDITOR-2's threshold *form*, per the existing methodological-considerations note |
| Duplicate resolution ↔ graph topology | Aggregation timing affects bridging-compound countability | `SCI0-009`/`SCI0-014` | Sequenced — duplicate-resolution implementation must preserve per-study provenance for graph construction, regardless of which policy AUDITOR-3 selects |
| Train/eval split ↔ N_w | Stricter leakage exclusion trades against achievable representativeness | ADR-0003 §3, §5 | Must be considered jointly — no clean sequencing exists |
| Threshold selection ↔ admissibility (anti-circularity) | Thresholds must not be tuned to the post-admissibility corpus | Constitution §1.4 | Strict ordering required: admissibility (AUDITOR-4) → seal (AUDITOR-2/`SCI0-028`) → audit (`SCI0-015`) |

## What this document does not do

- Does not resolve any of the five Auditor questions.
- Does not recommend an order of Auditor sign-off beyond the one strict ordering
  Constitution §1.4 already requires (admissibility before sealing, sealing before audit).
- Does not introduce any new governance rule; every dependency above follows from
  documents and analyses already in this repository.

## Independent Auditor decision required

The following remains for independent scientific determination:

1. Train/evaluation split.
2. `N_c`.
3. `N_b`.
4. `N_w`.
5. S4 sharpness factor.
6. Duplicate-resolution policy.
7. BindingDB/PubChem admissibility.
8. ATP Km source/scope/conflict policy.

None of the above is answered by this document. This document only establishes that
items 1–8 are not five (or eight) independent decisions — several interact, and the
Auditor may find it more efficient to resolve them in the sequence implied by §6's
anti-circularity constraint and the joint considerations in §2 and §5, rather than in
isolation.

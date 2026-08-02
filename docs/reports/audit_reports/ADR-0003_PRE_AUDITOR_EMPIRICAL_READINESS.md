# ADR-0003 Pre-Auditor Empirical Readiness Report

**This document contains EVIDENCE, ANALYSIS, CANDIDATE observations, and UNRESOLVED
questions only. It contains no DECISION, no ACCEPTED item, and nothing SEALED.**

---

## 1. Governance baseline

| Item | Value |
|---|---|
| Branch | `feature/adr-0003-auditor-brief` |
| HEAD | `75dcc23a9ea739915b0a097a2136dca1f20111b4` |
| `origin/main` | `3c55960cdc3ba06ed12eb878c5bc56711291925e` |
| `origin/develop` | `b73bdb33af0a87d2e2a5cef5d30a6667f80beeaa` |
| Working tree | Clean |
| `ADR-0003` | **Proposed** (unchanged) |
| `ADR-0006` | Accepted (unchanged) |
| `SCI0-001` / `002` / `003` | Pending (unchanged) |
| Scientific implementation | None — `data/`, `pocket/`, `features/`, `model/`, `train/`, `eval/`, `explain/` all contain zero non-`__init__` files |
| `sealed/MANIFEST.md` | Empty — nothing sealed |

No abort condition present. Proceeding.

---

## 2. Dependency map — AUDITOR decision → evidence → artefact → objective

| AUDITOR question | Evidence required | Existing artifact | Missing artifact | Earliest permissible objective |
|---|---|---|---|---|
| AUDITOR-1 (split) | Leakage metrics computed on the real measurement graph, at record/compound/scaffold-family/study granularity | Qualitative analysis only (`ADR-0003_AUDITOR_1_VALIDATION_EVIDENCE.md`) | The real graph itself; per-granularity leakage statistics | `SCI0-014` (measurement-graph construction), read via `SCI0-014b` (descriptive characterization) |
| AUDITOR-2 (`N_c`/`N_b`/`N_w`/S4) | Observed corpus connectivity structure: Lcc size, bridging-compound count, study clustering pattern | Synthetic simulation only, explicitly shown non-robust across models (`ADR-0003_AUDITOR_2_THRESHOLD_EVIDENCE.md`) | Real compound×isoform graph; real study-cluster structure | `SCI0-014` graph construction, characterized descriptively by `SCI0-014b` — **but sealing (`SCI0-028`) must happen before `SCI0-015` reads the sealed thresholds against this graph** |
| AUDITOR-3 (duplicate policy) | None outstanding at the policy level; mathematical requirement already established | `ADR-0003_AUDITOR_3_DUPLICATE_EVIDENCE.md` — Order-A requirement derived from Cheng–Prusoff nonlinearity | Nothing corpus-dependent | Policy is decidable now; implementation lands in `SCI0-009` (conflict resolution) and `SCI0-008` (normalization ordering) |
| AUDITOR-4 (BindingDB/PubChem admissibility) | Quantitative tier breakdown (T1–T4) of the real corpus | Four-tier framework defined (`ADR-0003_AUDITOR_4_PROVENANCE_EVIDENCE.md`) | Actual per-tier record counts | `SCI0-006`/`SCI0-006b` (source adapters, literature mining) populate the corpus; `SCI0-014b` can then report tier counts descriptively |
| AUDITOR-5 (ATP Km) | A verified, per-isoform, per-construct numeric Km(ATP) value from primary literature | Two dedicated primary-kinetics papers identified (Huang 2011, Maheshwari 2017); no values yet extracted | Full-text access to either paper, or an equivalent primary source | Not corpus-dependent — this is a literature-retrieval task independent of any SCI0 objective. Blocks `SCI0-008` regardless of corpus state |

**Key structural finding:** four of five AUDITOR questions (1, 2, 4, and part of 3's
implementation) are gated on **`SCI0-014`/`SCI0-014b`**, which cannot run before
`SCI0-002` through `SCI0-013` are complete. AUDITOR-5 is the only question that is
*not* gated on corpus construction — it is purely a literature-retrieval problem and
could in principle be resolved before any SCI0 objective runs.

---

## 3. Stage-0 corpus feasibility audit

Required inputs, per Phase 3, classified against what `SCI0-001` through `SCI0-014b`
already specify:

| Required field/structure | Classification | Basis |
|---|---|---|
| Source databases (ChEMBL, BindingDB, PubChem BioAssay) | **SPECIFIED BUT NOT AVAILABLE** | `SCI0-006` connectors specified in the backlog; not yet implemented |
| Literature mining (CrossRef, PubMed, PMC OA) | **SPECIFIED BUT NOT AVAILABLE** | `SCI0-006b`, with a "binding span-verification gate" already specified in principle |
| Isoform identity (α/β/γ/δ) | **SPECIFIED, NOT YET INSTANTIATED** | Constitution §2.1 defines pocket/isoform scope; no records exist yet |
| Assay metadata (type, [ATP], endpoint, organism, construct, publication, curation confidence) | **SPECIFIED BUT NOT AVAILABLE** | `SCI0-004` activity record schema explicitly requires these as *mandatory* fields — this is a strong, already-decided requirement, not an open question |
| ATP/[ATP] metadata | **SPECIFIED BUT NOT AVAILABLE** | Same as above; `SCI0-008` normalization is conditioned on this field being populated |
| Construct metadata | **SPECIFIED BUT NOT AVAILABLE** | `SCI0-007` "structured construct descriptor," explicitly required |
| Publication provenance | **SPECIFIED BUT NOT AVAILABLE** | `SCI0-003` provenance schema already exists as verified, unmerged code (`pi3k_cel` namespace) — the *mechanism* exists and is tested; it has no real records in it yet |
| Compound identity fields | **SPECIFIED BUT NOT AVAILABLE** | `SCI0-008b` chemical standardization (RDKit canonical SMILES/InChIKey) and `SCI0-008c` identifier harmonization both specified, not implemented |
| Duplicate-resolution fields | **SPECIFIED, POLICY PARTIALLY DECIDABLE NOW** | `SCI0-009`; the *policy* (Order-A, log-median, stratified) is argued in AUDITOR-3 evidence but not yet an Auditor decision, and no records exist to apply it to |
| Scaffold-family fields | **SPECIFIED BUT NOT AVAILABLE** | `SCI0-012` Bemis–Murcko scaffold assignment, not implemented |
| Within-study identifiers | **SPECIFIED BUT NOT AVAILABLE** | `SCI0-013` within-study/within-assay stratum extraction, not implemented |
| Graph nodes/edges (compound×isoform) | **SPECIFIED BUT NOT AVAILABLE** | `SCI0-014`, explicitly the "connectivity substrate for R1" — not implemented |

**Overall Phase 3 finding:** every structural field required for the Stage-0 audit is
**already specified** in the backlog and `SCI0-001` refinement document — there is no
missing *design*, only missing *implementation and data*. Nothing here is
**NOT SPECIFIED**. This is a meaningfully different situation from "the project doesn't
know what it needs" — it knows precisely what it needs and has not yet built it.

---

## 4. Empirical N_c/N_b/N_w evidence plan — measurability classification

| Quantity | Classification | Note |
|---|---|---|
| Number of unique compounds | REQUIRES CORPUS CONSTRUCTION | Needs `SCI0-006`/`006b` populated |
| Number of isoform-specific observations | REQUIRES CORPUS CONSTRUCTION | Needs `SCI0-004` records populated |
| Number of compounds bridging isoforms | REQUIRES CORPUS CONSTRUCTION | Needs `SCI0-014` graph built |
| Number of connected components | REQUIRES CORPUS CONSTRUCTION | Same |
| Largest connected component (Lcc) | REQUIRES CORPUS CONSTRUCTION | Same — this is the quantity the prior sensitivity analysis showed is highly model-dependent; only real data resolves this |
| Per-isoform coverage | REQUIRES CORPUS CONSTRUCTION | Needs populated records |
| Compound×isoform matrix sparsity | REQUIRES CORPUS CONSTRUCTION | Same |
| Number of within-study observations | REQUIRES CORPUS CONSTRUCTION | Needs `SCI0-013` |
| Number of studies | REQUIRES CORPUS CONSTRUCTION | Needs populated records with publication provenance |
| Number of scaffold families | REQUIRES CORPUS CONSTRUCTION | Needs `SCI0-012` |
| Scaffold-family distribution | REQUIRES CORPUS CONSTRUCTION | Same |
| Study-level clustering | REQUIRES CORPUS CONSTRUCTION | Needs real study-cluster structure — this is exactly the quantity that determined whether the "uniform random" or "clustered/hub" simulation model was closer to reality; **cannot be resolved without real data** |
| Cross-study compound overlap | REQUIRES CORPUS CONSTRUCTION | Needs populated records across ≥2 studies per compound |
| Cross-study scaffold overlap | REQUIRES CORPUS CONSTRUCTION | Same |
| Fraction of compounds in multiple isoform assays | REQUIRES CORPUS CONSTRUCTION | Needs `SCI0-014` |
| Fraction of eval compounds with related training compounds | REQUIRES CORPUS CONSTRUCTION | Needs `SCI0-012` scaffold assignment + `SCI0-013` stratum extraction |

**Every quantity in this list is REQUIRES CORPUS CONSTRUCTION.** MEASURABLE NOW: none.
This is not a negative result — it is the honest answer to the question Phase 4 asked,
and it is consistent with §2's dependency map: none of the AUDITOR-2-relevant objectives
(`SCI0-006` through `SCI0-014b`) have run yet.

**One nuance worth recording as ANALYSIS:** `SCI0-014b` ("Dataset characterization —
descriptive only; never modifies the snapshot; may not inform split, stratum or
threshold selection") is the repository's own designed mechanism for measuring these
exact quantities *after* the corpus exists, in a way that is explicitly firewalled from
influencing the threshold-setting it is meant to inform. This is a real, already-designed
answer to the circularity concern Phase 6 raises below — the project anticipated this
problem before this audit was requested.

---

## 5. AUDITOR-1 empirical leakage audit design

Candidate metrics, for the Independent Auditor's eventual use, once `SCI0-014` exists:

| Leakage type | Candidate metric | What it would measure |
|---|---|---|
| A. Record-level | Fraction of eval records with an identical record hash in training | Should be exactly 0% by construction |
| B. Compound-level | Fraction of eval compounds (by canonical InChIKey) also present in training via a different study | Measures assay/study-robustness overlap — expected to be nonzero under the current §3 proposal |
| C. Scaffold-family level | Fraction of eval compounds sharing a Bemis–Murcko scaffold family with any training compound | Measures the leakage mode Guo et al. 2024 (cited in `AUDITOR_1_VALIDATION_EVIDENCE.md`) flagged as inflating apparent performance |
| D. Study-level | Fraction of studies contributing records to both train and eval strata | Should be low/zero if within-study stratum extraction (`SCI0-013`) is implemented correctly |
| E. Isoform-level | Per-isoform representation ratio between train and eval | Detects whether one isoform (e.g., the sparsely-characterized p110β, per this project's own documentation) is systematically underrepresented in the gate |
| F. Near-neighbor chemical | Tanimoto similarity distribution between eval compounds and their nearest training-set neighbor | Directly operationalizes the Sheridan-style similarity-vs-performance analysis cited in the AUDITOR-1 evidence document |

**Candidate comparison matrix** (for the Auditor, not a recommendation):

| Split | Measures | Metric C expected value | Metric F expected distribution |
|---|---|---|---|
| Train-on-graph / eval-within-study (current §3 proposal) | Assay-robustness | Likely nonzero (not excluded) | Likely left-skewed (many close neighbors) |
| Compound-disjoint | Assay-robustness + basic compound novelty | Likely nonzero | Moderately left-skewed |
| Scaffold-family-disjoint | Series-level generalization | ≈0% by construction | Right-shifted relative to above |
| Stricter study/scaffold-disjoint | Combined generalization + assay-robustness | ≈0% | Most right-shifted |

None of these values can be populated without `SCI0-012` and `SCI0-014` existing.
**UNRESOLVED, REQUIRES CORPUS CONSTRUCTION.**

---

## 6. AUDITOR-2 threshold-information requirements

| Candidate | Protects against | Observable statistic | Fixed prospectively? | Depends on corpus size? | Depends on graph topology? | Depends on assay distribution? | Simulation-informed? | Empirical-data-required? |
|---|---|---|---|---|---|---|---|---|
| `N_c` | A comparative model learning from too few connected compounds | Lcc size | CANDIDATE: possibly as a relative fraction, not fixed absolute | Yes | **Yes, heavily** — prior sensitivity analysis showed Lcc varies ~4× depending on study-clustering assumption | Indirectly, via study count/size distribution | Only to bound plausible ranges, not to set a value | **Yes** |
| `N_b` | Cross-study confounding (AUDITOR-1 concern 5) going undetected | Bridging-compound count | CANDIDATE: possibly relative to observed study-cluster count | Yes | Yes | Yes | Only to bound plausible ranges | **Yes** |
| `N_w` | Insufficient representativeness in the within-study gate stratum | Scaffold-family × compounds-per-family count | CANDIDATE: yes, largely fixable prospectively — power analysis showed this is not corpus-size-sensitive in the same way | Weakly | No | No | **Yes — this is the one quantity a simulation legitimately informs, since it concerns per-record statistical power, not graph topology** | Partially — the representativeness component still benefits from knowing real scaffold-family counts |
| S4b sharpness factor | A model passing calibration via uninformative wide intervals | Ratio of predictive-interval width to within-study noise floor | CANDIDATE: yes, fixable prospectively via null-model calibration | No | No | Weakly, via noise-floor estimate | **Yes — the null-model calibration approach used previously is legitimate here** | No — the within-study noise floor (Constitution §2.4, ≥0.3 log) is already an accepted assumption |

**Test against the A/B/C/D formulation question (Phase 6):**

- `N_c`: evidence points toward **B (relative threshold)** being more defensible than
  an absolute number, given how sensitive Lcc is to unobservable structural assumptions.
  This is an ANALYSIS conclusion carried forward from the prior sensitivity work, not a
  new decision — and it remains the Auditor's to make.
- `N_b`: similarly leans toward **B or C (relative/adequacy criterion)**, for the same
  reason.
- `N_w`: leans toward **A (absolute threshold)** being defensible, since the quantity it
  protects (representativeness/power) is not corpus-size-dependent in the same way.
- S4b: is not a compound-count threshold at all; it's a ratio, already naturally
  relative to the noise floor.

**None of A/B/C/D is selected here.** This is evidence for the Auditor's consideration,
consistent with the ANALYSIS label.

---

## 7. AUDITOR-3 evidence requirements

No corpus-dependent evidence gap remains. The Order-A normalization requirement and the
log-median/confidence-filter recommendation (in `ADR-0003_AUDITOR_3_DUPLICATE_EVIDENCE.md`)
are mathematical/methodological arguments, not empirical measurements — they do not
depend on what the real corpus looks like. **REQUIRES INDEPENDENT AUDITOR DECISION**, but
not further evidence generation.

---

## 8. AUDITOR-4 provenance requirements

The four-tier classification (T1–T4) is defined; populating it with real counts requires
`SCI0-006`/`SCI0-006b` to run. **REQUIRES CORPUS CONSTRUCTION** for the quantitative
breakdown; the qualitative policy question is otherwise ready for Auditor review.

---

## 9. AUDITOR-5 verified primary evidence (carried forward, not re-litigated)

Per the prior evidence pass, two primary sources are **PRIMARY SOURCE IDENTIFIED —
NUMERIC VALUE UNVERIFIED**:

- Huang et al. 2011, *Anal Bioanal Chem* 401:1881–1888, DOI 10.1007/s00216-011-5257-z,
  PMID 21789487 — confirmed via abstract/figure-legend to contain an actual "Km for ATP"
  measurement with replicated experiments. Full text paywalled; not retrieved.
- Maheshwari et al. 2017, *J Biol Chem* 292:13541–13550, DOI 10.1074/jbc.M116.772426 —
  dedicated PI3Kα kinetics and structure paper. Full text not retrieved in this session's
  search snippets.

No new retrieval attempt was made in this pass, per the instruction to stop pursuing
arbitrary literature searches and instead focus this pass on corpus-feasibility analysis.
Both sources remain the concrete, named next step for whoever has full-text access.

**No numeric Km value is stated here.** VERIFIED EVIDENCE = existence and citation of the
two papers. UNRESOLVED = their numeric content.

---

## 10. Remaining evidence gaps — summary

1. **AUDITOR-1:** requires `SCI0-012` + `SCI0-014` to populate the leakage-metric
   comparison matrix in §5.
2. **AUDITOR-2:** requires `SCI0-014` (graph) and `SCI0-014b` (descriptive
   characterization, firewalled from informing the threshold it describes) to observe
   real Lcc, bridging-compound count, and study-clustering structure. This is the
   evidence gap with the clearest, most structural dependency — no shortcut exists.
3. **AUDITOR-3:** no corpus-dependent gap remains; ready for Auditor review as a
   methodological question.
4. **AUDITOR-4:** requires `SCI0-006`/`SCI0-006b` for quantitative tier counts; the
   qualitative policy is ready for Auditor review.
5. **AUDITOR-5:** requires full-text retrieval of two named, dated papers — independent
   of any SCI0 objective.

---

## 11. Exact work required before the Independent Auditor can decide each question

| Question | Exact next step |
|---|---|
| AUDITOR-1 | Run `SCI0-012` (scaffold assignment) and `SCI0-014` (graph construction) against a real, even if partial, corpus snapshot; compute the six leakage metrics in §5; present to Auditor alongside the existing qualitative analysis |
| AUDITOR-2 | Run `SCI0-014` and `SCI0-014b`; report real Lcc, bridging-compound count, and study-cluster structure descriptively; present the observed structure to the Auditor **before** any threshold is proposed, per `SCI0-028`'s ordering constraint |
| AUDITOR-3 | No further evidence needed; route the existing methodological analysis to the Auditor for a policy decision |
| AUDITOR-4 | Run `SCI0-006`/`SCI0-006b`; report real per-tier (T1–T4) record counts; present alongside the existing qualitative framework |
| AUDITOR-5 | Obtain full-text access to Huang et al. 2011 and/or Maheshwari et al. 2017 (standard subscription journals); extract the reported Km(ATP) value(s) with full experimental context; this can happen independently of and in parallel with all SCI0 work |

---

## Governance boundary confirmation

```text
ADR-0003 = Proposed
Independent Auditor decisions = unresolved
SCI0-001 = not started
Scientific implementation = none
Thresholds = not selected/sealed
ATP Km values = not selected/sealed
```

This report is a roadmap, not a decision. Every number, range, and formulation choice
above remains explicitly the Independent Scientific Auditor's to make.

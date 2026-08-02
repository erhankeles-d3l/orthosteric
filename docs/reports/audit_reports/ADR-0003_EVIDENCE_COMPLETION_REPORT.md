# ADR-0003 Evidence-Completion Report

> **No Auditor decision was made. No ADR-0003 acceptance/rejection/modification occurred.
> No threshold was sealed. No scientific implementation was started.**

---

## Governance status

- **ADR-0003:** Proposed
- **ADR-0006:** Accepted
- **SCI0-001:** Pending
- **SCI0-002:** Pending
- **SCI0-003:** Pending
- **Working tree:** clean (verified at end of task)
- **Foundation tag:** immutable, not touched
- **src/orthosteric/:** no scientific implementation; all scaffold packages remain empty

---

## Evidence matrix

| Auditor question | Evidence strength | Primary sources | Database evidence | Simulation/analysis | Candidate policies/ranges | Remaining uncertainty | Auditor decision still required |
|---|---|---|---|---|---|---|---|
| AUDITOR-1: train/eval split | **Moderate** | Guo et al. 2024; Ding et al. 2010; Lindström et al. 2004; Sheridan 2013 | — | None needed — structural/conceptual analysis sufficient | Scaffold-family exclusion as candidate safeguard; within-study stratum supported by proteochemometric double-CV precedent | No primary literature specific to 4-isoform PI3K selectivity models | **YES** |
| AUDITOR-2: N_c, N_b, N_w, S4b | **Moderate** for S4b/N_w; **Insufficient** for N_c/N_b (corrected) | ADR-0003 §5 operational definitions; Constitution §2.4 noise floor | — | Reproducible simulation with sensitivity analysis across 3 graph models (seed 20260801): the N_c/N_b headline finding from an earlier pass was NOT robust to alternate, equally plausible graph-generation assumptions (mean Lcc ranged 25–97 across models, same scenario) | N_w: 24–40 (8 families × 3–5 cmpds/fam, unaffected by the correction); S4b: k in [1.5, 2.0] (unaffected); N_c/N_b: no candidate range proposed — withdrawn pending real Stage 0 data | Exact corpus structure unknown until Stage 0 Q1; N_c/N_b conclusion is highly model-dependent, not resolvable by simulation alone | **YES** |
| AUDITOR-3: duplicate resolution | **Strong** — follows mathematically from Cheng-Prusoff nonlinearity + standard biostatistics | Constitution §2.4; Cheng-Prusoff relation; standard bioactivity practice | — | Mathematical analysis of normalization ordering | Log-median Ki after per-record Cheng-Prusoff (Order A), confidence-based outlier exclusion, stratified by isoform/construct/species | None materially new — policy choice is the remaining uncertainty | **YES** |
| AUDITOR-4: BindingDB/PubChem admissibility | **Moderate** | ChEMBL policy as methodological comparator; BindingDB/PubChem provenance architecture | BindingDB, PubChem BioAssay, ChEMBL architecture reviewed | — | Four-tier evidence classification (T1–T4); T4 excluded by Cheng-Prusoff requirement | Quantitative Stage 0 Q8 tier breakdown not yet possible | **YES** |
| AUDITOR-5: ATP Km policy | **Weak, all isoforms (corrected)** | Somoza et al. 2015 JBC (PMID 25631052): establishes only a combined 50-150 µM range across 3 isoforms, NOT per-isoform values; umbralisib sponsor documents traced to one uncited internal reference repeated across 6 filings, NOT independent corroboration | — | — | No per-isoform value can be established from currently retrievable sources; range-only inference for α/β/δ; γ has no ATP concentration retrieved at all | Full per-isoform table requires Somoza 2015 Table 2 (reCAPTCHA-blocked) or another primary source not yet found; 100 µM vs 10-20 µM discrepancy remains unresolved and is NOT to be averaged | **YES** |

---

## AUDITOR-1

**Strongest evidence:** Guo et al. 2024 showing scaffold splits overestimate VS performance; Lindström et al. 2004 establishing double-CV as required for unbiased proteochemometric estimates.

**Candidate approaches:** (1) ADR-0003 §3 as-is — assay-robustness claim only, explicitly labelled; (2) add scaffold-family exclusion at the within-study stratum boundary — closer to novel-scaffold generalization claim; (3) fully disjoint scaffold-family split — strongest generalization claim, reduces N_w.

**Evidence gaps:** no paper specifically validates this exact 4-isoform selectivity model design; inference by analogy from proteochemometrics.

**Auditor decision required: YES**

---

## AUDITOR-2

**Strongest evidence, corrected:** the N_w power finding (power trivially satisfied at any
representativeness level compatible with ADR-0003's existing 8-scaffold-family condition)
and the S4b null-model calibration are robust — both concern single-record statistical
properties, not graph structure. **The original N_c/N_b headline finding is withdrawn**
after a sensitivity analysis showed it is not robust to alternative, equally plausible
graph-generation assumptions.

**Simulation design:** bipartite graph model tested under three distinct generation
mechanisms (uniform random; clustered/hub studies; correlated per-compound coverage), 300
MC reps per model in the headline scenario, seed 20260801.

**Simulation results:** see `ADR-0003_AUDITOR_2_THRESHOLD_EVIDENCE.md` §4. Mean Lcc ranged
from 24.7 to 96.8 across the three models at identical parameters (300 compounds, 50%
coverage, 15 studies) — a nearly 4-fold spread driven entirely by an untestable-without-
real-data assumption about literature structure.

**Candidate ranges:**
- `N_c`: **no candidate proposed** — UNRESOLVED, withdrawn pending real Stage 0 Q1 data
- `N_b`: **no candidate proposed** — UNRESOLVED, same reason
- `N_w`: 24–40 (representativeness-based) — CANDIDATE RANGE, unaffected by the correction
- S4b: k in [1.5, 2.0] — CANDIDATE RANGE, unaffected by the correction

**Limitations:** the three-model sensitivity analysis is itself not exhaustive; no
simulation substitutes for measuring the real corpus's actual graph structure.

**Auditor decision required: YES**

---

## AUDITOR-3

**Strongest evidence:** mathematical derivation from Cheng-Prusoff nonlinearity — Order A (normalize then aggregate) is not a policy preference, it is a mathematical requirement when [ATP] differs across records.

**Candidate policies:** log-median Ki (post-normalization), stratified by isoform/construct/species, with confidence-score-based outlier exclusion.

**Methodological implications:** the Order A vs. B distinction should be specified as a hard requirement, not a soft preference, in the implementation specification.

**Auditor decision required: YES**

---

## AUDITOR-4

**Strongest evidence:** ChEMBL's publication-linking policy as methodological comparator; structural analysis of BindingDB/PubChem provenance.

**Provenance findings:** four provenance tiers identified (T1–T4); T4 (no publication, no recoverable [ATP]) excluded by Cheng-Prusoff normalization requirement — not a separate policy decision.

**Candidate evidence hierarchy:** T1 primary, T2 primary with declared assumption, T3 auxiliary with cross-validation condition, T4 excluded.

**Auditor decision required: YES**

---

## AUDITOR-5

**Primary literature:** Somoza et al. 2015 JBC — the only retrievable primary kinetic
source found. Methods snippet confirms isoforms were assayed at "2 × Km ATP," combined
range 100–300 µM across three isoforms (α, β, δ) — **this establishes only a shared
range, not per-isoform values.** Full Table 2 not retrieved (reCAPTCHA-blocked).

**Construct/isoform evidence:** human/murine recombinant p110/p85 heterodimers (α, β, δ);
p110γ alone. Regulatory-subunit presence standard for α/β/δ in commercial preparations.

**ATP Km values actually verified: NONE with isoform-specific confidence.**
- PI3Kα, β, δ: each individually somewhere within a shared 50–150 µM range (mathematical
  inference from the 2×Km/100–300µM statement). **No isoform-to-value mapping is
  established.** WEAK confidence, corrected from a prior draft's overreach.
- PI3Kγ: no ATP concentration retrieved at all. NOT ESTABLISHED.
- The "100 µM for PI3Kδ" figure from umbralisib sponsor documents is **reclassified as
  weak, non-independent evidence** — it traces to one uncited internal reference repeated
  across six clinical protocol filings, not six independent determinations.

**Conflict analysis:** 100 µM (umbralisib sponsor docs, weak/uncorroborated) vs. 10–20 µM
(Millipore kit technical spec, also uncorroborated) vs. an unallocated 50–150 µM range
(Somoza 2015, partial). **These are not averaged.** Candidate, unconfirmed explanations:
apparent vs. intrinsic Km; different lipid substrate/vesicle composition; different
recombinant constructs; manufacturer technical-note imprecision. No explanation is
preferred without further evidence.

**Candidate provenance/versioning policy:** unchanged — sealed CSV under `sealed/config/`
with content hash, retrieval date, confidence class per record, using the existing
`sealed/MANIFEST.md` mechanism. Mechanism proposal is independent of the value dispute
above.

**Remaining evidence gaps:** no per-isoform Km(ATP) value for any of the four PI3K
isoforms can be established from sources retrieved in this session. Somoza 2015 Table 2,
or an equivalent primary source, is required before AUDITOR-5 can be meaningfully closed.

**Auditor decision required: YES**

---

## Cross-decision dependencies

See `ADR-0003_CROSS_DECISION_DEPENDENCIES.md` for full analysis. Key ordering requirement:

1. **AUDITOR-4 before AUDITOR-2:** the achievable N_c/N_b/N_w depends on how many records survive provenance filtering. Stricter admissibility → smaller corpus → smaller Lcc → harder thresholds to clear.
2. **AUDITOR-5 before AUDITOR-3:** normalization must come before aggregation (Order A), so the Km policy must be sealed before the duplicate resolution policy is applied in practice.
3. **AUDITOR-1 and AUDITOR-2 interact:** stricter scaffold-family separation reduces the achievable N_w. If the Auditor requires scaffold-family exclusion, the N_w floor must be achievable under that stricter split.
4. **AUDITOR-5 and selectivity:** none of the four isoforms currently has a well-characterized Km (all are WEAK or NOT ESTABLISHED per the corrected AUDITOR-5 review). Asymmetric uncertainty across isoforms — if this situation persists once real values are found — would create an artificial selectivity signal for records measured at a fixed [ATP] near the boundary of whatever uncertainty range remains. This risk is undiminished by the correction; if anything it is more acute, since no isoform currently has a confidently established value at all.

**Pre-registration ordering (Constitution §1.4 requirement):** AUDITOR-4 → AUDITOR-5 → AUDITOR-3 → AUDITOR-2 → AUDITOR-1. None of these can be set after inspecting the scientific corpus.

---

## Evidence quality assessment

| Question | Quality | Justification |
|---|---|---|
| AUDITOR-1 | **Moderate** | Solid molecular ML literature; no specific 4-isoform PI3K selectivity study exists |
| AUDITOR-2 (N_c/N_b) | **Insufficient** | A sensitivity analysis across three plausible graph-generation models produced mean Lcc ranging from 25 to 97 at identical parameters — the original single-model finding was not robust and is withdrawn |
| AUDITOR-2 (N_w, S4b) | **Moderate** | Power analysis is definitive on the question it answers (power is not the constraint) and does not depend on graph-structure assumptions; S4b calibration is honest about its sensitivity to the assumed true-effect spread |
| AUDITOR-3 | **Strong** | Mathematical requirement from Cheng-Prusoff; supported by standard bioactivity practice |
| AUDITOR-4 | **Moderate** | Database architecture well-understood; quantitative tier breakdown requires Stage 0 |
| AUDITOR-5 (all isoforms) | **Weak to Insufficient** | Somoza 2015 establishes only a combined range across 3 isoforms, not per-isoform values; PI3Kγ has no retrieved value at all; the "100 µM for δ" figure traces to one uncited internal reference repeated across six sponsor documents, not independent corroboration — this is a downgrade from a prior draft's overstated confidence |

---

> No Auditor decision was made. No ADR-0003 acceptance/rejection/modification occurred. No threshold was sealed. No scientific implementation was started.

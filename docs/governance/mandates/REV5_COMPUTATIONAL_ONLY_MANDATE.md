# EXECUTION MANDATE — Computational-Only Comparative Selectivity Discovery (Rev. 5)

Rev. 4 plus an explicit execution sequence, a repository/governance implementation audit, and the β→power-check dependency made binding. Sections §1–§15 are carried forward from Rev. 4 unchanged except where marked **[Rev. 5]**.

---

## 0. Changes from Rev. 4

| # | Change |
|---|---|
| A | **§0.5 Execution Sequence added** — specification order ≠ execution order; conflating them produced the ordering bugs fixed in Revs. 2 and 3 |
| B | **§0.6 Implementation Audit added** — blocking, precedes all data work |
| C | **Label blinding becomes architecturally enforced** (import-linter contract), not a policy statement |
| D | **β adequacy is upstream of the power check** — β failure invalidates the endpoint §1 computes power *for* |
| E | **6XRL bridge doubles as a production-path smoke test** |
| F | **Pilot is the first shard of the corpus, retained** — calibration is label-free and motif-free, so no leakage |

---

## 0.5 EXECUTION SEQUENCE (binding) **[Rev. 5]**

> **The section numbering below is a specification order, not an execution order.** They diverge. Execute in the stages here; consult the numbered sections for binding detail.

### Stage A — Freeze and audit (no data computation)
1. **Freeze this document** — hash it, record in governance log. Nothing downstream may modify a frozen threshold.
2. **§0.6 Implementation audit** (blocking).

### Stage B — Structural preconditions (cheap, decisive, endpoint-determining)
3. **β receptor due diligence + Gate 1** (§3). *Runs before the power check: §3.1's β-failure consequence invalidates the endpoint the power check is computed for.*
4. **6XRL bridge + production-path smoke test** (§3, §0.6.4).

### Stage C — Statistical precondition (depends on Stage B's endpoint verdict)
5. **Seal literature panel** (§2) — must precede corpus assembly, which excludes it.
6. **Seal validation set + power check** (§1), computed on the **surviving** endpoint from Stage B.

### Stage D — Pilot and calibration
7. **Compute budget** (§4).
8. **Corpus assembly** (§5), including the training/held-out family split.
9. **Pilot docking** — first corpus shard, ~100 compounds (§6).
10. **Calibration gates** (§7).

### Stage E — Full execution (only if Stage D passes)
11. Full corpus docking (§8) → features (§9) → eligibility + nulls (§10) → generalization (§11) → **B7 freeze (§11.5)** → unblinding + ladder (§12) → promotion (§13) → report (§14) → gate and commit (§15).

**Do not begin Stage E's corpus docking before Stage D completes.** The first computationally decisive artifact is the §1 power-check result; the first structural execution dependency is β adequacy plus governed pilot docking.

---

## 0.6 IMPLEMENTATION AUDIT (BLOCKING) **[Rev. 5]**

Produces a written inventory before any data work. Purpose: distinguish what is reusable from what must be built, and convert the label-blinding guarantee from procedural to architectural.

### 0.6.1 Reusable as-is (built, tested, committed)

| Module / artifact | Status |
|---|---|
| `features/_ligand_moiety` | 11 classes, tested |
| `features/_residue_functional_class` | interaction-contextual, directional (H-bond donor/acceptor, anionic/cationic, cation-π), tested |
| `features/_representation_2_3` | Rep 2/3 + frozen geometry ladder, tested |
| `features/_interaction_occupancy` | atom- and residue-level, pose-dedup discipline |
| `features/_comparative_interaction_fingerprint` | UNMAPPED vs LOST distinction preserved |
| `pocket/_sequence_correspondence` | Gate-0 validated, `content_sha256: 08d88687…` |
| `features/_docking_interaction_detector` | incl. `residue_hbond_role`, `residue_charge_sign` |
| `data/structural_evidence/raw_interactions/` | per-pose records for the 24/50 corpora, on disk |
| Receptors | 8EXL, 6PYR, 6XRL prepped; AF-P42338 (β, disclosed tier) |

### 0.6.2 Must be built (not reuse — confirm scope before scheduling)

1. **Sealed-artifact machinery** — hash + timestamp + label separation for §1 and §2.
2. **Architecturally enforced label blinding** — see §0.6.3.
3. **Position-filtered S/H aggregation** — *specified in the earlier specificity-pocket × hinge mandate but never implemented.* §9's anchored features depend on it. This is a genuine new build, not a reuse item.
4. **Permutation null** — per-compound α-role shuffle, ≥1,000 resamples (§10.3 Null A).
5. **Paired bootstrap** — resample compounds once per replicate, both metrics on the same resample (§12.2).
6. **Sign-normalization unit test** — every baseline yields AUC > 0.5 on a synthetic α-favoring set (§12.1).
7. **B7 freeze artifact** — hashed, written before §12.
8. **Held-out coverage denominator** (§11).
9. **6AUD/6XRL calibration slope** (§7.1).

### 0.6.3 Label blinding must be architectural, not procedural **[Rev. 5, change C]**

Rev. 4 stated blinding as policy: *"labels stored separately, never loaded by §5–§11."* A statement in a document is not a mechanism, and prior assessment correctly flagged leakage control as adequate *only if technically enforced*.

**This project already has the enforcement pattern in production.** `import-linter` Contract 3 enforces *"no training path reaches Tier 2 (inert until `data.tier2_gate` or `learning.tier2_gate` exists)"* — a structural, CI-enforced barrier of exactly this shape.

**Required:** add an analogous contract forbidding any discovery-phase module (§5–§11 code paths) from importing the sealed-label module. Blinding then fails the build rather than failing silently. Verify the contract actually fires by writing a deliberately violating import and confirming CI rejects it — an unfired contract is untested.

### 0.6.4 Production-path smoke test **[Rev. 5, change E]**

Gate 1 validated 6XRL via a standalone script. The 6XRL bridge re-dock (§3) must run through the **production docking path**, confirming receptor prep, box derivation, and interaction detection all work there before a 100-compound pilot depends on it.

### 0.6.5 Integrity check

Confirm A4 (`SNAP-05748f6627ea`) byte-identical; confirm clean working tree; record commit hash; confirm the full gate (pytest / ruff / mypy / import-linter) passes at the audit baseline.

---

## FROZEN ENDPOINT (binding on §1, §10, §12)

> **Primary confirmatory contrast: α-selective vs other-selective.**
> **Secondary: α-selective vs pooled non-α.**
> **Intermediate and non-selective strata: descriptive only, never confirmatory.**

### Disclosure of endpoint selection (required, not optional)

**This endpoint was selected from three candidate contrasts on the basis of prior exploratory analysis.** The geometry-ladder work (on the 24/50 label-informed corpora) found α-vs-other_selective to be the contrast carrying reproducible signal, while α-vs-non_selective was a stable null and α-vs-intermediate fragmented under geometric refinement. Choosing the endpoint *because* it previously showed signal inflates the apparent significance of any confirmatory test built on it.

**Disclosed, not corrected.** Scaffold-disjointness of the sealed set partially mitigates it — the chemistry is disjoint — but does **not** eliminate it, because the endpoint choice was informed by the same biological phenomenon the sealed set measures. Every artifact reporting the §12 result must carry this disclosure.

---

## 1. Seal the retrospective set + POWER CHECK

**[Rev. 5] Executes at Stage C, after β adequacy is known (§3.1).** If β fails, the four-isoform endpoint is invalid and this power check must not be computed against it — see §3.1.

From A4 (`SNAP-05748f6627ea`, 39,002 accepted records — immutable): compounds with **within-study, within-assay four-isoform panels** (charter §2.3). Exclude the 24/50 corpora **and every scaffold-sharing compound** — permanently spent as hypothesis-generation evidence.

### 1.1 Power simulation

Simulate the **exact §12.2 criterion**, not a proxy:
- Effect size: **ΔAUC = 0.10** (the pre-registered margin itself).
- Structure: resample from the **actual sealed-set class and scaffold-family composition**, not idealized balanced classes.
- Procedure: paired bootstrap, ~10,000 replicates, exactly as §12.2.
- Output: distribution of `CI₉₅,lower(ΔAUC)` achievable at the available n.

### 1.2 Consequence — make-or-break, not preliminary

**Expect this to be demanding.** At ~15/class (~30 compounds in the primary contrast), paired ΔAUC CI half-widths of 0.10–0.16 imply that clearing `CI_lower > 0.10` needs a point estimate near **0.20 or above** — a large effect.

- **Achievable** → proceed to Stage D.
- **Not achievable** → the decisive gate **does not exist**. Report as a *dataset-limitation finding* **before** any corpus compute, then either (a) proceed descriptively with no confirmatory claim, limitation as headline, or (b) halt and prioritize enlarging the four-isoform panel corpus.
- **The margin is never lowered after the fact.**

Seal with SHA-256 + timestamp. Labels stored separately and **architecturally isolated** (§0.6.3). Access before §12 is a barrier violation — recorded, not quietly corrected.

---

## 2. Literature reference panel (sealed; diagnostic by mechanism class, NOT a gate)

**[Rev. 5] Seal at Stage C step 5 — must precede corpus assembly (§5), which excludes it.**

| Compound | Selectivity | Mechanism class | Capturable by static ATP-site docking? |
|---|---|---|---|
| alpelisib (BYL-719) | α | affinity pocket / position 859 | **Yes** |
| inavolisib | α | affinity pocket | **Yes** |
| idelalisib | δ | **induced** specificity pocket (propeller) | **Uncertain** |
| PIK-39 | β/δ | **induced** specificity pocket (propeller) | **Uncertain** |
| IPI-549 (eganelisib) | γ | ATP site | Yes |

Failure in the *affinity-pocket* class is concerning for the method. Failure in the *propeller/induced* class is expected-plausible and most likely a **receptor-ensemble limitation** — receptors here are static, and the Trp780/Met772 specificity pocket is absent in non-induced structures (charter §0.3, C6). That points to ensemble docking as the fix, not to invalidation.

**Disclosure:** IPI-549 was the Gate-1 reference ligand for 6XRL receptor validation — receptor redocking, not selectivity-feature discovery or tuning.

---

## 3. Receptor tier remediation

**[Rev. 5] Executes at Stage B, before §1.**

- **Alpha** 8EXL (1.989 Å, Gate 1 PASS 5/5) · **Delta** 6PYR (2.21 Å, Gate 1 PASS 5/5) — unchanged
- **Gamma** → **6XRL** (2.99 Å, Gate 1 PASS 4/5, hinge verified). 6AUD retired from production, **retained as the §7.1 calibration comparator**.
- **Beta** — AlphaFold-only. Search RCSB for a human PIK3CB experimental structure with a bound ATP-site ligand; identical 6XRL due-diligence (REMARK 465/480 completeness at pocket anchors — *not* resolution alone) + 5-seed Gate 1 with hinge confirmation.

**Bridge check + smoke test (~10 min):** re-dock the 50-compound corpus against 6XRL **through the production path** (§0.6.4), establishing both gamma continuity with committed results and that 6XRL functions in the pipeline the pilot will use.

### 3.1 β-failure consequence — and its effect on §1 **[Rev. 5, change D]**

If β cannot be given an adequate receptor (no passing experimental structure, or §7 shows it an extreme outlier on correspondence or interaction-detection rate):

> **The four-isoform confirmatory endpoint is INVALIDATED.** It is not silently converted into a three-isoform confirmatory study.

The reason is a label/signal mismatch: the frozen endpoint's "other-selective" class is defined by **four-isoform experimental labels**. A compound labelled other-selective *because it is β-selective* would have no structural basis for that label in a three-isoform comparison — signal and outcome variable would cease to refer to the same thing.

**[Rev. 5] Dependency on §1, made binding:** because §1's power check is computed **on this endpoint**, β failure means any power result computed against it is void. **§1 must therefore not run until β adequacy is settled** (hence Stage B before Stage C). If β fails, §1 is not run on the four-isoform endpoint at all.

Permitted response: report the β-receptor limitation as the finding. Any three-isoform (α vs γ/δ) analysis is **exploratory only**, requires its own separately pre-registered endpoint and its own power check, and **cannot inherit the confirmatory status** of the frozen endpoint.

---

## 4. Compute budget (GO / REDUCED_SCOPE_GO / NO_GO)

Measured: ~10.1 s/compound×isoform docking, ~3.2 s detection+aggregation, ~2 s prep → **~55 s/compound**, **~146 KB/compound**.

**Reproducibility:** `cpu=1` per dock is bit-exact (multi-threaded introduces ~0.03 kcal/mol non-determinism). **Run `cpu=1`, K docks concurrently as independent processes.**

| Corpus | 1 worker | 8 workers | Storage |
|---:|---:|---:|---:|
| 100 (pilot) | 1.5 h | ~11 min | 15 MB |
| 500 | 7.6 h | ~57 min | 73 MB |
| 2,000 | 30.6 h | ~3.8 h | 292 MB |

Shard at 500-compound boundaries. Emit the decision before launching; never silently reduce poses, isoforms, or QC to fit runtime.

---

## 5. Corpus assembly — scaffold families are the GO criterion

**Pre-registered target: ≥200 distinct Bemis–Murcko scaffold families (≥300 preferred).** Compound count derived, reported as secondary.

Label-blinded, not label-free. Hard exclusions: sealed-validation compounds and scaffolds; 24/50 compounds and scaffolds; the §2 panel. No property filtering that could correlate with selectivity class.

**Training/held-out split:** partition scaffold families into a discovery-training portion and a held-out portion **before** motif enumeration (charter §3.4).

---

## 6. PILOT docking — first corpus shard, ~100 compounds **[Rev. 5, change F]**

**The pilot is the first shard of the §5 corpus and is retained in it**, not a discarded throwaway set. §7 calibration is label-free and motif-free, so reusing these compounds in discovery introduces no leakage — and discarding 100 compounds of docking would waste budget for no methodological gain.

Scaffold-diverse; docked against all four production receptors **plus 6AUD** (gamma calibration comparator only).

**Governance artifacts required:** provenance per record (compound, isoform, receptor, pose, seed, detector version, correspondence hash), shard hash, decision record for the §4 budget call.

---

## 7. Receptor calibration on pilot (GATING — diagnose, never auto-correct)

### 7.1 The 6AUD/6XRL calibration slope

Gamma has two receptors of known differing structural quality — 6AUD (incomplete at Trp812/Val882, Gate-1 FAIL) and 6XRL (complete, Gate-1 PASS). Same protein, same biology.

- **C** = completeness metric per receptor: fraction of pocket residues within contact range having all side-chain heavy atoms at full occupancy.
- **M** = interaction metric per receptor: mean detected interactions per compound.

```
calibration_slope   = (M_6XRL − M_6AUD) / (C_6XRL − C_6AUD)
predicted_offset    = calibration_slope × (C_α − C_other)
attribution_fraction = predicted_offset / observed_offset
```

| attribution_fraction | Decision |
|---|---|
| **≥ 0.75** | Predominantly completeness-attributable → **pre-registered normalization permitted** |
| 0.25 – 0.75 | Partially attributable → report raw **and** normalized, neither primary; disclose ambiguity |
| **< 0.25** | Not completeness-attributable → **do NOT normalize**; normalizing risks subtracting the phenomenon of interest |

**Required limitation statement:** this is an **internal estimate of receptor-representation sensitivity**, from a single receptor pair, assumed transferable across isoforms and roughly linear in C. It is **not a ground-truth artifact magnitude**; the n=1-pair basis must be disclosed wherever used.

### 7.2 Diagnose, never auto-center

Measure per isoform: Vina score distribution; detected-interaction count by type; occupied Rep-2 bins; pocket residues in contact range; correspondence-mapping rate (known to differ: 95.5% α→β, 89.1% α→γ, 92.4% α→δ). Raw Δα always reported; normalized never replaces raw; normalization only under §7.1's ≥0.75 branch.

### 7.3 Ligand-property confound — frozen thresholds

Predict Δα from ligand descriptors alone (MW, cLogP, TPSA, rotatable bonds, heavy-atom count), **5-fold scaffold-aware CV**:

| CV-R² | Decision |
|---|---|
| **≥ 0.50** | **STOP** — signal substantially confounded by ligand properties; **not interpretable as a structural selectivity signal under the present protocol** |
| 0.25 – 0.50 | Proceed with disclosure + property-residualized secondary analysis alongside |
| < 0.25 | Proceed |

### 7.4 Gate

§7.1 attribution < 0.25 with a large unexplained offset, or CV-R² ≥ 0.50, or β an extreme outlier (→ §3.1) → **STOP**; report as a receptor-representation / property-confounding finding.

---

## 8. Full corpus docking (only if Stage D passes)

Frozen protocol; 6XRL for gamma; `cpu=1` per process, K concurrent; 5 poses; exhaustiveness 8; seeds recorded.

---

## 9. Comparative features — motifs enumerated, not clustered

Disjoint partition per compound:

- **A** — productive in α, weak/absent in all competitors → α-favoring
- **B** — productive in ≥1 competitor, weak/absent in α → α-disfavoring
- **C** — productive across the board → conserved, **selectivity-uninformative** (tracked for potency, never penalized)
- **D** — productive nowhere → irrelevant

`Rα = |A|`, `Pα = |B|`, `Δα = Rα − Pα`. **All three reported** — Δα discards magnitude: (Rα=10, Pα=8) and (Rα=2, Pα=0) share Δα=2 but are very different molecules.

**A motif is a comparative feature key** — `(ligand_pharmacophore_class × residue_functional_class × interaction_type[, geometry_bin])` with its A/B/C/D assignment — produced **deterministically** by the existing Rep-2/3 machinery. **No clustering in the confirmatory chain.** Clustering may run as a discovery/visualization aid, reported as such.

Position-anchored features (specificity pocket 780/772; hinge 851/882/828) as a **position-filtered subset** — *new build per §0.6.2 item 3*. The unfiltered pocket-wide version is too permissive (~98–99% redundancy) and is never the anchored feature.

**Confirmatory evidence chain:**
`comparative features → recurring motifs → scaffold recurrence → scaffold-held-out reproduction → B7`

---

## 10. Motif ELIGIBILITY and the permutation null (GATING)

### 10.1 Eligibility — discovery-training portion only

1. Recurs across **≥ 5 independent Bemis–Murcko scaffold families** (K = 5). *The ≤25% dominance rule implies K ≥ 4; 5 is the pre-registered minimum.*
2. Passes **≤ 25% chemotype dominance**.

**Held-out reproduction is NOT an eligibility criterion.** Bundling it in would leave §11 nothing independent to assess and would put held-out data inside B7's composition. Eligibility determines B7; generalization independently characterizes it.

Family count is also reported as a **continuous** quality measure; full distribution reported; "well-supported" tier flagged at ≥10 families.

### 10.2 The permutation statistic

**T = number of eligible α-favoring (set A) motifs**, applying §10.1 identically under real and permuted designations, by the same code path.

### 10.3 Two distinct nulls

Five permutations cannot support a 95th percentile (minimum p = 1/(n+1)), and whole-isoform designation offers only **three** non-identity options.

**Null A — per-compound α-role shuffle (primary, quantitative).** Per compound, randomly designate which of its four landscapes is "α"; recompute T. Destroys consistent isoform-specific structure, preserves marginal landscape distribution. Unlimited resamples.

> **Criterion: `T_α > Q₀.₉₅(T_perm)` over ≥ 1,000 permutations.** Failing this, the extraction produces no isoform-specific structure beyond chance and the discovery output is void (the S9c standard).

**Null B — quality-matched α↔δ swap (structured, single comparison).** Alpha (1.989 Å) and delta (2.21 Å) are the closest-matched pair — both complete crystal structures, both Gate-1 PASS 5/5. One specific contrast, **not** a percentile test, interpreted jointly with §7.1's slope and §7.2's baselines.

**Why both:** Null A tests whether isoform-specific structure exists at all but does not control receptor quality; Null B controls quality but supports no percentile inference. β and γ whole-isoform permutations reported, **flagged quality-confounded**.

---

## 11. GENERALIZATION — held-out scaffold families (independent test, not a filter)

**Report per-family, not pooled** — 18/20 families is a different finding from 2/20 with a strong average.

**Coverage denominator (required):**

```
held-out families expressing the motif
──────────────────────────────────────────────────────────
held-out families containing ≥1 compound bearing the
required ligand pharmacophore class
```

Without it, "failed to reproduce" conflates *not general* with *not testable*.

**Study-level gate (not a B7 filter):** broad held-out failure means the **generality claim** fails and the result is series-specific SAR — but B7's composition, frozen from §10.1, is unchanged and §12 still runs. A B7 built largely from non-generalizing motifs will simply not beat B2.

### 11.5 FREEZE B7 — before any unblinding

```
Eligible motifs := §10.1 (training-portion recurrence + dominance),
                   surviving §10.3 Null A
R_α = Σ (occupancy-weighted α-favoring eligible motifs)
P_α = Σ (occupancy-weighted α-disfavoring eligible motifs)
B7  = S_α = R_α − P_α        [R_α, P_α also reported separately]

Conserved (set C): weight ZERO in S_α.
Weights: uniform (1.0) by default.
Direction: HIGHER = more α-favoring.
```

Non-uniform weighting requires a documented, **non-label-derived** criterion stated before freezing. **Any weight fit to maximize label agreement makes the result label-informed and disqualifies the sealed-set claim.** Write the frozen definition to a hashed artifact before §12.

---

## 12. Sealed unblinding + BASELINE LADDER (decisive gate)

One-time event; log date, content hash, the frozen §11.5 B7 definition, and the pre-registered prediction.

### 12.1 The ladder — ALL baselines sign-normalized

> **Binding convention: HIGHER = MORE α-FAVORING for every baseline.** Vina scores are negative and more-negative means better binding, so raw scores must be *inverted*. Rev. 3 defined B2 as `score_α − mean(score_β,γ,δ)`, which is **more negative** for α-favoring compounds — opposite to B7. Left uncorrected, B2 scores AUC < 0.5 by construction and `ΔAUC = AUC_B7 − AUC_B2` is spuriously inflated, handing the confirmatory comparison a fake win.

| # | Baseline | Definition (sign-normalized) | Role |
|---|---|---|---|
| B0 | Random / scaffold-frequency prior | — | descriptive |
| B1 | α docking score alone | **−Vina_α** | descriptive |
| **B2** | **ΔVina** | **mean(Vina_β,γ,δ) − Vina_α** | **comparator of record** |
| B3 | Interaction-count difference | count_α − mean(count_β,γ,δ) | descriptive |
| B4 | Rep-1 residue-level fingerprint | Δ, α-favoring positive | descriptive |
| B5 | Rep-2 chemical-role fingerprint | Δ, α-favoring positive | descriptive |
| B6 | Rep-3 role + coarse geometry | Δ, α-favoring positive | descriptive |
| **B7** | **Composite, frozen at §11.5** | S_α, α-favoring positive | **confirmatory** |

**Mandatory sign-normalization test.** Before any ladder computation, a unit test must verify on a synthetic case with a known answer that **every** baseline yields AUC > 0.5 for a constructed α-favoring set. The B2 bug was not visible by inspection; this test catches it. No ladder result is valid without it passing.

**Multiplicity discipline: B7 vs B2 is the sole pre-registered confirmatory comparison.** B0–B6 are descriptive context. Report every level; claim only the pre-registered one.

### 12.2 Statistical criterion — paired bootstrap, CI lower bound

```
per replicate:  resample compounds with replacement (n = sealed-set size)
                compute M_B7 and M_B2 on the SAME resampled compounds
                Δ = M_B7 − M_B2
→ percentile CI on the Δ distribution, ~10,000 replicates
```

*(Paired, unlike the geometry-ladder contrasts where strata were different compounds and independent resampling was correct. Pairing removes between-compound variance and materially improves power at this n.)*

Metric: rank agreement (AUC/concordance) on the **frozen primary endpoint**. Secondary reported separately, never substituted.

> **Decision rule: B7 outperforms B2 only if `CI₉₅,lower(ΔAUC) > 0.10`.**

A claim that the improvement is *at least* 0.10, not merely non-zero; it subsumes exclude-zero since 0.10 > 0. Frozen before execution (charter precedent: S2 requires ≥0.3 log RMSD over a ligand-only baseline). **At plausible sealed-set sizes this likely requires a point estimate near ΔAUC ≈ 0.20 — see §1.2. Never lowered after the fact.**

**STOP CONDITION (binding):** if B7 fails, the composite is **not justified**, nothing is promoted, and this is the headline result. A finding that ΔVina performs as well as the elaborate pipeline is legitimate, useful, and cheaper for anyone building on it.

### 12.3 Retrospective tests

1. Do sealed-set compounds carrying the signature show `IC50_α ≪ IC50_β, IC50_γ, IC50_δ` (within-study, within-assay only)?
2. Does the signal rank the §2 panel correctly — **interpreted by mechanism class**, not pass/fail?

**No iteration within a model generation.**

---

## 13. CANDIDATE surrogate reward — promotion, not construction

If §7, §10, §11, §12 all pass, the **already-frozen** B7 (§11.5) is promoted to **candidate surrogate reward** and documented. **Nothing is constructed here** — construction after §12 would be fitting to the sealed set.

> **Binding statement, required in every artifact referencing this object:**
> *Its ability to function as a reward for generative molecular design is **not established** by this study. Demonstrating reward utility requires a subsequent computational generation/optimization evaluation — testing whether a generative model optimizing against this signal produces molecules that retain the signal under independent scoring, do not exploit degeneracies in the scoring function, and remain synthetically and physicochemically plausible. Retrospective ranking of known compounds does not demonstrate any of these.*

Potency remains a **constraint** (charter §2.3 floor, pAct_α ≥ 7.0), never a penalty.

---

## 14. Claim ceiling (binding vocabulary)

| Permitted | Prohibited |
|---|---|
| "scaffold-generalized computational comparative selectivity signal" | "validated selectivity mechanism" |
| "candidate surrogate reward" | "surrogate reward" (unqualified) / "validated reward" |
| "scaffold-disjoint retrospective validation against previously existing experimental measurements" | "independent validation" / "independent experimental confirmation" |
| "internal estimate of receptor-representation sensitivity" | "ground-truth artifact magnitude" |
| "distinguishes the α interaction landscape from β/γ/δ across unrelated scaffold families" | "causal" / "causes α selectivity" |
| "outperforms simpler docking-derived baselines on held-out scaffold families" | "predicts selectivity" (unqualified) |

**Every report of the §12 result must carry the endpoint-selection disclosure.**

**Final defensible claim:** *We identify a scaffold-generalized comparative structural signal distinguishing the PI3Kα interaction landscape from β/γ/δ, surviving receptor-representation, ligand-property, representation, geometry, pose, and permutation controls, outperforming simpler docking-derived baselines on held-out scaffold families, and scaffold-disjointly retrospectively consistent with previously measured isoform selectivity — reported as a candidate surrogate reward whose utility for generative design remains to be evaluated, and whose primary endpoint was selected from prior exploratory analysis.*

---

## 15. Gate and commit

Full validation gate (pytest / ruff / mypy / import-linter **including the new label-blinding contract**), A4 byte-identity verification, governance artifacts with hashes, commit.

**Outcome framework — report whichever obtains, without adjusting language to compensate:**

- **Implementation audit reveals blinding cannot be enforced (§0.6.3)** → build the enforcement before proceeding; do not proceed on a procedural promise
- **β receptor inadequate (§3.1)** → four-isoform confirmatory endpoint invalidated; receptor-limitation finding; §1 not run against it
- **Power check fails (§1.2)** → decisive gate does not exist; dataset-limitation finding, *before* corpus spend
- **Calibration failed (§7.4)** → receptor-representation / property-confounding finding
- **Null A failed (§10.3)** → no isoform-specific structure beyond chance; contribution withdrawn
- **Null B quality-confounded** → α's apparent advantage not separable from receptor quality
- **Baselines win (§12.2)** → composite unjustified; promote nothing
- **Generality fails (§11)** → series-specific SAR, not a selectivity principle
- **All pass** → strongest result of the campaign, stated at the §14 ceiling and no higher
- **All pass except retrospective consistency** → structural pattern real but does not track measured selectivity

---

## What this does not authorize

No claim of experimental validation, independence, or causality. No claim that the candidate reward works as a generative-design reward. No weights fit to selectivity labels then described as validated. No clustering result treated as confirmatory. No three-isoform confirmatory claim if β fails. No power check computed against an endpoint β has invalidated. No merging the 24/50 label-informed corpus with the label-blinded corpus into one model. No unblinding before §12, no second look after. No B7 modification after §11.5. No Δα normalization outside §7.1's ≥0.75 branch. No lowering of the §12.2 margin after seeing results. **No Stage E corpus docking before Stage D completes.**

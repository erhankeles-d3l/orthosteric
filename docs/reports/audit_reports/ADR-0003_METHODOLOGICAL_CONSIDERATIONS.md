# ADR-0003 Methodological Considerations (AUDITOR-1, AUDITOR-3, AUDITOR-4)

**Status of this document: developer technical recommendation — requires Independent
Scientific Auditor approval**, for every recommendation below individually. No item here
changes ADR-0003, and none is adopted merely by appearing in this document.

---

## AUDITOR-1 — Train-on-graph vs. evaluate-within-study

### What the current proposal permits

Training on the full connected evidence graph while gating on the within-study stratum
(ADR-0003 §3) is internally consistent with this project's own stated noise model: within
one study/assay, systematic effects largely cancel in a difference target; across studies
they do not (§2.4's two-floor treatment already reflects this).

### Six leakage modes, examined explicitly

1. **Assay/study heterogeneity robustness** — what evaluating on the within-study
   stratum actually measures. Legitimate, and the proposal supports this claim cleanly.
2. **Chemical generalization** (novel scaffolds never seen in any form during training)
   — the proposal does **not** measure this, and nothing in ADR-0003 §3 claims it does.
   The risk is not in the ADR's claim but in how a later report might *describe* the
   result — this should be guarded against explicitly, not left to interpretation.
3. **Scaffold-family generalization** — a middle case: same scaffold family, different
   specific compound, in training vs. evaluation. This is the leakage mode most likely to
   be silently present if evaluation-stratum exclusion happens only at the record level.
4. **Record-level leakage** — the same literal record in both train and eval. Prevented
   trivially by construction (a record belongs to one stratum).
5. **Compound-level leakage** — the same compound, different assay/study, appearing in
   both train (via one study) and eval (via another). **This is permitted by the current
   proposal as written**, and is exactly what distinguishes claim (1) from claim (2)/(3)
   above. It is not a defect — it's what makes the design measure assay-robustness rather
   than novel-chemistry generalization — but it must be named, not implied.
6. **Scaffold-family leakage** — as (3). Not explicitly excluded by ADR-0003 §3 as
   currently worded.

### Candidate methodological safeguard

> Developer technical recommendation — requires Independent Scientific Auditor approval:
> exclude the within-study evaluation stratum from training at the **scaffold-family**
> level, not merely the record level, and require any completion report using S2/S4/S5
> to state explicitly which of the two generalization claims (assay-robustness vs.
> novel-scaffold) the reported number supports.

### What remains the Auditor's decision

Accept as-is (assay-robustness claim only, clearly labelled) / accept with the
scaffold-family exclusion modification / reject and require a stricter split. This
document does not choose among these.

---

## AUDITOR-3 — Duplicate-resolution policy

### Comparative analysis of the three named alternatives

| Policy | Robustness | Reproducibility | Bias risk |
|---|---|---|---|
| Most recent | Poor — recency has no epistemic link to accuracy | High (trivially deterministic) | Real risk if assay convention (e.g. typical `[ATP]`) drifted over time; a "most recent" rule would systematically prefer newer conventions regardless of quality |
| Highest confidence | Better than recency | High, if the confidence score itself is deterministic (it is, per this project's existing non-learned scoring) | Risk of conflating "well-documented" with "accurate" — a meticulously reported but methodologically unusual measurement could outscore a terse but standard one |
| Median | Good — robust to a single outlier measurement | High | Distorted on raw (non-log) scale by the long right tail typical of affinity data |

### The ordering question — examined explicitly, as required

```
raw IC50 → Cheng–Prusoff normalization → Ki → aggregation      (Order A)
raw IC50 → aggregation → Cheng–Prusoff normalization → Ki      (Order B)
```

These are **not equivalent**, because the Cheng–Prusoff relationship is nonlinear in
`[ATP]`. Two raw IC50 values measured under different `[ATP]` cannot be meaningfully
averaged before normalization (Order B) without conflating assay-condition variance with
biological variance. **Order A is the only one of the two that is methodologically
sound**, and this is close to a factual claim rather than a policy preference — it
follows directly from the nonlinearity of the normalization already specified in
ADR-0003 §4, not from a new assumption introduced here.

### Developer technical recommendation — requires Independent Scientific Auditor approval

> Normalize each raw measurement to Ki via Cheng–Prusoff first (Order A). Use the
> project's existing deterministic confidence score only as an exclusion filter for
> clear outliers, not as an aggregation weight. Aggregate the remainder by **log-median**
> Ki, stratified by assay type / isoform / construct. Use "most recent" only as a final
> tiebreaker when confidence scores are exactly equal — never as the primary rule.

This is a recommendation. The Auditor may accept it, modify it, or select a different
policy entirely; nothing here is adopted by virtue of being written down.

---

## AUDITOR-4 — BindingDB/PubChem admissibility without a primary publication

### Mapped against the existing Constitution evidence classes (§2.5)

| Record type | Nearest existing evidence class | Verifiable? |
|---|---|---|
| Traceable primary source, even via BindingDB/PubChem indexing | E1–E2, same as any literature record | Yes, if the primary paper is retrievable |
| Database-level annotation, no primary publication | Below E1 — no existing class captures this cleanly | Assay conditions, `[ATP]`, and organism cannot be independently confirmed |
| Unclear provenance | Not classifiable | No |
| Independently cross-validated (concordant with a separate independent submission) | Comparable to E1, with a corroboration flag | Partially — corroboration substitutes for primary-source traceability |

### Developer technical recommendation — requires Independent Scientific Auditor approval

> Records lacking a primary publication are **excluded from the primary training and
> evaluation target by default**. Admissible only as low-reliability auxiliary evidence,
> and only if independently corroborated by a second, concordant, independent submission,
> or if structured metadata is sufficient to reconstruct assay type, `[ATP]`, and
> organism without a primary paper. This is a direct application of the project's
> existing E1–E4 framework and the existing auxiliary/primary split in Constitution
> §2.3(2) — not a new rule, a specific instance of an existing one.

### Consequence for corpus size and Q8 (Stage 0 audit)

If adopted, this recommendation would likely **reduce** the apparent corpus size
reported at Stage 0 relative to an unrestricted-admissibility policy. This is disclosed
explicitly because it interacts with `N_c`/`N_w` (AUDITOR-2): a stricter admissibility
policy makes the connectivity thresholds harder to clear, which is exactly the kind of
cross-question interaction the Auditor should weigh jointly, not each item in isolation.

---

## Cross-question note carried into the final report

The interaction flagged above (AUDITOR-4's admissibility strictness vs. AUDITOR-2's
connectivity thresholds) is the clearest concrete cross-dependency identified across all
five questions. It does not indicate circularity — no rule here was set by looking at
downstream results — but it does mean the Auditor may want to resolve AUDITOR-4 before
finalizing AUDITOR-2's numeric candidates, since the achievable corpus size depends on
the admissibility policy chosen.

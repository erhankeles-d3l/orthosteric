# AUDITOR-3 Duplicate Resolution Evidence

**Status:** Evidence prepared | CANDIDATE POLICY — requires Auditor approval

---

## 1. Types of replicate measurements in PI3K biochemical data

| Type | Description | Treatment implication |
|---|---|---|
| Technical replicate | Same compound, same assay run, same lab | Average before aggregation; contributes single evidence unit |
| Biological replicate | Same compound, same assay design, independent run | Same lab / operator effects; still a single experimental context |
| Independent publication | Same compound, independently published assay | Different study context; cross-study noise applies |
| Cross-condition replicate | Same compound, different [ATP] or different substrate | Cannot be averaged; [ATP] must be normalized before aggregating |
| Conflicting measurement | Values incompatible within stated uncertainty | Requires confidence-filtered exclusion or non-normalizable flag |

---

## 2. Mathematical analysis: normalization ordering

**FACT — directly supported by ADR-0003 §4 and basic chemistry:**

The Cheng–Prusoff relation is:

    Ki = IC50 / (1 + [ATP] / Km)

This is **nonlinear in [ATP]**. Two IC50 values measured at different [ATP] concentrations (e.g., 10 µM and 100 µM) represent different compound concentrations required for 50% inhibition purely because of the different ATP competition.

**Order A (correct):**
    IC50_1 (at [ATP]_1) → Ki_1
    IC50_2 (at [ATP]_2) → Ki_2
    aggregated Ki = log_median(Ki_1, Ki_2)

**Order B (incorrect):**
    aggregated IC50 = (IC50_1 + IC50_2) / 2  ← mathematically invalid if [ATP]_1 ≠ [ATP]_2
    aggregated IC50 → Ki

**EVIDENCE SYNTHESIS:** Order A is required whenever measurements have been taken under different [ATP]. This follows directly from the nonlinearity of Cheng–Prusoff and is not a policy choice — it is a mathematical requirement.

---

## 3. Aggregation scale: raw vs. log

**EVIDENCE SYNTHESIS — supported by multiple sources:**

Bioactivity data (IC50, Ki) are log-normally distributed across compound series (standard practice in medicinal chemistry). Arithmetic mean of raw values is dominated by outliers; median of log-values (= geometric median of raw values) is robust to this. 

**CANDIDATE POLICY — requires Auditor approval:** aggregate in log-Ki space, not raw Ki space.

---

## 4. Comparison of candidate policies

| Policy | Robustness to outliers | Reproducibility | Bias risk | Notes |
|---|---|---|---|---|
| Log-median Ki | High | Deterministic | Low | Robust to single extreme measurement |
| Log-arithmetic mean Ki | Medium | Deterministic | Medium | More sensitive to outliers than median |
| Most-recent | Low | Deterministic | High | Recency has no epistemic link to accuracy; temporal drift in assay conditions creates systematic bias |
| Highest-confidence | Medium | Deterministic if confidence score is deterministic (it is, per project governance) | Medium | Risk of conflating documentation quality with measurement accuracy |
| Log-median with confidence-based outlier filter | High | Deterministic | Low | Uses confidence score where it is most defensible: outlier exclusion, not weighting |

**RECOMMENDATION — not a governance decision:** log-median Ki with confidence-based outlier exclusion (not weighting), after per-record Cheng–Prusoff normalization (Order A), stratified by assay/isoform/construct. "Most-recent" rejected on epistemic grounds; not recommended even as a tiebreaker except as a last resort.

---

## 5. Stratification requirement

Records differing in:
- isoform (α, β, γ, δ)
- construct (p110/p85 heterodimer vs. p110γ/p101 vs. p110γ/p84)
- species (human vs. murine — directly relevant for PI3Kδ, where commercial murine constructs were widely used)
- assay format (radiometric vs. fluorescence-based vs. HTRF)

should **not** be pooled before aggregation. Stratification is required before applying any aggregation policy.

**CANDIDATE POLICY — requires Auditor approval:** stratify first by isoform × construct × species, then apply log-median within each stratum.

---

## 6. What remains the Auditor's decision

- Confirm or reject the Order A normalization requirement;
- Select among the candidate aggregation policies;
- Specify whether confidence-based filtering uses a hard exclusion threshold or a softer mechanism;
- Specify whether "conflicting measurement" triggers non-normalizable flag or exclusion.

**Independent Auditor decision still required: YES.**

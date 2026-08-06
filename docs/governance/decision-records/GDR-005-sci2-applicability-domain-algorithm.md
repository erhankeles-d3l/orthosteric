# Governance Decision Record GDR-005 — SCI-2 Per-Target Applicability Domain Algorithm

**Category:** Scientific (methodology — which AD algorithm implements
Constitution §4.2(4) per-target requirement; resolution of GGR-004 from
SCI2-001).  
**Status:** Accepted.  
**Date:** 2026-08-06.  
**Decided by:** Project Owner, direct instruction (2026-08-06).  
**Resolves:** SCI2-001 GGR-004 and GDR-004 disposition table row GGR-004.  
**Companion documents:** SCI2-001-specification.md §4.4, GDR-004.

---

## Decision

**AD algorithm = per-isoform leverage-based k-nearest-neighbour with
self-calibrating 95th-percentile training-internal threshold.**

Algorithm identifier (canonical): `leverage_knn_tanimoto_95pct_v1`

---

## Algorithm specification

### Step 1 — Per-isoform training coverage fingerprints

For each Tier 1 isoform i in {alpha, beta, gamma, delta}, construct the set
T_i of Morgan ECFP4 fingerprints (radius 2, 2048 bits) for all compounds in
that isoform's training split. T_i may differ across isoforms because structural
evidence availability differs (Constitution §2.1 Tier 1 data asymmetry; p110beta
is the sparsest isoform).

### Step 2 — Training-internal nearest-neighbour distance distribution

For each compound j in T_i, compute d_i(j) = 1 - max_{k in T_i, k != j}
Tanimoto(fp(j), fp(k)), i.e. the distance to the nearest training neighbour
excluding the compound itself. Compute the 95th percentile of {d_i(j)} over all
j in T_i. Call this tau_i (the AD threshold for isoform i).

Rationale for 95th percentile: by definition, 95% of training compounds are
within AD. 5% outlier rate in training is an accepted convention in QSAR
applicability domain literature (Tropsha et al. 2003; OECD guidance on QSAR
validation). The percentile is computed from data, not invented.

### Step 3 — Query compound AD flag per isoform

For a query compound q with fingerprint fp(q), compute:
  d_i(q) = 1 - max_{j in T_i} Tanimoto(fp(q), fp(j))
  in_AD_i(q) = True iff d_i(q) <= tau_i

### Step 4 — Per-selectivity-axis AD (derived)

The AD flag for selectivity axis alpha-vs-x is:
  in_AD_lr_vs_x(q) = in_AD_alpha(q) AND in_AD_x(q)

Rationale: predicting a selectivity ratio requires both isoforms to be
individually within AD. This is a conservative conjunction consistent with
Constitution §2.4 (joint confidence composes as a conjunction).

### Step 5 — S8b test

On Tier 2 queries (where structural features may differ substantially from
Tier 1), the AD flags must fire more frequently than on within-distribution
Tier 1 compounds. Equal confidence on Vps34 and PI3Kbeta is a kill criterion
(Constitution §1.4 S8b).

---

## What this record resolves and what remains

**Resolved by this record:**
- The AD algorithm class (leverage-based k-NN).
- The distance metric (Tanimoto on ECFP4).
- The threshold calibration rule (95th percentile of training-internal distances).
- The selectivity-axis AD derivation rule (conjunction of isoform ADs).

**Not resolved by this record:**
- Fingerprint parameters (radius=2, 2048 bits) -- these are the same parameters
  used throughout SCI1-019 (NearestNeighborBaseline) and are an engineering choice
  consistent with existing code. No separate GDR required.
- Re-calibration policy when a new model generation is trained -- standard
  practice: recalibrate tau_i from the new training split. No new GDR required.
- Whether structural (pocket feature) distance replaces or supplements ECFP4
  distance for the per-isoform AD -- structural AD is an Extension refinement
  not required for Core gates; may be added without a GDR as long as the ECFP4
  baseline remains the primary comparison.

---

## Leakage analysis

The 95th-percentile tau_i is computed from the TRAINING split only. No
test-set or validation-set compounds enter the calibration. The threshold
therefore does not leak test information.

The only potential leakage: if model selection is performed on validation-set
AD flags, those flags could partially encode test distribution properties.
This is resolved by GDR-009's validation protocol (scaffold-aware k-fold;
model selection uses validation-fold prediction quality, not AD coverage).

---

## S8b testability

The leverage-based AD is directly testable against S8b: Tier 2 compounds
(mTOR, Vps34, DNA-PK, Class II PI3Ks) occupy different regions of chemical
space from Tier 1 PI3K inhibitors. Their distances d_i(q) will exceed tau_i
for most Tier 2 compounds, causing the AD flag to fire. This is the correct
S8b behavior without engineering it in: it emerges from the actual
distribution gap between Tier 1 and Tier 2 chemotypes.

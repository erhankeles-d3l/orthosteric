# Governance Decision Record GDR-009 — SCI-2 Loss Function and Validation Protocol

**Category:** Scientific (methodology — specific loss formulation and model
selection protocol; resolution of GGR-003 residual and GGR-009 from SCI2-001).  
**Status:** Accepted.  
**Date:** 2026-08-06.  
**Decided by:** Project Owner, direct instruction (2026-08-06).  
**Resolves:** SCI2-001 GGR-003 (residual) and GGR-009; GDR-004 disposition table.  
**Companion documents:** SCI2-001-specification.md §5.1–§5.3, GDR-007, GDR-008.

---

## Decision

### Loss function

**Total training loss = equal-weight sum of four Tobit-1 Gaussian NLL terms:**

  L = NLL(pAct_alpha; mu_alpha, sigma^2_alpha)
    + NLL(Delta_alpha_beta; mu_ab, sigma^2_ab)
    + NLL(Delta_alpha_gamma; mu_ag, sigma^2_ag)
    + NLL(Delta_alpha_delta; mu_ad, sigma^2_ad)

where each NLL is the Tobit-1 censored Gaussian negative log-likelihood
(GDR-008), and each (mu, sigma^2) is a heteroscedastic Gaussian head
(GDR-007).

Equal weighting between all four terms, including pAct_alpha and the three
Delta terms.

Loss function identifier (canonical): `tobit1_gaussian_nll_equal_weight_v1`

### Validation protocol

**Scaffold-aware leave-one-scaffold-family-out cross-validation on the
training set, with a fixed held-out test set.**

Protocol identifier (canonical): `scaffold_loso_cv_v1`

---

## Loss function justification

### Equal weighting across all four output heads

Constitution §4.2(2): "Productive alpha binding and beta/gamma/delta sparing
enter the objective with equal weight -- not as an affinity model with a
penalty bolted on."

This constraint requires the three Delta terms to receive equal weight.
It also constrains the pAct_alpha term: treating pAct_alpha as dominant
would produce "an affinity model with a selectivity penalty bolted on,"
which §4.2(2) explicitly prohibits. Equal weighting of all four terms is
the implementation of §4.2(2) that neither privileges affinity nor imposes
a one-sided penalty.

Formally: let w be the coefficient on pAct_alpha relative to each Delta term.
- w >> 1 would produce an affinity model with selectivity penalty (prohibited).
- w = 1 (equal weighting) satisfies §4.2(2).
- w << 1 would underweight pAct_alpha, harming S4a calibration.
This record sets w = 1.

### pAct_alpha head is required despite not being a selectivity axis

pAct_alpha is not a selectivity axis but is required for two reasons:
1. S4a calibration of the alpha isoform requires calibrated pAct_alpha predictions.
2. Joint optimization with pAct_alpha prevents the comparative encoder from
   discarding absolute activity information entirely, which would harm
   generalization.

### INDETERMINATE treatment

INDETERMINATE binding classifications (Constitution §2.2) contribute ZERO to
the training loss. This is implemented by a per-record mask: if a record's
binding classification for any isoform is INDETERMINATE, its NLL contribution
for that isoform's head is set to zero. The record still contributes to
other isoforms' heads if those are classified.

---

## Validation protocol justification

### Scaffold-aware leave-one-scaffold-family-out (LOSO-CV)

The existing SCI1-017 scaffold_split provides the test set. The LOSO-CV
for model selection operates within the non-test compounds:

1. Compute Bemis-Murcko scaffold families for all training+validation compounds.
2. In each CV fold, hold out one scaffold family as the validation fold.
3. Train on remaining families; evaluate on held-out family.
4. Final model: retrain on all training+validation compounds using the
   hyperparameters that achieved best mean validation performance across folds.

This is stricter than random k-fold: it ensures no scaffold leakage between
training and validation.

**Why not random k-fold?** Constitution §3.4: "Model-selection folds respect
the same series boundaries as the final split." Random k-fold mixes scaffold
families between folds, violating this requirement.

**Why LOSO and not a fixed validation split?** A fixed validation split
(single scaffold family held out) gives noisy model selection due to
variance across scaffold families. LOSO-CV averages this out.

**Early stopping:** within each LOSO fold, early stopping on the held-out
fold's NLL is permitted and does not constitute test-set leakage.

### Test set isolation

The held-out test set (from SCI1-017 scaffold_split) is accessed:
- Once per model generation.
- Only for reporting S2, S3, S4a, S4b, S6 gate criteria.
- Never for model selection, hyperparameter tuning, or early stopping.
- Query logged per the SCI-1 evaluation protocol.

---

## What this record resolves

**Resolved:**
- Total training loss: equal-weight sum of four Tobit-1 Gaussian NLL terms.
- INDETERMINATE treatment: zero contribution to loss (per-record mask).
- pAct_alpha equal weighting with Delta terms (implements §4.2(2)).
- Validation protocol: scaffold-aware LOSO-CV within training set.
- Test set access: once per model generation, for gate reporting only.

**Not resolved:**
- Model architecture (graph neural network, transformer, etc.) -- engineering
  choice belonging in the Implementation Specification, not a GDR.
- Optimizer and learning rate schedule -- engineering choice per §7.9.
- Batch size and training duration -- engineering choice per §7.9.
- Regularization (L2, dropout rate) -- engineering choice per §7.9.
- Whether auxiliary losses (e.g. pose prediction) improve performance --
  may be explored without a GDR provided they do not change the primary
  loss structure governed here.

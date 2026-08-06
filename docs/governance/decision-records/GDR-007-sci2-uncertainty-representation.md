# Governance Decision Record GDR-007 — SCI-2 Uncertainty Representation

**Category:** Scientific (methodology — which uncertainty method implements
Constitution §2.4 per-target calibrated uncertainty; resolution of GGR-007
from SCI2-001).  
**Status:** Accepted.  
**Date:** 2026-08-06.  
**Decided by:** Project Owner, direct instruction (2026-08-06).  
**Resolves:** SCI2-001 GGR-007 and GDR-004 disposition table row GGR-007.  
**Companion documents:** SCI2-001-specification.md §12, GDR-008, GDR-009.

---

## Decision

**Uncertainty representation = heteroscedastic Gaussian predictive
distribution. The model outputs both a mean and a log-variance for each
selectivity axis and for pAct_alpha.**

Algorithm identifier (canonical): `heteroscedastic_gaussian_v1`

---

## Method specification

### Predictive distribution

For each output head (pAct_alpha; Delta_alpha_beta; Delta_alpha_gamma;
Delta_alpha_delta), the model outputs two scalars: a predicted mean mu and
a predicted log-variance log(sigma^2). The predictive distribution is:

  y | x ~ Normal(mu(x), sigma^2(x))

where sigma^2(x) is the aleatoric uncertainty for compound x. This is
heteroscedastic because the variance is input-dependent -- compounds that
are structurally distant from the training distribution will (ideally)
receive higher sigma^2.

### Why this method was chosen over alternatives

**vs. deep ensemble:** Ensembles give the best calibration in the literature
(Lakshminarayanan et al. 2017) but require training N independent models
(typically N=5-10). At the model scale required for this project (four-isoform
joint features), training costs scale prohibitively. Ensemble uncertainty is
also harder to certify per-isoform. This method is preferred for Core scope.
Ensembles may be explored in Extension without a new GDR.

**vs. MC Dropout:** MC Dropout requires post-hoc stochastic forward passes and
is known to be poorly calibrated for regression tasks without careful tuning.
The heteroscedastic Gaussian approach has a principled training objective
(Gaussian NLL) and requires no post-hoc tuning.

**vs. conformal prediction:** Conformal prediction gives marginal coverage
guarantees but requires a separate calibration set (distinct from training
and validation). In a scaffold-aware split, the calibration set must itself
be scaffold-separated, shrinking the effective training set. The heteroscedastic
Gaussian requires no calibration set; post-hoc temperature scaling on the
validation fold is sufficient if S4a is not met.

**vs. Gaussian process:** GPs have excellent calibration but cubic scaling
with training data size. At the number of training compounds expected for this
project (hundreds to thousands), GPs become computationally impractical.

### Aleatoric vs epistemic decomposition

Constitution §2.4: "Distinguish epistemic from aleatoric uncertainty."

This record governs the aleatoric component (per-compound output sigma^2).
Epistemic uncertainty (model uncertainty due to limited training data) may
be estimated via MC Dropout with few forward passes (k=20) as a secondary
diagnostic -- this does not require a GDR since it is not used for gating.
The reported uncertainty for S4a/S4b is sigma^2 (aleatoric). The epistemic
component is informational.

### S4b sharpness criterion

Constitution Amendment A1 S4b: "Mean predictive interval width per target <=
the within-study label noise floor x [SEALED AT STAGE 0]."

The predictive interval half-width for a calibrated Gaussian is z * sigma,
where z = 1.645 for 90% coverage and z = 1.96 for 95% coverage.

This GDR governs that S4b is evaluated at 95% coverage (z = 1.96). The
multiplier on the noise floor is still "[SEALED AT STAGE 0]" and is not
set here. What this record adds: the interval width for S4b is computed as
2 * 1.96 * sigma_hat per compound, averaged over the evaluation set per isoform.

### Per-target requirement

Constitution §4.2(4): per-target AD; Constitution §2.4: per-target uncertainty.

Four separate (mu, log_sigma2) output heads -- one per isoform for pAct, and
three for Delta_alpha_x axes. Each head has its own sigma^2. The JointUncertaintyMethod
(from learning/_interfaces.py) governs how these combine into a joint selectivity
confidence; this GDR does not change that composition.

### Post-hoc temperature scaling

If S4a (ECE <= 0.10 per isoform) is not met on the validation fold, temperature
scaling may be applied as a post-hoc recalibration step. Temperature scaling
divides log_sigma2 by a scalar T (calibrated on the validation fold) without
changing the model weights. T is computed per-isoform. This is an engineering
post-processing step, not a GDR-required decision.

---

## What this record resolves

**Resolved:**
- Uncertainty representation: heteroscedastic Gaussian (mean + log-variance).
- S4b interval width formula: 2 * 1.96 * sigma_hat.
- Aleatoric vs epistemic decomposition: aleatoric = sigma^2 (primary, for gating).
- Post-hoc temperature scaling: permitted as engineering recalibration.

**Not resolved:**
- The [SEALED AT STAGE 0] S4b sharpness multiplier -- requires real corpus data.
- Whether Extension uses ensemble uncertainty instead of / in addition to
  heteroscedastic Gaussian -- may be decided without a GDR.

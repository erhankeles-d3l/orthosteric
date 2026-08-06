# Governance Decision Record GDR-008 — SCI-2 Censored Likelihood Form

**Category:** Scientific (methodology — which parametric form implements
Constitution §3.3 censored-likelihood requirement; resolution of GGR-008
from SCI2-001).  
**Status:** Accepted.  
**Date:** 2026-08-06.  
**Decided by:** Project Owner, direct instruction (2026-08-06).  
**Resolves:** SCI2-001 GGR-008 and GDR-004 disposition table row GGR-008.  
**Companion documents:** SCI2-001-specification.md §5.3, GDR-007, GDR-009.

---

## Decision

**Censored likelihood form = Tobit-1 censored normal regression.**

Algorithm identifier (canonical): `tobit1_censored_normal_v1`

---

## Constitutional mandate

Constitution §3.3: "Right-censored inactives retained and modelled with a
censored likelihood -- never discarded, never imputed to the threshold."

A right-censored activity record carries the information: true pIC50 < censor
threshold c (i.e. the compound was measured at concentration c without achieving
50% inhibition). This is distinct from knowing pIC50 is exactly c.

---

## Method specification

### The Tobit-1 model for pAct

For an observed (non-censored) record with measured pAct = y:
  contribution to negative log-likelihood (NLL) = -log Normal(y; mu, sigma^2)
  where mu and sigma^2 are the model's predicted mean and variance for this example.

For a right-censored record at threshold c (meaning true pAct < c):
  The observed variable is: pIC50 < c, i.e. y < c.
  Contribution to NLL = -log Phi((c - mu) / sigma)
  where Phi is the standard normal CDF.

This is the Tobit-1 model (Tobin 1958), which treats censored observations
as coming from the same Normal(mu, sigma^2) distribution but with only
interval information [pAct < c].

### Application to log-selectivity-ratio targets

For the Delta_alpha_x = pAct_alpha - pAct_x axes:
- If pAct_alpha is censored at c_alpha and pAct_x is measured at y_x:
  Delta_alpha_x < c_alpha - y_x (right-censored bound).
  Contribution: -log Phi((c_alpha - y_x - mu_Delta) / sigma_Delta)

- If pAct_alpha is measured at y_alpha and pAct_x is censored at c_x:
  Delta_alpha_x > y_alpha - c_x (left-censored bound).
  Contribution: -log (1 - Phi((y_alpha - c_x - mu_Delta) / sigma_Delta))

- If both are censored: the Delta is interval-censored. Use the difference
  of CDFs: -log (Phi((c_alpha - c_x - mu_Delta) / sigma_Delta) - Phi(
  (c_alpha - c_x - mu_Delta_lo) / sigma_Delta)) -- or simplify by treating
  double-censored examples as INDETERMINATE (contributing zero to the NLL).
  Double-censored examples are rare in practice (both compounds inactive in
  the same panel); the INDETERMINATE treatment is the conservative default.

### Why Tobit-1 was chosen

1. **Standard in QSAR activity regression**: Tobit regression is the established
   standard for handling censored IC50 data (Gaulton et al. 2012 ChEMBL; 
   Sheridan 2013 J. Chem. Inf. Model.).

2. **Consistent with GDR-007 Gaussian predictive distribution**: Tobit-1 directly
   uses the same Normal(mu, sigma^2) that GDR-007 specifies. The censored
   likelihood is a natural extension of the uncensored NLL loss.

3. **Does not impute**: Right-censored compounds are not imputed to the threshold
   or discarded. Their information content (compound is inactive) is preserved.

4. **Verifiable**: The Tobit-1 censoring can be verified by inspecting the NLL
   contributions of censored vs uncensored records.

### Normality assumption

Tobit-1 assumes normality of the underlying pAct distribution. pAct = -log10(IC50)
is approximately normal for sets of related compounds within an assay. Cross-assay
normality is weaker; however, the within-study stratum evaluation (used for S4a/S4b)
mitigates this because within a single assay the distributional assumption is more
defensible.

If post-hoc calibration (GDR-007 temperature scaling) indicates systematic
miscalibration that persists after scaling, this may indicate non-normality and
should be reported. No action is specified here; diagnosis triggers a future review.

---

## What this record resolves

**Resolved:**
- Censored likelihood form: Tobit-1 censored normal.
- Formulas for right-censored pAct and censored Delta_alpha_x.
- Treatment of double-censored examples: INDETERMINATE (zero NLL contribution).

**Not resolved:**
- The assay-specific censor threshold c: this comes from the activity data
  records themselves (field: `ActivityRecord.is_censored`, `pac_value`).
  No new GDR required.
- Whether interval-censored variants (Tobit-2 or interval censoring) are
  used for Extension analysis -- may be added without a GDR as a diagnostic.

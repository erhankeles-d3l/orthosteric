"""Correlate docking-derived comparative features against REAL experimental
selectivity (A4's lr_vs_beta/gamma/delta), for the 24-compound production
pilot.

This is the actual scientific test this whole pipeline was built to
support: does the computational (docking) comparative signal move in the
same direction as the experimental comparative signal? Reported honestly
regardless of outcome -- this analysis does not know in advance whether
docking will correlate with experiment, and a null or weak result is a
valid, reportable outcome, not a failure of the pipeline.

A4 is read-only throughout (only reads the already-frozen experimental
values from the compound-selection file, itself derived from A4 upstream).
"""

from __future__ import annotations

import json
from pathlib import Path

from scipy.stats import pearsonr, spearmanr

compounds = json.loads(
    Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/production_pilot_compound_selection.json").read_text()
)
results = json.loads(
    Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/production_pilot_results.json").read_text()
)

exp_by_id = {c["compound_id"]: c for c in compounds}

_AXES = [("PI3Kbeta", "lr_vs_beta"), ("PI3Kgamma", "lr_vs_gamma"), ("PI3Kdelta", "lr_vs_delta")]

print("=== Docking-derived Δscore vs experimental selectivity (24 compounds) ===\n")

rows = []
for cid, exp in exp_by_id.items():
    dock_alpha = results.get(f"{cid}__PI3Kalpha", {}).get("docking_score")
    if dock_alpha is None:
        continue
    row = {"compound_id": cid, "stratum": exp["stratum"]}
    for iso, exp_key in _AXES:
        dock_x = results.get(f"{cid}__{iso}", {}).get("docking_score")
        if dock_x is None:
            continue
        # Delta-dock convention (established in the prior 5-compound pilot):
        # dock(X) - dock(alpha). A MORE NEGATIVE alpha score (stronger
        # predicted alpha binding) with a LESS negative X score gives a
        # POSITIVE delta_dock -- matching the sign of pAct_alpha - pAct_X
        # (positive = alpha-preferential), so the two axes are directly
        # comparable without a sign flip.
        row[f"delta_dock_{iso}"] = dock_x - dock_alpha
        row[f"exp_{iso}"] = exp[exp_key]
    rows.append(row)

print(f"Compounds with complete data: {len(rows)}/{len(compounds)}\n")

print(f"{'compound':<18}{'stratum':<18}" + "".join(f"{'dd_'+iso[-5:]:>10}{'exp_'+iso[-5:]:>10}" for iso, _ in _AXES))
for r in rows:
    line = f"{r['compound_id'][:16]:<18}{r['stratum']:<18}"
    for iso, _ in _AXES:
        dd = r.get(f"delta_dock_{iso}")
        ex = r.get(f"exp_{iso}")
        line += f"{dd:>10.2f}{ex:>10.2f}" if dd is not None and ex is not None else f"{'N/A':>10}{'N/A':>10}"
    print(line)

print("\n=== Correlation: docking Δscore vs experimental selectivity, per axis ===")
correlation_results = {}
for iso, _ in _AXES:
    dds = [r[f"delta_dock_{iso}"] for r in rows if f"delta_dock_{iso}" in r]
    exs = [r[f"exp_{iso}"] for r in rows if f"exp_{iso}" in r]
    n = len(dds)
    if n < 3:
        print(f"  {iso}: insufficient data (n={n})")
        continue
    pear_r, pear_p = pearsonr(dds, exs)
    spear_r, spear_p = spearmanr(dds, exs)
    sign_agree = sum(1 for dd, ex in zip(dds, exs, strict=True) if (dd > 0) == (ex > 0))
    correlation_results[iso] = {
        "n": n, "pearson_r": pear_r, "pearson_p": pear_p,
        "spearman_r": spear_r, "spearman_p": spear_p,
        "sign_agreement": sign_agree, "sign_agreement_pct": round(100 * sign_agree / n, 1),
    }
    print(f"  alpha_vs_{iso[5:]:<7} n={n:2}  Pearson r={pear_r:+.3f} (p={pear_p:.3f})  "
          f"Spearman rho={spear_r:+.3f} (p={spear_p:.3f})  sign_agreement={sign_agree}/{n} "
          f"({100*sign_agree/n:.0f}%)")

print("\n=== Interaction-type-count differentials vs experimental selectivity ===")
print("(descriptive only -- 24 compounds is far too few to test 5 interaction")
print(" types x 3 axes with any statistical power; reported for completeness,")
print(" not as a validated finding)")

itype_corr = {}
for it_type in ("h_bond", "salt_bridge", "charged_contact_candidate", "hydrophobic_contact", "cation_pi", "pi_pi"):
    for iso, exp_key in _AXES:
        pairs = []
        for cid, exp in exp_by_id.items():
            a_counts = results.get(f"{cid}__PI3Kalpha", {}).get("interaction_type_counts", {})
            x_counts = results.get(f"{cid}__{iso}", {}).get("interaction_type_counts", {})
            if a_counts is None or x_counts is None:
                continue
            delta_count = x_counts.get(it_type, 0) - a_counts.get(it_type, 0)
            pairs.append((delta_count, exp[exp_key]))
        if len({p[0] for p in pairs}) < 2:  # noqa: PLR2004
            continue  # constant, correlation undefined
        dds = [p[0] for p in pairs]
        exs = [p[1] for p in pairs]
        try:
            r, p = spearmanr(dds, exs)
            if abs(r) > 0.3:  # noqa: PLR2004  -- only report non-trivial correlations
                itype_corr[f"{it_type}_vs_{iso}"] = {"spearman_r": r, "p": p, "n": len(pairs)}
                print(f"  delta_{it_type} vs {iso}: rho={r:+.3f} (p={p:.3f}, n={len(pairs)})")
        except Exception:
            pass

out = {
    "n_compounds": len(rows),
    "per_axis_correlation": correlation_results,
    "interaction_type_correlations_above_0.3": itype_corr,
    "rows": rows,
}
out_path = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/production_pilot_correlation_analysis.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"\nWrote {out_path}")

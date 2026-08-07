"""Breakdown of cross-isoform interaction patterns by interaction TYPE,
and correlation with real experimental selectivity strata, for the
EXPANDED 50-compound production run. Identical analysis to
analysis/run_motif_stratum_breakdown.py (24-compound version) --
only the input files change, plus a symmetric other_favored-per-compound
metric added (the 24-compound version only computed this for
alpha_favored; added here for a complete comparison).

Reads real output of analysis/run_expanded_interaction_motif_fingerprints.py.
Does not rerun docking. A4 is not touched.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

comparative = json.loads(
    Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/expanded_comparative_interaction_fingerprints.json").read_text()
)
compounds = json.loads(
    Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/expanded_pilot_compound_selection.json").read_text()
)
stratum_by_id = {c["compound_id"]: c["stratum"] for c in compounds}

print("=== Cross-isoform pattern breakdown BY INTERACTION TYPE (n=50 compounds) ===\n")
by_type: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
for cid, records in comparative.items():
    for r in records:
        by_type[r["interaction_type"]][r["pattern"]] += 1

for itype in sorted(by_type):
    totals = by_type[itype]
    total_n = sum(totals.values())
    print(f"{itype} (n={total_n}):")
    for pattern, count in sorted(totals.items(), key=lambda x: -x[1]):
        print(f"    {pattern}: {count} ({100*count/total_n:.1f}%)")

print("\n=== Alpha-favored motifs: which compounds, which stratum? ===")
alpha_favored_by_stratum: dict[str, int] = defaultdict(int)
alpha_favored_compounds = []
for cid, records in comparative.items():
    stratum = stratum_by_id.get(cid, "unknown")
    for r in records:
        if r["pattern"] == "alpha_favored":
            alpha_favored_by_stratum[stratum] += 1
            alpha_favored_compounds.append((cid, r["interaction_type"], r["canonical_position"], stratum))

print("Alpha-favored motif count by experimental stratum:")
for stratum, count in sorted(alpha_favored_by_stratum.items()):
    n_compounds_in_stratum = sum(1 for s in stratum_by_id.values() if s == stratum)
    print(f"  {stratum} ({n_compounds_in_stratum} compounds): {count} alpha-favored motifs")

print("\nAlpha-favored motif details:")
for cid, itype, pos, stratum in alpha_favored_compounds:
    print(f"  {cid[:16]}... [{stratum}] {itype} @ canonical position {pos}")

print("\n=== Other-favored motifs: which compounds, which stratum? ===")
other_favored_by_stratum: dict[str, int] = defaultdict(int)
for cid, records in comparative.items():
    stratum = stratum_by_id.get(cid, "unknown")
    for r in records:
        if r["pattern"] == "other_favored":
            other_favored_by_stratum[stratum] += 1

print("Other(beta/gamma/delta)-favored motif count by experimental stratum:")
for stratum, count in sorted(other_favored_by_stratum.items()):
    n_compounds_in_stratum = sum(1 for s in stratum_by_id.values() if s == stratum)
    print(f"  {stratum} ({n_compounds_in_stratum} compounds): {count} other-favored motifs")

print("\n=== Conserved motifs (non-selective structural compatibility) ===")
conserved_by_type: dict[str, int] = defaultdict(int)
for cid, records in comparative.items():
    for r in records:
        if r["pattern"] == "conserved":
            conserved_by_type[r["interaction_type"]] += 1
print("Conserved motif count by interaction type:", dict(conserved_by_type))

# ── Directional check, BOTH directions this time ────────────────────────────
print("\n=== Directional check: alpha-favored motifs per compound, by stratum ===")
n_af_per_compound: dict[str, list[int]] = defaultdict(list)
n_of_per_compound: dict[str, list[int]] = defaultdict(list)
for cid, records in comparative.items():
    stratum = stratum_by_id.get(cid, "unknown")
    n_af = sum(1 for r in records if r["pattern"] == "alpha_favored")
    n_of = sum(1 for r in records if r["pattern"] == "other_favored")
    n_af_per_compound[stratum].append(n_af)
    n_of_per_compound[stratum].append(n_of)

for stratum, counts in sorted(n_af_per_compound.items()):
    mean_af = sum(counts) / len(counts) if counts else 0.0
    print(f"  {stratum}: mean alpha-favored motifs/compound = {mean_af:.2f} (n={len(counts)} compounds)")

print("\n=== Directional check: other-favored motifs per compound, by stratum ===")
print("(expect the OPPOSITE direction from alpha-favored if the pipeline carries real signal:")
print(" other_selective compounds should show MORE other-favored motifs than alpha_selective ones)")
for stratum, counts in sorted(n_of_per_compound.items()):
    mean_of = sum(counts) / len(counts) if counts else 0.0
    print(f"  {stratum}: mean other-favored motifs/compound = {mean_of:.2f} (n={len(counts)} compounds)")

# ── Direct comparison: does mean(alpha_favored) - mean(other_favored) rank
# alpha_selective > non_selective > other_selective, as the hypothesis would
# predict? ────────────────────────────────────────────────────────────────────
print("\n=== Net alpha-preference score per stratum: mean(alpha_favored) - mean(other_favored) ===")
net_by_stratum = {}
for stratum in n_af_per_compound:
    mean_af = sum(n_af_per_compound[stratum]) / len(n_af_per_compound[stratum])
    mean_of = sum(n_of_per_compound[stratum]) / len(n_of_per_compound[stratum])
    net_by_stratum[stratum] = mean_af - mean_of
    print(f"  {stratum}: net = {mean_af:.2f} - {mean_of:.2f} = {net_by_stratum[stratum]:+.2f}")

expected_order = ["alpha_selective", "intermediate", "non_selective", "other_selective"]
actual_order = sorted(net_by_stratum, key=lambda s: -net_by_stratum[s])
print(f"\nExpected order (alpha-favored to other-favored): {expected_order}")
print(f"Actual order by net score (highest to lowest):    {actual_order}")
print(f"Matches expected order: {actual_order == expected_order}")

out = {
    "n_compounds": len(compounds),
    "pattern_by_interaction_type": {k: dict(v) for k, v in by_type.items()},
    "alpha_favored_by_stratum": dict(alpha_favored_by_stratum),
    "other_favored_by_stratum": dict(other_favored_by_stratum),
    "conserved_by_type": dict(conserved_by_type),
    "alpha_favored_per_compound_by_stratum": {k: v for k, v in n_af_per_compound.items()},
    "other_favored_per_compound_by_stratum": {k: v for k, v in n_of_per_compound.items()},
    "net_alpha_preference_by_stratum": net_by_stratum,
    "matches_expected_order": actual_order == expected_order,
}
out_path = Path("/home/ubuntu/Documents/orthosteric/docs/governance/EXPANDED_INTERACTION_MOTIF_STRATUM_BREAKDOWN.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"\nWrote {out_path}")

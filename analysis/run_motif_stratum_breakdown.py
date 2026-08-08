"""Breakdown of cross-isoform interaction patterns by interaction TYPE
(not aggregated across all types), and correlation with the real
experimental selectivity strata already established for the 24-compound
production pilot.

Reads the real output of analysis/run_interaction_motif_fingerprints.py.
Does not rerun docking. A4 is not touched.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

comparative = json.loads(
    Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/comparative_interaction_fingerprints.json").read_text()
)
compounds = json.loads(
    Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/production_pilot_compound_selection.json").read_text()
)
stratum_by_id = {c["compound_id"]: c["stratum"] for c in compounds}

print("=== Cross-isoform pattern breakdown BY INTERACTION TYPE ===\n")
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

# ── Directional check: do alpha-selective compounds have MORE alpha-favored
# motifs per compound than non-selective compounds? ─────────────────────────
print("\n=== Directional check: alpha-favored motifs per compound, by stratum ===")
n_af_per_compound: dict[str, list[int]] = defaultdict(list)
for cid, records in comparative.items():
    stratum = stratum_by_id.get(cid, "unknown")
    n_af = sum(1 for r in records if r["pattern"] == "alpha_favored")
    n_af_per_compound[stratum].append(n_af)

for stratum, counts in sorted(n_af_per_compound.items()):
    mean_af = sum(counts) / len(counts) if counts else 0.0
    print(f"  {stratum}: mean alpha-favored motifs/compound = {mean_af:.2f} (n={len(counts)} compounds, "
          f"raw counts={counts})")

out = {
    "pattern_by_interaction_type": {k: dict(v) for k, v in by_type.items()},
    "alpha_favored_by_stratum": dict(alpha_favored_by_stratum),
    "other_favored_by_stratum": dict(other_favored_by_stratum),
    "conserved_by_type": dict(conserved_by_type),
    "alpha_favored_per_compound_by_stratum": {k: v for k, v in n_af_per_compound.items()},
}
out_path = Path("/home/ubuntu/Documents/orthosteric/docs/governance/INTERACTION_MOTIF_STRATUM_BREAKDOWN.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"\nWrote {out_path}")

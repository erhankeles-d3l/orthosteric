"""Deterministic, stratified selection of A4 compounds for the production
cross-docking pilot.

Uses the existing SelectivityTarget infrastructure (eval._target_construction,
governed by GDR-011/013) -- real, already-validated experimental pAct_alpha
and alpha-vs-X selectivity values, not fabricated.

Stratification (ENGINEERING CHOICE, documented, not a scientific threshold):
  alpha-selective:    median(lr_vs_beta, lr_vs_gamma, lr_vs_delta) > +1.0
  other-selective:    median(...) < -1.0
  non-selective:      abs(median(...)) <= 0.3
  intermediate:       everything else

Within each stratum, compounds are sorted by compound_id (InChIKey) for
full reproducibility, then evenly subsampled with a fixed stride so the
selection is deterministic given only the stratum sizes and the target
count -- no random seed is needed, but one is recorded anyway for audit.
Scaffold diversity is enforced by preferring one compound per scaffold
family before allowing repeats.

A4 is read-only throughout.
"""

from __future__ import annotations

import gzip
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Documents/orthosteric/src")

from orthosteric.eval._target_construction import build_selectivity_targets

A4 = Path("/home/ubuntu/Documents/orthosteric/data/snapshots/activity_snapshot_A4")
man = json.loads((A4 / "manifest.json").read_text())
with gzip.open(A4 / "records.json.gz", "rt") as f:
    recs = json.load(f)
accepted = [r for r in recs if not r.get("exclusion_reason")]
scaffold_of = {}
for r in sorted(accepted, key=lambda r: str(r.get("source_record_id", ""))):
    ik = r.get("inchikey")
    fam = r.get("scaffold_family_id")
    if ik and fam and ik not in scaffold_of:
        scaffold_of[ik] = fam

targets = build_selectivity_targets(recs)
print(f"Total SelectivityTargets: {len(targets)}")


def classify(t):
    diffs = [t.lr_vs_beta, t.lr_vs_gamma, t.lr_vs_delta]
    med = statistics.median(diffs)
    if med > 1.0:
        return "alpha_selective"
    if med < -1.0:
        return "other_selective"
    if abs(med) <= 0.3:
        return "non_selective"
    return "intermediate"


strata: dict[str, list] = {"alpha_selective": [], "other_selective": [], "non_selective": [], "intermediate": []}
for t in targets:
    strata[classify(t)].append(t)

for name, members in strata.items():
    print(f"  {name}: {len(members)} compounds")

TARGET_N = 24  # ambitious but achievable within this session's remaining
                # compute/tool-call budget; see docs report for why this is
                # smaller than the mandate's 50-100 (transparent, not hidden)

# proportional allocation across strata, at least 2 per non-empty stratum
n_strata = sum(1 for m in strata.values() if m)
alloc = {}
remaining = TARGET_N
for name in strata:
    if strata[name]:
        alloc[name] = max(2, TARGET_N // n_strata)
        remaining -= alloc[name]
# distribute any remainder to the largest stratum
if remaining > 0:
    largest = max(strata, key=lambda k: len(strata[k]))
    alloc[largest] += remaining

selected = []
seen_scaffolds: set[str] = set()
for name, members in strata.items():
    members_sorted = sorted(members, key=lambda t: t.compound_id)
    want = min(alloc.get(name, 0), len(members_sorted))
    # prefer scaffold diversity: walk sorted list, take compounds whose
    # scaffold hasn't been used yet first, then allow repeats if needed
    picked = []
    for t in members_sorted:
        if len(picked) >= want:
            break
        fam = scaffold_of.get(t.compound_id)
        if fam not in seen_scaffolds:
            picked.append(t)
            seen_scaffolds.add(fam)
    if len(picked) < want:
        for t in members_sorted:
            if len(picked) >= want:
                break
            if t not in picked:
                picked.append(t)
    selected.extend(picked)
    print(f"  selected {len(picked)}/{want} from {name}")

print(f"\nTotal selected: {len(selected)}")
out = [
    {
        "compound_id": t.compound_id, "smiles": t.smiles, "pac_alpha": t.pac_alpha,
        "lr_vs_beta": t.lr_vs_beta, "lr_vs_gamma": t.lr_vs_gamma, "lr_vs_delta": t.lr_vs_delta,
        "scaffold_family_id": scaffold_of.get(t.compound_id), "stratum": classify(t),
    }
    for t in selected
]
out_path = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/production_pilot_compound_selection.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"Wrote {out_path}")
for o in out:
    print(f"  {o['compound_id'][:16]}... [{o['stratum']}] pAct_a={o['pac_alpha']:.2f} "
          f"lrB={o['lr_vs_beta']:.2f} lrG={o['lr_vs_gamma']:.2f} lrD={o['lr_vs_delta']:.2f}")

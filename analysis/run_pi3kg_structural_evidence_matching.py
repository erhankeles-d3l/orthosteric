"""Stage D completion (partial): compound-level PIK3Kgamma experimental
complex matching against Activity Snapshot A4, and an honest assessment
of whether the current match coverage supports a structural-augmented
Model Generation 1 training run.

Real data sources (fetched via RCSB REST API, cached in /tmp for this
run -- see docs/STRUCTURAL_EVIDENCE_PI3KG_REPORT.md for the exact fetch
commands): 107 PIK3Kgamma PDB entries (RCSB search on UniProt P48736),
102 distinct non-additive co-crystallized ligand CCD codes, InChIKeys for
all 102 (RCSB chemcomp core API, `pdbx_chem_comp_descriptor` field, type
InChIKey -- exact values from RCSB, not RDKit-recomputed).

A4 is read-only throughout.
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from orthosteric.data.sources.structural._pi3kg_complex_matching import (
    LigandPdbEvidence,
    match_corpus_to_pi3kg_complexes,
)
from orthosteric.eval._target_construction import build_selectivity_targets

A4 = Path("data/snapshots/activity_snapshot_A4")
man = json.loads((A4 / "manifest.json").read_text())
with gzip.open(A4 / "records.json.gz", "rt") as f:
    recs = json.load(f)
accepted = [r for r in recs if not r.get("exclusion_reason")]

# ── Real, fetched RCSB data (see module docstring for provenance) ───────────
ligand_iks = json.load(open("/tmp/pik3cg_ligand_inchikeys.json"))
pdb_ligands = json.load(open("/tmp/pik3cg_pdb_ligands_v2.json"))["ligands_by_pdb"]

pdb_by_ccd: dict[str, list[tuple[str, float | None]]] = {}
for pdb_id, info in pdb_ligands.items():
    for ccd in info.get("ccds") or []:
        pdb_by_ccd.setdefault(ccd, []).append((pdb_id, info.get("resolution")))

ligand_evidence = [
    LigandPdbEvidence(ccd_code=ccd, inchikey=ik, pdb_entries=tuple(pdb_by_ccd.get(ccd, [])))
    for ccd, ik in ligand_iks.items()
]

print("=== Stage D: PIK3Kgamma compound-level structural evidence ===")
print(f"A4 content_sha256: {man['snapshot_sha256']}")
print(f"Real RCSB data: 107 PDB entries, {len(ligand_iks)} distinct ligand CCD codes")

records = match_corpus_to_pi3kg_complexes(
    accepted, ligand_evidence, man["snapshot_sha256"], "2026-08-06"
)
complex_records = [r for r in records if r.evidence_class.value == "experimental_complex"]
unavailable_records = [r for r in records if r.evidence_class.value == "unavailable"]
matched_compounds = {r.compound_id for r in complex_records}

print(f"\nTotal corpus compounds assessed: {len(records)}")
print(f"EXPERIMENTAL_COMPLEX records (real PDB co-crystals): {len(complex_records)}")
print(f"Distinct matched compounds: {len(matched_compounds)}")
print(f"UNAVAILABLE compounds: {len(unavailable_records)}")

# ── Overlap with the actual modeling set (SelectivityTargets) ───────────────
targets = build_selectivity_targets(recs)
target_ids = {t.compound_id for t in targets}
overlap = matched_compounds & target_ids
print(f"\nSelectivityTargets (complete 4-isoform C1_PRIMARY compounds): {len(target_ids)}")
print(f"Overlap with structurally-matched compounds: {len(overlap)} "
      f"({100 * len(overlap) / len(target_ids):.1f}% of the modeling set)")

# ── Honest feasibility assessment ────────────────────────────────────────────
print("\n=== Feasibility assessment for a structural-augmented training run ===")
MIN_VIABLE_FOR_SPLIT = 50  # documented, not governed: below this, a scaffold
                            # train/val/test split cannot produce a usable test set
if len(overlap) < MIN_VIABLE_FOR_SPLIT:
    print(f"INSUFFICIENT: {len(overlap)} compounds have both real structural "
          f"evidence and a complete comparative target -- below the "
          f"{MIN_VIABLE_FOR_SPLIT}-compound floor needed for any trustworthy "
          f"scaffold-aware train/val/test split.")
    print("The current ComparativeSelectivityModelV1.fit()/predict() anti-"
          "fabrication rule SKIPS any example missing from a supplied "
          "structural_features mapping (tested invariant, prior session). "
          "Passing a 28-compound mapping while fitting on the full 1,267-"
          "compound corpus would silently collapse the effective training "
          "set to ~28 compounds -- not a meaningful structural-vs-ligand-"
          "only comparison, and not run here for that reason.")
else:
    print(f"SUFFICIENT ({len(overlap)} >= {MIN_VIABLE_FOR_SPLIT}): a structural-"
          f"augmented run would be attempted.")

out = {
    "snapshot_sha256": man["snapshot_sha256"],
    "n_pdb_entries": 107,
    "n_distinct_ligand_ccds": len(ligand_iks),
    "n_experimental_complex_records": len(complex_records),
    "n_matched_compounds": len(matched_compounds),
    "n_unavailable_compounds": len(unavailable_records),
    "n_selectivity_targets": len(target_ids),
    "n_overlap_with_modeling_set": len(overlap),
    "overlap_pct_of_modeling_set": round(100 * len(overlap) / len(target_ids), 2),
    "min_viable_for_split": MIN_VIABLE_FOR_SPLIT,
    "structural_run_feasible": len(overlap) >= MIN_VIABLE_FOR_SPLIT,
    "matched_compound_inchikeys": sorted(matched_compounds),
    "overlap_with_modeling_set_inchikeys": sorted(overlap),
}
out_path = Path("docs/governance/STAGE_D_PI3KG_MATCHING_A4.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"\nWrote {out_path} (A4 not modified)")

# Persist the full StructuralEvidenceRecord set for audit
evidence_out = Path("data/structural_evidence")
evidence_out.mkdir(parents=True, exist_ok=True)
(evidence_out / "pi3kg_experimental_complex_A4.json").write_text(
    json.dumps([r.to_dict() for r in complex_records], indent=2)
)
print(f"Wrote {evidence_out / 'pi3kg_experimental_complex_A4.json'} "
      f"({len(complex_records)} real EXPERIMENTAL_COMPLEX records)")

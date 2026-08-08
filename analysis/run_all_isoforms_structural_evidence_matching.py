"""Stage D completion: compound-level structural-evidence matching for
PIK3CA (alpha) and PIK3CD (delta) against Activity Snapshot A4, alongside
the existing PIK3Kgamma result, and an honest combined feasibility
assessment for a structural-augmented Model Generation 1 training run.

Real data sources, fetched via RCSB REST API (see
/tmp/fetch_alpha_delta_pdb_evidence.py for the exact fetch code; mirrors
the PIK3Kgamma methodology in docs/STRUCTURAL_EVIDENCE_PI3KG_REPORT.md):
  - PIK3CA (P42336): 135 PDB entries (exact UniProt accession match),
    95 distinct non-solvent/ion co-crystallized ligand CCDs, all with
    RCSB-computed InChIKeys.
  - PIK3CD (O00329): 20 PDB entries, 20 distinct ligand CCDs.
  - PIK3CB (P42338, human): 0 PDB entries. Two mouse-ortholog (Q8BTI9)
    structures exist (2Y3A, 4BFR) but are NOT used as same-species
    structural evidence for the human corpus -- see
    docs/STRUCTURAL_EVIDENCE_ALL_ISOFORMS_REPORT.md for the cross-species
    exclusion rationale. PI3Kbeta therefore remains CORPUS_INSUFFICIENT
    (human), unchanged from before this session.

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
targets = build_selectivity_targets(recs)
target_ids = {t.compound_id for t in targets}

print("=== Stage D: alpha/beta/delta compound-level structural evidence ===")
print(f"A4 content_sha256: {man['snapshot_sha256']}")
print(f"SelectivityTargets (complete 4-isoform C1_PRIMARY compounds): {len(target_ids)}")

MIN_VIABLE_FOR_SPLIT = 50  # documented, not governed (same floor as the PI3Kgamma run)

all_results = {}


def run_isoform(label, tag, n_pdb_entries):
    pdb_ligands = json.load(open(f"/tmp/{tag}_pdb_ligands.json"))
    ligand_iks = json.load(open(f"/tmp/{tag}_ligand_inchikeys.json"))

    pdb_by_ccd: dict[str, list[tuple[str, float | None]]] = {}
    for pdb_id, info in pdb_ligands.items():
        for ccd in info.get("ccds") or []:
            pdb_by_ccd.setdefault(ccd, []).append((pdb_id, info.get("resolution")))

    ligand_evidence = [
        LigandPdbEvidence(ccd_code=ccd, inchikey=ik, pdb_entries=tuple(pdb_by_ccd.get(ccd, [])))
        for ccd, ik in ligand_iks.items()
    ]

    records = match_corpus_to_pi3kg_complexes(
        accepted, ligand_evidence, man["snapshot_sha256"], "2026-08-06", isoform=label
    )
    complex_records = [r for r in records if r.evidence_class.value == "experimental_complex"]
    matched_compounds = {r.compound_id for r in complex_records}
    overlap = matched_compounds & target_ids

    print(f"\n--- {label} ---")
    print(f"  PDB entries: {n_pdb_entries}, distinct ligands: {len(ligand_iks)}")
    print(f"  Matched corpus compounds: {len(matched_compounds)}")
    print(f"  Overlap with modeling set: {len(overlap)} "
          f"({100 * len(overlap) / len(target_ids):.2f}% of {len(target_ids)})")

    evidence_out = Path("data/structural_evidence")
    evidence_out.mkdir(parents=True, exist_ok=True)
    fname = evidence_out / f"{tag}_experimental_complex_A4.json"
    fname.write_text(json.dumps([r.to_dict() for r in complex_records], indent=2))

    all_results[label] = {
        "n_pdb_entries": n_pdb_entries,
        "n_distinct_ligands": len(ligand_iks),
        "n_matched_compounds": len(matched_compounds),
        "n_overlap_with_modeling_set": len(overlap),
        "overlap_pct": round(100 * len(overlap) / len(target_ids), 2),
        "overlap_inchikeys": sorted(overlap),
    }
    return matched_compounds, overlap


alpha_matched, alpha_overlap = run_isoform("PI3Kalpha", "pik3ca", 135)
delta_matched, delta_overlap = run_isoform("PI3Kdelta", "pik3cd", 20)

# ── Existing PIK3Kgamma result (read, not recomputed -- A4 unchanged) ──────
gamma_json = json.loads(Path("docs/governance/STAGE_D_PI3KG_MATCHING_A4.json").read_text())
gamma_overlap = set(gamma_json["overlap_with_modeling_set_inchikeys"])
print(f"\n--- PI3Kgamma (prior session result, re-read not recomputed) ---")
print(f"  Overlap with modeling set: {len(gamma_overlap)} "
      f"({gamma_json['overlap_pct_of_modeling_set']:.2f}%)")

# ── Combined feasibility: compounds with structural evidence in ALL 4 -----
# isoforms (the only basis on which a genuinely structural-vs-ligand-only
# comparative experiment is meaningful; beta has none, so "all 4" is
# structurally impossible and reported as such, not glossed over).
all_four_overlap = alpha_overlap & delta_overlap & gamma_overlap
any_isoform_overlap = alpha_overlap | delta_overlap | gamma_overlap

print(f"\n=== Combined feasibility (alpha, gamma, delta -- beta has zero human PDB coverage) ===")
print(f"Compounds with structural evidence in ALL THREE non-beta isoforms AND a complete "
      f"4-isoform modeling target: {len(all_four_overlap)}")
print(f"Compounds with structural evidence in AT LEAST ONE of alpha/gamma/delta AND a "
      f"complete 4-isoform modeling target: {len(any_isoform_overlap)}")

feasible_any = len(any_isoform_overlap) >= MIN_VIABLE_FOR_SPLIT
feasible_all = len(all_four_overlap) >= MIN_VIABLE_FOR_SPLIT
print(f"\nSUFFICIENT for INDICATOR_ZERO_FILL run (>= {MIN_VIABLE_FOR_SPLIT} compounds with "
      f"ANY structural evidence, all others zero-filled+flagged): {feasible_any} "
      f"({len(any_isoform_overlap)})")
print(f"SUFFICIENT for full-coverage run (>= {MIN_VIABLE_FOR_SPLIT} compounds with structural "
      f"evidence in every non-beta isoform simultaneously): {feasible_all} "
      f"({len(all_four_overlap)})")

out = {
    "snapshot_sha256": man["snapshot_sha256"],
    "n_selectivity_targets": len(target_ids),
    "per_isoform": all_results,
    "pik3kgamma_prior_result": {
        "overlap_pct": gamma_json["overlap_pct_of_modeling_set"],
        "n_overlap": len(gamma_overlap),
    },
    "pik3kbeta_human_pdb_entries": 0,
    "pik3kbeta_note": "Zero human PIK3CB (P42338) PDB entries exist. Two mouse-ortholog "
                       "(Q8BTI9) entries (2Y3A, 4BFR) exist but are excluded as cross-species "
                       "evidence -- see docs/STRUCTURAL_EVIDENCE_ALL_ISOFORMS_REPORT.md.",
    "n_all_three_nonbeta_overlap": len(all_four_overlap),
    "n_any_nonbeta_overlap": len(any_isoform_overlap),
    "min_viable_for_split": MIN_VIABLE_FOR_SPLIT,
    "feasible_indicator_zero_fill_run": feasible_any,
    "feasible_full_coverage_run": feasible_all,
    "any_nonbeta_overlap_inchikeys": sorted(any_isoform_overlap),
    "all_three_nonbeta_overlap_inchikeys": sorted(all_four_overlap),
}
out_path = Path("docs/governance/STAGE_D_ALL_ISOFORMS_MATCHING_A4.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"\nWrote {out_path} (A4 not modified)")

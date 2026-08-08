"""GATE 3 — Re-analyze the ALREADY-COLLECTED 24- and 50-compound pose
data at the corrected (residue-level primary) interaction-fingerprint
granularity, per Part I/J of the validation-campaign mandate.

Does NOT perform new docking. Re-parses the already-saved pose PDBQT
files on disk (from commits eafe327/2f26c5c) and re-derives per-pose
interactions directly, then aggregates at residue level (marginalizing
over ligand atom identity) rather than approximating from the
already-aggregated atom-level JSON -- this avoids under-counting cases
where different atoms carry the same interaction in different,
non-overlapping poses.

Also applies the UNMAPPED_RESIDUE fix (Part J): a canonical position
with no corresponding residue in a given isoform is no longer silently
folded into LOST_AT_MAPPED_POSITION.

A4 is not touched.
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Documents/orthosteric/src")

import numpy as np
from scipy.spatial import cKDTree

from orthosteric.features._comparative_interaction_fingerprint import (
    CompoundIsoformResidueFingerprint,
    build_residue_level_comparative_fingerprint,
)
from orthosteric.features._docking_interaction_detector import (
    detect_all_interactions,
    parse_pdbqt_atoms,
    parse_pdbqt_multi_pose,
)
from orthosteric.features._interaction_occupancy import aggregate_residue_level_occupancy
from orthosteric.features._ligand_protonation import charged_atom_names_from_pose, protonate_ligand
from orthosteric.pocket._sequence_correspondence import build_correspondence_table

WORKDIR = Path("/home/ubuntu/docking_pilot")
RECEPTOR_DIR = WORKDIR / "receptors"

RECEPTOR_PDBQT_PATHS = {
    "PI3Kalpha": RECEPTOR_DIR / "8EXL_protein_only.pdbqt",
    "PI3Kbeta": RECEPTOR_DIR / "AF-P42338.pdbqt",
    "PI3Kgamma": RECEPTOR_DIR / "6AUD_protein_only.pdbqt",
    "PI3Kdelta": RECEPTOR_DIR / "6PYR_protein_only.pdbqt",
}
RECEPTOR_PDB_PATHS = {
    "PI3Kalpha": RECEPTOR_DIR / "8EXL.pdb",
    "PI3Kbeta": RECEPTOR_DIR / "AF-P42338.pdb",
    "PI3Kgamma": RECEPTOR_DIR / "6AUD.pdb",
    "PI3Kdelta": RECEPTOR_DIR / "6PYR.pdb",
}

print("=== GATE 3: residue-level re-analysis of already-collected pose data ===\n")
print("Rebuilding correspondence table (same as committed, verified in Gate 0)...")
correspondence_table = build_correspondence_table(RECEPTOR_PDB_PATHS, reference_isoform="PI3Kalpha")
print(f"  content_sha256: {correspondence_table.content_sha256()}\n")

receptor_atoms_cache = {iso: parse_pdbqt_atoms(p, is_ligand=False) for iso, p in RECEPTOR_PDBQT_PATHS.items()}
receptor_kdtree_cache = {
    iso: cKDTree(np.array([a.coord for a in atoms])) for iso, atoms in receptor_atoms_cache.items()
}


def kdtree_filter(iso, ligand_atoms, radius=12.0):
    tree = receptor_kdtree_cache[iso]
    protein_atoms = receptor_atoms_cache[iso]
    lig_coords = np.array([a.coord for a in ligand_atoms])
    hit_sets = tree.query_ball_point(lig_coords, r=radius)
    hit_indices = set()
    for hits in hit_sets:
        hit_indices.update(hits)
    keep_residues = {(protein_atoms[i].chain_id, protein_atoms[i].residue_seq) for i in hit_indices}
    return [pa for pa in protein_atoms if (pa.chain_id, pa.residue_seq) in keep_residues]


def reanalyze_dataset(pose_dir: Path, compound_selection_path: Path, label: str):
    print(f"\n--- {label} ({pose_dir}) ---")
    compounds = json.loads(compound_selection_path.read_text())
    stratum_by_id = {c["compound_id"]: c["stratum"] for c in compounds}
    protonation_cache = {}
    all_fingerprints: dict[str, dict[str, CompoundIsoformResidueFingerprint]] = defaultdict(dict)
    n_reparsed, n_missing = 0, 0

    t0 = time.time()
    for c in compounds:
        cid, smi = c["compound_id"], c["smiles"]
        if cid not in protonation_cache:
            protonation_cache[cid] = protonate_ligand(smi, ph=7.4)
        protonation = protonation_cache[cid]

        for iso in RECEPTOR_PDBQT_PATHS:
            pose_path = pose_dir / f"{cid}__{iso}.pdbqt"
            if not pose_path.exists():
                n_missing += 1
                continue
            poses = parse_pdbqt_multi_pose(pose_path, is_ligand=True)
            per_pose_interactions = []
            for pose_atoms in poses:
                protein_atoms = kdtree_filter(iso, pose_atoms)
                confirmed_charged = (
                    charged_atom_names_from_pose(protonation, pose_atoms) if protonation else frozenset()
                )
                meta = {"compound_id": cid, "isoform": iso, "receptor_id": iso, "docking_score": None}
                interactions = detect_all_interactions(
                    pose_atoms, protein_atoms, meta, frozenset(), confirmed_charged
                )
                per_pose_interactions.append(interactions)
            residue_occs = aggregate_residue_level_occupancy(per_pose_interactions)
            all_fingerprints[cid][iso] = CompoundIsoformResidueFingerprint(cid, iso, tuple(residue_occs))
            n_reparsed += 1

    elapsed = time.time() - t0
    print(f"  Re-parsed {n_reparsed} compound x isoform pose sets, {n_missing} missing, {elapsed:.1f}s")

    all_comparative = {}
    pattern_totals: dict[str, int] = defaultdict(int)
    for cid, fps_by_iso in all_fingerprints.items():
        records = build_residue_level_comparative_fingerprint(
            cid, fps_by_iso, correspondence_table=correspondence_table
        )
        all_comparative[cid] = [r.to_dict() for r in records]
        for r in records:
            pattern_totals[r.pattern.value] += 1

    print("  Residue-level cross-isoform pattern totals:")
    total_n = sum(pattern_totals.values())
    for pattern, count in sorted(pattern_totals.items(), key=lambda x: -x[1]):
        print(f"    {pattern}: {count} ({100*count/total_n:.1f}%)")

    # directional check by stratum, same as before, now at residue level
    n_af_per_compound: dict[str, list[int]] = defaultdict(list)
    n_of_per_compound: dict[str, list[int]] = defaultdict(list)
    for cid, records in all_comparative.items():
        stratum = stratum_by_id.get(cid, "unknown")
        n_af = sum(1 for r in records if r["pattern"] == "alpha_favored")
        n_of = sum(1 for r in records if r["pattern"] == "other_favored")
        n_af_per_compound[stratum].append(n_af)
        n_of_per_compound[stratum].append(n_of)

    print("\n  Directional check (residue-level): mean alpha-favored / other-favored per compound, by stratum:")
    net_by_stratum = {}
    for stratum in n_af_per_compound:
        mean_af = sum(n_af_per_compound[stratum]) / len(n_af_per_compound[stratum])
        mean_of = sum(n_of_per_compound[stratum]) / len(n_of_per_compound[stratum])
        net_by_stratum[stratum] = mean_af - mean_of
        print(f"    {stratum}: alpha_favored={mean_af:.2f} other_favored={mean_of:.2f} net={mean_af-mean_of:+.2f}")

    return {
        "label": label, "n_reparsed": n_reparsed, "n_missing": n_missing,
        "wall_time_s": elapsed, "pattern_totals": dict(pattern_totals),
        "pattern_totals_pct": {k: round(100*v/total_n, 1) for k, v in pattern_totals.items()},
        "alpha_favored_per_compound_by_stratum": {k: v for k, v in n_af_per_compound.items()},
        "other_favored_per_compound_by_stratum": {k: v for k, v in n_of_per_compound.items()},
        "net_by_stratum": net_by_stratum,
        "correspondence_table_sha256": correspondence_table.content_sha256(),
    }, all_comparative


results_24, comparative_24 = reanalyze_dataset(
    WORKDIR / "occupancy_poses",
    Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/production_pilot_compound_selection.json"),
    "24-compound (commit eafe327)",
)
results_50, comparative_50 = reanalyze_dataset(
    WORKDIR / "occupancy_poses_expanded",
    Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/expanded_pilot_compound_selection.json"),
    "50-compound (commit 2f26c5c)",
)

out_dir = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence")
(out_dir / "residue_level_comparative_24.json").write_text(json.dumps(comparative_24, indent=2))
(out_dir / "residue_level_comparative_50.json").write_text(json.dumps(comparative_50, indent=2))
summary_path = Path("/home/ubuntu/Documents/orthosteric/docs/governance/GATE3_RESIDUE_LEVEL_REANALYSIS.json")
summary_path.write_text(json.dumps({"24_compound": results_24, "50_compound": results_50}, indent=2))
print(f"\nWrote {summary_path}")
print(f"Wrote {out_dir / 'residue_level_comparative_24.json'}")
print(f"Wrote {out_dir / 'residue_level_comparative_50.json'}")

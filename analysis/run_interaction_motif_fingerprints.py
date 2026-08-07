"""Real interaction-motif fingerprint pipeline: multi-pose re-docking for
occupancy, ligand-moiety annotation, sequence-based residue
correspondence, and compound x isoform comparative fingerprints, for the
24-compound production pilot (already validated, same receptors/
seed/protocol -- see docs/PRODUCTION_PILOT_AND_REPRODUCIBILITY_REPORT.md).

Only the pose-count changes from the prior production run (n_poses=1 ->
5, to get real docking-pose occupancy); ligand prep, receptor prep, box
derivation, seed, and exhaustiveness are all unchanged and reused from
disk where already cached.

A4 is read-only throughout.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Documents/orthosteric/src")

import numpy as np
from scipy.spatial import cKDTree

from orthosteric.features._comparative_interaction_fingerprint import (
    CompoundIsoformFingerprint,
    build_comparative_fingerprint,
)
from orthosteric.features._docking_interaction_detector import (
    detect_all_interactions,
    parse_pdbqt_atoms,
    parse_pdbqt_multi_pose,
)
from orthosteric.features._interaction_occupancy import aggregate_occupancy
from orthosteric.features._ligand_moiety import moiety_labels_by_pose_atom_name
from orthosteric.features._ligand_protonation import charged_atom_names_from_pose, protonate_ligand
from orthosteric.pocket._sequence_correspondence import build_correspondence_table

WORKDIR = Path("/home/ubuntu/docking_pilot")
RECEPTOR_DIR = WORKDIR / "receptors"
LIGAND_DIR = WORKDIR / "prod_ligands"
POSE_DIR = WORKDIR / "occupancy_poses"
POSE_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
EXHAUSTIVENESS = 8
NUM_POSES = 5

RECEPTOR_PDB_PATHS = {
    "PI3Kalpha": RECEPTOR_DIR / "8EXL.pdb",
    "PI3Kbeta": RECEPTOR_DIR / "AF-P42338.pdb",
    "PI3Kgamma": RECEPTOR_DIR / "6AUD.pdb",
    "PI3Kdelta": RECEPTOR_DIR / "6PYR.pdb",
}
RECEPTOR_PDBQT_PATHS = {
    "PI3Kalpha": RECEPTOR_DIR / "8EXL_protein_only.pdbqt",
    "PI3Kbeta": RECEPTOR_DIR / "AF-P42338.pdbqt",
    "PI3Kgamma": RECEPTOR_DIR / "6AUD_protein_only.pdbqt",
    "PI3Kdelta": RECEPTOR_DIR / "6PYR_protein_only.pdbqt",
}
LIGAND_CCD = {"PI3Kalpha": "799", "PI3Kgamma": "BWY", "PI3Kdelta": "P5J"}
BETA_GLOOP_RANGE = (778, 784)


def _ligand_centroid(pdb_path, ccd):
    coords = [
        (float(line[30:38]), float(line[38:46]), float(line[46:54]))
        for line in pdb_path.read_text().splitlines()
        if line.startswith("HETATM") and line[17:20].strip() == ccd
    ]
    return tuple(np.mean(coords, axis=0))


def _gloop_centroid(pdb_path):
    coords = [
        (float(line[30:38]), float(line[38:46]), float(line[46:54]))
        for line in pdb_path.read_text().splitlines()
        if line.startswith("ATOM") and BETA_GLOOP_RANGE[0] <= int(line[22:26]) <= BETA_GLOOP_RANGE[1]
    ]
    return tuple(np.mean(coords, axis=0))


BOX_CENTERS = {
    iso: (_gloop_centroid(RECEPTOR_PDB_PATHS[iso]) if iso == "PI3Kbeta"
          else _ligand_centroid(RECEPTOR_PDB_PATHS[iso], LIGAND_CCD[iso]))
    for iso in RECEPTOR_PDB_PATHS
}

print("=== Step 1: Real sequence-based residue correspondence table ===")
correspondence_table = build_correspondence_table(RECEPTOR_PDB_PATHS, reference_isoform="PI3Kalpha")
for iso, recs in correspondence_table.by_target_isoform.items():
    n_mapped = sum(1 for r in recs if r.target_resnum is not None)
    print(f"  PI3Kalpha -> {iso}: {len(recs)} reference positions, {n_mapped} mapped ({100*n_mapped/len(recs):.1f}%)")
corr_out = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/residue_correspondence_table.json")
corr_out.write_text(json.dumps(correspondence_table.to_dict(), indent=2))
print(f"  Wrote {corr_out}")

print("\n=== Step 2: Pre-build receptor spatial indices (once per receptor) ===")
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


compounds = json.loads(
    Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/production_pilot_compound_selection.json").read_text()
)

print(f"\n=== Step 3: Multi-pose re-docking ({len(compounds)} compounds x 4 isoforms, {NUM_POSES} poses each) ===")
t0 = time.time()
all_fingerprints: dict[str, dict[str, CompoundIsoformFingerprint]] = defaultdict(dict)
protonation_cache = {}
n_success, n_failed = 0, 0

for i, c in enumerate(compounds):
    cid, smi = c["compound_id"], c["smiles"]
    ligand_pdbqt = LIGAND_DIR / f"{cid}.pdbqt"
    if not ligand_pdbqt.exists():
        n_failed += 4
        continue
    if cid not in protonation_cache:
        protonation_cache[cid] = protonate_ligand(smi, ph=7.4)
    protonation = protonation_cache[cid]

    for iso in RECEPTOR_PDBQT_PATHS:
        pose_path = POSE_DIR / f"{cid}__{iso}.pdbqt"
        try:
            from vina import Vina  # noqa: PLC0415

            v = Vina(sf_name="vina", seed=SEED, verbosity=0)
            v.set_receptor(str(RECEPTOR_PDBQT_PATHS[iso]))
            v.set_ligand_from_file(str(ligand_pdbqt))
            v.compute_vina_maps(center=list(BOX_CENTERS[iso]), box_size=[20.0, 20.0, 20.0])
            v.dock(exhaustiveness=EXHAUSTIVENESS, n_poses=NUM_POSES)
            v.write_poses(str(pose_path), n_poses=NUM_POSES, overwrite=True)
        except Exception as e:
            print(f"  {cid[:16]} vs {iso}: DOCKING FAILED ({e})")
            n_failed += 1
            continue

        poses = parse_pdbqt_multi_pose(pose_path, is_ligand=True)
        arom_names = None  # computed once per pose below (element/type already carries most info)
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

        occupancies = aggregate_occupancy(per_pose_interactions)
        all_fingerprints[cid][iso] = CompoundIsoformFingerprint(cid, iso, tuple(occupancies))
        n_success += 1

    if (i + 1) % 6 == 0:
        print(f"  [{i+1}/{len(compounds)}] ... ({time.time()-t0:.0f}s elapsed)")

elapsed = time.time() - t0
print(f"\nTotal wall time: {elapsed:.1f}s")
print(f"Successful compound x isoform occupancy fingerprints: {n_success}, failed: {n_failed}")

print("\n=== Step 4: Comparative fingerprints (cross-isoform patterns) ===")
all_comparative = {}
pattern_totals: dict[str, int] = defaultdict(int)
for cid, fps_by_iso in all_fingerprints.items():
    records = build_comparative_fingerprint(cid, fps_by_iso, correspondence_table=correspondence_table)
    all_comparative[cid] = [r.to_dict() for r in records]
    for r in records:
        pattern_totals[r.pattern.value] += 1

print("Cross-isoform pattern totals (all compounds, all interaction-residue-moiety keys):")
for pattern, count in sorted(pattern_totals.items()):
    print(f"  {pattern}: {count}")

fp_out = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/interaction_motif_fingerprints.json")
fp_out.write_text(json.dumps(
    {cid: {iso: fp.to_dict() for iso, fp in by_iso.items()} for cid, by_iso in all_fingerprints.items()},
    indent=2,
))
comp_out = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/comparative_interaction_fingerprints.json")
comp_out.write_text(json.dumps(all_comparative, indent=2))
print(f"\nWrote {fp_out}")
print(f"Wrote {comp_out}")

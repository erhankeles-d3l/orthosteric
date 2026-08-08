"""Dimension 3 -- Ligand redocking / interaction recovery (CORRECTED).

Two real methodological bugs from the first run, fixed here before any
conclusion is drawn:

1. Wrong "hinge" residue checked. 773 (mouse) / 779 (human) is the
   specificity-pocket Met (analogous to alpha's Met772), not the hinge.
   The correct hinge-equivalent position -- from this script's own
   correspondence data, and consistent with this project's established
   Val851(alpha)/Val828(delta)/Val882(gamma) hinge-anchor numbering
   pattern -- is 851 (mouse 4BFR) / 857 (human AF-P42338), a Ser.

2. Cross-frame RMSD is meaningless for the AF-P42338 case. AF's model
   coordinates live in an arbitrary frame with no shared reference to
   4BFR's crystallographic frame -- there is nothing to compute RMSD
   against. Fixed by (a) computing RMSD only for the 4BFR self-
   consistency check, where both poses share 4BFR's own frame, and
   (b) validating the AF-P42338 redocking by pocket-proximity (did the
   docked ligand centroid land near AF's own G-loop/pocket region, in
   AF's own frame) and interaction-based hinge recovery -- both
   frame-independent, which is what the pre-registered Dimension 3
   criteria actually require (hinge H-bond recovery, interaction-type
   overlap), not a cross-structure geometric RMSD.

Ligand: J82, verified SMILES from live RCSB CCD this session
(C[C@H]1Cc2ccccc2N1C(=O)CC3=NC(=CC(=O)N3)N4CCOCC4, C19H22N4O3, 26 heavy
atoms -- matches the direct count from the raw 4BFR HETATM records).

No selectivity labels, sealed-set data, or downstream results are
loaded anywhere in this script -- label-blind and outcome-blind per
the pre-registered admissibility criteria.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Documents/orthosteric/src")

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from scipy.optimize import linear_sum_assignment

from orthosteric.features._docking_interaction_detector import detect_hbonds, parse_pdbqt_atoms

RECEPTOR_DIR = Path("/home/ubuntu/docking_pilot/receptors")
BETA_REMEDIATION_DIR = Path("/home/ubuntu/docking_pilot/beta_remediation")
BETA_REMEDIATION_DIR.mkdir(exist_ok=True)

N_SEEDS = 5
EXHAUSTIVENESS = 8
RMSD_PASS_THRESHOLD = 2.0
POCKET_PROXIMITY_THRESHOLD_A = 8.0  # generous sanity-check radius, not a precision claim

J82_SMILES = "C[C@H]1Cc2ccccc2N1C(=O)CC3=NC(=CC(=O)N3)N4CCOCC4"

_AUTODOCK_TYPE_TO_ELEMENT = {
    "A": "C", "C": "C", "N": "N", "NA": "N", "OA": "O", "O": "O",
    "SA": "S", "S": "S", "HD": "H", "H": "H", "F": "F", "Cl": "Cl",
    "Br": "Br", "I": "I", "P": "P",
}


def crystal_reference_coords(pdb_path: Path, ccd: str, chain: str) -> tuple[np.ndarray, list[str]]:
    heavy = [
        line
        for line in pdb_path.read_text().splitlines()
        if line.startswith("HETATM")
        and line[17:20].strip() == ccd
        and line[21] == chain
        and line[76:78].strip() != "H"
    ]
    coords = np.array(
        [(float(line[30:38]), float(line[38:46]), float(line[46:54])) for line in heavy]
    )
    elements = [line[76:78].strip() for line in heavy]
    return coords, elements


def pose_coords(pose_path: Path) -> tuple[np.ndarray, list[str]]:
    atoms = parse_pdbqt_atoms(pose_path, is_ligand=True)
    kept = [
        (a.x, a.y, a.z, _AUTODOCK_TYPE_TO_ELEMENT[a.autodock_type])
        for a in atoms
        if a.autodock_type in _AUTODOCK_TYPE_TO_ELEMENT
        and _AUTODOCK_TYPE_TO_ELEMENT[a.autodock_type] != "H"
    ]
    coords = np.array([(x, y, z) for x, y, z, _ in kept])
    elements = [e for _, _, _, e in kept]
    return coords, elements


def same_element_rmsd(coords_a, elems_a, coords_b, elems_b):
    if len(elems_a) != len(elems_b):
        return None, f"heavy atom count mismatch: {len(elems_a)} vs {len(elems_b)}"
    total_sq, n = 0.0, 0
    for el in set(elems_a):
        idx_a = [i for i, e in enumerate(elems_a) if e == el]
        idx_b = [i for i, e in enumerate(elems_b) if e == el]
        if len(idx_a) != len(idx_b):
            return None, f"element count mismatch for {el}"
        c_a, c_b = coords_a[idx_a], coords_b[idx_b]
        cost = np.linalg.norm(c_a[:, None, :] - c_b[None, :, :], axis=2)
        r, c = linear_sum_assignment(cost)
        total_sq += float((cost[r, c] ** 2).sum())
        n += len(r)
    return (total_sq / n) ** 0.5, None


def prepare_ligand_pdbqt(smiles: str, out_prefix: Path, seed: int) -> Path | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    if AllChem.EmbedMolecule(mol, params) != 0:
        return None
    try:
        AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
    except Exception:
        pass
    sdf_path = out_prefix.with_suffix(".sdf")
    w = Chem.SDWriter(str(sdf_path))
    w.write(mol)
    w.close()
    pdbqt_path = out_prefix.with_suffix(".pdbqt")
    result = subprocess.run(
        [sys.executable, "/home/ubuntu/.local/bin/mk_prepare_ligand.py",
         "-i", str(sdf_path), "-o", str(pdbqt_path), "--rigid_macrocycles"],
        capture_output=True, text=True, timeout=60,
    )
    if not pdbqt_path.exists():
        print(f"    ligand prep failed: {result.stderr[:300]}")
        return None
    return pdbqt_path


def run_self_consistency(label, receptor_pdbqt, box_center, crystal_coords, crystal_elements, hinge_resnum):
    """4BFR-vs-itself: RMSD is valid here, same coordinate frame throughout."""
    print(f"\n--- {label} (self-consistency, RMSD valid: same frame) ---")
    seed_results = []
    for seed in range(1, N_SEEDS + 1):
        prefix = BETA_REMEDIATION_DIR / f"{label}_seed{seed}"
        ligand_pdbqt = prepare_ligand_pdbqt(J82_SMILES, prefix, seed=seed)
        if ligand_pdbqt is None:
            seed_results.append({"seed": seed, "error": "ligand_prep_failed"})
            continue
        n_heavy_ligand = sum(
            1 for line in ligand_pdbqt.read_text().splitlines()
            if line.startswith(("ATOM", "HETATM")) and line.split()[-1] != "HD"
        )
        if n_heavy_ligand != len(crystal_elements):
            seed_results.append({"seed": seed, "error": f"heavy atom mismatch: {n_heavy_ligand} vs {len(crystal_elements)}"})
            continue

        pose_path = prefix.with_name(f"{prefix.name}_pose.pdbqt")
        t0 = time.time()
        try:
            from vina import Vina  # noqa: PLC0415

            v = Vina(sf_name="vina", seed=seed, cpu=1, verbosity=0)
            v.set_receptor(str(receptor_pdbqt))
            v.set_ligand_from_file(str(ligand_pdbqt))
            v.compute_vina_maps(center=box_center, box_size=[20.0, 20.0, 20.0])
            v.dock(exhaustiveness=EXHAUSTIVENESS, n_poses=1)
            v.write_poses(str(pose_path), n_poses=1, overwrite=True)
            score = float(v.energies(n_poses=1)[0][0])
        except Exception as e:
            seed_results.append({"seed": seed, "error": f"docking_failed: {e}"})
            continue
        dock_time = time.time() - t0

        docked_coords, docked_elements = pose_coords(pose_path)
        rmsd, err = same_element_rmsd(crystal_coords, crystal_elements, docked_coords, docked_elements)

        hinge_hit = False
        if rmsd is not None:
            receptor_atoms = parse_pdbqt_atoms(receptor_pdbqt, is_ligand=False)
            nearby = [a for a in receptor_atoms if abs(a.residue_seq - hinge_resnum) <= 2]
            pose_atoms = parse_pdbqt_atoms(pose_path, is_ligand=True)
            hb = detect_hbonds(pose_atoms, nearby, {"compound_id": "J82", "isoform": label, "receptor_id": label})
            hinge_hit = any(h.residue_number == hinge_resnum for h in hb)

        seed_results.append({
            "seed": seed, "rmsd": round(rmsd, 3) if rmsd is not None else None,
            "rmsd_error": err, "score": score, "hinge_hbond_hit": hinge_hit,
            "dock_time_s": round(dock_time, 1),
        })
        if rmsd is not None:
            print(f"  seed {seed}: RMSD={rmsd:.3f} A, score={score:.2f}, hinge_hit={hinge_hit}")
        else:
            print(f"  seed {seed}: RMSD calc failed ({err}), score={score}")

    valid_rmsds = [r["rmsd"] for r in seed_results if r.get("rmsd") is not None]
    n_pass = sum(1 for r in valid_rmsds if r <= RMSD_PASS_THRESHOLD)
    n_hinge = sum(1 for r in seed_results if r.get("hinge_hbond_hit"))
    print(f"  Summary: {n_pass}/{len(valid_rmsds)} <=2.0A, hinge hits {n_hinge}/{len(seed_results)}")
    return {
        "label": label, "seed_results": seed_results, "n_valid_rmsd": len(valid_rmsds),
        "n_pass_2A": n_pass, "n_hinge_hits": n_hinge,
        "gate1_style_verdict": "PASS" if n_pass >= 3 else ("PARTIAL" if n_pass >= 2 else "FAIL"),
    }


def run_af_redocking(label, receptor_pdbqt, box_center, n_ligand_heavy_atoms, hinge_resnum):
    """AF-P42338: no shared coordinate frame with 4BFR exists, so
    cross-structure RMSD is not computed (would be meaningless). Instead:
    pocket-proximity sanity check (did the pose land near AF's own
    intended pocket region, in AF's own frame) + interaction-based hinge
    recovery (frame-independent)."""
    print(f"\n--- {label} (no cross-frame RMSD -- pocket-proximity + interaction-based validation) ---")
    seed_results = []
    for seed in range(1, N_SEEDS + 1):
        prefix = BETA_REMEDIATION_DIR / f"{label}_seed{seed}"
        ligand_pdbqt = prepare_ligand_pdbqt(J82_SMILES, prefix, seed=seed)
        if ligand_pdbqt is None:
            seed_results.append({"seed": seed, "error": "ligand_prep_failed"})
            continue
        n_heavy_ligand = sum(
            1 for line in ligand_pdbqt.read_text().splitlines()
            if line.startswith(("ATOM", "HETATM")) and line.split()[-1] != "HD"
        )
        if n_heavy_ligand != n_ligand_heavy_atoms:
            seed_results.append({"seed": seed, "error": f"heavy atom mismatch: {n_heavy_ligand} vs {n_ligand_heavy_atoms}"})
            continue

        pose_path = prefix.with_name(f"{prefix.name}_pose.pdbqt")
        t0 = time.time()
        try:
            from vina import Vina  # noqa: PLC0415

            v = Vina(sf_name="vina", seed=seed, cpu=1, verbosity=0)
            v.set_receptor(str(receptor_pdbqt))
            v.set_ligand_from_file(str(ligand_pdbqt))
            v.compute_vina_maps(center=box_center, box_size=[20.0, 20.0, 20.0])
            v.dock(exhaustiveness=EXHAUSTIVENESS, n_poses=1)
            v.write_poses(str(pose_path), n_poses=1, overwrite=True)
            score = float(v.energies(n_poses=1)[0][0])
        except Exception as e:
            seed_results.append({"seed": seed, "error": f"docking_failed: {e}"})
            continue
        dock_time = time.time() - t0

        pose_atoms = parse_pdbqt_atoms(pose_path, is_ligand=True)
        pose_centroid = np.mean([(a.x, a.y, a.z) for a in pose_atoms], axis=0)
        distance_from_box_center = float(np.linalg.norm(pose_centroid - np.array(box_center)))
        in_pocket = distance_from_box_center <= POCKET_PROXIMITY_THRESHOLD_A

        receptor_atoms = parse_pdbqt_atoms(receptor_pdbqt, is_ligand=False)
        nearby = [a for a in receptor_atoms if abs(a.residue_seq - hinge_resnum) <= 2]
        hb = detect_hbonds(pose_atoms, nearby, {"compound_id": "J82", "isoform": label, "receptor_id": label})
        hinge_hit = any(h.residue_number == hinge_resnum for h in hb)

        seed_results.append({
            "seed": seed, "score": score,
            "distance_from_box_center_a": round(distance_from_box_center, 2),
            "in_pocket_sanity_check": in_pocket, "hinge_hbond_hit": hinge_hit,
            "dock_time_s": round(dock_time, 1),
        })
        print(f"  seed {seed}: score={score:.2f}, centroid_dist_from_box={distance_from_box_center:.2f}A, "
              f"in_pocket={in_pocket}, hinge_hit={hinge_hit}")

    n_in_pocket = sum(1 for r in seed_results if r.get("in_pocket_sanity_check"))
    n_hinge = sum(1 for r in seed_results if r.get("hinge_hbond_hit"))
    print(f"  Summary: {n_in_pocket}/{N_SEEDS} landed in pocket region, hinge hits {n_hinge}/{N_SEEDS}")
    return {
        "label": label, "seed_results": seed_results,
        "n_in_pocket": n_in_pocket, "n_hinge_hits": n_hinge,
    }


print("=== Dimension 3 (corrected): J82 redocking -- 4BFR self-consistency + human AF-P42338 ===")

crystal_coords, crystal_elements = crystal_reference_coords(RECEPTOR_DIR / "4BFR_raw.pdb", "J82", "A")
print(f"Crystal reference (4BFR, chain A): {len(crystal_elements)} heavy atoms (expect 26)")

box_center_4bfr = crystal_coords.mean(axis=0).tolist()
result_4bfr = run_self_consistency(
    "4BFR_self", RECEPTOR_DIR / "4BFR_chainA_protein.pdbqt", box_center_4bfr,
    crystal_coords, crystal_elements, hinge_resnum=851,  # CORRECTED: mouse Ser851 = hinge-equivalent
)

# Human AF-P42338: box centered on the mapped pocket region (residues 777-937
# in human numbering, per the correspondence table), NOT the G-loop alone --
# the G-loop (778-784) and the hinge (857) are different parts of the same
# pocket, and centering only on the G-loop under-covers the hinge/adenine
# region a J82-sized ligand needs to reach.
af_pdb = RECEPTOR_DIR / "AF-P42338.pdb"
af_pdbqt = RECEPTOR_DIR / "AF-P42338.pdbqt"
pocket_human_resnums = {777, 778, 779, 785, 786, 787, 803, 805, 813, 839, 851, 852, 853, 854, 857, 926, 934, 936, 937}
pocket_coords = []
for line in af_pdb.read_text().splitlines():
    if line.startswith("ATOM"):
        resnum = int(line[22:26])
        if resnum in pocket_human_resnums:
            pocket_coords.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
box_center_af = np.array(pocket_coords).mean(axis=0).tolist()
print(f"\nAF-P42338 pocket-centroid box center (mapped 19-residue pocket, human numbering): {box_center_af}")

result_af = run_af_redocking(
    "AF_P42338", af_pdbqt, box_center_af, n_ligand_heavy_atoms=len(crystal_elements), hinge_resnum=857,
)

out = {
    "4bfr_self_consistency": result_4bfr, "af_p42338_redocking": result_af,
    "box_center_4bfr": box_center_4bfr, "box_center_af_pocket_centroid": box_center_af,
    "correction_note": (
        "First run of this script checked the wrong hinge residue (773/779, "
        "the specificity-pocket Met, not the hinge) and reported a "
        "cross-frame RMSD for AF-P42338 that is methodologically meaningless "
        "(AF and 4BFR share no common coordinate frame). Both fixed here: "
        "hinge corrected to 851 (mouse) / 857 (human); AF validated by "
        "pocket-proximity sanity check + frame-independent interaction "
        "detection instead of a meaningless cross-frame RMSD."
    ),
}
out_path = Path("/home/ubuntu/Documents/orthosteric/docs/governance/BETA_DIMENSION3_REDOCKING.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"\nWrote {out_path}")

"""GATE 1 remediation candidate -- 6XRL (PI3Kgamma, IPI-549/V7Y).

Per the mandate: "Find and pre-register a better experimental gamma
structure first... only if no adequate structure exists should modeled
completion be considered." 6XRL was identified via structural due
diligence (Trp812/Val882 -- the exact residues diagnosed as the cause of
6AUD's Gate-1 failure -- are fully modeled, full-occupancy in 6XRL,
confirmed by inspecting REMARK 465/480 directly, not assumed from
resolution alone). This script actually TESTS that plausibility via the
same Gate-1 redocking protocol already used for alpha/gamma/delta,
rather than treating structural completeness as sufficient on its own.

Ligand identity (V7Y) verified independently against the live RCSB CCD
this session (canonical stereo SMILES, InChIKey XUMALORDVCFWKV-IBGZPJMESA-N,
C30H24N8O2, 64 heavy atoms -- confirmed as IPI-549/eganelisib via
DrugBank cross-reference), not trusted from any prior label.
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

from orthosteric.features._docking_interaction_detector import parse_pdbqt_atoms

WORKDIR = Path("/home/ubuntu/docking_pilot")
RECEPTOR_DIR = WORKDIR / "receptors"
GATE1_DIR = WORKDIR / "gate1_redocking"
GATE1_DIR.mkdir(parents=True, exist_ok=True)

N_SEEDS = 5
EXHAUSTIVENESS = 8
RMSD_PASS_THRESHOLD = 2.0

_AUTODOCK_TYPE_TO_ELEMENT = {
    "A": "C",
    "C": "C",
    "N": "N",
    "NA": "N",
    "OA": "O",
    "O": "O",
    "SA": "S",
    "S": "S",
    "HD": "H",
    "H": "H",
    "F": "F",
    "Cl": "Cl",
    "Br": "Br",
    "I": "I",
    "P": "P",
}

CANDIDATE = {
    "pdb_id": "6XRL",
    "receptor_pdbqt": RECEPTOR_DIR / "6XRL_protein_only.pdbqt",
    "receptor_pdb": RECEPTOR_DIR / "6XRL_protein_only.pdb",
    "ligand_ccd": "V7Y",
    # Verified this session directly against the live RCSB CCD entry for
    # V7Y (canonical stereo SMILES, CACTVS 3.385) -- not carried over
    # from any prior session's memory of this compound.
    "smiles": "C[C@H](NC(=O)c1c(N)nn2cccnc12)C3=Cc4cccc(C#Cc5cnn(C)c5)c4C(=O)N3c6ccccc6",
    "hinge_residue": 882,  # same numbering convention as the existing 6AUD entry
}


def crystal_reference_coords_from_raw(pdb_path: Path, ccd: str) -> tuple[np.ndarray, list[str]]:
    """Extract heavy-atom coordinates for one HETATM residue.

    Filters hydrogens BEFORE any RDKit parsing, directly by element
    (PDB column 77-78, verified against the real file on disk this
    session). 6XRL's deposition includes explicit riding-hydrogen
    positions for the ligand (confirmed by direct inspection of the raw
    HETATM records -- unusual, but real). RDKit's MolFromPDBBlock
    removeHs=True did not reliably strip these when sanitize=False (no
    bond perception to rely on), so hydrogens are excluded here
    directly by element rather than trusted to a downstream flag.
    """
    heavy_atoms = [
        line
        for line in pdb_path.read_text().splitlines()
        if line.startswith("HETATM") and line[17:20].strip() == ccd and line[76:78].strip() != "H"
    ]
    coords = np.array(
        [(float(line[30:38]), float(line[38:46]), float(line[46:54])) for line in heavy_atoms]
    )
    elements = [line[76:78].strip() for line in heavy_atoms]
    return coords, elements


def pose_coords(pose_path: Path) -> tuple[np.ndarray, list[str]]:
    atoms = parse_pdbqt_atoms(pose_path, is_ligand=True)
    kept = [
        (a.x, a.y, a.z, _AUTODOCK_TYPE_TO_ELEMENT[a.autodock_type])
        for a in atoms
        if a.autodock_type in _AUTODOCK_TYPE_TO_ELEMENT
        and _AUTODOCK_TYPE_TO_ELEMENT[a.autodock_type] != "H"
    ]
    if not kept:
        return np.empty((0, 3)), []
    coords = np.array([(x, y, z) for x, y, z, _ in kept])
    elements = [e for _, _, _, e in kept]
    return coords, elements


def same_element_rmsd(
    coords_a: np.ndarray, elems_a: list[str], coords_b: np.ndarray, elems_b: list[str]
) -> tuple[float | None, str | None]:
    if len(elems_a) != len(elems_b):
        return None, f"total heavy-atom count mismatch: {len(elems_a)} vs {len(elems_b)}"
    total_sq, n = 0.0, 0
    for el in set(elems_a):
        idx_a = [i for i, e in enumerate(elems_a) if e == el]
        idx_b = [i for i, e in enumerate(elems_b) if e == el]
        if len(idx_a) != len(idx_b):
            return None, f"element count mismatch for {el}: {len(idx_a)} vs {len(idx_b)}"
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
        [
            sys.executable,
            "/home/ubuntu/.local/bin/mk_prepare_ligand.py",
            "-i",
            str(sdf_path),
            "-o",
            str(pdbqt_path),
            "--rigid_macrocycles",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if not pdbqt_path.exists():
        print(f"    ligand prep failed: {result.stderr[:300]}")
        return None
    return pdbqt_path


print("=== GATE 1 REMEDIATION CANDIDATE: 6XRL (PI3Kgamma / IPI-549) ===\n")

crystal_coords, crystal_elements = crystal_reference_coords_from_raw(
    CANDIDATE["receptor_pdb"].parent / "6XRL_raw.pdb", CANDIDATE["ligand_ccd"]
)
print(f"Crystal reference: {len(crystal_elements)} heavy atoms (expected 40 for C30H24N8O2)")
if len(crystal_elements) != 40:
    print(
        "  WARNING: heavy atom count does not match molecular formula -- investigate before proceeding"
    )
box_center = crystal_coords.mean(axis=0).tolist()
print(f"Box center (co-crystallized V7Y centroid): {box_center}")

seed_results = []
for seed in range(1, N_SEEDS + 1):
    prefix = GATE1_DIR / f"PI3Kgamma_6XRL_seed{seed}"
    ligand_pdbqt = prepare_ligand_pdbqt(CANDIDATE["smiles"], prefix, seed=seed)
    if ligand_pdbqt is None:
        seed_results.append({"seed": seed, "error": "ligand_prep_failed"})
        continue

    n_heavy_ligand = sum(
        1
        for line in ligand_pdbqt.read_text().splitlines()
        if line.startswith(("ATOM", "HETATM")) and line.split()[-1] != "HD"
    )
    if n_heavy_ligand != len(crystal_elements):
        seed_results.append(
            {
                "seed": seed,
                "error": f"heavy atom count mismatch even before docking: "
                f"{n_heavy_ligand} (ligand prep) vs {len(crystal_elements)} (crystal)",
            }
        )
        continue

    pose_path = prefix.with_name(f"{prefix.name}_pose.pdbqt")
    t0 = time.time()
    try:
        from vina import Vina  # noqa: PLC0415

        v = Vina(sf_name="vina", seed=seed, verbosity=0)
        v.set_receptor(str(CANDIDATE["receptor_pdbqt"]))
        v.set_ligand_from_file(str(ligand_pdbqt))
        v.compute_vina_maps(center=box_center, box_size=[20.0, 20.0, 20.0])
        v.dock(exhaustiveness=EXHAUSTIVENESS, n_poses=1)
        v.write_poses(str(pose_path), n_poses=1, overwrite=True)
        energies = v.energies(n_poses=1)
        score = float(energies[0][0]) if len(energies) else None
    except Exception as e:
        seed_results.append({"seed": seed, "error": f"docking_failed: {e}"})
        continue
    dock_time = time.time() - t0

    docked_coords, docked_elements = pose_coords(pose_path)
    rmsd, err = same_element_rmsd(crystal_coords, crystal_elements, docked_coords, docked_elements)
    seed_results.append(
        {
            "seed": seed,
            "rmsd": round(rmsd, 3) if rmsd is not None else None,
            "rmsd_error": err,
            "score": score,
            "dock_time_s": round(dock_time, 1),
        }
    )
    if rmsd is not None:
        print(f"  seed {seed}: RMSD={rmsd:.3f} A, score={score:.2f}, time={dock_time:.1f}s")
    else:
        print(f"  seed {seed}: RMSD calc failed ({err}), score={score}")

valid_rmsds = [r["rmsd"] for r in seed_results if r.get("rmsd") is not None]
n_pass = sum(1 for r in valid_rmsds if r <= RMSD_PASS_THRESHOLD)
report = {
    "pdb_id": "6XRL",
    "ligand_ccd": "V7Y",
    "ligand_common_name": "IPI-549 (eganelisib)",
    "resolution_a": 2.99,
    "specificity_pocket_completeness_check": (
        "Trp812 and Val882 -- the exact residues diagnosed as the cause of 6AUD's "
        "Gate-1 failure -- verified fully modeled, full-occupancy in 6XRL "
        "(absent from both REMARK 465 and REMARK 480 in the raw deposited PDB)."
    ),
    "seed_results": seed_results,
    "n_valid_rmsd": len(valid_rmsds),
    "best_rmsd": min(valid_rmsds) if valid_rmsds else None,
    "median_rmsd": float(np.median(valid_rmsds)) if valid_rmsds else None,
    "worst_rmsd": max(valid_rmsds) if valid_rmsds else None,
    "n_pass_2A": n_pass,
    "gate1_pose_criterion": "PASS" if n_pass >= 3 else "FAIL",
}
print(
    f"\nSummary: {n_pass}/{len(valid_rmsds)} valid runs <= 2.0 A -> {report['gate1_pose_criterion']}"
)

out_path = Path(
    "/home/ubuntu/Documents/orthosteric/docs/governance/GATE1_GAMMA_REMEDIATION_6XRL.json"
)
out_path.write_text(json.dumps(report, indent=2))
print(f"\nWrote {out_path}")

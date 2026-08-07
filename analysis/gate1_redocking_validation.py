"""GATE 1 — Redocking / self-docking validation.

Mandatory, blocking. For alpha/8EXL, gamma/6AUD, delta/6PYR: redock the
real co-crystallized reference ligand (identity independently verified
against the actual RCSB Chemical Component Dictionary this session --
not trusted from prior labels) back into its own receptor, using the
exact same production ligand-preparation and docking protocol already
used for all other compounds in this project.

RMSD method (documented, bounded engineering decision -- not the
project's own conventional bond-topology RMSD, chosen after two real
bugs surfaced while attempting that approach; see commit message):
same-element Hungarian (optimal linear-sum-assignment) matching of heavy
atoms directly in the fixed receptor coordinate frame -- valid because
the receptor never moves between the crystal structure and the docked
pose (no rigid-body alignment step needed, unlike comparing two
independently-solved structures). This is symmetry-aware for genuine
local chemical symmetry (equivalent atoms of the same element within
matching distance are optimally, not arbitrarily, assigned) but is
coarser than full bond-graph-aware RMSD for stereochemistry-sensitive
cases; noted as a limitation in the final report.

`--rigid_macrocycles` is passed to Meeko for the reference-ligand
preparation specifically: ligand 799 contains a fused 7-membered
benzoxazepine ring, and Meeko's default macrocycle ring-breaking
introduces G0/CG0 placeholder pseudo-atoms with no fixed 1:1 real-atom
correspondence, which is incompatible with the atom-count-matching this
gate depends on. This does not change production docking protocol
elsewhere in this project; it is scoped to this validation gate's
specific need to have both structures at a known, fixed heavy-atom count.
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
    "A": "C", "C": "C", "N": "N", "NA": "N", "OA": "O", "O": "O",
    "SA": "S", "S": "S", "HD": "H", "H": "H", "F": "F", "Cl": "Cl",
    "Br": "Br", "I": "I", "P": "P",
}

REFERENCE_COMPLEXES = {
    "PI3Kalpha": {
        "pdb_id": "8EXL", "receptor_pdbqt": RECEPTOR_DIR / "8EXL_protein_only.pdbqt",
        "receptor_pdb": RECEPTOR_DIR / "8EXL.pdb", "ligand_ccd": "799",
        "smiles": "Cc1nc(n(n1)C(C)C)c2cn3c(n2)-c4ccc(cc4OCC3)c5cnn(c5)C(C)(C)C(=O)N",
        "hinge_residue": 851,
    },
    "PI3Kgamma": {
        "pdb_id": "6AUD", "receptor_pdbqt": RECEPTOR_DIR / "6AUD_protein_only.pdbqt",
        "receptor_pdb": RECEPTOR_DIR / "6AUD.pdb", "ligand_ccd": "BWY",
        "smiles": "CC(C)n1c(ncn1)c2cn3c(n2)-c4cc(ccc4OCC3)[S@@](=O)C5CCN(CC5)C(C)(C)C",
        "hinge_residue": 882,
    },
    "PI3Kdelta": {
        "pdb_id": "6PYR", "receptor_pdbqt": RECEPTOR_DIR / "6PYR_protein_only.pdbqt",
        "receptor_pdb": RECEPTOR_DIR / "6PYR.pdb", "ligand_ccd": "P5J",
        "smiles": "Cc1ncc(cn1)c2ccn3c(n2)c(cn3)c4ccc5c(c4)[C@](C(=O)N5)(C)Cc6ccccc6",
        "hinge_residue": 828,
    },
}


def crystal_reference_coords(pdb_path: Path, ccd: str) -> tuple[np.ndarray, list[str]]:
    hetatm = [
        line for line in pdb_path.read_text().splitlines()
        if line.startswith("HETATM") and line[17:20].strip() == ccd
    ]
    block = "\n".join(hetatm) + "\nEND\n"
    mol = Chem.MolFromPDBBlock(block, sanitize=False, removeHs=True)
    if mol is None:
        return np.empty((0, 3)), []
    coords = mol.GetConformer().GetPositions()
    elements = [a.GetSymbol() for a in mol.GetAtoms()]
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
    """Optimal (Hungarian) same-element matching, no rigid-body alignment
    (both structures already share the receptor's fixed coordinate frame)."""
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
        [sys.executable, "/home/ubuntu/.local/bin/mk_prepare_ligand.py",
         "-i", str(sdf_path), "-o", str(pdbqt_path), "--rigid_macrocycles"],
        capture_output=True, text=True, timeout=60,
    )
    if not pdbqt_path.exists():
        print(f"    ligand prep failed: {result.stderr[:300]}")
        return None
    return pdbqt_path


print("=== GATE 1: Redocking / self-docking validation ===\n")
report = {}

for iso, cfg in REFERENCE_COMPLEXES.items():
    print(f"\n--- {iso} ({cfg['pdb_id']} / ligand {cfg['ligand_ccd']}) ---")

    crystal_coords, crystal_elements = crystal_reference_coords(cfg["receptor_pdb"], cfg["ligand_ccd"])
    if len(crystal_elements) == 0:
        print("  FAILED to extract crystal reference. Skipping.")
        report[iso] = {"error": "crystal_extraction_failed"}
        continue
    print(f"  Crystal reference: {len(crystal_elements)} heavy atoms")
    box_center = crystal_coords.mean(axis=0).tolist()

    seed_results = []
    for seed in range(1, N_SEEDS + 1):
        prefix = GATE1_DIR / f"{iso}_seed{seed}"
        ligand_pdbqt = prepare_ligand_pdbqt(cfg["smiles"], prefix, seed=seed)
        if ligand_pdbqt is None:
            seed_results.append({"seed": seed, "error": "ligand_prep_failed"})
            continue

        n_heavy_ligand = sum(
            1 for line in ligand_pdbqt.read_text().splitlines()
            if line.startswith(("ATOM", "HETATM")) and line.split()[-1] != "HD"
        )
        if n_heavy_ligand != len(crystal_elements):
            seed_results.append({
                "seed": seed,
                "error": f"heavy atom count mismatch even before docking: "
                         f"{n_heavy_ligand} (ligand prep) vs {len(crystal_elements)} (crystal)",
            })
            continue

        pose_path = prefix.with_name(f"{prefix.name}_pose.pdbqt")
        t0 = time.time()
        try:
            from vina import Vina  # noqa: PLC0415

            v = Vina(sf_name="vina", seed=seed, verbosity=0)
            v.set_receptor(str(cfg["receptor_pdbqt"]))
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
        seed_results.append({
            "seed": seed, "rmsd": round(rmsd, 3) if rmsd is not None else None,
            "rmsd_error": err, "score": score, "dock_time_s": round(dock_time, 1),
        })
        if rmsd is not None:
            print(f"  seed {seed}: RMSD={rmsd:.3f} A, score={score:.2f}, time={dock_time:.1f}s")
        else:
            print(f"  seed {seed}: RMSD calc failed ({err}), score={score}")

    valid_rmsds = [r["rmsd"] for r in seed_results if r.get("rmsd") is not None]
    n_pass = sum(1 for r in valid_rmsds if r <= RMSD_PASS_THRESHOLD)
    report[iso] = {
        "pdb_id": cfg["pdb_id"], "ligand_ccd": cfg["ligand_ccd"],
        "seed_results": seed_results, "n_valid_rmsd": len(valid_rmsds),
        "best_rmsd": min(valid_rmsds) if valid_rmsds else None,
        "median_rmsd": float(np.median(valid_rmsds)) if valid_rmsds else None,
        "worst_rmsd": max(valid_rmsds) if valid_rmsds else None,
        "n_pass_2A": n_pass,
        "gate1_pose_criterion": "PASS" if n_pass >= 3 else "FAIL",
    }
    print(f"  Summary: {n_pass}/{len(valid_rmsds)} valid runs <= 2.0 A "
          f"-> {report[iso]['gate1_pose_criterion']}")

out_path = Path("/home/ubuntu/Documents/orthosteric/docs/governance/GATE1_REDOCKING_VALIDATION.json")
out_path.write_text(json.dumps(report, indent=2))
print(f"\nWrote {out_path}")

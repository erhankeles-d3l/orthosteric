"""Stage B, Part 2 -- 6XRL production-path bridge + smoke test (SS0.6.4).

Gate 1 validated 6XRL via a standalone script docking ONLY the single
reference ligand (V7Y/IPI-549). This script re-docks the ACTUAL
50-compound corpus against 6XRL through the same production pattern
already used for alpha/gamma(6AUD)/delta/beta (mirroring
run_docking_pilot_four_isoform.py's dock() function), confirming
receptor prep, box derivation, and interaction detection all work
end-to-end at real corpus scale before any pilot work depends on it.

cpu=1 per process, per Rev. 5 SS4's explicit reproducibility requirement
(multi-threaded Vina introduces ~0.03 kcal/mol non-determinism,
documented earlier in this project) -- not carried over from the older
script, which did not set this explicitly; applied here going forward.
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

from orthosteric.features._docking_interaction_detector import (
    detect_hbonds,
    parse_pdbqt_atoms,
    parse_pdbqt_multi_pose,
)

WORKDIR = Path("/home/ubuntu/docking_pilot")
RECEPTOR_DIR = WORKDIR / "receptors"
BRIDGE_DIR = WORKDIR / "6xrl_bridge_poses"
BRIDGE_DIR.mkdir(exist_ok=True)

SEED = 42
EXHAUSTIVENESS = 8
NUM_MODES = 5
CPU = 1  # bit-exact, per Rev. 5 SS4

RECEPTOR_PDBQT = RECEPTOR_DIR / "6XRL_protein_only.pdbqt"
RAW_PDB = RECEPTOR_DIR / "6XRL_raw.pdb"


def v7y_box_center() -> list[float]:
    """Box center: co-crystallized V7Y centroid, same value already
    established and used in Gate 1 (GATE1_GAMMA_REMEDIATION_6XRL.json)."""
    heavy = [
        line
        for line in RAW_PDB.read_text().splitlines()
        if line.startswith("HETATM") and line[17:20].strip() == "V7Y" and line[76:78].strip() != "H"
    ]
    coords = np.array([(float(line[30:38]), float(line[38:46]), float(line[46:54])) for line in heavy])
    return coords.mean(axis=0).tolist()


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
        return None
    return pdbqt_path


print("=== Stage B Part 2: 6XRL production-path bridge (50-compound corpus) ===\n")
box_center = v7y_box_center()
print(f"Box center (V7Y centroid, matches Gate 1): {box_center}")

compounds = json.loads(
    Path(
        "/home/ubuntu/Documents/orthosteric/data/structural_evidence/expanded_pilot_compound_selection.json"
    ).read_text()
)
print(f"Corpus: {len(compounds)} compounds\n")

results = []
receptor_atoms_cache = parse_pdbqt_atoms(RECEPTOR_PDBQT, is_ligand=False)
t0 = time.time()
n_docked, n_failed = 0, 0

for i, c in enumerate(compounds):
    cid, smi = c["compound_id"], c["smiles"]
    prefix = BRIDGE_DIR / cid
    ligand_pdbqt = prepare_ligand_pdbqt(smi, prefix, seed=SEED)
    if ligand_pdbqt is None:
        n_failed += 1
        results.append({"compound_id": cid, "error": "ligand_prep_failed"})
        continue

    pose_path = prefix.with_name(f"{cid}_pose.pdbqt")
    try:
        from vina import Vina  # noqa: PLC0415

        v = Vina(sf_name="vina", seed=SEED, cpu=CPU, verbosity=0)
        v.set_receptor(str(RECEPTOR_PDBQT))
        v.set_ligand_from_file(str(ligand_pdbqt))
        v.compute_vina_maps(center=list(box_center), box_size=[20.0, 20.0, 20.0])
        v.dock(exhaustiveness=EXHAUSTIVENESS, n_poses=NUM_MODES)
        v.write_poses(str(pose_path), n_poses=NUM_MODES, overwrite=True)
        best_score = float(v.energies(n_poses=1)[0][0])
        n_docked += 1
        results.append({"compound_id": cid, "best_score": best_score, "pose_path": str(pose_path)})
    except Exception as e:
        n_failed += 1
        results.append({"compound_id": cid, "error": str(e)[:200]})

    if (i + 1) % 10 == 0:
        print(f"  {i + 1}/{len(compounds)} processed, {time.time() - t0:.1f}s elapsed")

elapsed = time.time() - t0
print(f"\nDocked {n_docked}/{len(compounds)}, {n_failed} failed, {elapsed:.1f}s total")

# Smoke test: run interaction detection on every successful pose set and
# confirm the hinge H-bond (Val882) recovery rate across the WHOLE corpus,
# not just the single Gate-1 reference ligand.
print("\n--- Interaction-detection smoke test ---")
hinge_hits, total_checked, detection_errors = 0, 0, 0
for r in results:
    if "pose_path" not in r:
        continue
    pose_path = Path(r["pose_path"])
    if not pose_path.exists():
        continue
    try:
        poses = parse_pdbqt_multi_pose(pose_path, is_ligand=True)
        best_pose = poses[0]
        nearby = [a for a in receptor_atoms_cache if abs(a.residue_seq - 882) <= 3]
        hb = detect_hbonds(
            best_pose,
            nearby,
            {"compound_id": r["compound_id"], "isoform": "PI3Kgamma", "receptor_id": "6XRL"},
        )
        total_checked += 1
        if any(h.residue_number == 882 for h in hb):
            hinge_hits += 1
    except Exception:
        detection_errors += 1

print(f"Interaction detection ran cleanly on {total_checked}/{n_docked} pose sets ({detection_errors} errors)")
print(
    f"Hinge H-bond (Val882) recovered in top pose: {hinge_hits}/{total_checked} "
    f"({100 * hinge_hits / max(total_checked, 1):.1f}%)"
)

summary = {
    "n_compounds": len(compounds),
    "n_docked": n_docked,
    "n_failed": n_failed,
    "wall_time_s": round(elapsed, 1),
    "box_center": box_center,
    "smoke_test": {
        "total_pose_sets_checked": total_checked,
        "detection_errors": detection_errors,
        "hinge_hbond_hits": hinge_hits,
        "hinge_hbond_hit_rate": round(hinge_hits / max(total_checked, 1), 4),
    },
    "failed_compounds": [r for r in results if "error" in r],
}
out_path = Path("/home/ubuntu/Documents/orthosteric/docs/governance/STAGE_B_6XRL_BRIDGE_SMOKE_TEST.json")
out_path.write_text(json.dumps(summary, indent=2))
print(f"\nWrote {out_path}")

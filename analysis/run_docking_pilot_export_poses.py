"""Rerun the four-isoform cross-docking pilot, this time exporting the
best-pose 3D coordinates (not just the score) for interaction-geometry
analysis.

Reuses the exact receptors/ligands/boxes/seed from
analysis/run_docking_pilot_four_isoform.py. A4 is read-only throughout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Documents/orthosteric/src")

WORKDIR = Path("/home/ubuntu/docking_pilot")
RECEPTOR_DIR = WORKDIR / "receptors"
LIGAND_DIR = WORKDIR / "ligands"
POSE_DIR = WORKDIR / "poses"
POSE_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
EXHAUSTIVENESS = 8
NUM_MODES = 5

BETA_GLOOP_RANGE = (778, 784)


def gloop_centroid(af_pdb: Path) -> tuple[float, float, float]:
    coords = []
    for line in af_pdb.read_text().splitlines():
        if line.startswith("ATOM"):
            resnum = int(line[22:26])
            if BETA_GLOOP_RANGE[0] <= resnum <= BETA_GLOOP_RANGE[1]:
                x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
                coords.append((x, y, z))
    n = len(coords)
    return (sum(c[0] for c in coords) / n, sum(c[1] for c in coords) / n, sum(c[2] for c in coords) / n)


def ligand_centroid(pdb_path: Path, ccd: str) -> tuple[float, float, float]:
    coords = []
    for line in pdb_path.read_text().splitlines():
        if line.startswith("HETATM") and line[17:20].strip() == ccd:
            x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
            coords.append((x, y, z))
    n = len(coords)
    return (sum(c[0] for c in coords) / n, sum(c[1] for c in coords) / n, sum(c[2] for c in coords) / n)


RECEPTORS = {
    "PI3Kalpha": {
        "pdbqt": RECEPTOR_DIR / "8EXL_protein_only.pdbqt",
        "protein_pdb": RECEPTOR_DIR / "8EXL_protein_only.pdb",
        "centroid": ligand_centroid(RECEPTOR_DIR / "8EXL.pdb", "799"),
        "receptor_id": "8EXL", "source_class": "experimental_receptor",
    },
    "PI3Kbeta": {
        "pdbqt": RECEPTOR_DIR / "AF-P42338.pdbqt",
        "protein_pdb": RECEPTOR_DIR / "AF-P42338.pdb",
        "centroid": gloop_centroid(RECEPTOR_DIR / "AF-P42338.pdb"),
        "receptor_id": "AF-P42338", "source_class": "alphafold_receptor",
    },
    "PI3Kgamma": {
        "pdbqt": RECEPTOR_DIR / "6AUD_protein_only.pdbqt",
        "protein_pdb": RECEPTOR_DIR / "6AUD_protein_only.pdb",
        "centroid": ligand_centroid(RECEPTOR_DIR / "6AUD.pdb", "BWY"),
        "receptor_id": "6AUD", "source_class": "experimental_receptor",
    },
    "PI3Kdelta": {
        "pdbqt": RECEPTOR_DIR / "6PYR_protein_only.pdbqt",
        "protein_pdb": RECEPTOR_DIR / "6PYR_protein_only.pdb",
        "centroid": ligand_centroid(RECEPTOR_DIR / "6PYR.pdb", "P5J"),
        "receptor_id": "6PYR", "source_class": "experimental_receptor",
    },
}

PILOT_LIGANDS = {
    "LY294002": "O=C1c2ccccc2Oc2cc(N3CCOCC3)ccc12",
    "Quercetin": "Oc1cc(O)c2c(=O)c(O)c(-c3ccc(O)c(O)c3)oc2c1",
    "Staurosporine_core": "CN[C@@H]1C[C@H]2O[C@@](C)([C@@H]1OC)n3c4ccccc4c5c6CNC(=O)c6c7c8ccccc8n2c7c35",
    "Simple_pyrimidine": "Cc1ccc(-c2nc(N)nc(N)n2)cc1",
    "Morpholino_quinazoline": "COc1cc2ncnc(N3CCOCC3)c2cc1OC",
}


def dock_and_export_pose(receptor_pdbqt, ligand_pdbqt, box_center, out_pose_path, box_size=(20.0, 20.0, 20.0)):
    from vina import Vina  # noqa: PLC0415

    v = Vina(sf_name="vina", seed=SEED, verbosity=0)
    v.set_receptor(str(receptor_pdbqt))
    v.set_ligand_from_file(str(ligand_pdbqt))
    v.compute_vina_maps(center=list(box_center), box_size=list(box_size))
    v.dock(exhaustiveness=EXHAUSTIVENESS, n_poses=NUM_MODES)
    energies = v.energies(n_poses=NUM_MODES)
    v.write_poses(str(out_pose_path), n_poses=1, overwrite=True)
    return float(energies[0][0])


manifest = {}
for cid, smi in PILOT_LIGANDS.items():
    ligand_pdbqt = LIGAND_DIR / f"{cid}.pdbqt"
    if not ligand_pdbqt.exists():
        print(f"  {cid}: ligand PDBQT missing, skip")
        continue
    for iso, r in RECEPTORS.items():
        pose_path = POSE_DIR / f"{cid}__{iso}.pdbqt"
        try:
            score = dock_and_export_pose(r["pdbqt"], ligand_pdbqt, r["centroid"], pose_path)
            print(f"  {cid} vs {iso}: score={score:.2f}, pose written to {pose_path.name}")
            manifest[f"{cid}__{iso}"] = {
                "compound_id": cid, "isoform": iso, "smiles": smi,
                "receptor_id": r["receptor_id"], "receptor_source_class": r["source_class"],
                "receptor_protein_pdb": str(r["protein_pdb"]),
                "pose_pdbqt": str(pose_path), "docking_score": score,
                "seed": SEED, "exhaustiveness": EXHAUSTIVENESS,
            }
        except Exception as e:
            print(f"  {cid} vs {iso}: FAILED ({e})")

manifest_path = POSE_DIR / "manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2))
print(f"\nWrote {manifest_path} ({len(manifest)} entries)")

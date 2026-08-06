"""Docking pilot: real receptor prep, ligand prep, and AutoDock Vina
docking for a small, chemically diverse compound set against real
experimental PIK3Kalpha/gamma/delta receptors.

Toolchain (installed this session, verified working):
  RDKit 2026.03.5 (ligand 3D embedding, protonation-neutral SMILES parse)
  Meeko 0.7.1 (receptor PDB->PDBQT via mk_prepare_receptor.py; ligand
    PDBQT via mk_prepare_ligand.py)
  AutoDock Vina 1.2.7 (python `vina` package, precompiled wheel)

Receptors (real, fetched RCSB PDB files, chosen for good resolution +
single clean co-crystallized ligand for box derivation):
  PI3Kalpha: 8EXL (1.989 A, ligand 799)
  PI3Kgamma: 6AUD (2.015 A, ligand BWY)
  PI3Kdelta: 6PYR (2.21 A, ligand P5J)
  PI3Kbeta:  NOT RUN this pilot -- no human PDB structure exists, and no
    AlphaFold-derived box definition has been resolved yet (no bound
    ligand to center a box on; would require a residue-based box from a
    conserved active-site UniProt annotation, not yet done). Explicitly
    recorded as DockingOutcome.NO_RECEPTOR_AVAILABLE, never silently
    skipped or fabricated with an arbitrary box.

Box derivation: the co-crystallized ligand's heavy-atom centroid -- a
real, defensible, non-arbitrary derivation (never an invented box),
recorded in DockingBox.derivation_method.

Scale: this is a PILOT (small compound set), not production. Per the
mandate: "First build a pilot... Then scale only after the pilot passes
QC." Production scaling is the explicit next step, not attempted here.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Documents/orthosteric/src")

from rdkit import Chem
from rdkit.Chem import AllChem

from orthosteric.data.sources.structural._docking_record import (
    DockingBox,
    DockingComplexRecord,
    DockingOutcome,
    ReceptorSourceClass,
)

WORKDIR = Path("/home/ubuntu/docking_pilot")
RECEPTOR_DIR = WORKDIR / "receptors"
LIGAND_DIR = WORKDIR / "ligands"
LIGAND_DIR.mkdir(parents=True, exist_ok=True)
RECEPTOR_DIR.mkdir(parents=True, exist_ok=True)

RECEPTORS = {
    "PI3Kalpha": {"pdb_id": "8EXL", "ligand_ccd": "799", "resolution": 1.989},
    "PI3Kgamma": {"pdb_id": "6AUD", "ligand_ccd": "BWY", "resolution": 2.015},
    "PI3Kdelta": {"pdb_id": "6PYR", "ligand_ccd": "P5J", "resolution": 2.21},
}

RETRIEVAL_TS = "2026-08-06T00:00:00Z"
SEED = 42
EXHAUSTIVENESS = 8
NUM_MODES = 5
PIPELINE_VERSION = "docking_pipeline_v1_vina1.2.7_meeko0.7.1"


def strip_receptor_and_get_ligand_centroid(
    pdb_id: str, ligand_ccd: str,
) -> tuple[Path, tuple[float, float, float]]:
    """Strip everything except the first protein chain's ATOM records
    (drop waters, ions, the co-crystallized ligand itself, alt confs B+),
    write a clean receptor PDB, and compute the ligand's heavy-atom
    centroid from the original file (before stripping it) for box
    derivation."""
    raw = (RECEPTOR_DIR / f"{pdb_id}.pdb").read_text().splitlines()
    protein_lines = []
    ligand_coords = []
    seen_chain = None
    for line in raw:
        if line.startswith(("ATOM", "HETATM")):
            record_name = line[17:20].strip()
            chain = line[21]
            altloc = line[16]
            if altloc not in (" ", "A"):
                continue
            if record_name == ligand_ccd:
                try:
                    x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
                    ligand_coords.append((x, y, z))
                except ValueError:
                    pass
                continue
            if line.startswith("ATOM"):
                if seen_chain is None:
                    seen_chain = chain
                if chain == seen_chain:
                    protein_lines.append(line)
    if not ligand_coords:
        raise ValueError(f"No {ligand_ccd} coordinates found in {pdb_id}")
    cx = sum(c[0] for c in ligand_coords) / len(ligand_coords)
    cy = sum(c[1] for c in ligand_coords) / len(ligand_coords)
    cz = sum(c[2] for c in ligand_coords) / len(ligand_coords)

    out_path = RECEPTOR_DIR / f"{pdb_id}_protein_only.pdb"
    out_path.write_text("\n".join(protein_lines) + "\nEND\n")
    return out_path, (cx, cy, cz)


def prepare_receptor_pdbqt(protein_pdb: Path) -> Path:
    out_pdbqt = protein_pdb.with_suffix(".pdbqt")
    result = subprocess.run(
        [sys.executable, "/home/ubuntu/.local/bin/mk_prepare_receptor.py",
         "--read_pdb", str(protein_pdb), "-o", str(protein_pdb.with_suffix("")),
         "-p", "-a", "--default_altloc", "A"],
        capture_output=True, text=True, timeout=120,
    )
    if not out_pdbqt.exists():
        raise RuntimeError(f"Receptor prep failed for {protein_pdb}: {result.stdout}\n{result.stderr}")
    return out_pdbqt


def prepare_ligand_pdbqt(smiles: str, compound_id: str) -> Path | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = SEED
    if AllChem.EmbedMolecule(mol, params) != 0:
        return None
    try:
        AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
    except Exception:
        pass
    sdf_path = LIGAND_DIR / f"{compound_id}.sdf"
    writer = Chem.SDWriter(str(sdf_path))
    writer.write(mol)
    writer.close()

    pdbqt_path = LIGAND_DIR / f"{compound_id}.pdbqt"
    result = subprocess.run(
        [sys.executable, "/home/ubuntu/.local/bin/mk_prepare_ligand.py",
         "-i", str(sdf_path), "-o", str(pdbqt_path)],
        capture_output=True, text=True, timeout=60,
    )
    if not pdbqt_path.exists():
        print(f"    ligand prep failed for {compound_id}: {result.stderr[:300]}")
        return None
    return pdbqt_path


def dock(receptor_pdbqt: Path, ligand_pdbqt: Path, box_center, box_size=(20.0, 20.0, 20.0)):
    from vina import Vina  # noqa: PLC0415

    v = Vina(sf_name="vina", seed=SEED, verbosity=0)
    v.set_receptor(str(receptor_pdbqt))
    v.set_ligand_from_file(str(ligand_pdbqt))
    v.compute_vina_maps(center=list(box_center), box_size=list(box_size))
    v.dock(exhaustiveness=EXHAUSTIVENESS, n_poses=NUM_MODES)
    energies = v.energies(n_poses=NUM_MODES)
    return energies


print("=== Receptor preparation ===")
receptor_info = {}
for iso, info in RECEPTORS.items():
    print(f"  {iso}: {info['pdb_id']} (ligand {info['ligand_ccd']}, {info['resolution']} A)")
    protein_pdb, centroid = strip_receptor_and_get_ligand_centroid(info["pdb_id"], info["ligand_ccd"])
    receptor_pdbqt = prepare_receptor_pdbqt(protein_pdb)
    print(f"    protein-only PDB: {protein_pdb.name}, PDBQT: {receptor_pdbqt.name}")
    print(f"    box centroid (from {info['ligand_ccd']}): {centroid}")
    receptor_info[iso] = {
        "pdb_id": info["pdb_id"], "pdbqt": receptor_pdbqt, "centroid": centroid,
        "resolution": info["resolution"], "ligand_ccd": info["ligand_ccd"],
    }

PILOT_LIGANDS = {
    "LY294002": "O=C1c2ccccc2Oc2cc(N3CCOCC3)ccc12",
    "Quercetin": "Oc1cc(O)c2c(=O)c(O)c(-c3ccc(O)c(O)c3)oc2c1",
    "Staurosporine_core": "CN[C@@H]1C[C@H]2O[C@@](C)([C@@H]1OC)n3c4ccccc4c5c6CNC(=O)c6c7c8ccccc8n2c7c35",
    "Simple_pyrimidine": "Cc1ccc(-c2nc(N)nc(N)n2)cc1",
    "Morpholino_quinazoline": "COc1cc2ncnc(N3CCOCC3)c2cc1OC",
}

print(f"\n=== Ligand preparation ({len(PILOT_LIGANDS)} compounds) ===")
prepared_ligands = {}
for cid, smi in PILOT_LIGANDS.items():
    path = prepare_ligand_pdbqt(smi, cid)
    status = "OK" if path else "FAILED"
    print(f"  {cid}: {status}")
    prepared_ligands[cid] = path

print(f"\n=== Docking ({sum(1 for p in prepared_ligands.values() if p)} ligands x {len(receptor_info)} receptors) ===")
records = []
t0 = time.time()
for cid, smi in PILOT_LIGANDS.items():
    ligand_pdbqt = prepared_ligands[cid]
    for iso, rinfo in receptor_info.items():
        if ligand_pdbqt is None:
            records.append(DockingComplexRecord(
                compound_id=cid, inchikey=None, isoform=iso,
                outcome=DockingOutcome.LIGAND_PREPARATION_FAILED,
                receptor_source_class=ReceptorSourceClass.EXPERIMENTAL_RECEPTOR,
                receptor_identifier=rinfo["pdb_id"], ligand_smiles=smi,
                pipeline_version=PIPELINE_VERSION, retrieval_timestamp=RETRIEVAL_TS,
                failure_reason="RDKit embedding or meeko ligand PDBQT prep failed",
            ))
            continue
        box = DockingBox(
            center_x=rinfo["centroid"][0], center_y=rinfo["centroid"][1], center_z=rinfo["centroid"][2],
            size_x=20.0, size_y=20.0, size_z=20.0,
            derivation_method=f"centroid_of_cocrystallized_ligand:{rinfo['ligand_ccd']}@{rinfo['pdb_id']}",
        )
        try:
            energies = dock(rinfo["pdbqt"], ligand_pdbqt, rinfo["centroid"])
            best_score = float(energies[0][0])
            print(f"  {cid} vs {iso} ({rinfo['pdb_id']}): score={best_score:.2f} kcal/mol")
            records.append(DockingComplexRecord(
                compound_id=cid, inchikey=None, isoform=iso,
                outcome=DockingOutcome.SUCCESS,
                receptor_source_class=ReceptorSourceClass.EXPERIMENTAL_RECEPTOR,
                receptor_identifier=rinfo["pdb_id"],
                receptor_preparation_software="meeko", receptor_preparation_version="0.7.1",
                ligand_smiles=smi,
                ligand_preparation_software="rdkit+meeko", ligand_preparation_version="2026.03.5+0.7.1",
                docking_engine="AutoDock Vina", docking_engine_version="1.2.7",
                docking_box=box, exhaustiveness=EXHAUSTIVENESS, num_modes=NUM_MODES, seed=SEED,
                pose_rank=1, docking_score=best_score,
                pipeline_version=PIPELINE_VERSION, retrieval_timestamp=RETRIEVAL_TS,
            ))
        except Exception as e:
            print(f"  {cid} vs {iso}: DOCKING FAILED ({e})")
            records.append(DockingComplexRecord(
                compound_id=cid, inchikey=None, isoform=iso,
                outcome=DockingOutcome.DOCKING_ENGINE_FAILED,
                receptor_source_class=ReceptorSourceClass.EXPERIMENTAL_RECEPTOR,
                receptor_identifier=rinfo["pdb_id"], ligand_smiles=smi,
                pipeline_version=PIPELINE_VERSION, retrieval_timestamp=RETRIEVAL_TS,
                failure_reason=str(e)[:300],
            ))

for cid, smi in PILOT_LIGANDS.items():
    records.append(DockingComplexRecord(
        compound_id=cid, inchikey=None, isoform="PI3Kbeta",
        outcome=DockingOutcome.NO_RECEPTOR_AVAILABLE, ligand_smiles=smi,
        pipeline_version=PIPELINE_VERSION, retrieval_timestamp=RETRIEVAL_TS,
        failure_reason="No human PIK3CB PDB structure; no AlphaFold-derived box resolved this pilot",
    ))

elapsed = time.time() - t0
print(f"\nTotal docking wall time: {elapsed:.1f}s")

out_path = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/docking_pilot_A4.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps([r.to_dict() for r in records], indent=2))
print(f"Wrote {out_path} ({len(records)} records)")

n_success = sum(1 for r in records if r.outcome == DockingOutcome.SUCCESS)
n_total = len(records)
print(f"\nSuccess rate: {n_success}/{n_total} ({100*n_success/n_total:.1f}%)")

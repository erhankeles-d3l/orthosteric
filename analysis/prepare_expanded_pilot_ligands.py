"""Prepare ligand PDBQTs for any of the 50 expanded-pilot compounds not
already on disk from the prior 24-compound run (23/24 overlap, so ~27
new ligands need preparation). Reuses the exact same RDKit ETKDG +
Meeko preparation already validated in prior sessions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Documents/orthosteric/src")

from rdkit import Chem
from rdkit.Chem import AllChem

LIGAND_DIR = Path("/home/ubuntu/docking_pilot/prod_ligands")
LIGAND_DIR.mkdir(parents=True, exist_ok=True)
SEED = 42


def prepare_ligand_pdbqt(smiles: str, compound_id: str) -> Path | None:
    pdbqt_path = LIGAND_DIR / f"{compound_id}.pdbqt"
    if pdbqt_path.exists():
        return pdbqt_path
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
    result = subprocess.run(
        [sys.executable, "/home/ubuntu/.local/bin/mk_prepare_ligand.py",
         "-i", str(sdf_path), "-o", str(pdbqt_path)],
        capture_output=True, text=True, timeout=60,
    )
    if not pdbqt_path.exists():
        print(f"    ligand prep failed for {compound_id}: {result.stderr[:200]}")
        return None
    return pdbqt_path


compounds = json.loads(
    Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/expanded_pilot_compound_selection.json").read_text()
)
n_already, n_new, n_failed = 0, 0, 0
for c in compounds:
    existing = LIGAND_DIR / f"{c['compound_id']}.pdbqt"
    was_there = existing.exists()
    result = prepare_ligand_pdbqt(c["smiles"], c["compound_id"])
    if was_there:
        n_already += 1
    elif result is not None:
        n_new += 1
    else:
        n_failed += 1
        print(f"  FAILED: {c['compound_id'][:16]}")

print(f"\nAlready prepared: {n_already}, newly prepared: {n_new}, failed: {n_failed}")
print(f"Total usable ligands: {n_already + n_new}/{len(compounds)}")

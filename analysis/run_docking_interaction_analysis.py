"""Run the atom-residue interaction detector on the real 20 docking poses
(4 isoforms x 5 pilot compounds), and build the comparative four-isoform
interaction report.

Reads: /home/ubuntu/docking_pilot/poses/manifest.json (produced by
analysis/run_docking_pilot_export_poses.py -- real Vina poses, real
receptors, same seed/box/protocol as the scored pilot).

A4 is not touched.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/Documents/orthosteric/src")

import numpy as np
from rdkit import Chem

from orthosteric.features._docking_interaction_detector import (
    content_sha256,
    detect_all_interactions,
    parse_pdbqt_atoms,
    residue_level_summary,
)

#: Spatial pre-filter radius (efficiency only, not a scientific threshold --
#: comfortably larger than every detector's own cutoff, e.g. PI_PI's 6.0 A
#: candidate search from the ligand ring centroid, so no true candidate is
#: ever excluded by this filter; it only skips protein atoms that are
#: geometrically impossible to satisfy any implemented interaction).
_POCKET_PREFILTER_RADIUS_A = 12.0


def filter_pocket_atoms(ligand_atoms, protein_atoms):
    """Restrict protein_atoms to those within _POCKET_PREFILTER_RADIUS_A of
    any ligand atom, at the RESIDUE level (whole residues kept together so
    ring/charged-group geometry within one residue is never split).
    Fully vectorized (no per-atom Python loop) for speed on whole-protein
    receptors (~8,000 atoms)."""
    lig_coords = np.array([a.coord for a in ligand_atoms])  # (L, 3)
    prot_coords = np.array([a.coord for a in protein_atoms])  # (P, 3)
    # (P, L) pairwise distances, then min over ligand axis -> (P,)
    diffs = prot_coords[:, None, :] - lig_coords[None, :, :]
    min_dist = np.min(np.linalg.norm(diffs, axis=2), axis=1)
    close_mask = min_dist <= _POCKET_PREFILTER_RADIUS_A
    keep_residues = {
        (pa.chain_id, pa.residue_seq) for pa, keep in zip(protein_atoms, close_mask, strict=True) if keep
    }
    return [pa for pa in protein_atoms if (pa.chain_id, pa.residue_seq) in keep_residues]


POSE_DIR = Path("/home/ubuntu/docking_pilot/poses")
manifest = json.loads((POSE_DIR / "manifest.json").read_text())

_ISOFORMS = ("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta")


def ligand_aromatic_atom_names(smiles: str, ligand_atoms) -> frozenset[str]:
    """Same technique as SCI1-004's _ligand_aromatic_atom_names: match
    RDKit's aromatic-atom indices to the PDBQT heavy-atom order."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return frozenset()
        arom_idx = frozenset(a.GetIdx() for a in mol.GetAtoms() if a.GetIsAromatic())
        if not arom_idx:
            return frozenset()
        heavy = [a for a in ligand_atoms if a.element != "H"]
        if len(heavy) != mol.GetNumHeavyAtoms():
            return frozenset()
        return frozenset(heavy[i].name for i in arom_idx if i < len(heavy))
    except Exception:
        return frozenset()


all_results = {}
per_compound_type_counts: dict[str, dict[str, dict[str, int]]] = defaultdict(dict)

print("=== Atom-residue interaction detection on 20 real docking poses ===\n")
for key, entry in manifest.items():
    cid, iso = entry["compound_id"], entry["isoform"]
    pose_path = Path(entry["pose_pdbqt"])
    receptor_pdb = Path(entry["receptor_protein_pdb"])
    receptor_pdbqt = receptor_pdb.with_suffix(".pdbqt")

    ligand_atoms = parse_pdbqt_atoms(pose_path, is_ligand=True)
    protein_atoms_full = parse_pdbqt_atoms(receptor_pdbqt, is_ligand=False)
    protein_atoms = filter_pocket_atoms(ligand_atoms, protein_atoms_full)
    arom_names = ligand_aromatic_atom_names(entry["smiles"], ligand_atoms)

    meta = {
        "compound_id": cid, "isoform": iso, "receptor_id": entry["receptor_id"],
        "docking_score": entry["docking_score"],
    }
    interactions = detect_all_interactions(ligand_atoms, protein_atoms, meta, arom_names)
    summary = residue_level_summary(interactions)

    type_counts: dict[str, int] = {}
    for it in interactions:
        type_counts[it.interaction_type.value] = type_counts.get(it.interaction_type.value, 0) + 1
    per_compound_type_counts[cid][iso] = type_counts

    all_results[key] = {
        "compound_id": cid, "isoform": iso, "receptor_id": entry["receptor_id"],
        "docking_score": entry["docking_score"],
        "n_ligand_atoms": len(ligand_atoms), "n_protein_pocket_atoms_considered": len(protein_atoms),
        "n_interactions": len(interactions), "interaction_type_counts": type_counts,
        "atom_level": [it.to_dict() for it in interactions],
        "residue_level": summary,
        "content_sha256": content_sha256(interactions),
    }
    print(f"{cid:<24} vs {iso:<12} (score={entry['docking_score']:+.2f}): "
          f"{len(interactions)} interactions {type_counts}")

out_path = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/docking_interaction_report_A4.json")
out_path.write_text(json.dumps(all_results, indent=2))
print(f"\nWrote {out_path}")

# ── Comparative four-isoform report per compound ────────────────────────────
print("\n=== Comparative interaction-type-count profile (per compound) ===")
comparative = {}
for cid, by_iso in per_compound_type_counts.items():
    print(f"\n{cid}:")
    all_types = sorted({t for counts in by_iso.values() for t in counts})
    row = {"header": ["isoform"] + all_types}
    rows = []
    for iso in _ISOFORMS:
        counts = by_iso.get(iso, {})
        rows.append([iso] + [counts.get(t, 0) for t in all_types])
        print(f"  {iso:<12} " + "  ".join(f"{t}={counts.get(t, 0)}" for t in all_types))
    comparative[cid] = {"types": all_types, "rows": rows}

    # conserved vs differential (interaction-type-count level, NOT residue-
    # correspondence level -- SCI1-003's alignment algorithm is RULE_MISSING,
    # so this is the honest level of comparison available)
    for t in all_types:
        counts_by_iso = {iso: by_iso.get(iso, {}).get(t, 0) for iso in _ISOFORMS}
        if len(set(counts_by_iso.values())) == 1:
            note = f"    {t}: CONSERVED across all 4 isoforms (count={next(iter(counts_by_iso.values()))})"
        else:
            note = f"    {t}: DIFFERENTIAL across isoforms {counts_by_iso}"
        print(note)

comp_out = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence/docking_interaction_comparative_A4.json")
comp_out.write_text(json.dumps(comparative, indent=2))
print(f"\nWrote {comp_out}")

# ── Aggregate summary ────────────────────────────────────────────────────────
print("\n=== Aggregate summary ===")
n_total = len(all_results)
n_with_interactions = sum(1 for r in all_results.values() if r["n_interactions"] > 0)
type_totals: dict[str, int] = defaultdict(int)
for r in all_results.values():
    for t, c in r["interaction_type_counts"].items():
        type_totals[t] += c
print(f"Total pose analyses: {n_total}")
print(f"Poses with >=1 detected interaction: {n_with_interactions}")
print(f"Total interactions by type (all 20 poses): {dict(type_totals)}")

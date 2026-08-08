"""Geometry-sensitivity ladder execution (Action 1).

Reparses the 296 already-saved pose files ONE more time -- this time
ALSO saving the raw per-pose interaction records to disk, so no further
reparse is ever needed for any future geometry-resolution experiment.
Computes Representation 3 at "intermediate" and "fine" ladder rungs
using the FROZEN, deterministic boundaries in
features._representation_2_3.frozen_ladder_boundaries (derived from the
already-committed coarse boundaries before this script was run -- see
that module's docstring for the exact rule).

Rep 2 and Rep 3 ("coarse") are NOT recomputed here -- they are
deterministic and already verified reproducible in the prior commit;
this script only adds the two new rungs.
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

from orthosteric.features._docking_interaction_detector import (
    detect_all_interactions,
    parse_pdbqt_atoms,
    parse_pdbqt_multi_pose,
)
from orthosteric.features._ligand_moiety import moiety_labels_by_pose_atom_name
from orthosteric.features._ligand_protonation import charged_atom_names_from_pose, protonate_ligand
from orthosteric.features._representation_2_3 import aggregate_representation_3_at_resolution
from orthosteric.pocket._sequence_correspondence import build_correspondence_table

WORKDIR = Path("/home/ubuntu/docking_pilot")
RECEPTOR_DIR = WORKDIR / "receptors"
OUT_DIR = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence")
RAW_DIR = OUT_DIR / "raw_interactions"
RAW_DIR.mkdir(exist_ok=True)

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

print("=== Geometry ladder: reparse once, save raw data, compute intermediate+fine rungs ===\n")
correspondence_table = build_correspondence_table(RECEPTOR_PDB_PATHS, reference_isoform="PI3Kalpha")
print(f"Correspondence table content_sha256: {correspondence_table.content_sha256()}\n")

CANONICAL_LOOKUP: dict[str, dict[tuple[str, int], int | None]] = {"PI3Kalpha": {}}
for iso in ("PI3Kbeta", "PI3Kgamma", "PI3Kdelta"):
    CANONICAL_LOOKUP[iso] = {
        ("A", rec.target_resnum): rec.reference_resnum
        for rec in correspondence_table.by_target_isoform.get(iso, [])
        if rec.target_resnum is not None
    }

receptor_atoms_cache = {iso: parse_pdbqt_atoms(p, is_ligand=False) for iso, p in RECEPTOR_PDBQT_PATHS.items()}
receptor_kdtree_cache = {
    iso: cKDTree(np.array([a.coord for a in atoms])) for iso, atoms in receptor_atoms_cache.items()
}


def alpha_canonical_lookup(iso: str, protein_atoms: list) -> dict[tuple[str, int], int | None]:
    if iso == "PI3Kalpha":
        return {("A", a.residue_seq): a.residue_seq for a in protein_atoms}
    return CANONICAL_LOOKUP[iso]


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


def process_dataset(pose_dir: Path, compound_selection_path: Path, label: str, raw_out_name: str):
    print(f"\n--- {label} ({pose_dir}) ---")
    compounds = json.loads(compound_selection_path.read_text())
    protonation_cache: dict[str, object] = {}

    rep3_intermediate: dict[str, dict[str, list]] = defaultdict(dict)
    rep3_fine: dict[str, dict[str, list]] = defaultdict(dict)
    raw_interactions: dict[str, dict[str, list]] = defaultdict(dict)  # for future reuse

    n_processed, n_missing = 0, 0
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
            moiety_map = None
            for pose_atoms in poses:
                protein_atoms = kdtree_filter(iso, pose_atoms)
                confirmed_charged = (
                    charged_atom_names_from_pose(protonation, pose_atoms) if protonation else frozenset()
                )
                if moiety_map is None:
                    moiety_map = moiety_labels_by_pose_atom_name(smi, pose_atoms, frozenset())
                meta = {"compound_id": cid, "isoform": iso, "receptor_id": iso, "docking_score": None}
                interactions = detect_all_interactions(
                    pose_atoms, protein_atoms, meta, frozenset(), confirmed_charged
                )
                per_pose_interactions.append(interactions)

            # Save raw interactions (compact: only fields the ladder/any
            # future geometry work needs) for reuse without reparsing.
            raw_interactions[cid][iso] = [[it.to_dict() for it in pose] for pose in per_pose_interactions]

            canon_lookup = alpha_canonical_lookup(iso, receptor_atoms_cache[iso])
            rep3_intermediate[cid][iso] = [
                r.to_dict()
                for r in aggregate_representation_3_at_resolution(
                    per_pose_interactions, moiety_map or {}, canon_lookup, "intermediate"
                )
            ]
            rep3_fine[cid][iso] = [
                r.to_dict()
                for r in aggregate_representation_3_at_resolution(
                    per_pose_interactions, moiety_map or {}, canon_lookup, "fine"
                )
            ]
            n_processed += 1

    elapsed = time.time() - t0
    print(f"  Processed {n_processed} compound x isoform pose sets, {n_missing} missing, {elapsed:.1f}s")

    (RAW_DIR / raw_out_name).write_text(json.dumps(raw_interactions))
    print(f"  Wrote raw interactions to {RAW_DIR / raw_out_name}")
    return rep3_intermediate, rep3_fine, {"n_processed": n_processed, "n_missing": n_missing, "wall_time_s": elapsed}


rep3_int_24, rep3_fine_24, summary_24 = process_dataset(
    WORKDIR / "occupancy_poses",
    Path(OUT_DIR / "production_pilot_compound_selection.json"),
    "24-compound",
    "raw_interactions_24.json",
)
rep3_int_50, rep3_fine_50, summary_50 = process_dataset(
    WORKDIR / "occupancy_poses_expanded",
    Path(OUT_DIR / "expanded_pilot_compound_selection.json"),
    "50-compound",
    "raw_interactions_50.json",
)

(OUT_DIR / "representation3_intermediate_24.json").write_text(json.dumps(rep3_int_24, indent=2))
(OUT_DIR / "representation3_fine_24.json").write_text(json.dumps(rep3_fine_24, indent=2))
(OUT_DIR / "representation3_intermediate_50.json").write_text(json.dumps(rep3_int_50, indent=2))
(OUT_DIR / "representation3_fine_50.json").write_text(json.dumps(rep3_fine_50, indent=2))

summary_path = Path(
    "/home/ubuntu/Documents/orthosteric/docs/governance/GEOMETRY_LADDER_REPARSE_SUMMARY.json"
)
summary_path.write_text(
    json.dumps(
        {
            "correspondence_table_sha256": correspondence_table.content_sha256(),
            "24_compound": summary_24,
            "50_compound": summary_50,
        },
        indent=2,
    )
)
print(f"\nWrote {summary_path}")
print("Wrote representation3_intermediate_{24,50}.json, representation3_fine_{24,50}.json")

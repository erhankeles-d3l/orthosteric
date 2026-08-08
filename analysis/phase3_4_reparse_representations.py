"""GATE 4 / Phase 3-4 -- Reparse ALREADY-SAVED poses (24- and 50-compound
sets) computing all four representations in one pass: atom-level
(unchanged, provenance), residue-level (Gate 3, unchanged), and the two
NEW representations from this mandate: Representation 2 (chemically
role-aware) and Representation 3 (role-aware + coarse geometry).

Does NOT perform new docking. Re-parses the same 296 already-saved pose
PDBQT files re-used in commit 7b3fe61's Gate-3 reanalysis, this time
also invoking the enriched detector (residue_hbond_role/
residue_charge_sign, additive fields from this mandate's Phase 1) and
the new Representation-2/3 aggregation.
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

from orthosteric.features._comparative_interaction_fingerprint import (
    CompoundIsoformResidueFingerprint,
    build_residue_level_comparative_fingerprint,
)
from orthosteric.features._docking_interaction_detector import (
    detect_all_interactions,
    parse_pdbqt_atoms,
    parse_pdbqt_multi_pose,
)
from orthosteric.features._interaction_occupancy import aggregate_residue_level_occupancy
from orthosteric.features._ligand_moiety import moiety_labels_by_pose_atom_name
from orthosteric.features._ligand_protonation import charged_atom_names_from_pose, protonate_ligand
from orthosteric.features._representation_2_3 import (
    aggregate_representation_2,
    aggregate_representation_3,
)
from orthosteric.pocket._sequence_correspondence import build_correspondence_table

WORKDIR = Path("/home/ubuntu/docking_pilot")
RECEPTOR_DIR = WORKDIR / "receptors"

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

print("=== Phase 3-4: reparse existing poses, build Rep 0/1/2/3 in one pass ===\n")
correspondence_table = build_correspondence_table(RECEPTOR_PDB_PATHS, reference_isoform="PI3Kalpha")
print(f"Correspondence table content_sha256: {correspondence_table.content_sha256()}\n")

# Reverse lookup per isoform: target residue_number -> canonical (alpha) position.
# Alpha itself is the identity mapping (it IS the reference).
CANONICAL_LOOKUP: dict[str, dict[tuple[str, int], int | None]] = {"PI3Kalpha": {}}
for iso in ("PI3Kbeta", "PI3Kgamma", "PI3Kdelta"):
    CANONICAL_LOOKUP[iso] = {
        ("A", rec.target_resnum): rec.reference_resnum
        for rec in correspondence_table.by_target_isoform.get(iso, [])
        if rec.target_resnum is not None
    }

receptor_atoms_cache = {
    iso: parse_pdbqt_atoms(p, is_ligand=False) for iso, p in RECEPTOR_PDBQT_PATHS.items()
}
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


def reanalyze_dataset(pose_dir: Path, compound_selection_path: Path, label: str):
    print(f"\n--- {label} ({pose_dir}) ---")
    compounds = json.loads(compound_selection_path.read_text())
    stratum_by_id = {c["compound_id"]: c["stratum"] for c in compounds}
    protonation_cache: dict[str, object] = {}
    moiety_cache: dict[str, dict] = {}  # compound_id -> {atom_name: LigandMoiety} (isoform-agnostic
    # for the same compound since ligand topology doesn't change across receptors)

    fp_by_compound: dict[str, dict[str, CompoundIsoformResidueFingerprint]] = defaultdict(dict)
    rep2_by_compound: dict[str, dict[str, list]] = defaultdict(dict)
    rep3_by_compound: dict[str, dict[str, list]] = defaultdict(dict)

    n_reparsed, n_missing = 0, 0
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
            moiety_map: dict[str, object] | None = None
            for pose_atoms in poses:
                protein_atoms = kdtree_filter(iso, pose_atoms)
                confirmed_charged = (
                    charged_atom_names_from_pose(protonation, pose_atoms)
                    if protonation
                    else frozenset()
                )
                if moiety_map is None:
                    # confirmed_charged_indices left empty (RDKit atom
                    # indices, not the pose-atom NAMES this script
                    # otherwise works with) -- phenolate/protonated-amine
                    # moieties simply fall through to their neutral SMARTS
                    # classification (hydroxyl/amine) for this pass, a
                    # documented simplification, not a fabricated charge
                    # state either way.
                    moiety_map = moiety_labels_by_pose_atom_name(smi, pose_atoms, frozenset())
                meta = {
                    "compound_id": cid,
                    "isoform": iso,
                    "receptor_id": iso,
                    "docking_score": None,
                }
                interactions = detect_all_interactions(
                    pose_atoms, protein_atoms, meta, frozenset(), confirmed_charged
                )
                per_pose_interactions.append(interactions)

            residue_occs = aggregate_residue_level_occupancy(per_pose_interactions)
            fp_by_compound[cid][iso] = CompoundIsoformResidueFingerprint(
                cid, iso, tuple(residue_occs)
            )

            canon_lookup = alpha_canonical_lookup(iso, receptor_atoms_cache[iso])
            rep2_by_compound[cid][iso] = aggregate_representation_2(
                per_pose_interactions, moiety_map or {}, canon_lookup
            )
            rep3_by_compound[cid][iso] = aggregate_representation_3(
                per_pose_interactions, moiety_map or {}, canon_lookup
            )
            n_reparsed += 1

    elapsed = time.time() - t0
    print(
        f"  Re-parsed {n_reparsed} compound x isoform pose sets, {n_missing} missing, {elapsed:.1f}s"
    )

    # Residue-level comparative (Gate 3, unchanged) -- kept for the SS13
    # rescue-analysis cross-reference.
    residue_comparative = {}
    for cid, fps_by_iso in fp_by_compound.items():
        records = build_residue_level_comparative_fingerprint(
            cid, fps_by_iso, correspondence_table=correspondence_table
        )
        residue_comparative[cid] = [r.to_dict() for r in records]

    rep2_serialized = {
        cid: {iso: [r.to_dict() for r in recs] for iso, recs in by_iso.items()}
        for cid, by_iso in rep2_by_compound.items()
    }
    rep3_serialized = {
        cid: {iso: [r.to_dict() for r in recs] for iso, recs in by_iso.items()}
        for cid, by_iso in rep3_by_compound.items()
    }

    return (
        {
            "label": label,
            "n_reparsed": n_reparsed,
            "n_missing": n_missing,
            "wall_time_s": elapsed,
            "correspondence_table_sha256": correspondence_table.content_sha256(),
            "stratum_by_id": stratum_by_id,
        },
        residue_comparative,
        rep2_serialized,
        rep3_serialized,
    )


summary_24, res_comp_24, rep2_24, rep3_24 = reanalyze_dataset(
    WORKDIR / "occupancy_poses",
    Path(
        "/home/ubuntu/Documents/orthosteric/data/structural_evidence/production_pilot_compound_selection.json"
    ),
    "24-compound (commit eafe327)",
)
summary_50, res_comp_50, rep2_50, rep3_50 = reanalyze_dataset(
    WORKDIR / "occupancy_poses_expanded",
    Path(
        "/home/ubuntu/Documents/orthosteric/data/structural_evidence/expanded_pilot_compound_selection.json"
    ),
    "50-compound (commit 2f26c5c)",
)

out_dir = Path("/home/ubuntu/Documents/orthosteric/data/structural_evidence")
(out_dir / "representation2_24.json").write_text(json.dumps(rep2_24, indent=2))
(out_dir / "representation2_50.json").write_text(json.dumps(rep2_50, indent=2))
(out_dir / "representation3_24.json").write_text(json.dumps(rep3_24, indent=2))
(out_dir / "representation3_50.json").write_text(json.dumps(rep3_50, indent=2))
(out_dir / "residue_level_comparative_24_rebuilt.json").write_text(
    json.dumps(res_comp_24, indent=2)
)
(out_dir / "residue_level_comparative_50_rebuilt.json").write_text(
    json.dumps(res_comp_50, indent=2)
)

summary_path = Path(
    "/home/ubuntu/Documents/orthosteric/docs/governance/PHASE3_4_REPARSE_SUMMARY.json"
)
summary_path.write_text(
    json.dumps({"24_compound": summary_24, "50_compound": summary_50}, indent=2)
)
print(f"\nWrote {summary_path}")
print(
    "Wrote representation2_24.json, representation2_50.json, representation3_24.json, representation3_50.json"
)

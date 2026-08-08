"""Tests for Representations 2 and 3 (features._representation_2_3).

Exit criteria (mandate SS9, SS12, SS16, SS19, SS27):
  (1) Residue identity and canonical position are NEVER part of the
      Representation-2/3 comparison key -- an Asp-mediated and a
      Glu-mediated instance of the SAME chemical role merge into ONE bin.
  (2) Multi-position pooling (SS16): two distinct canonical positions
      producing the same Representation-2 key within one pose count as
      occupancy 1 for that pose, not 2.
  (3) Multi-atom pooling: the same discipline one level up from the
      existing atom-level dedup, re-verified at this new aggregation
      level rather than assumed inherited.
  (4) Geometry bins do not alter Representation-2 occupancy semantics --
      Representation 2 itself carries no geometry.
  (5) Representation 3 adds geometry to the key without ever including
      canonical position or residue identity either.
  (6) An unresolved ligand moiety or unresolved residue functional role
      is excluded from the comparative bin, not forced in.
"""

from __future__ import annotations

from typing import Any

from orthosteric.features._docking_interaction_detector import (
    AtomResidueInteraction,
    InteractionGeometryStatus,
    InteractionType,
)
from orthosteric.features._ligand_moiety import LigandMoiety
from orthosteric.features._representation_2_3 import (
    GeometryBin,
    aggregate_representation_2,
    aggregate_representation_3,
    geometry_bin,
)


def _interaction(
    itype: Any,
    residue_number: int = 852,
    residue_name: str = "ASP",
    ligand_atom_name: str = "O1",
    **overrides: Any,
) -> AtomResidueInteraction:
    defaults: dict[str, Any] = {
        "interaction_type": itype,
        "status": InteractionGeometryStatus.OBSERVED,
        "ligand_atom_index": 0,
        "ligand_atom_name": ligand_atom_name,
        "ligand_atom_element": "O",
        "residue_number": residue_number,
        "residue_name": residue_name,
        "chain_id": "A",
        "protein_atom_name": "OD1",
        "distance_angstrom": 2.8,
        "angle_degrees": None,
        "plane_angle_degrees": None,
        "compound_id": "C1",
        "isoform": "PI3Kalpha",
        "receptor_id": "r1",
        "docking_score": None,
    }
    defaults.update(overrides)
    return AtomResidueInteraction(**defaults)


# ── SS9: residue identity / canonical position excluded from the key ─────


def test_asp_and_glu_same_role_merge_into_one_representation_2_bin() -> None:
    """The textbook example the mandate itself gives: alpha-Asp / delta-Glu,
    same H-bond-acceptor role, must be ONE Representation-2 bin, not two."""
    asp_record = _interaction(
        InteractionType.H_BOND,
        residue_number=852,
        residue_name="ASP",
        residue_hbond_role="acceptor",
        ligand_atom_name="N1",
    )
    glu_record = _interaction(
        InteractionType.H_BOND,
        residue_number=900,
        residue_name="GLU",
        residue_hbond_role="acceptor",
        ligand_atom_name="N1",
    )
    moiety_map = {"N1": LigandMoiety.AMINE_N}
    canon_lookup: dict[tuple[str, int], int | None] = {
        ("A", 852): 852,
        ("A", 900): 852,
    }  # both map to canonical 852

    rec_asp = aggregate_representation_2([[asp_record]], moiety_map, canon_lookup)
    rec_glu = aggregate_representation_2([[glu_record]], moiety_map, canon_lookup)
    assert len(rec_asp) == 1
    assert len(rec_glu) == 1
    assert (
        rec_asp[0].ligand_pharmacophore_class,
        rec_asp[0].residue_functional_class,
        rec_asp[0].interaction_type,
    ) == (
        rec_glu[0].ligand_pharmacophore_class,
        rec_glu[0].residue_functional_class,
        rec_glu[0].interaction_type,
    )
    # Both in the SAME pose set would collapse to one bin:
    combined = aggregate_representation_2([[asp_record, glu_record]], moiety_map, canon_lookup)
    assert len(combined) == 1
    assert combined[0].contributing_residue_identities == frozenset({"ASP852", "GLU900"})


def test_residue_identity_never_appears_in_the_key_tuple() -> None:
    record = _interaction(
        InteractionType.H_BOND, residue_hbond_role="acceptor", ligand_atom_name="N1"
    )
    moiety_map = {"N1": LigandMoiety.AMINE_N}
    results = aggregate_representation_2([[record]], moiety_map, {})
    result_dict = results[0].to_dict()
    assert "residue_identity" not in result_dict
    assert "canonical_position" not in result_dict
    # Identity/position are present ONLY as explicitly-named metadata fields:
    assert set(result_dict.keys()) == {
        "ligand_pharmacophore_class",
        "residue_functional_class",
        "interaction_type",
        "n_poses_evaluated",
        "n_poses_with_interaction",
        "occupancy",
        "occupancy_class",
        "contributing_residue_identities",
        "contributing_canonical_positions",
        "policy",
    }


# ── SS16: multi-position pooling within one pose ─────────────────────────


def test_two_canonical_positions_same_key_one_pose_counts_once() -> None:
    """Two DIFFERENT canonical positions (e.g. two different residues in
    the pocket both donating an H-bond) that land in the same
    Representation-2 key, within the SAME pose, must contribute
    occupancy 1 for that pose -- not 2."""
    donor_a = _interaction(
        InteractionType.H_BOND,
        residue_number=780,
        residue_name="SER",
        residue_hbond_role="donor",
        ligand_atom_name="O1",
    )
    donor_b = _interaction(
        InteractionType.H_BOND,
        residue_number=900,
        residue_name="THR",
        residue_hbond_role="donor",
        ligand_atom_name="O1",
    )
    moiety_map = {"O1": LigandMoiety.CARBONYL_O}
    # One pose containing BOTH interactions:
    results = aggregate_representation_2([[donor_a, donor_b]], moiety_map, {})
    assert len(results) == 1
    assert results[0].n_poses_evaluated == 1
    assert results[0].n_poses_with_interaction == 1  # NOT 2
    assert results[0].occupancy == 1.0


def test_multi_atom_pooling_reverified_at_representation_2_level() -> None:
    """Two different LIGAND atoms both hitting the same residue role in
    the same pose must also count once, not twice -- re-verifying the
    existing atom-level dedup discipline holds at this new aggregation
    level rather than assuming it is automatically inherited."""
    atom_a = _interaction(
        InteractionType.H_BOND,
        residue_number=852,
        residue_name="ASP",
        residue_hbond_role="acceptor",
        ligand_atom_name="N1",
    )
    atom_b = _interaction(
        InteractionType.H_BOND,
        residue_number=852,
        residue_name="ASP",
        residue_hbond_role="acceptor",
        ligand_atom_name="N2",
    )
    moiety_map = {"N1": LigandMoiety.AMINE_N, "N2": LigandMoiety.AMINE_N}
    results = aggregate_representation_2([[atom_a, atom_b]], moiety_map, {})
    assert len(results) == 1
    assert results[0].n_poses_with_interaction == 1


def test_pooling_across_multiple_poses_counts_correctly() -> None:
    """Across poses, occupancy must still reflect fraction-of-poses, even
    with multi-position pooling active within each individual pose."""
    donor_a = _interaction(
        InteractionType.H_BOND,
        residue_number=780,
        residue_hbond_role="donor",
        ligand_atom_name="O1",
    )
    donor_b = _interaction(
        InteractionType.H_BOND,
        residue_number=900,
        residue_hbond_role="donor",
        ligand_atom_name="O1",
    )
    moiety_map = {"O1": LigandMoiety.CARBONYL_O}
    # Pose 1: both fire (pools to 1). Pose 2: neither fires. Pose 3: only donor_a fires.
    per_pose = [[donor_a, donor_b], [], [donor_a]]
    results = aggregate_representation_2(per_pose, moiety_map, {})
    assert len(results) == 1
    assert results[0].n_poses_evaluated == 3
    assert results[0].n_poses_with_interaction == 2  # poses 1 and 3
    assert results[0].occupancy == 2 / 3


# ── Unresolved exclusion ──────────────────────────────────────────────────


def test_unresolved_ligand_moiety_excluded_not_forced() -> None:
    record = _interaction(
        InteractionType.H_BOND, residue_hbond_role="acceptor", ligand_atom_name="N1"
    )
    results = aggregate_representation_2([[record]], {}, {})  # empty moiety map -> unresolved
    assert results == []


def test_unresolved_residue_role_excluded_not_forced() -> None:
    record = _interaction(InteractionType.H_BOND, residue_hbond_role=None, ligand_atom_name="N1")
    moiety_map = {"N1": LigandMoiety.AMINE_N}
    results = aggregate_representation_2([[record]], moiety_map, {})
    assert results == []


# ── Representation 3: geometry bin added, key exclusions still hold ──────


def test_geometry_bin_h_bond_optimal_vs_weak() -> None:
    close = _interaction(InteractionType.H_BOND, residue_hbond_role="donor", distance_angstrom=2.7)
    far = _interaction(InteractionType.H_BOND, residue_hbond_role="donor", distance_angstrom=3.4)
    assert geometry_bin(close) == GeometryBin.H_BOND_OPTIMAL_OR_STRONG
    assert geometry_bin(far) == GeometryBin.H_BOND_LONG_OR_WEAK


def test_geometry_bin_uses_distance_only_for_aromatic_documented() -> None:
    """SS10.3: aromatic geometry binning is distance-only for the primary
    Representation-3 key -- plane_angle_degrees must not silently affect
    this bin (it is retained as separate metadata, tested elsewhere)."""
    close_parallel = _interaction(
        InteractionType.PI_PI, distance_angstrom=4.0, plane_angle_degrees=5.0
    )
    close_perpendicular = _interaction(
        InteractionType.PI_PI, distance_angstrom=4.0, plane_angle_degrees=85.0
    )
    assert geometry_bin(close_parallel) == geometry_bin(close_perpendicular)
    assert geometry_bin(close_parallel) == GeometryBin.AROMATIC_FAVORABLE_CLOSE


def test_representation_3_key_still_excludes_residue_identity_and_position() -> None:
    asp_record = _interaction(
        InteractionType.H_BOND,
        residue_number=852,
        residue_name="ASP",
        residue_hbond_role="acceptor",
        ligand_atom_name="N1",
        distance_angstrom=2.8,
    )
    glu_record = _interaction(
        InteractionType.H_BOND,
        residue_number=900,
        residue_name="GLU",
        residue_hbond_role="acceptor",
        ligand_atom_name="N1",
        distance_angstrom=2.9,
    )
    moiety_map = {"N1": LigandMoiety.AMINE_N}
    results = aggregate_representation_3([[asp_record, glu_record]], moiety_map, {})
    assert len(results) == 1  # same geometry bin -> still merges despite different residues


def test_representation_3_splits_when_geometry_bin_differs() -> None:
    """Unlike Representation 2, Representation 3 legitimately produces
    TWO bins when geometry differs, even for the same chemical role."""
    close = _interaction(
        InteractionType.H_BOND,
        residue_number=852,
        residue_hbond_role="acceptor",
        ligand_atom_name="N1",
        distance_angstrom=2.7,
    )
    far = _interaction(
        InteractionType.H_BOND,
        residue_number=852,
        residue_hbond_role="acceptor",
        ligand_atom_name="N1",
        distance_angstrom=3.4,
    )
    moiety_map = {"N1": LigandMoiety.AMINE_N}
    results = aggregate_representation_3([[close], [far]], moiety_map, {})
    assert len(results) == 2


def test_representation_3_no_key_field_named_residue_identity_or_position() -> None:
    record = _interaction(
        InteractionType.H_BOND, residue_hbond_role="acceptor", ligand_atom_name="N1"
    )
    moiety_map = {"N1": LigandMoiety.AMINE_N}
    result_dict = aggregate_representation_3([[record]], moiety_map, {})[0].to_dict()
    assert "residue_identity" not in result_dict
    assert "canonical_position" not in result_dict

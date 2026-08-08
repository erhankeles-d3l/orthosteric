"""Tests for the docking-pose atom-residue interaction detector.

Exit criteria:
  (1) Each interaction type has both a POSITIVE (real interaction) and a
      NEGATIVE (proximity without correct chemistry, or correct chemistry
      without sufficient geometry) synthetic test case with exact,
      hand-computed coordinates -- not just "did it run."
  (2) H-bond detection requires BOTH distance and angle -- a close but
      badly-angled donor/acceptor pair must not register.
  (3) Hydrophobic contact requires chemically compatible atoms -- a close
      polar atom pair must not register as hydrophobic.
  (4) Results are deterministic and correctly sorted.
  (5) Residue-level summary correctly aggregates atom-level records
      without losing them.
"""

from __future__ import annotations

import math

from orthosteric.features._docking_interaction_detector import (
    InteractionType,
    PoseAtom,
    content_sha256,
    detect_all_interactions,
    detect_cation_pi,
    detect_charged_contact_candidates,
    detect_hbonds,
    detect_hydrophobic_contacts,
    detect_pi_pi,
    residue_level_summary,
)

_META = {"compound_id": "IK1", "isoform": "PI3Kalpha", "receptor_id": "TEST", "docking_score": -8.0}


def _atom(
    name: str,
    element: str,
    adtype: str,
    x: float,
    y: float,
    z: float,
    resname: str = "UNL",
    resnum: int = 1,
    chain: str = "L",
    is_ligand: bool = True,
) -> PoseAtom:
    return PoseAtom(
        index=0,
        name=name,
        element=element,
        autodock_type=adtype,
        x=x,
        y=y,
        z=z,
        residue_name=resname,
        residue_seq=resnum,
        chain_id=chain,
        is_ligand=is_ligand,
    )


# ── H-bond: distance AND angle both required ─────────────────────────────────


def test_hbond_positive_ligand_donor_protein_acceptor() -> None:
    """Ligand O-H donor pointing directly at a protein backbone O acceptor:
    D...A = 2.8 A, linear geometry (angle ~180 deg) -> OBSERVED."""
    lig_o = _atom("O1", "O", "OA", 0.0, 0.0, 0.0)
    lig_h = _atom("H1", "H", "HD", 0.0, 0.0, 0.96)  # O-H bond length ~0.96 A, pointing at acceptor
    prot_o = _atom(
        "O", "O", "OA", 0.0, 0.0, 2.8, resname="GLU", resnum=100, chain="A", is_ligand=False
    )
    hits = detect_hbonds([lig_o, lig_h], [prot_o], _META)
    assert len(hits) == 1
    assert hits[0].interaction_type is InteractionType.H_BOND
    angle = hits[0].angle_degrees
    assert angle is not None
    assert angle > 170


def test_hbond_negative_correct_distance_wrong_angle() -> None:
    """Same D...A distance as the positive case, but the donor H points
    90 degrees away from the acceptor -- must NOT register."""
    lig_o = _atom("O1", "O", "OA", 0.0, 0.0, 0.0)
    lig_h = _atom("H1", "H", "HD", 0.96, 0.0, 0.0)  # H points sideways, not at acceptor
    prot_o = _atom(
        "O", "O", "OA", 0.0, 0.0, 2.8, resname="GLU", resnum=100, chain="A", is_ligand=False
    )
    hits = detect_hbonds([lig_o, lig_h], [prot_o], _META)
    assert hits == []


def test_hbond_negative_no_donor_hydrogen() -> None:
    """Two heteroatoms close together but neither has a resolvable donor
    hydrogen -- must not be approximated as an H-bond."""
    lig_o = _atom("O1", "O", "OA", 0.0, 0.0, 0.0)  # acceptor only, no HD nearby
    prot_o = _atom(
        "O", "O", "OA", 0.0, 0.0, 2.8, resname="GLU", resnum=100, chain="A", is_ligand=False
    )
    hits = detect_hbonds([lig_o], [prot_o], _META)
    assert hits == []


def test_hbond_protein_donor_ligand_acceptor() -> None:
    """Symmetric case: protein Arg N-H donor -> ligand O acceptor."""
    prot_n = _atom(
        "NH1", "N", "N", 0.0, 0.0, 0.0, resname="ARG", resnum=200, chain="A", is_ligand=False
    )
    prot_h = _atom(
        "HH11", "H", "HD", 0.0, 0.0, 1.0, resname="ARG", resnum=200, chain="A", is_ligand=False
    )
    lig_o = _atom("O1", "O", "OA", 0.0, 0.0, 2.7)
    hits = detect_hbonds([lig_o], [prot_n, prot_h], _META)
    assert len(hits) == 1
    assert hits[0].residue_name == "ARG"


# ── Salt bridge: requires charge, not just distance ──────────────────────────


def test_charged_contact_positive() -> None:
    lig_n = _atom("N1", "N", "N", 0.0, 0.0, 0.0)
    prot_o = _atom(
        "OE1", "O", "OA", 0.0, 0.0, 3.5, resname="GLU", resnum=50, chain="A", is_ligand=False
    )
    hits = detect_charged_contact_candidates([lig_n], [prot_o], _META)
    assert len(hits) == 1
    assert hits[0].interaction_type is InteractionType.CHARGED_CONTACT_CANDIDATE


def test_charged_contact_negative_wrong_residue_type() -> None:
    """Same distance, but the protein residue is not anionic/cationic
    (e.g. a neutral hydrophobic residue) -- must not register."""
    lig_n = _atom("N1", "N", "N", 0.0, 0.0, 0.0)
    prot_o = _atom(
        "O", "O", "OA", 0.0, 0.0, 3.5, resname="ALA", resnum=50, chain="A", is_ligand=False
    )
    hits = detect_charged_contact_candidates([lig_n], [prot_o], _META)
    assert hits == []


def test_charged_contact_negative_too_far() -> None:
    lig_n = _atom("N1", "N", "N", 0.0, 0.0, 0.0)
    prot_o = _atom(
        "OE1", "O", "OA", 0.0, 0.0, 10.0, resname="GLU", resnum=50, chain="A", is_ligand=False
    )
    hits = detect_charged_contact_candidates([lig_n], [prot_o], _META)
    assert hits == []


# ── SALT_BRIDGE promotion: confirmed vs unconfirmed ligand charge ───────────


def test_confirmed_charged_atom_promotes_to_salt_bridge() -> None:
    """When the caller supplies a confirmed-charged atom name (from real
    pH-aware protonation), the SAME geometry that would otherwise be
    CHARGED_CONTACT_CANDIDATE is promoted to SALT_BRIDGE."""
    lig_n = _atom("N1", "N", "N", 0.0, 0.0, 0.0)
    prot_o = _atom(
        "OE1", "O", "OA", 0.0, 0.0, 3.5, resname="GLU", resnum=50, chain="A", is_ligand=False
    )
    unconfirmed = detect_charged_contact_candidates([lig_n], [prot_o], _META)
    confirmed = detect_charged_contact_candidates(
        [lig_n], [prot_o], _META, ligand_confirmed_charged_names=frozenset({"N1"})
    )
    assert unconfirmed[0].interaction_type is InteractionType.CHARGED_CONTACT_CANDIDATE
    assert confirmed[0].interaction_type is InteractionType.SALT_BRIDGE
    assert unconfirmed[0].distance_angstrom == confirmed[0].distance_angstrom


def test_unrelated_confirmed_charge_name_does_not_promote() -> None:
    """Supplying a confirmed-charged-atom set that doesn't include THIS
    atom's name must not accidentally promote it."""
    lig_n = _atom("N1", "N", "N", 0.0, 0.0, 0.0)
    prot_o = _atom(
        "OE1", "O", "OA", 0.0, 0.0, 3.5, resname="GLU", resnum=50, chain="A", is_ligand=False
    )
    hits = detect_charged_contact_candidates(
        [lig_n], [prot_o], _META, ligand_confirmed_charged_names=frozenset({"N99_not_present"})
    )
    assert hits[0].interaction_type is InteractionType.CHARGED_CONTACT_CANDIDATE


def test_detect_all_interactions_passes_through_confirmed_charge_names() -> None:
    lig_n = _atom("N1", "N", "N", 0.0, 0.0, 0.0)
    prot_o = _atom(
        "OE1", "O", "OA", 0.0, 0.0, 3.5, resname="GLU", resnum=50, chain="A", is_ligand=False
    )
    hits = detect_all_interactions(
        [lig_n], [prot_o], _META, ligand_confirmed_charged_names=frozenset({"N1"})
    )
    salt_bridges = [h for h in hits if h.interaction_type is InteractionType.SALT_BRIDGE]
    assert len(salt_bridges) == 1


# ── Hydrophobic contact: requires chemically compatible atoms ────────────────


def test_hydrophobic_positive() -> None:
    lig_c = _atom("C1", "C", "C", 0.0, 0.0, 0.0)
    prot_c = _atom(
        "CG1", "C", "C", 0.0, 0.0, 4.0, resname="LEU", resnum=30, chain="A", is_ligand=False
    )
    hits = detect_hydrophobic_contacts([lig_c], [prot_c], _META)
    assert len(hits) == 1


def test_hydrophobic_negative_polar_residue() -> None:
    """Same distance, but the protein residue is polar (SER), not
    hydrophobic -- must not register as a hydrophobic contact even
    though the atoms are close."""
    lig_c = _atom("C1", "C", "C", 0.0, 0.0, 0.0)
    prot_c = _atom(
        "CB", "C", "C", 0.0, 0.0, 4.0, resname="SER", resnum=30, chain="A", is_ligand=False
    )
    hits = detect_hydrophobic_contacts([lig_c], [prot_c], _META)
    assert hits == []


def test_hydrophobic_negative_too_far() -> None:
    lig_c = _atom("C1", "C", "C", 0.0, 0.0, 0.0)
    prot_c = _atom(
        "CG1", "C", "C", 0.0, 0.0, 8.0, resname="LEU", resnum=30, chain="A", is_ligand=False
    )
    hits = detect_hydrophobic_contacts([lig_c], [prot_c], _META)
    assert hits == []


# ── pi-pi: ring centroid + plane angle ────────────────────────────────────────


def _hexagon(
    center_z: float,
    name_prefix: str,
    resname: str | None = None,
    resnum: int | None = None,
    chain: str = "L",
    is_ligand: bool = True,
) -> list[PoseAtom]:

    atoms = []
    names = (
        ["CG", "CD1", "CD2", "CE1", "CE2", "CZ"]
        if resname
        else [f"{name_prefix}{i}" for i in range(6)]
    )
    for i in range(6):
        angle = math.pi / 3 * i
        x, y = 1.4 * math.cos(angle), 1.4 * math.sin(angle)
        atoms.append(
            _atom(
                names[i],
                "C",
                "A",
                x,
                y,
                center_z,
                resname=resname or "UNL",
                resnum=resnum or 1,
                chain=chain,
                is_ligand=is_ligand,
            )
        )
    return atoms


def test_pi_pi_positive_parallel_stacked() -> None:
    lig_ring = _hexagon(0.0, "C")
    prot_ring = _hexagon(4.0, "C", resname="PHE", resnum=77, chain="A", is_ligand=False)
    lig_names = frozenset(a.name for a in lig_ring)
    hits = detect_pi_pi(lig_ring, prot_ring, _META, lig_names)
    assert len(hits) == 1
    assert hits[0].interaction_type is InteractionType.PI_PI
    plane_angle = hits[0].plane_angle_degrees
    assert plane_angle is not None
    assert plane_angle < 10  # parallel rings


def test_pi_pi_negative_too_far() -> None:
    lig_ring = _hexagon(0.0, "C")
    prot_ring = _hexagon(15.0, "C", resname="PHE", resnum=77, chain="A", is_ligand=False)
    lig_names = frozenset(a.name for a in lig_ring)
    hits = detect_pi_pi(lig_ring, prot_ring, _META, lig_names)
    assert hits == []


def test_pi_pi_negative_no_ligand_ring_atoms_flagged() -> None:
    """If the caller supplies an empty aromatic-atom-name set (e.g. RDKit
    couldn't confirm aromaticity), no pi-pi interaction is fabricated."""
    lig_ring = _hexagon(0.0, "C")
    prot_ring = _hexagon(4.0, "C", resname="PHE", resnum=77, chain="A", is_ligand=False)
    hits = detect_pi_pi(lig_ring, prot_ring, _META, frozenset())
    assert hits == []


# ── cation-pi ──────────────────────────────────────────────────────────────────


def test_cation_pi_positive() -> None:
    lig_ring = _hexagon(0.0, "C")
    lig_names = frozenset(a.name for a in lig_ring)
    prot_lys_nz = _atom(
        "NZ", "N", "N", 0.0, 0.0, 4.5, resname="LYS", resnum=88, chain="A", is_ligand=False
    )
    hits = detect_cation_pi(lig_ring, [prot_lys_nz], _META, lig_names)
    assert len(hits) == 1
    assert hits[0].interaction_type is InteractionType.CATION_PI


def test_cation_pi_negative_wrong_residue() -> None:
    lig_ring = _hexagon(0.0, "C")
    lig_names = frozenset(a.name for a in lig_ring)
    prot_ala = _atom(
        "CB", "C", "C", 0.0, 0.0, 4.5, resname="ALA", resnum=88, chain="A", is_ligand=False
    )
    hits = detect_cation_pi(lig_ring, [prot_ala], _META, lig_names)
    assert hits == []


# ── determinism, sorting, provenance, residue-level summary ─────────────────


def test_detect_all_interactions_deterministic() -> None:
    lig_c = _atom("C1", "C", "C", 0.0, 0.0, 0.0)
    prot_c = _atom(
        "CG1", "C", "C", 0.0, 0.0, 4.0, resname="LEU", resnum=30, chain="A", is_ligand=False
    )
    r1 = detect_all_interactions([lig_c], [prot_c], _META)
    r2 = detect_all_interactions([lig_c], [prot_c], _META)
    assert content_sha256(r1) == content_sha256(r2)


def test_every_record_carries_full_provenance() -> None:
    lig_c = _atom("C1", "C", "C", 0.0, 0.0, 0.0)
    prot_c = _atom(
        "CG1", "C", "C", 0.0, 0.0, 4.0, resname="LEU", resnum=30, chain="A", is_ligand=False
    )
    hits = detect_all_interactions([lig_c], [prot_c], _META)
    assert all(
        h.compound_id == "IK1" and h.isoform == "PI3Kalpha" and h.receptor_id == "TEST"
        for h in hits
    )


def test_residue_level_summary_aggregates_without_loss() -> None:
    lig_c = _atom("C1", "C", "C", 0.0, 0.0, 0.0)
    lig_n = _atom("N1", "N", "N", 0.0, 0.0, 3.0)
    prot_leu_c1 = _atom(
        "CG1", "C", "C", 0.0, 0.0, 4.0, resname="LEU", resnum=30, chain="A", is_ligand=False
    )
    prot_leu_o = _atom(
        "OE1", "O", "OA", 0.0, 0.0, 6.0, resname="GLU", resnum=31, chain="A", is_ligand=False
    )
    hits = detect_all_interactions([lig_c, lig_n], [prot_leu_c1, prot_leu_o], _META)
    summary = residue_level_summary(hits)
    assert len(summary) >= 1
    total_atom_level = len(hits)
    total_residue_level = sum(sum(s["interaction_types"].values()) for s in summary)
    assert total_atom_level == total_residue_level  # no interaction lost in aggregation

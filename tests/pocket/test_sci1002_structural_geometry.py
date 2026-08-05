"""SCI1-002 Milestone 3 tests: pocket geometry, rotamer states, SASA.

All BioPython structures are constructed synthetically using StructureBuilder
so no real PDB files are required. Values are explicitly fabricated for
testing; no scientific claim is implied (CLAUDE.md §1).

Exit criteria:
  Geometry
  (G1) PocketGeometry is frozen (immutable after creation).
  (G2) Centroid of Cα atoms is correct.
  (G3) Bounding box is correct.
  (G4) Max pairwise Cα distance is correct.
  (G5) Atoms missing from the BioPython structure are counted, not fabricated.
  (G6) volume_angstrom3 is always None (RULE_MISSING).
  (G7) content_sha256 is deterministic (same inputs -> same hash).
  (G8) Different structures produce different hashes.
  (G9) Coordinate rounding is deterministic (no float ordering surprises).

  Rotamer
  (R1) PocketRotamerStates is frozen.
  (R2) GLY/ALA correctly produce NOT_APPLICABLE.
  (R3) Residue absent from structure produces MISSING_RESIDUE.
  (R4) Residue present but side-chain atom missing produces MISSING_ATOMS.
  (R5) Fully-resolved GLN (affinity pocket) produces OBSERVED with chi1+chi2.
  (R6) rotamer_label is always None (RULE_MISSING).
  (R7) content_sha256 is deterministic.
  (R8) CHI_ATOM_NAMES covers all important pocket residue types.

  SASA
  (S1) PocketSASA is frozen.
  (S2) GOVERNED_PROBE_RADIUS_ANGSTROM == 1.4.
  (S3) Absent residue produces MISSING, not a computed value.
  (S4) Observed residue produces a non-negative absolute SASA.
  (S5) Relative SASA is in [0, ~2] for reasonable structures (allows >1 for
       loop conformations but not wildly negative).
  (S6) Probe-radius deviation from 1.4 Å is recorded in deviation_note.
  (S7) content_sha256 is deterministic.
  (S8) TIEN_2013_MAX_ASA has an entry for every standard amino acid.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from Bio.PDB.StructureBuilder import StructureBuilder

from orthosteric.pocket import (
    GOVERNED_PROBE_RADIUS_ANGSTROM,
    TIEN_2013_MAX_ASA,
    ConformationalState,
    ConstructClass,
    GeometryConfig,
    PocketResidue,
    PocketResidueSet,
    ResidueRecord,
    RotamerAvailability,
    SASAAvailability,
    SASAConfig,
    StructureRecord,
    SubRegion,
    compute_pocket_geometry,
    compute_pocket_rotamer_states,
    compute_pocket_sasa,
    make_record_id,
)
from orthosteric.pocket._pocket_definition import POCKET_DEFINITION_ALGORITHM_VERSION
from orthosteric.pocket._rotamer_state import CHI_ATOM_NAMES
from tests.pocket.test_structure_record import _construct, _ligand, _prov

PIPELINE_V = "sci1002_test_v1"

# ── Synthetic structure builders ──────────────────────────────────────────────


def _build_bio_structure(
    residues: list[dict[str, Any]],
    structure_id: str = "TEST",
) -> Any:
    """Build a minimal synthetic BioPython structure from a residue spec list.

    Each element of `residues` is:
        {
          "chain": str,          # chain id, e.g. "A"
          "seq": int,            # residue sequence number
          "ins": str,            # insertion code, e.g. " "
          "name": str,           # 3-letter residue name
          "atoms": {             # atom_name -> (x, y, z)
            "CA": (1.0, 2.0, 3.0),
            ...
          }
        }
    """
    sb = StructureBuilder()  # type: ignore[no-untyped-call]
    sb.init_structure(structure_id)
    sb.init_model(0)
    current_chain = None
    for rdata in residues:
        if rdata["chain"] != current_chain:
            sb.init_chain(rdata["chain"])
            current_chain = rdata["chain"]
        sb.init_residue(rdata["name"], " ", rdata["seq"], rdata["ins"])
        for atom_name, (x, y, z) in rdata["atoms"].items():
            sb.init_atom(
                atom_name,
                np.array([x, y, z], dtype=np.float64),
                1.0,
                1.0,
                " ",
                atom_name,
                None,
                element=atom_name[0],
            )
    return sb.get_structure()  # type: ignore[no-untyped-call]


def _make_structure_record(pdb_id: str = "TSST") -> StructureRecord:
    prov = _prov(pdb_id=pdb_id)
    construct = _construct()
    rid = make_record_id(prov, construct)
    return StructureRecord(
        record_id=rid,
        provenance=prov,
        construct=construct,
        conformational_state=ConformationalState.LIGAND_BOUND,
        chains=(),
        atp_site_ligands=(_ligand(),),
        all_ligands=(_ligand(),),
        preprocessing_flags=(),
    )


def _make_residue_record(
    chain_id: str = "A",
    residue_seq: int = 1,
    residue_name: str = "ALA",
    ins_code: str = " ",
) -> ResidueRecord:
    return ResidueRecord(
        chain_id=chain_id,
        residue_seq=residue_seq,
        insertion_code=ins_code,
        residue_name=residue_name,
        canonical_position=None,
        is_missing=False,
        missing_modelled=False,
    )


def _make_pocket_residue(
    rr: ResidueRecord,
    sub: SubRegion = SubRegion.AFFINITY_POCKET,
    structure_record_id: str = "test_id",
) -> PocketResidue:
    return PocketResidue(
        residue=rr,
        structure_record_id=structure_record_id,
        minimum_distance_to_ligand=2.8,
        sub_region=sub,
        observed_in_n_structures=2,
        correspondence_stable=True,
        present_with_propeller_ligand=False,
    )


def _make_pocket_set(
    pocket_residues: list[PocketResidue], structure_record_id: str = "test_id"
) -> PocketResidueSet:
    return PocketResidueSet(
        isoform="PI3Kalpha",
        construct_class=ConstructClass.P110_P85_HETERODIMER,
        contributing_record_ids=(structure_record_id,),
        n_contributing_structures=1,
        residues=tuple(pocket_residues),
        n_residues_total=len(pocket_residues),
        n_residues_correspondence_stable=len(pocket_residues),
        n_residues_propeller_only=0,
        cutoff_angstrom=5.0,
        algorithm_version=POCKET_DEFINITION_ALGORITHM_VERSION,
    )


# ── Geometry tests ─────────────────────────────────────────────────────────────


def _two_residue_structure() -> tuple[Any, StructureRecord, PocketResidueSet]:
    """Two GLN residues at known coordinates for geometric assertions."""
    bio = _build_bio_structure(
        [
            {
                "chain": "A",
                "seq": 1,
                "ins": " ",
                "name": "GLN",
                "atoms": {
                    "N": (0.0, 0.0, 0.0),
                    "CA": (1.0, 0.0, 0.0),
                    "C": (2.0, 0.0, 0.0),
                    "O": (2.5, 1.0, 0.0),
                    "CB": (1.0, 1.0, 0.0),
                    "CG": (1.0, 2.0, 0.0),
                    "CD": (1.0, 3.0, 0.0),
                    "OE1": (0.0, 3.5, 0.0),
                    "NE2": (2.0, 3.5, 0.0),
                },
            },
            {
                "chain": "A",
                "seq": 2,
                "ins": " ",
                "name": "GLN",
                "atoms": {
                    "N": (3.0, 0.0, 0.0),
                    "CA": (4.0, 0.0, 0.0),
                    "C": (5.0, 0.0, 0.0),
                    "O": (5.5, 1.0, 0.0),
                    "CB": (4.0, 1.0, 0.0),
                    "CG": (4.0, 2.0, 0.0),
                    "CD": (4.0, 3.0, 0.0),
                    "OE1": (3.0, 3.5, 0.0),
                    "NE2": (5.0, 3.5, 0.0),
                },
            },
        ]
    )
    rec = _make_structure_record()
    rr1 = _make_residue_record("A", 1, "GLN")
    rr2 = _make_residue_record("A", 2, "GLN")
    prs = _make_pocket_set(
        [
            _make_pocket_residue(rr1, structure_record_id=rec.record_id),
            _make_pocket_residue(rr2, structure_record_id=rec.record_id),
        ],
        structure_record_id=rec.record_id,
    )
    return bio, rec, prs


def test_g1_pocket_geometry_is_frozen() -> None:
    bio, rec, prs = _two_residue_structure()
    geom = compute_pocket_geometry(bio, rec, prs)
    with pytest.raises((AttributeError, TypeError)):
        geom.n_pocket_residues = 999  # type: ignore[misc]


def test_g2_centroid_ca_is_mean_of_ca_coordinates() -> None:
    bio, rec, prs = _two_residue_structure()
    geom = compute_pocket_geometry(bio, rec, prs)
    # CA at (1,0,0) and (4,0,0) -> centroid = (2.5, 0, 0)
    assert geom.centroid_ca is not None
    assert abs(geom.centroid_ca[0] - 2.5) < 0.01
    assert abs(geom.centroid_ca[1] - 0.0) < 0.01
    assert abs(geom.centroid_ca[2] - 0.0) < 0.01


def test_g3_bounding_box_is_correct() -> None:
    bio, rec, prs = _two_residue_structure()
    geom = compute_pocket_geometry(bio, rec, prs)
    assert geom.bounding_box_min_ca is not None
    assert geom.bounding_box_max_ca is not None
    # CA at x=1 and x=4; y=z=0 both
    assert abs(geom.bounding_box_min_ca[0] - 1.0) < 0.01
    assert abs(geom.bounding_box_max_ca[0] - 4.0) < 0.01


def test_g4_max_ca_pairwise_distance_is_correct() -> None:
    bio, rec, prs = _two_residue_structure()
    geom = compute_pocket_geometry(bio, rec, prs)
    # CA at (1,0,0) and (4,0,0) -> distance = 3.0 Å
    assert geom.max_ca_pairwise_distance_angstrom is not None
    assert abs(geom.max_ca_pairwise_distance_angstrom - 3.0) < 0.01


def test_g5_missing_residue_counted_not_fabricated() -> None:
    bio, rec, prs = _two_residue_structure()
    # Add a residue to the pocket set that is NOT in the structure
    extra_rr = _make_residue_record("A", 999, "GLN")
    extra_pr = _make_pocket_residue(extra_rr, structure_record_id=rec.record_id)
    big_prs = _make_pocket_set([*prs.residues, extra_pr], structure_record_id=rec.record_id)
    geom = compute_pocket_geometry(bio, rec, big_prs)
    assert geom.n_atoms_missing_coordinates == 1
    # Total atoms still only from the 2 present residues
    assert geom.n_calpha_atoms == 2


def test_g6_volume_is_always_none() -> None:
    bio, rec, prs = _two_residue_structure()
    geom = compute_pocket_geometry(bio, rec, prs)
    assert geom.volume_angstrom3 is None
    assert "RULE_MISSING" in geom.volume_governance_note


def test_g7_content_sha256_is_deterministic() -> None:
    bio, rec, prs = _two_residue_structure()
    g1 = compute_pocket_geometry(bio, rec, prs)
    g2 = compute_pocket_geometry(bio, rec, prs)
    assert g1.content_sha256() == g2.content_sha256()


def test_g8_different_structures_different_hash() -> None:
    bio1, rec1, prs1 = _two_residue_structure()
    # Shift one coordinate slightly
    bio2 = _build_bio_structure(
        [
            {
                "chain": "A",
                "seq": 1,
                "ins": " ",
                "name": "GLN",
                "atoms": {
                    "N": (0.0, 0.0, 0.0),
                    "CA": (1.5, 0.0, 0.0),
                    "C": (2.0, 0.0, 0.0),
                    "O": (2.5, 1.0, 0.0),
                    "CB": (1.5, 1.0, 0.0),
                    "CG": (1.5, 2.0, 0.0),
                    "CD": (1.5, 3.0, 0.0),
                    "OE1": (0.5, 3.5, 0.0),
                    "NE2": (2.5, 3.5, 0.0),
                },
            },
            {
                "chain": "A",
                "seq": 2,
                "ins": " ",
                "name": "GLN",
                "atoms": {
                    "N": (3.0, 0.0, 0.0),
                    "CA": (4.0, 0.0, 0.0),
                    "C": (5.0, 0.0, 0.0),
                    "O": (5.5, 1.0, 0.0),
                    "CB": (4.0, 1.0, 0.0),
                    "CG": (4.0, 2.0, 0.0),
                    "CD": (4.0, 3.0, 0.0),
                    "OE1": (3.0, 3.5, 0.0),
                    "NE2": (5.0, 3.5, 0.0),
                },
            },
        ]
    )
    rec2 = _make_structure_record("TSST")  # same record id
    rr1 = _make_residue_record("A", 1, "GLN")
    rr2 = _make_residue_record("A", 2, "GLN")
    prs2 = _make_pocket_set(
        [
            _make_pocket_residue(rr1, structure_record_id=rec2.record_id),
            _make_pocket_residue(rr2, structure_record_id=rec2.record_id),
        ],
        structure_record_id=rec2.record_id,
    )
    g1 = compute_pocket_geometry(bio1, rec1, prs1)
    g2 = compute_pocket_geometry(bio2, rec2, prs2)
    assert g1.content_sha256() != g2.content_sha256()


def test_g9_custom_rounding_config() -> None:
    bio, rec, prs = _two_residue_structure()
    g2 = compute_pocket_geometry(bio, rec, prs, config=GeometryConfig(coord_decimal_places=2))
    g4 = compute_pocket_geometry(bio, rec, prs, config=GeometryConfig(coord_decimal_places=4))
    # Same centroid value but different precision — the integer part is the same
    assert g2.centroid_ca is not None
    assert g4.centroid_ca is not None
    assert abs(g2.centroid_ca[0] - g4.centroid_ca[0]) < 0.01


# ── Rotamer tests ──────────────────────────────────────────────────────────────


def _gly_ala_gln_structure() -> tuple[Any, StructureRecord, PocketResidueSet]:
    """GLY (no chi), ALA (no chi), GLN (2 chi angles) in one pocket."""
    bio = _build_bio_structure(
        [
            {
                "chain": "A",
                "seq": 1,
                "ins": " ",
                "name": "GLY",
                "atoms": {
                    "N": (0.0, 0.0, 0.0),
                    "CA": (1.0, 0.0, 0.0),
                    "C": (2.0, 0.0, 0.0),
                    "O": (2.5, 1.0, 0.0),
                },
            },
            {
                "chain": "A",
                "seq": 2,
                "ins": " ",
                "name": "ALA",
                "atoms": {
                    "N": (3.0, 0.0, 0.0),
                    "CA": (4.0, 0.0, 0.0),
                    "C": (5.0, 0.0, 0.0),
                    "O": (5.5, 1.0, 0.0),
                    "CB": (4.0, 1.0, 0.0),
                },
            },
            # GLN with complete sidechain in a sensible geometry
            {
                "chain": "A",
                "seq": 3,
                "ins": " ",
                "name": "GLN",
                "atoms": {
                    "N": (6.0, 0.0, 0.0),
                    "CA": (7.0, 0.0, 0.0),
                    "C": (8.0, 0.0, 0.0),
                    "O": (8.5, 1.0, 0.0),
                    "CB": (7.0, 1.5, 0.0),
                    "CG": (7.0, 2.8, 0.5),
                    "CD": (7.0, 4.1, 0.0),
                    "OE1": (6.0, 4.5, 0.0),
                    "NE2": (8.0, 4.5, 0.0),
                },
            },
        ]
    )
    rec = _make_structure_record()
    residues = [
        _make_pocket_residue(
            _make_residue_record("A", 1, "GLY"), structure_record_id=rec.record_id
        ),
        _make_pocket_residue(
            _make_residue_record("A", 2, "ALA"), structure_record_id=rec.record_id
        ),
        _make_pocket_residue(
            _make_residue_record("A", 3, "GLN"), structure_record_id=rec.record_id
        ),
    ]
    prs = _make_pocket_set(residues, structure_record_id=rec.record_id)
    return bio, rec, prs


def test_r1_pocket_rotamer_states_is_frozen() -> None:
    bio, rec, prs = _gly_ala_gln_structure()
    states = compute_pocket_rotamer_states(bio, rec, prs)
    with pytest.raises((AttributeError, TypeError)):
        states.n_observed = 99  # type: ignore[misc]


def test_r2_gly_ala_produce_not_applicable() -> None:
    bio, rec, prs = _gly_ala_gln_structure()
    states = compute_pocket_rotamer_states(bio, rec, prs)
    by_name = {s.residue_name: s for s in states.residue_states}
    assert by_name["GLY"].availability == RotamerAvailability.NOT_APPLICABLE
    assert by_name["ALA"].availability == RotamerAvailability.NOT_APPLICABLE
    assert by_name["GLY"].n_chi_expected == 0
    assert by_name["GLY"].chi_angles == ()


def test_r3_missing_residue_produces_missing_residue_status() -> None:
    bio, rec, prs = _gly_ala_gln_structure()
    # Add a residue not in the structure
    extra_rr = _make_residue_record("A", 999, "MET")
    big_prs = _make_pocket_set(
        [*prs.residues, _make_pocket_residue(extra_rr, structure_record_id=rec.record_id)],
        structure_record_id=rec.record_id,
    )
    states = compute_pocket_rotamer_states(bio, rec, big_prs)
    met_state = next(s for s in states.residue_states if s.residue_name == "MET")
    assert met_state.availability == RotamerAvailability.MISSING_RESIDUE
    assert met_state.n_chi_computed == 0


def test_r4_missing_sidechain_atom_produces_missing_atoms() -> None:
    """CYS with only backbone — no SG -> MISSING_ATOMS."""
    bio = _build_bio_structure(
        [
            {
                "chain": "A",
                "seq": 1,
                "ins": " ",
                "name": "CYS",
                "atoms": {
                    "N": (0.0, 0.0, 0.0),
                    "CA": (1.0, 0.0, 0.0),
                    "C": (2.0, 0.0, 0.0),
                    "O": (2.5, 1.0, 0.0),
                    "CB": (1.0, 1.5, 0.0),
                },
            },  # SG is absent
        ]
    )
    rec = _make_structure_record()
    rr = _make_residue_record("A", 1, "CYS")
    prs = _make_pocket_set(
        [_make_pocket_residue(rr, structure_record_id=rec.record_id)],
        structure_record_id=rec.record_id,
    )
    states = compute_pocket_rotamer_states(bio, rec, prs)
    cys_state = states.residue_states[0]
    assert cys_state.availability == RotamerAvailability.MISSING_ATOMS
    assert "SG" in cys_state.missing_atom_names
    assert cys_state.n_chi_computed == 0


def test_r5_gln_with_complete_sidechain_is_observed_with_chi_angles() -> None:
    bio, rec, prs = _gly_ala_gln_structure()
    states = compute_pocket_rotamer_states(bio, rec, prs)
    by_name = {s.residue_name: s for s in states.residue_states}
    gln = by_name["GLN"]
    assert gln.availability == RotamerAvailability.OBSERVED
    assert gln.n_chi_expected == 3  # GLN has chi1, chi2, chi3
    # All 3 should be computed from the complete sidechain
    assert gln.n_chi_computed == 3
    # Values should be finite angles
    for chi in gln.chi_angles:
        assert -180.0 <= chi.value_degrees < 180.0
        assert chi.chi_index in (1, 2, 3)


def test_r6_rotamer_label_is_always_none() -> None:
    bio, rec, prs = _gly_ala_gln_structure()
    states = compute_pocket_rotamer_states(bio, rec, prs)
    for s in states.residue_states:
        assert s.rotamer_label is None
    assert "RULE_MISSING" in states.classification_governance_note


def test_r7_rotamer_content_sha_is_deterministic() -> None:
    bio, rec, prs = _gly_ala_gln_structure()
    s1 = compute_pocket_rotamer_states(bio, rec, prs)
    s2 = compute_pocket_rotamer_states(bio, rec, prs)
    assert s1.content_sha256() == s2.content_sha256()


def test_r8_chi_atom_names_covers_key_pocket_residues() -> None:
    """TRP (Trp780), MET (Met772), GLN (position-859) must be present —
    these are the Constitution §0.3 selectivity-determinant residues."""
    assert "TRP" in CHI_ATOM_NAMES
    assert "MET" in CHI_ATOM_NAMES
    assert "GLN" in CHI_ATOM_NAMES
    # And common pocket contacts
    for aa in ("ARG", "ASP", "GLU", "HIS", "ILE", "LEU", "LYS", "PHE", "SER", "THR", "TYR", "VAL"):
        assert aa in CHI_ATOM_NAMES, f"{aa} missing from CHI_ATOM_NAMES"


# ── SASA tests ────────────────────────────────────────────────────────────────


def _single_gly_structure() -> tuple[Any, StructureRecord, PocketResidueSet]:
    """Single GLY for basic SASA tests."""
    bio = _build_bio_structure(
        [
            {
                "chain": "A",
                "seq": 1,
                "ins": " ",
                "name": "GLY",
                "atoms": {
                    "N": (0.0, 0.0, 0.0),
                    "CA": (1.5, 0.0, 0.0),
                    "C": (2.5, 1.0, 0.0),
                    "O": (2.5, 2.0, 0.0),
                },
            },
        ]
    )
    rec = _make_structure_record()
    rr = _make_residue_record("A", 1, "GLY")
    prs = _make_pocket_set(
        [_make_pocket_residue(rr, structure_record_id=rec.record_id)],
        structure_record_id=rec.record_id,
    )
    return bio, rec, prs


def test_s1_pocket_sasa_is_frozen() -> None:
    bio, rec, prs = _single_gly_structure()
    sasa = compute_pocket_sasa(bio, rec, prs)
    with pytest.raises((AttributeError, TypeError)):
        sasa.n_observed = 99  # type: ignore[misc]


def test_s2_governed_probe_radius_is_1_4() -> None:
    assert GOVERNED_PROBE_RADIUS_ANGSTROM == 1.4


def test_s3_absent_residue_is_missing_not_computed() -> None:
    bio, rec, prs = _single_gly_structure()
    # Add an absent residue
    extra_rr = _make_residue_record("A", 999, "ALA")
    big_prs = _make_pocket_set(
        [*prs.residues, _make_pocket_residue(extra_rr, structure_record_id=rec.record_id)],
        structure_record_id=rec.record_id,
    )
    sasa = compute_pocket_sasa(bio, rec, big_prs)
    missing = [r for r in sasa.residue_sasas if r.availability == SASAAvailability.MISSING]
    assert len(missing) == 1
    assert missing[0].absolute_sasa_angstrom2 is None


def test_s4_observed_residue_has_non_negative_sasa() -> None:
    bio, rec, prs = _single_gly_structure()
    sasa = compute_pocket_sasa(bio, rec, prs)
    assert sasa.n_observed == 1
    gly = sasa.residue_sasas[0]
    assert gly.availability == SASAAvailability.OBSERVED
    assert gly.absolute_sasa_angstrom2 is not None
    assert gly.absolute_sasa_angstrom2 >= 0.0


def test_s5_relative_sasa_is_reasonable() -> None:
    """relative_sasa = absolute / TIEN_2013 reference. For an isolated
    residue in solvent, it can exceed 1.0 slightly but should not be
    wildly negative or astronomically large."""
    bio, rec, prs = _single_gly_structure()
    sasa = compute_pocket_sasa(bio, rec, prs)
    gly = sasa.residue_sasas[0]
    assert gly.relative_sasa is not None
    assert gly.relative_sasa >= 0.0
    assert gly.relative_sasa < 3.0  # isolated residue should be < ~3x reference


def test_s6_probe_radius_deviation_recorded() -> None:
    bio, rec, prs = _single_gly_structure()
    # Use a non-standard probe radius
    config = SASAConfig(probe_radius_angstrom=1.2, n_sphere_points=50)
    sasa = compute_pocket_sasa(bio, rec, prs, config=config)
    assert sasa.probe_radius_angstrom == 1.2
    assert "PROBE_RADIUS_DEVIATION" in sasa.probe_radius_deviation_note


def test_s6b_standard_probe_no_deviation_note() -> None:
    bio, rec, prs = _single_gly_structure()
    sasa = compute_pocket_sasa(bio, rec, prs)
    assert sasa.probe_radius_deviation_note == ""


def test_s7_sasa_content_sha_is_deterministic() -> None:
    bio, rec, prs = _single_gly_structure()
    s1 = compute_pocket_sasa(bio, rec, prs)
    s2 = compute_pocket_sasa(bio, rec, prs)
    assert s1.content_sha256() == s2.content_sha256()


def test_s8_tien_2013_has_all_standard_amino_acids() -> None:
    """TIEN_2013_MAX_ASA must cover all 20 standard amino acids so that
    relative SASA is computable for any pocket residue."""
    standard_aa = {
        "ALA",
        "ARG",
        "ASN",
        "ASP",
        "CYS",
        "GLN",
        "GLU",
        "GLY",
        "HIS",
        "ILE",
        "LEU",
        "LYS",
        "MET",
        "PHE",
        "PRO",
        "SER",
        "THR",
        "TRP",
        "TYR",
        "VAL",
    }
    missing = standard_aa - set(TIEN_2013_MAX_ASA.keys())
    assert not missing, f"TIEN_2013_MAX_ASA missing entries for: {sorted(missing)}"
    for aa, max_asa in TIEN_2013_MAX_ASA.items():
        assert max_asa > 0, f"TIEN_2013_MAX_ASA[{aa}] must be positive; got {max_asa}"

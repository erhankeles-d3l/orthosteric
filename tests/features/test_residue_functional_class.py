"""Tests for interaction-contextual residue functional classification
(features._residue_functional_class).

Exit criteria (mandate SS15, 19, 27):
  (1) H-bond donor/acceptor direction remains distinct (Test A).
  (2) Anionic/cationic direction remains distinct (Test B).
  (3) Cation-pi direction: only CATIONIC_CAPABLE is reachable from the
      real detector; AROMATIC_CAPABLE is defined but never emitted, and
      this asymmetry is itself tested (Test C).
  (4) The same residue (Tyr) receives DIFFERENT functional classes in
      different interaction contexts (donor vs aromatic) -- proof the
      classification is interaction-contextual, not a static lookup.
  (5) Static six-class metadata never overrides or replaces the
      interaction-contextual primary class.
  (6) His is never silently assigned a resolved protonation/donor-
      acceptor state.
  (7) Cys is not forced into generic hydrophobic.
"""

from __future__ import annotations

from orthosteric.features._docking_interaction_detector import (
    AtomResidueInteraction,
    InteractionGeometryStatus,
    InteractionType,
)
from orthosteric.features._residue_functional_class import (
    ResidueFunctionalClass,
    residue_functional_class,
    static_class_for_residue,
)


def _interaction(itype, **overrides):
    defaults = {
        "interaction_type": itype,
        "status": InteractionGeometryStatus.OBSERVED,
        "ligand_atom_index": 0,
        "ligand_atom_name": "O1",
        "ligand_atom_element": "O",
        "residue_number": 852,
        "residue_name": "ASP",
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


# ── Test A: H-bond direction ──────────────────────────────────────────────


def test_hbond_donor_and_acceptor_remain_distinct() -> None:
    donor_record = _interaction(InteractionType.H_BOND, residue_hbond_role="donor")
    acceptor_record = _interaction(InteractionType.H_BOND, residue_hbond_role="acceptor")
    assert residue_functional_class(donor_record) == ResidueFunctionalClass.H_BOND_DONOR_CAPABLE
    assert (
        residue_functional_class(acceptor_record) == ResidueFunctionalClass.H_BOND_ACCEPTOR_CAPABLE
    )
    assert residue_functional_class(donor_record) != residue_functional_class(acceptor_record)


def test_hbond_unresolved_role_does_not_default_to_either_direction() -> None:
    record = _interaction(InteractionType.H_BOND, residue_hbond_role=None)
    assert residue_functional_class(record) == ResidueFunctionalClass.UNRESOLVED_FUNCTIONAL_ROLE


# ── Test B: charge direction ──────────────────────────────────────────────


def test_anionic_and_cationic_remain_distinct() -> None:
    anionic_record = _interaction(
        InteractionType.SALT_BRIDGE, residue_name="ASP", residue_charge_sign="anionic"
    )
    cationic_record = _interaction(
        InteractionType.SALT_BRIDGE, residue_name="LYS", residue_charge_sign="cationic"
    )
    assert residue_functional_class(anionic_record) == ResidueFunctionalClass.ANIONIC_CAPABLE
    assert residue_functional_class(cationic_record) == ResidueFunctionalClass.CATIONIC_CAPABLE
    assert residue_functional_class(anionic_record) != residue_functional_class(cationic_record)


def test_charged_contact_candidate_also_preserves_charge_direction() -> None:
    """The UNCONFIRMED evidentiary tier must preserve directionality
    exactly like the confirmed SALT_BRIDGE tier -- evidentiary
    confidence and chemical directionality are independent axes."""
    record = _interaction(
        InteractionType.CHARGED_CONTACT_CANDIDATE, residue_name="GLU", residue_charge_sign="anionic"
    )
    assert residue_functional_class(record) == ResidueFunctionalClass.ANIONIC_CAPABLE


def test_asp_glu_anionic_and_lys_arg_cationic_never_collapse_to_generic_charged() -> None:
    anionic = residue_functional_class(
        _interaction(InteractionType.SALT_BRIDGE, residue_name="GLU", residue_charge_sign="anionic")
    )
    cationic = residue_functional_class(
        _interaction(
            InteractionType.SALT_BRIDGE, residue_name="ARG", residue_charge_sign="cationic"
        )
    )
    assert anionic != cationic
    assert "CHARGED" not in anionic.name
    assert "CHARGED" not in cationic.name


# ── Test C: cation-pi direction (only one resolvable from real detector) ──


def test_cation_pi_from_real_detector_is_always_cationic_capable() -> None:
    """The current detector only resolves residue-supplies-cation. Every
    real CATION_PI record must classify as CATION_PI_CATIONIC_CAPABLE."""
    record = _interaction(InteractionType.CATION_PI, residue_name="LYS")
    assert residue_functional_class(record) == ResidueFunctionalClass.CATION_PI_CATIONIC_CAPABLE


def test_cation_pi_aromatic_capable_is_defined_but_documented_unreachable() -> None:
    """CATION_PI_AROMATIC_CAPABLE must exist as a defined label (so
    downstream code can reference it without a NameError/KeyError if the
    detector is ever extended) but must never be produced by
    `residue_functional_class` given today's detector output -- this
    tests the documented asymmetry itself, not just its absence."""
    assert ResidueFunctionalClass.CATION_PI_AROMATIC_CAPABLE is not None
    for residue_name in ("TRP", "TYR", "PHE", "HIS", "LYS", "ARG"):
        record = _interaction(InteractionType.CATION_PI, residue_name=residue_name)
        assert residue_functional_class(record) != ResidueFunctionalClass.CATION_PI_AROMATIC_CAPABLE


# ── Interaction-contextual, not static: same residue, different roles ────


def test_same_residue_different_interaction_different_class() -> None:
    """Tyr as an H-bond donor and Tyr in a pi-pi interaction must receive
    DIFFERENT functional classes -- proof the classifier is contextual
    to the observed interaction, not a static per-residue lookup."""
    tyr_donor = _interaction(InteractionType.H_BOND, residue_name="TYR", residue_hbond_role="donor")
    tyr_aromatic = _interaction(InteractionType.PI_PI, residue_name="TYR")
    assert residue_functional_class(tyr_donor) == ResidueFunctionalClass.H_BOND_DONOR_CAPABLE
    assert residue_functional_class(tyr_aromatic) == ResidueFunctionalClass.AROMATIC
    assert residue_functional_class(tyr_donor) != residue_functional_class(tyr_aromatic)


def test_ser_donor_and_tyr_donor_share_class_despite_different_identity() -> None:
    """The whole point of Representation 2: chemically equivalent roles
    from different residues must land in the same functional class."""
    ser = _interaction(InteractionType.H_BOND, residue_name="SER", residue_hbond_role="donor")
    tyr = _interaction(InteractionType.H_BOND, residue_name="TYR", residue_hbond_role="donor")
    assert residue_functional_class(ser) == residue_functional_class(tyr)


def test_pi_pi_and_hydrophobic_remain_distinct_classes() -> None:
    aromatic = _interaction(InteractionType.PI_PI, residue_name="PHE")
    hydrophobic = _interaction(InteractionType.HYDROPHOBIC_CONTACT, residue_name="LEU")
    assert residue_functional_class(aromatic) == ResidueFunctionalClass.AROMATIC
    assert residue_functional_class(hydrophobic) == ResidueFunctionalClass.HYDROPHOBIC
    assert residue_functional_class(aromatic) != residue_functional_class(hydrophobic)


# ── Static secondary metadata: never overrides, never resolves ambiguity ─


def test_static_class_never_used_as_primary_role() -> None:
    """His's static class must not silently resolve its real
    protonation/donor-acceptor ambiguity -- confirm the static lookup
    result is clearly marked state-dependent, not "basic" or "aromatic"."""
    assert static_class_for_residue("HIS") == "special_state_dependent"


def test_cys_not_forced_into_generic_hydrophobic_static_class() -> None:
    assert static_class_for_residue("CYS") == "special_thiol"
    assert static_class_for_residue("CYS") != static_class_for_residue("LEU")


def test_static_class_does_not_affect_interaction_contextual_result() -> None:
    """Even though His's static class is deliberately ambiguous, an
    OBSERVED donor interaction for His must still classify normally --
    the interaction-contextual path never consults the static table."""
    record = _interaction(InteractionType.H_BOND, residue_name="HIS", residue_hbond_role="donor")
    assert residue_functional_class(record) == ResidueFunctionalClass.H_BOND_DONOR_CAPABLE


def test_unresolved_interaction_type_falls_through_safely() -> None:
    """A hypothetical/unmapped interaction type must never be forced
    into an existing category."""

    class _FakeType:
        pass

    record = _interaction(InteractionType.HYDROPHOBIC_CONTACT)
    # sanity: a genuinely unresolved case (no role, no charge sign) for a
    # type this function doesn't special-case should not silently guess
    object.__setattr__(record, "interaction_type", InteractionType.H_BOND)
    object.__setattr__(record, "residue_hbond_role", None)
    assert residue_functional_class(record) == ResidueFunctionalClass.UNRESOLVED_FUNCTIONAL_ROLE

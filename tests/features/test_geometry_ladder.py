"""Tests for the geometry-sensitivity ladder (features._representation_2_3
frozen_ladder_boundaries / geometry_bin_at_resolution).

Exit criteria (per the geometry-ladder mandate):
  (1) Coarse rung of the ladder reproduces the original, already-
      committed `geometry_bin` result exactly -- the ladder is a strict
      extension, never a silent redefinition of the existing rung.
  (2) Intermediate/fine boundaries are DERIVED, deterministic functions
      of the already-committed coarse boundary and outer cutoff -- same
      inputs always produce the same boundaries, and the coarse
      boundary itself is never moved when refining to intermediate/fine.
  (3) Aromatic (PI_PI) remains distance-only at every rung -- plane
      angle never affects the bin.
  (4) Finer rungs never lose the coarser rung's information: a value
      classified in the "close" half at coarse resolution is never
      reclassified into what would be the "peripheral" half at a finer
      resolution (intermediate/fine only subdivide within each existing
      coarse half, never move the coarse/peripheral boundary).
"""

from __future__ import annotations

from orthosteric.features._docking_interaction_detector import (
    AtomResidueInteraction,
    InteractionGeometryStatus,
    InteractionType,
)
from orthosteric.features._representation_2_3 import (
    frozen_ladder_boundaries,
    geometry_bin,
    geometry_bin_at_resolution,
)


def _interaction(itype, distance, **overrides):
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
        "distance_angstrom": distance,
        "angle_degrees": None,
        "plane_angle_degrees": None,
        "compound_id": "C1",
        "isoform": "PI3Kalpha",
        "receptor_id": "r1",
        "docking_score": None,
    }
    defaults.update(overrides)
    return AtomResidueInteraction(**defaults)


def test_coarse_rung_matches_existing_geometry_bin_exactly() -> None:
    """The ladder's 'coarse' rung must reproduce the already-committed
    geometry_bin() output, not a redefinition of it."""
    for itype, close_d, far_d in (
        (InteractionType.H_BOND, 2.7, 3.4),
        (InteractionType.HYDROPHOBIC_CONTACT, 3.5, 4.4),
        (InteractionType.PI_PI, 4.0, 5.5),
        (InteractionType.CATION_PI, 4.0, 5.5),
        (InteractionType.SALT_BRIDGE, 3.0, 3.9),
    ):
        for d in (close_d, far_d):
            record = _interaction(itype, d)
            original = geometry_bin(record).value
            ladder_coarse = geometry_bin_at_resolution(record, "coarse")
            # original is a hand-named enum value; ladder_coarse is a
            # generic "{type}__coarse__binNofM" label -- compare which
            # SIDE of the boundary each falls on, not the literal string.
            original_is_close = "peripheral" not in original and "weak" not in original
            ladder_is_close = ladder_coarse.endswith("bin0of2")
            assert original_is_close == ladder_is_close, (itype, d, original, ladder_coarse)


def test_boundaries_are_deterministic_pure_functions() -> None:
    b1 = frozen_ladder_boundaries(InteractionType.H_BOND)
    b2 = frozen_ladder_boundaries(InteractionType.H_BOND)
    assert b1 == b2


def test_coarse_boundary_never_moves_across_rungs() -> None:
    """The single coarse cutpoint must appear, UNCHANGED, inside both the
    intermediate and fine boundary lists -- refinement never relocates
    an already-committed boundary."""
    for itype in (
        InteractionType.H_BOND,
        InteractionType.HYDROPHOBIC_CONTACT,
        InteractionType.PI_PI,
    ):
        b = frozen_ladder_boundaries(itype)
        coarse_boundary = b["coarse"][0]
        assert coarse_boundary in b["intermediate"]
        assert coarse_boundary in b["fine"]


def test_intermediate_only_refines_the_peripheral_half() -> None:
    """Intermediate adds exactly one NEW cutpoint, and it must lie in the
    peripheral (beyond-coarse) region, not the close region -- refining
    granularity where the coarse rung had none, not moving anything."""
    for itype in (InteractionType.H_BOND, InteractionType.SALT_BRIDGE):
        b = frozen_ladder_boundaries(itype)
        coarse_boundary = b["coarse"][0]
        new_cutpoints = set(b["intermediate"]) - set(b["coarse"])
        assert len(new_cutpoints) == 1
        assert next(iter(new_cutpoints)) > coarse_boundary


def test_fine_adds_exactly_one_more_cutpoint_in_the_close_region() -> None:
    for itype in (InteractionType.H_BOND, InteractionType.CATION_PI):
        b = frozen_ladder_boundaries(itype)
        coarse_boundary = b["coarse"][0]
        new_cutpoints = set(b["fine"]) - set(b["intermediate"])
        assert len(new_cutpoints) == 1
        assert next(iter(new_cutpoints)) < coarse_boundary


def test_aromatic_remains_distance_only_at_every_rung() -> None:
    close_parallel = _interaction(InteractionType.PI_PI, 4.0, plane_angle_degrees=5.0)
    close_perp = _interaction(InteractionType.PI_PI, 4.0, plane_angle_degrees=85.0)
    for resolution in ("coarse", "intermediate", "fine"):
        assert geometry_bin_at_resolution(close_parallel, resolution) == geometry_bin_at_resolution(
            close_perp, resolution
        )


def test_finer_rungs_never_cross_the_original_coarse_close_peripheral_boundary() -> None:
    """A value on the CLOSE side at coarse resolution must remain on the
    close side of the ladder's finest resolution too -- intermediate/
    fine only add resolution WITHIN each half, never redraw the
    original close/peripheral line."""
    itype = InteractionType.H_BOND
    b = frozen_ladder_boundaries(itype)
    coarse_boundary = b["coarse"][0]
    close_value = coarse_boundary - 0.1
    peripheral_value = coarse_boundary + 0.1

    close_record = _interaction(itype, close_value)
    peripheral_record = _interaction(itype, peripheral_value)
    for resolution in ("intermediate", "fine"):
        close_bin = geometry_bin_at_resolution(close_record, resolution)
        peripheral_bin = geometry_bin_at_resolution(peripheral_record, resolution)
        assert close_bin != peripheral_bin


def test_finer_resolution_produces_more_or_equal_bins_never_fewer() -> None:
    itype = InteractionType.H_BOND
    n_bins = {
        res: len(frozen_ladder_boundaries(itype)[res]) + 1
        for res in ("coarse", "intermediate", "fine")
    }
    assert n_bins["coarse"] <= n_bins["intermediate"] <= n_bins["fine"]
    assert n_bins == {"coarse": 2, "intermediate": 3, "fine": 4}


def test_distance_none_returns_not_applicable_at_every_resolution() -> None:
    record = _interaction(InteractionType.H_BOND, None)
    for resolution in ("coarse", "intermediate", "fine"):
        assert geometry_bin_at_resolution(record, resolution) == "not_applicable"

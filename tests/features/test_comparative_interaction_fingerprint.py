"""Tests for compound x isoform comparative interaction fingerprints
(features._comparative_interaction_fingerprint).

Exit criteria:
  (1) An interaction present in ALL isoforms at similar occupancy is
      classified CONSERVED.
  (2) An interaction much higher-occupancy in alpha is ALPHA_FAVORED.
  (3) An interaction much higher-occupancy in a non-alpha isoform is
      OTHER_FAVORED.
  (4) An interaction present in one isoform and genuinely absent (0
      occupancy, not missing-data) in another is LOST.
  (5) Residue correspondence correctly canonicalizes non-alpha residue
      numbers onto the alpha reference frame before comparison -- two
      isoforms' occupancy for "the same" interaction only compare
      correctly when keyed by canonical position, not raw residue number.
  (6) Without a correspondence table, canonical_position is None
      (never a fabricated guess).
  (7) An isoform absent from the input dict contributes no record for
      that isoform (never fabricated as a false zero).
"""

from __future__ import annotations

from orthosteric.features._comparative_interaction_fingerprint import (
    CompoundIsoformFingerprint,
    CrossIsoformPattern,
    build_comparative_fingerprint,
)
from orthosteric.features._interaction_occupancy import InteractionOccupancy, OccupancyClass
from orthosteric.pocket._sequence_correspondence import CorrespondenceRecord, CorrespondenceTable


def _occ(itype, resnum, occupancy, chain="A", atom_name="O1", resname="GLU"):
    return InteractionOccupancy(
        interaction_type=itype,
        residue_number=resnum,
        residue_name=resname,
        chain_id=chain,
        ligand_atom_name=atom_name,
        n_poses_evaluated=5,
        n_poses_with_interaction=round(occupancy * 5),
        occupancy=occupancy,
        occupancy_class=OccupancyClass.RECURRENT,
        distances=(),
    )


def test_conserved_pattern_when_all_isoforms_similar() -> None:
    fps = {
        "PI3Kalpha": CompoundIsoformFingerprint("C1", "PI3Kalpha", (_occ("h_bond", 852, 0.8),)),
        "PI3Kbeta": CompoundIsoformFingerprint("C1", "PI3Kbeta", (_occ("h_bond", 852, 0.8),)),
    }
    records = build_comparative_fingerprint("C1", fps)
    assert records[0].pattern == CrossIsoformPattern.CONSERVED


def test_alpha_favored_pattern() -> None:
    fps = {
        "PI3Kalpha": CompoundIsoformFingerprint("C1", "PI3Kalpha", (_occ("h_bond", 852, 1.0),)),
        "PI3Kbeta": CompoundIsoformFingerprint("C1", "PI3Kbeta", (_occ("h_bond", 852, 0.2),)),
    }
    records = build_comparative_fingerprint("C1", fps)
    assert records[0].pattern == CrossIsoformPattern.ALPHA_FAVORED


def test_other_favored_pattern() -> None:
    fps = {
        "PI3Kalpha": CompoundIsoformFingerprint("C1", "PI3Kalpha", (_occ("h_bond", 852, 0.2),)),
        "PI3Kgamma": CompoundIsoformFingerprint("C1", "PI3Kgamma", (_occ("h_bond", 852, 1.0),)),
    }
    records = build_comparative_fingerprint("C1", fps)
    assert records[0].pattern == CrossIsoformPattern.OTHER_FAVORED


def test_lost_pattern_when_genuinely_absent_in_one_isoform() -> None:
    fps = {
        "PI3Kalpha": CompoundIsoformFingerprint("C1", "PI3Kalpha", (_occ("h_bond", 852, 0.8),)),
        "PI3Kdelta": CompoundIsoformFingerprint(
            "C1", "PI3Kdelta", ()
        ),  # no h_bond at all -> occupancy 0
    }
    records = build_comparative_fingerprint("C1", fps)
    assert records[0].pattern == CrossIsoformPattern.LOST
    assert records[0].occupancy_by_isoform["PI3Kdelta"] == 0.0


def test_correspondence_table_canonicalizes_residue_numbers() -> None:
    """The SAME structural interaction shows up at residue 852 in alpha
    and residue 900 in beta (per a correspondence table); without
    correspondence these would be treated as two unrelated interactions.
    """
    table = CorrespondenceTable(
        reference_isoform="PI3Kalpha",
        by_target_isoform={
            "PI3Kbeta": [
                CorrespondenceRecord("PI3Kalpha", 852, "PI3Kbeta", 900),
            ]
        },
    )
    fps = {
        "PI3Kalpha": CompoundIsoformFingerprint("C1", "PI3Kalpha", (_occ("h_bond", 852, 0.8),)),
        "PI3Kbeta": CompoundIsoformFingerprint("C1", "PI3Kbeta", (_occ("h_bond", 900, 0.8),)),
    }
    records = build_comparative_fingerprint("C1", fps, correspondence_table=table)
    assert len(records) == 1  # correctly merged into ONE canonical record, not two
    assert records[0].canonical_position == 852
    assert records[0].pattern == CrossIsoformPattern.CONSERVED


def test_without_correspondence_table_canonical_position_is_none() -> None:
    fps = {"PI3Kalpha": CompoundIsoformFingerprint("C1", "PI3Kalpha", (_occ("h_bond", 852, 0.8),))}
    records = build_comparative_fingerprint("C1", fps, correspondence_table=None)
    assert records[0].canonical_position is None


def test_missing_isoform_not_fabricated_as_zero() -> None:
    """An isoform entirely absent from the input dict (e.g. no receptor
    available) contributes no key for that isoform -- distinct from a
    genuinely-absent (occupancy=0) interaction in an isoform that WAS
    evaluated."""
    fps = {"PI3Kalpha": CompoundIsoformFingerprint("C1", "PI3Kalpha", (_occ("h_bond", 852, 0.8),))}
    records = build_comparative_fingerprint("C1", fps)
    assert "PI3Kbeta" not in records[0].occupancy_by_isoform
    assert set(records[0].occupancy_by_isoform.keys()) == {"PI3Kalpha"}

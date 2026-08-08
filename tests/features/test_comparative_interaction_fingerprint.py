"""Tests for compound x isoform comparative interaction fingerprints
(features._comparative_interaction_fingerprint).

Exit criteria:
  (1) An interaction present in ALL isoforms at similar occupancy is
      classified CONSERVED.
  (2) An interaction much higher-occupancy in alpha is ALPHA_FAVORED.
  (3) An interaction much higher-occupancy in a non-alpha isoform is
      OTHER_FAVORED.
  (4) An interaction present in one isoform and genuinely absent (0
      occupancy, not missing-data) in another, AT A VALIDLY MAPPED
      POSITION, is LOST_AT_MAPPED_POSITION.
  (5) Residue correspondence correctly canonicalizes non-alpha residue
      numbers onto the alpha reference frame before comparison -- two
      isoforms' occupancy for "the same" interaction only compare
      correctly when keyed by canonical position, not raw residue number.
  (6) Without a correspondence table, canonical_position is None
      (never a fabricated guess).
  (7) An isoform absent from the input dict contributes no record for
      that isoform (never fabricated as a false zero).
  (8) A canonical position with NO corresponding residue in one isoform
      (an alignment gap) is UNMAPPED_RESIDUE, never LOST_AT_MAPPED_POSITION
      -- there is no homologous position to have lost anything at.
  (9) The residue-level (primary) fingerprint marginalizes over ligand
      atom identity: two different atoms hitting the same residue via
      the same interaction type in the same isoform must not be treated
      as two separate comparative keys.
"""

from __future__ import annotations

from typing import Any

from orthosteric.features._comparative_interaction_fingerprint import (
    CompoundIsoformFingerprint,
    CompoundIsoformResidueFingerprint,
    CrossIsoformPattern,
    build_comparative_fingerprint,
    build_residue_level_comparative_fingerprint,
)
from orthosteric.features._interaction_occupancy import (
    InteractionOccupancy,
    OccupancyClass,
    ResidueLevelOccupancy,
)
from orthosteric.pocket._sequence_correspondence import CorrespondenceRecord, CorrespondenceTable


def _occ(
    itype: Any,
    resnum: int,
    occupancy: float,
    chain: str = "A",
    atom_name: str = "O1",
    resname: str = "GLU",
) -> InteractionOccupancy:
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


def _residue_occ(
    itype: Any,
    resnum: int,
    occupancy: float,
    chain: str = "A",
    resname: str = "GLU",
    atoms: frozenset[str] = frozenset({"O1"}),
) -> ResidueLevelOccupancy:
    return ResidueLevelOccupancy(
        interaction_type=itype,
        residue_number=resnum,
        residue_name=resname,
        chain_id=chain,
        n_poses_evaluated=5,
        n_poses_with_interaction=round(occupancy * 5),
        occupancy=occupancy,
        occupancy_class=OccupancyClass.RECURRENT,
        contributing_atom_names=atoms,
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
    assert records[0].pattern == CrossIsoformPattern.LOST_AT_MAPPED_POSITION
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


# ── UNMAPPED_RESIDUE: never confused with LOST_AT_MAPPED_POSITION ───────────


def test_unmapped_residue_when_no_correspondence_exists() -> None:
    """Alpha residue 852 has NO corresponding residue in delta at all
    (an alignment gap, per the correspondence table) -- this must be
    UNMAPPED_RESIDUE, never LOST_AT_MAPPED_POSITION, even though delta's
    occupancy for this key is 0.0."""
    table = CorrespondenceTable(
        reference_isoform="PI3Kalpha",
        by_target_isoform={
            "PI3Kdelta": [
                CorrespondenceRecord("PI3Kalpha", 852, "PI3Kdelta", None),  # explicit gap
            ]
        },
    )
    fps = {
        "PI3Kalpha": CompoundIsoformFingerprint("C1", "PI3Kalpha", (_occ("h_bond", 852, 0.8),)),
        "PI3Kdelta": CompoundIsoformFingerprint("C1", "PI3Kdelta", ()),
    }
    records = build_comparative_fingerprint("C1", fps, correspondence_table=table)
    assert records[0].pattern == CrossIsoformPattern.UNMAPPED_RESIDUE


def test_unmapped_takes_priority_even_with_other_isoforms_present() -> None:
    """Even if beta DOES have a valid mapping and matches alpha's
    occupancy closely, an UNMAPPED delta must still force the whole
    record to UNMAPPED_RESIDUE rather than CONSERVED (the comparison
    set as a whole cannot be honestly summarized when part of it lacks
    a valid position)."""
    table = CorrespondenceTable(
        reference_isoform="PI3Kalpha",
        by_target_isoform={
            "PI3Kbeta": [CorrespondenceRecord("PI3Kalpha", 852, "PI3Kbeta", 900)],
            "PI3Kdelta": [CorrespondenceRecord("PI3Kalpha", 852, "PI3Kdelta", None)],
        },
    )
    fps = {
        "PI3Kalpha": CompoundIsoformFingerprint("C1", "PI3Kalpha", (_occ("h_bond", 852, 0.8),)),
        "PI3Kbeta": CompoundIsoformFingerprint("C1", "PI3Kbeta", (_occ("h_bond", 900, 0.8),)),
        "PI3Kdelta": CompoundIsoformFingerprint("C1", "PI3Kdelta", ()),
    }
    records = build_comparative_fingerprint("C1", fps, correspondence_table=table)
    assert records[0].pattern == CrossIsoformPattern.UNMAPPED_RESIDUE


# ── Residue-level (primary) fingerprint: marginalizes over ligand atom ──────


def test_residue_level_marginalizes_over_ligand_atom() -> None:
    """Two DIFFERENT ligand atoms both hitting residue 852 via H-bond in
    the same isoform must collapse to ONE residue-level comparative key,
    not two -- this is the entire point of the residue-level fix."""
    fps = {
        "PI3Kalpha": CompoundIsoformResidueFingerprint(
            "C1", "PI3Kalpha", (_residue_occ("h_bond", 852, 0.8, atoms=frozenset({"O1", "O2"})),)
        ),
    }
    records = build_residue_level_comparative_fingerprint("C1", fps)
    assert len(records) == 1  # both atoms' contributions collapsed to one comparative key
    assert records[0].occupancy_by_isoform["PI3Kalpha"] == 0.8


def test_residue_level_lost_at_mapped_position() -> None:
    fps = {
        "PI3Kalpha": CompoundIsoformResidueFingerprint(
            "C1", "PI3Kalpha", (_residue_occ("h_bond", 852, 0.8),)
        ),
        "PI3Kdelta": CompoundIsoformResidueFingerprint("C1", "PI3Kdelta", ()),
    }
    records = build_residue_level_comparative_fingerprint("C1", fps)
    assert records[0].pattern == CrossIsoformPattern.LOST_AT_MAPPED_POSITION


def test_residue_level_unmapped_residue() -> None:
    table = CorrespondenceTable(
        reference_isoform="PI3Kalpha",
        by_target_isoform={
            "PI3Kdelta": [CorrespondenceRecord("PI3Kalpha", 852, "PI3Kdelta", None)]
        },
    )
    fps = {
        "PI3Kalpha": CompoundIsoformResidueFingerprint(
            "C1", "PI3Kalpha", (_residue_occ("h_bond", 852, 0.8),)
        ),
        "PI3Kdelta": CompoundIsoformResidueFingerprint("C1", "PI3Kdelta", ()),
    }
    records = build_residue_level_comparative_fingerprint("C1", fps, correspondence_table=table)
    assert records[0].pattern == CrossIsoformPattern.UNMAPPED_RESIDUE


def test_residue_level_correspondence_table_sha256_recorded() -> None:
    table = CorrespondenceTable(reference_isoform="PI3Kalpha", by_target_isoform={})
    fps = {
        "PI3Kalpha": CompoundIsoformResidueFingerprint(
            "C1", "PI3Kalpha", (_residue_occ("h_bond", 852, 0.8),)
        ),
    }
    records = build_residue_level_comparative_fingerprint("C1", fps, correspondence_table=table)
    assert records[0].correspondence_table_sha256 == table.content_sha256()


def test_residue_level_no_table_sha256_is_none() -> None:
    fps = {
        "PI3Kalpha": CompoundIsoformResidueFingerprint(
            "C1", "PI3Kalpha", (_residue_occ("h_bond", 852, 0.8),)
        ),
    }
    records = build_residue_level_comparative_fingerprint("C1", fps)
    assert records[0].correspondence_table_sha256 is None

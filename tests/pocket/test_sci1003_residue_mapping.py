"""SCI1-003 tests: cross-isoform residue correspondence data model.

Exit criteria M1-M14 — see inline comments.
"""

from __future__ import annotations

import pytest

from orthosteric.pocket import (
    TIER1_ISOFORMS,
    AnchorPosition,
    CorrespondenceAssignment,
    CorrespondenceStatus,
    ResidueCorrespondenceTable,
    annotate_pocket_residue_set,
    build_correspondence_table,
    make_anchor_assignments,
)
from orthosteric.pocket._pocket_definition import (
    POCKET_DEFINITION_ALGORITHM_VERSION,
    PocketResidue,
    PocketResidueSet,
    SubRegion,
)
from orthosteric.pocket._structure_record import ConstructClass, ResidueRecord


def _residue(seq: int = 859, name: str = "GLN") -> ResidueRecord:
    return ResidueRecord(
        chain_id="A",
        residue_seq=seq,
        insertion_code=" ",
        residue_name=name,
        canonical_position=None,
        is_missing=False,
        missing_modelled=False,
    )


def _pocket_res(rr: ResidueRecord, sub: SubRegion = SubRegion.AFFINITY_POCKET) -> PocketResidue:
    return PocketResidue(
        residue=rr,
        structure_record_id="test",
        minimum_distance_to_ligand=2.5,
        sub_region=sub,
        observed_in_n_structures=2,
        correspondence_stable=True,
        present_with_propeller_ligand=False,
    )


def _alpha_anchors() -> list[CorrespondenceAssignment]:
    return list(
        make_anchor_assignments(
            isoform="PI3Kalpha",
            alpha_859_residue_id="A_859_ ",
            trp780_residue_id="A_780_ ",
            met772_residue_id="A_772_ ",
            provenance_note="synthetic test — manually curated",
        )
    )


def _simple_table() -> ResidueCorrespondenceTable:
    return build_correspondence_table(
        assignments=_alpha_anchors(),
        isoforms_covered=frozenset({"PI3Kalpha"}),
    )


# (M1) Frozen
def test_m1_frozen() -> None:
    a = CorrespondenceAssignment(
        residue_id="A_859_ ",
        isoform="PI3Kalpha",
        canonical_position=859,
        status=CorrespondenceStatus.ANCHOR,
        anchor_position=AnchorPosition.ALPHA_859,
        reference_isoform="PI3Kalpha",
        provenance_note="test",
    )
    with pytest.raises((AttributeError, TypeError)):
        a.canonical_position = 999  # type: ignore[misc]


# (M2) Three anchor positions with correct names
def test_m2_three_named_anchor_positions() -> None:
    vals = {ap.value for ap in AnchorPosition}
    assert vals == {"alpha_859", "trp780", "met772"}


# (M3) Tier 1 isoforms
def test_m3_tier1_isoforms() -> None:
    assert frozenset({"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}) == TIER1_ISOFORMS


# (M4) reference_isoform must be PI3Kalpha
def test_m4_reference_isoform_required() -> None:
    with pytest.raises(ValueError, match="PI3Kalpha"):
        CorrespondenceAssignment(
            residue_id="A_859_ ",
            isoform="PI3Kbeta",
            canonical_position=859,
            status=CorrespondenceStatus.MAPPED,
            anchor_position=None,
            reference_isoform="PI3Kbeta",
            provenance_note="test",
        )


# (M5) UNMAPPED must have canonical_position == None
def test_m5_unmapped_requires_none_position() -> None:
    with pytest.raises(ValueError, match="must be None"):
        CorrespondenceAssignment(
            residue_id="A_999_ ",
            isoform="PI3Kalpha",
            canonical_position=999,
            status=CorrespondenceStatus.UNMAPPED,
            anchor_position=None,
            reference_isoform="PI3Kalpha",
            provenance_note="",
        )


# (M6) Non-UNMAPPED must have canonical_position != None
def test_m6_non_unmapped_requires_position() -> None:
    with pytest.raises(ValueError, match="must not be None"):
        CorrespondenceAssignment(
            residue_id="A_859_ ",
            isoform="PI3Kalpha",
            canonical_position=None,
            status=CorrespondenceStatus.ANCHOR,
            anchor_position=AnchorPosition.ALPHA_859,
            reference_isoform="PI3Kalpha",
            provenance_note="test",
        )


def test_m6b_unmapped_none_is_valid() -> None:
    a = CorrespondenceAssignment(
        residue_id="A_999_ ",
        isoform="PI3Kalpha",
        canonical_position=None,
        status=CorrespondenceStatus.UNMAPPED,
        anchor_position=None,
        reference_isoform="PI3Kalpha",
        provenance_note="",
    )
    assert a.canonical_position is None
    assert not a.is_anchor


# (M7) make_anchor_assignments: three ANCHOR-status entries
def test_m7_make_anchor_assignments_three_anchors() -> None:
    anchors = _alpha_anchors()
    assert len(anchors) == 3
    for a in anchors:
        assert a.status == CorrespondenceStatus.ANCHOR
        assert a.is_anchor
        assert a.canonical_position is not None


def test_m7b_anchor_positions_are_correct_values() -> None:
    anchors = _alpha_anchors()
    by_ap = {a.anchor_position: a for a in anchors}
    assert by_ap[AnchorPosition.ALPHA_859].canonical_position == 859
    assert by_ap[AnchorPosition.TRP780].canonical_position == 780
    assert by_ap[AnchorPosition.MET772].canonical_position == 772


# (M8) build_correspondence_table: counts + deterministic hash
def test_m8_table_counts_correct() -> None:
    table = _simple_table()
    assert table.n_mapped == 3  # ANCHOR counts as mapped
    assert table.n_provisional == 0
    assert table.n_unmapped == 0
    assert len(table.assignments) == 3


def test_m8b_table_hash_deterministic() -> None:
    assert _simple_table().content_sha256() == _simple_table().content_sha256()


# (M9) Duplicate (residue_id, isoform) raises
def test_m9_duplicate_raises() -> None:
    anchors = _alpha_anchors()
    dup = CorrespondenceAssignment(
        residue_id="A_859_ ",
        isoform="PI3Kalpha",
        canonical_position=None,
        status=CorrespondenceStatus.UNMAPPED,
        anchor_position=None,
        reference_isoform="PI3Kalpha",
        provenance_note="",
    )
    with pytest.raises(ValueError, match="Duplicate"):
        build_correspondence_table([*anchors, dup], isoforms_covered=frozenset({"PI3Kalpha"}))


# (M10) all_anchors_covered
def test_m10_all_covered_when_all_three_present() -> None:
    assert _simple_table().all_anchors_covered is True


def test_m10b_not_all_covered_when_one_missing() -> None:
    partial = [a for a in _alpha_anchors() if a.anchor_position != AnchorPosition.ALPHA_859]
    table = build_correspondence_table(partial, isoforms_covered=frozenset({"PI3Kalpha"}))
    assert table.all_anchors_covered is False
    assert "alpha_859" not in table.anchor_positions_covered


# (M11) RULE_MISSING governance note
def test_m11_rule_missing_note_nonempty() -> None:
    table = _simple_table()
    assert table.alignment_algorithm == "RULE_MISSING"
    assert "RULE_MISSING" in table.alignment_governance_note


def test_m11b_named_algorithm_has_empty_note() -> None:
    table = build_correspondence_table(
        _alpha_anchors(), frozenset({"PI3Kalpha"}), alignment_algorithm="MUSTANG_v3.2.3"
    )
    assert table.alignment_governance_note == ""


# (M12) annotate_pocket_residue_set
def test_m12_annotate_mapped_and_unmapped() -> None:
    rr859 = _residue(859, "GLN")
    rr900 = _residue(900, "ALA")
    prs = PocketResidueSet(
        isoform="PI3Kalpha",
        construct_class=ConstructClass.P110_P85_HETERODIMER,
        contributing_record_ids=("t",),
        n_contributing_structures=1,
        residues=(_pocket_res(rr859), _pocket_res(rr900, SubRegion.ADENINE_HINGE)),
        n_residues_total=2,
        n_residues_correspondence_stable=2,
        n_residues_propeller_only=0,
        cutoff_angstrom=5.0,
        algorithm_version=POCKET_DEFINITION_ALGORITHM_VERSION,
    )
    results = annotate_pocket_residue_set(prs, _simple_table())
    rd = {rid: (canon, status) for rid, canon, status in results}
    assert rd["A_859_ "][1] == CorrespondenceStatus.ANCHOR
    assert rd["A_859_ "][0] == 859
    assert rd["A_900_ "][1] == CorrespondenceStatus.UNMAPPED
    assert rd["A_900_ "][0] is None


# (M13) Determinism
def test_m13_deterministic() -> None:
    assert _simple_table().content_sha256() == _simple_table().content_sha256()


# (M14) Different assignments -> different hashes
def test_m14_different_hash() -> None:
    t1 = _simple_table()
    beta_anchors = list(
        make_anchor_assignments(
            isoform="PI3Kbeta",
            alpha_859_residue_id="B_860_ ",
            trp780_residue_id="B_781_ ",
            met772_residue_id="B_773_ ",
            provenance_note="test beta",
        )
    )
    t2 = build_correspondence_table(
        _alpha_anchors() + beta_anchors, frozenset({"PI3Kalpha", "PI3Kbeta"})
    )
    assert t1.content_sha256() != t2.content_sha256()

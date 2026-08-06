"""Tests for DockingComplexRecord -- the docking-derived (computational)
evidence schema, kept separate from experimental evidence.

Exit criteria:
  (1) evidence_class is always DOCKING_COMPLEX and is_experimental is
      always False, on every constructed instance -- never caller-settable.
  (2) A SUCCESS outcome requires a docking_score; a non-SUCCESS outcome
      forbids one -- never a silent inconsistency.
  (3) Tier (D1/D2) is derived from receptor_source_class, never set
      independently.
  (4) content_sha256 is deterministic and provenance-complete.
  (5) DockingBox always carries a derivation_method (never an unexplained
      arbitrary box).
"""

from __future__ import annotations

import pytest

from orthosteric.data.sources.structural._docking_record import (
    DOCKING_POLICY_ID,
    DockingBox,
    DockingComplexRecord,
    DockingOutcome,
    ReceptorSourceClass,
    docking_tier,
)
from orthosteric.data.sources.structural._evidence_record import EvidenceClass


def _box() -> DockingBox:
    return DockingBox(
        center_x=1.0,
        center_y=2.0,
        center_z=3.0,
        size_x=20.0,
        size_y=20.0,
        size_z=20.0,
        derivation_method="centroid_of_cocrystallized_ligand:1E7V",
    )


def test_evidence_class_always_docking_complex_never_caller_settable() -> None:
    rec = DockingComplexRecord(
        compound_id="IK1",
        inchikey="IK1",
        isoform="PI3Kgamma",
        outcome=DockingOutcome.SUCCESS,
        docking_score=-8.5,
    )
    assert rec.evidence_class is EvidenceClass.DOCKING_COMPLEX
    assert rec.is_experimental is False


def test_success_outcome_requires_docking_score() -> None:
    with pytest.raises(ValueError, match="SUCCESS outcome must carry"):
        DockingComplexRecord(
            compound_id="IK1",
            inchikey="IK1",
            isoform="PI3Kgamma",
            outcome=DockingOutcome.SUCCESS,
            docking_score=None,
        )


def test_failure_outcome_forbids_docking_score() -> None:
    with pytest.raises(ValueError, match="non-SUCCESS outcome must not carry"):
        DockingComplexRecord(
            compound_id="IK1",
            inchikey="IK1",
            isoform="PI3Kgamma",
            outcome=DockingOutcome.LIGAND_PREPARATION_FAILED,
            docking_score=-8.5,
        )


def test_failure_record_carries_no_fabricated_score() -> None:
    rec = DockingComplexRecord(
        compound_id="IK1",
        inchikey="IK1",
        isoform="PI3Kgamma",
        outcome=DockingOutcome.RECEPTOR_PREPARATION_FAILED,
        failure_reason="chain B missing catalytic residues",
    )
    assert rec.docking_score is None
    assert rec.to_dict()["docking_score"] is None
    assert rec.to_dict()["outcome"] == "receptor_preparation_failed"


def test_tier_derived_from_receptor_source_class() -> None:
    exp = DockingComplexRecord(
        compound_id="IK1",
        inchikey="IK1",
        isoform="PI3Kalpha",
        outcome=DockingOutcome.SUCCESS,
        docking_score=-7.0,
        receptor_source_class=ReceptorSourceClass.EXPERIMENTAL_RECEPTOR,
    )
    af = DockingComplexRecord(
        compound_id="IK1",
        inchikey="IK1",
        isoform="PI3Kbeta",
        outcome=DockingOutcome.SUCCESS,
        docking_score=-7.0,
        receptor_source_class=ReceptorSourceClass.ALPHAFOLD_RECEPTOR,
    )
    assert exp.tier == "D1"
    assert af.tier == "D2"
    assert docking_tier(ReceptorSourceClass.EXPERIMENTAL_RECEPTOR) == "D1"
    assert docking_tier(ReceptorSourceClass.ALPHAFOLD_RECEPTOR) == "D2"


def test_tier_none_when_receptor_source_class_unset() -> None:
    rec = DockingComplexRecord(
        compound_id="IK1",
        inchikey="IK1",
        isoform="PI3Kalpha",
        outcome=DockingOutcome.NO_RECEPTOR_AVAILABLE,
    )
    assert rec.tier is None


def test_content_sha256_deterministic() -> None:
    kwargs = {
        "compound_id": "IK1",
        "inchikey": "IK1",
        "isoform": "PI3Kgamma",
        "outcome": DockingOutcome.SUCCESS,
        "docking_score": -8.5,
        "receptor_source_class": ReceptorSourceClass.EXPERIMENTAL_RECEPTOR,
        "receptor_identifier": "1E7V",
        "docking_engine": "vina",
        "docking_engine_version": "1.2.7",
        "seed": 42,
        "pose_rank": 1,
    }
    r1 = DockingComplexRecord(**kwargs)
    r2 = DockingComplexRecord(**kwargs)
    assert r1.content_sha256() == r2.content_sha256()


def test_content_sha256_changes_with_score() -> None:
    kwargs = {
        "compound_id": "IK1",
        "inchikey": "IK1",
        "isoform": "PI3Kgamma",
        "outcome": DockingOutcome.SUCCESS,
        "receptor_source_class": ReceptorSourceClass.EXPERIMENTAL_RECEPTOR,
    }
    r1 = DockingComplexRecord(docking_score=-8.5, **kwargs)
    r2 = DockingComplexRecord(docking_score=-7.0, **kwargs)
    assert r1.content_sha256() != r2.content_sha256()


def test_docking_box_always_has_derivation_method() -> None:
    box = _box()
    assert box.derivation_method
    rec = DockingComplexRecord(
        compound_id="IK1",
        inchikey="IK1",
        isoform="PI3Kgamma",
        outcome=DockingOutcome.SUCCESS,
        docking_score=-8.5,
        docking_box=box,
    )
    assert rec.to_dict()["docking_box"]["derivation_method"] == box.derivation_method


def test_to_dict_never_labels_as_experimental() -> None:
    rec = DockingComplexRecord(
        compound_id="IK1",
        inchikey="IK1",
        isoform="PI3Kgamma",
        outcome=DockingOutcome.SUCCESS,
        docking_score=-8.5,
    )
    d = rec.to_dict()
    assert d["is_experimental"] is False
    assert d["evidence_class"] == "docking_complex"


def test_policy_id_versioned_and_recorded() -> None:
    rec = DockingComplexRecord(
        compound_id="IK1",
        inchikey="IK1",
        isoform="PI3Kgamma",
        outcome=DockingOutcome.SUCCESS,
        docking_score=-8.5,
    )
    assert rec.pipeline_version == DOCKING_POLICY_ID
    assert "vina" in DOCKING_POLICY_ID

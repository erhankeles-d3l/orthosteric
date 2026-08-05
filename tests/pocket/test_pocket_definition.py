"""Tests for SCI1-001 Milestone 2: PocketDefinitionPolicy and PocketResidueSet.

Exit criteria:
  (1) GOVERNED_DISTANCE_CUTOFF_ANGSTROM == 5.0 (Constitution §2.1).
  (2) default_pocket_definition_policy() is_primary_definition == True.
  (3) Apo structures are rejected by the primary policy.
  (4) AlphaFold structures are flagged (not silently promoted).
  (5) LIGAND_BOUND state with no ligands fails validation.
  (6) PocketResidueSet n_contributing_structures must match tuple length.
  (7) PocketResidueSet n_residues_total must match residues tuple length.
  (8) PocketResidue minimum_distance_to_ligand must be >= 0.
  (9) to_canonical_dict is deterministic and stable.
"""

from __future__ import annotations

import json

import pytest

from orthosteric.pocket import (
    GOVERNED_DISTANCE_CUTOFF_ANGSTROM,
    GOVERNED_MIN_STRUCTURES_FOR_STABILITY,
    ConformationalState,
    ConstructClass,
    PocketDefinitionPolicy,
    PocketResidue,
    PocketResidueSet,
    ResidueRecord,
    StructureSource,
    SubRegion,
    default_pocket_definition_policy,
)
from orthosteric.pocket._pocket_definition import POCKET_DEFINITION_ALGORITHM_VERSION
from tests.pocket.test_structure_record import _ligand, _prov, _record

PIPELINE_V = "sci1001_v1"


# ── Exit criterion 1: governed cutoff value ───────────────────────────────────


def test_governed_distance_cutoff_is_five_angstrom() -> None:
    """Constitution §2.1 specifies 5.0 Å; this must not drift."""
    assert GOVERNED_DISTANCE_CUTOFF_ANGSTROM == 5.0


def test_governed_min_structures_is_two() -> None:
    assert GOVERNED_MIN_STRUCTURES_FOR_STABILITY == 2


# ── Exit criterion 2: default policy is primary ───────────────────────────────


def test_default_policy_is_primary() -> None:
    policy = default_pocket_definition_policy()
    assert policy.is_primary_definition is True
    assert policy.cutoff_angstrom == 5.0
    assert not policy.allow_apo_structures
    assert policy.require_propeller_coverage


def test_modified_cutoff_is_not_primary() -> None:
    policy = PocketDefinitionPolicy(
        policy_version="test_non_primary",
        cutoff_angstrom=4.0,  # different from governed default
        min_structures_for_stability=2,
        allow_apo_structures=False,
        require_propeller_coverage=True,
    )
    assert not policy.is_primary_definition


# ── Exit criterion 3: apo rejection ───────────────────────────────────────────


def test_apo_structure_rejected_by_primary_policy() -> None:
    policy = default_pocket_definition_policy()
    record = _record(state=ConformationalState.APO)
    violations = policy.validate_input_structure(record)
    apo_violations = [v for v in violations if "APO_PROHIBITED" in v]
    assert len(apo_violations) == 1


def test_apo_structure_allowed_when_policy_permits() -> None:
    permissive_policy = PocketDefinitionPolicy(
        policy_version="test_apo_allowed",
        cutoff_angstrom=5.0,
        min_structures_for_stability=1,
        allow_apo_structures=True,  # explicit override
        require_propeller_coverage=False,
    )
    record = _record(state=ConformationalState.APO)
    violations = permissive_policy.validate_input_structure(record)
    apo_violations = [v for v in violations if "APO_PROHIBITED" in v]
    assert len(apo_violations) == 0


# ── Exit criterion 4: AlphaFold provenance flagged ────────────────────────────


def test_alphafold_structure_flagged_not_rejected() -> None:
    """AlphaFold structures are usable as governed fallback but must be
    explicitly flagged, never silently promoted to experimental status."""
    policy = default_pocket_definition_policy()
    af_prov = _prov(
        source=StructureSource.ALPHAFOLD_GOVERNED_FALLBACK,
        pdb_id="AF-P42336-F1",
        alphafold_version="v4",
    )
    record = _record(
        prov=af_prov,
        state=ConformationalState.LIGAND_BOUND,
        ligands=(_ligand(),),
    )
    violations = policy.validate_input_structure(record)
    af_flags = [v for v in violations if "PROVENANCE_FLAG" in v]
    assert len(af_flags) == 1
    assert "AlphaFold" in af_flags[0]


# ── Exit criterion 5: ligand-bound with no ligands fails ──────────────────────


def test_ligand_bound_no_ligands_flagged_as_preprocessing_error() -> None:
    """This can't arise through StructureRecord construction (it's validated
    there), but the policy validator also checks for it explicitly so the
    failure mode is caught at both levels. The StructureRecord constructor
    enforces it as a type-level invariant, so we test that here."""
    with pytest.raises(ValueError, match="at least one ATP-site ligand"):
        _record(state=ConformationalState.LIGAND_BOUND, ligands=())


# ── Exit criterion 6 & 7: PocketResidueSet consistency ───────────────────────


def _residue() -> ResidueRecord:
    return ResidueRecord(
        chain_id="A",
        residue_seq=859,
        insertion_code=" ",
        residue_name="GLN",
        canonical_position=859,
        is_missing=False,
        missing_modelled=False,
    )


def _pocket_residue() -> PocketResidue:
    return PocketResidue(
        residue=_residue(),
        structure_record_id="abc123",
        minimum_distance_to_ligand=2.8,
        sub_region=SubRegion.AFFINITY_POCKET,
        observed_in_n_structures=2,
        correspondence_stable=True,
        present_with_propeller_ligand=False,
    )


def test_n_contributing_structures_must_match_tuple_length() -> None:
    with pytest.raises(ValueError, match="n_contributing_structures must equal"):
        PocketResidueSet(
            isoform="PI3Kalpha",
            construct_class=ConstructClass.P110_P85_HETERODIMER,
            contributing_record_ids=("r1", "r2"),
            n_contributing_structures=5,  # mismatch!
            residues=(_pocket_residue(),),
            n_residues_total=1,
            n_residues_correspondence_stable=1,
            n_residues_propeller_only=0,
            cutoff_angstrom=5.0,
            algorithm_version=POCKET_DEFINITION_ALGORITHM_VERSION,
        )


def test_n_residues_total_must_match_residues_tuple_length() -> None:
    with pytest.raises(ValueError, match="n_residues_total must equal"):
        PocketResidueSet(
            isoform="PI3Kalpha",
            construct_class=ConstructClass.P110_P85_HETERODIMER,
            contributing_record_ids=("r1",),
            n_contributing_structures=1,
            residues=(_pocket_residue(),),
            n_residues_total=999,  # mismatch!
            n_residues_correspondence_stable=1,
            n_residues_propeller_only=0,
            cutoff_angstrom=5.0,
            algorithm_version=POCKET_DEFINITION_ALGORITHM_VERSION,
        )


# ── Exit criterion 8: minimum_distance validation ────────────────────────────


def test_negative_minimum_distance_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        PocketResidue(
            residue=_residue(),
            structure_record_id="abc123",
            minimum_distance_to_ligand=-1.0,  # invalid!
            sub_region=SubRegion.AFFINITY_POCKET,
            observed_in_n_structures=1,
            correspondence_stable=False,
            present_with_propeller_ligand=False,
        )


# ── Exit criterion 9: deterministic canonical dict ────────────────────────────


def test_pocket_residue_set_canonical_dict_deterministic() -> None:
    prs = PocketResidueSet(
        isoform="PI3Kalpha",
        construct_class=ConstructClass.P110_P85_HETERODIMER,
        contributing_record_ids=("r1", "r2"),
        n_contributing_structures=2,
        residues=(_pocket_residue(),),
        n_residues_total=1,
        n_residues_correspondence_stable=1,
        n_residues_propeller_only=0,
        cutoff_angstrom=5.0,
        algorithm_version=POCKET_DEFINITION_ALGORITHM_VERSION,
    )
    d = json.loads(json.dumps(prs.to_canonical_dict()))
    assert d["isoform"] == "PI3Kalpha"
    assert d["cutoff_angstrom"] == 5.0
    # contributing_record_ids should be sorted
    assert d["contributing_record_ids"] == ["r1", "r2"]


def test_policy_canonical_dict_roundtrip() -> None:
    policy = default_pocket_definition_policy()
    d = json.loads(json.dumps(policy.to_canonical_dict()))
    assert d["cutoff_angstrom"] == 5.0
    assert d["allow_apo_structures"] is False


# ── Sub-region annotations ────────────────────────────────────────────────────


def test_all_subregions_are_available() -> None:
    """All Constitution §0.3 sub-regions must be accessible."""
    names = {sr.value for sr in SubRegion}
    assert "adenine_hinge" in names
    assert "affinity_pocket" in names
    assert "specificity_pocket" in names
    assert "tryptophan_shelf" in names
    assert "water_network" in names


def test_specificity_pocket_residue_flagged_propeller_only() -> None:
    """The induced specificity pocket is only visible in propeller-ligand
    structures. This is the operational form of Constitution §A.6 (C6)."""
    pr = PocketResidue(
        residue=_residue(),
        structure_record_id="abc123",
        minimum_distance_to_ligand=3.5,
        sub_region=SubRegion.SPECIFICITY_POCKET,
        observed_in_n_structures=1,
        correspondence_stable=False,  # only 1 structure
        present_with_propeller_ligand=True,  # must be True for specificity pocket
    )
    assert pr.sub_region == SubRegion.SPECIFICITY_POCKET
    assert pr.present_with_propeller_ligand is True
    assert not pr.correspondence_stable  # 1 < 2 (governed min)

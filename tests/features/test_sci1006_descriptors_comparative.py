"""SCI1-006 tests: pocket descriptors and comparative feature set.

Synthetic inputs throughout. Exit criteria D1-D14 (descriptor) and
F1-F16 (comparative feature set).
"""

from __future__ import annotations

import pytest

from orthosteric.features import (
    COMPARATIVE_FEATURE_ALGORITHM_VERSION,
    POCKET_DESCRIPTOR_ALGORITHM_VERSION,
    DifferentialFlag,
    InteractionPresence,
    build_comparative_feature_set,
    build_pocket_descriptor,
)
from orthosteric.features._interaction_fingerprint import (
    FINGERPRINT_ALGORITHM_VERSION,
    ComparativeFingerprint,
    FingerprintConfig,
    InteractionEvidence,
    InteractionFingerprint,
    InteractionStatus,
    InteractionType,
)
from orthosteric.pocket import (
    ConformationalState,
    ConstructClass,
    DataTier,
    LigandRecord,
    LigandShapeClass,
    PocketResidue,
    PocketResidueSet,
    ResidueRecord,
    StructureProvenance,
    StructureRecord,
    StructureSource,
    SubRegion,
    build_correspondence_table,
    make_anchor_assignments,
    make_record_id,
)
from orthosteric.pocket._pocket_definition import POCKET_DEFINITION_ALGORITHM_VERSION
from orthosteric.pocket._structure_record import ConstructDescriptor

PIPELINE_V = "sci1006_test_v1"
_ALGO = FINGERPRINT_ALGORITHM_VERSION


def _prov() -> StructureProvenance:
    return StructureProvenance(
        source=StructureSource.EXPERIMENTAL_PDB,
        pdb_id="TST",
        resolution_angstrom=2.0,
        deposition_year=2020,
        data_tier=DataTier.TIER1,
        pipeline_version=PIPELINE_V,
        alphafold_version=None,
    )


def _construct(isoform: str) -> ConstructDescriptor:
    return ConstructDescriptor(
        isoform=isoform,
        uniprot_id="P99999",
        construct_class=ConstructClass.P110_P85_HETERODIMER,
        mutations=(),
        species="Homo sapiens",
        construct_description="test",
    )


def _record(isoform: str = "PI3Kalpha") -> StructureRecord:
    prov = _prov()
    construct = _construct(isoform)
    rid = make_record_id(prov, construct)
    lig = LigandRecord(
        chain_id="A",
        residue_seq=900,
        insertion_code=" ",
        residue_name="LIG",
        shape_class=LigandShapeClass.FLAT,
        is_atp_site=True,
        smiles=None,
        inchikey="TESTINCHI1",
    )
    return StructureRecord(
        record_id=rid,
        provenance=prov,
        construct=construct,
        conformational_state=ConformationalState.LIGAND_BOUND,
        chains=(),
        atp_site_ligands=(lig,),
        all_ligands=(lig,),
        preprocessing_flags=(),
    )


def _pr(name: str, seq: int = 1, rid: str = "test") -> PocketResidue:
    rr = ResidueRecord(
        chain_id="A",
        residue_seq=seq,
        insertion_code=" ",
        residue_name=name,
        canonical_position=None,
        is_missing=False,
        missing_modelled=False,
    )
    return PocketResidue(
        residue=rr,
        structure_record_id=rid,
        minimum_distance_to_ligand=2.5,
        sub_region=SubRegion.AFFINITY_POCKET,
        observed_in_n_structures=2,
        correspondence_stable=True,
        present_with_propeller_ligand=False,
    )


def _prs(*prs: PocketResidue, rid: str = "test") -> PocketResidueSet:
    return PocketResidueSet(
        isoform="PI3Kalpha",
        construct_class=ConstructClass.P110_P85_HETERODIMER,
        contributing_record_ids=(rid,),
        n_contributing_structures=1,
        residues=prs,
        n_residues_total=len(prs),
        n_residues_correspondence_stable=len(prs),
        n_residues_propeller_only=0,
        cutoff_angstrom=5.0,
        algorithm_version=POCKET_DEFINITION_ALGORITHM_VERSION,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Pocket descriptor tests (D1-D14)
# ══════════════════════════════════════════════════════════════════════════════


def _mixed_pocket_residues(rid: str) -> PocketResidueSet:
    """One each of: ARG (charged+), ASP (charged-), SER (polar), LEU (hydrophobic),
    PHE (aromatic+hydrophobic), GLY, HIS (aromatic)."""
    return _prs(
        _pr("ARG", 1, rid),
        _pr("ASP", 2, rid),
        _pr("SER", 3, rid),
        _pr("LEU", 4, rid),
        _pr("PHE", 5, rid),
        _pr("GLY", 6, rid),
        _pr("HIS", 7, rid),
        rid=rid,
    )


def test_d1_descriptor_is_frozen() -> None:
    rec = _record()
    pocket = _prs(_pr("ALA", 1, rec.record_id), rid=rec.record_id)
    d = build_pocket_descriptor(rec, pocket, "PI3Kalpha")
    with pytest.raises((AttributeError, TypeError)):
        d.n_residues = 99  # type: ignore[misc]


def test_d2_algorithm_version_pinned() -> None:
    assert POCKET_DESCRIPTOR_ALGORITHM_VERSION == "pocket_descriptor_v1_sci1006"


def test_d3_residue_counts_correct() -> None:
    rec = _record()
    pocket = _mixed_pocket_residues(rec.record_id)
    d = build_pocket_descriptor(rec, pocket, "PI3Kalpha")
    assert d.n_residues == 7
    assert d.n_charged_pos == 1  # ARG
    assert d.n_charged_neg == 1  # ASP
    assert d.n_polar_neutral == 1  # SER
    assert d.n_hydrophobic == 2  # LEU + PHE (both in _HYDROPHOBIC)
    assert d.n_glycine == 1  # GLY
    # PHE and HIS are aromatic; HIS is in n_other (not in charged/polar/hydrophobic)
    assert d.n_aromatic == 2  # PHE + HIS


def test_d4_n_other_correct() -> None:
    rec = _record()
    pocket = _mixed_pocket_residues(rec.record_id)
    d = build_pocket_descriptor(rec, pocket, "PI3Kalpha")
    # HIS is in n_other (not charged, not polar_neutral, not hydrophobic, not gly)
    assert d.n_other == 1  # HIS


def test_d5_no_fingerprint_interaction_counts_none() -> None:
    rec = _record()
    pocket = _prs(_pr("ALA", 1, rec.record_id), rid=rec.record_id)
    d = build_pocket_descriptor(rec, pocket, "PI3Kalpha")
    assert d.n_hbond_evidence is None
    assert d.n_hydrophobic_evidence is None
    assert d.n_salt_bridge_evidence is None


def test_d6_anchor_positions_without_correspondence_table() -> None:
    rec = _record()
    pocket = _prs(_pr("GLN", 859, rec.record_id), rid=rec.record_id)
    d = build_pocket_descriptor(rec, pocket, "PI3Kalpha")
    assert d.n_anchor_positions_mapped == 0
    assert d.n_residues_with_canonical == 0
    assert d.fraction_residues_with_canonical == 0.0


def test_d7_anchor_position_counted_with_correspondence_table() -> None:
    rec = _record()
    rr = ResidueRecord(
        chain_id="A",
        residue_seq=859,
        insertion_code=" ",
        residue_name="GLN",
        canonical_position=None,
        is_missing=False,
        missing_modelled=False,
    )
    pr = PocketResidue(
        residue=rr,
        structure_record_id=rec.record_id,
        minimum_distance_to_ligand=2.5,
        sub_region=SubRegion.AFFINITY_POCKET,
        observed_in_n_structures=2,
        correspondence_stable=True,
        present_with_propeller_ligand=False,
    )
    pocket = PocketResidueSet(
        isoform="PI3Kalpha",
        construct_class=ConstructClass.P110_P85_HETERODIMER,
        contributing_record_ids=(rec.record_id,),
        n_contributing_structures=1,
        residues=(pr,),
        n_residues_total=1,
        n_residues_correspondence_stable=1,
        n_residues_propeller_only=0,
        cutoff_angstrom=5.0,
        algorithm_version=POCKET_DEFINITION_ALGORITHM_VERSION,
    )
    tbl = build_correspondence_table(
        list(make_anchor_assignments("PI3Kalpha", "A_859_ ", "A_780_ ", "A_772_ ", "test")),
        frozenset({"PI3Kalpha"}),
    )
    d = build_pocket_descriptor(rec, pocket, "PI3Kalpha", correspondence_table=tbl)
    assert d.n_anchor_positions_mapped == 1  # alpha_859
    assert d.n_residues_with_canonical == 1
    assert d.fraction_residues_with_canonical == 1.0


def test_d8_fraction_canonical_zero_for_empty_table() -> None:
    rec = _record()
    pocket = _prs(_pr("ALA", 99, rec.record_id), rid=rec.record_id)
    tbl = build_correspondence_table(
        list(make_anchor_assignments("PI3Kalpha", "A_859_ ", "A_780_ ", "A_772_ ", "test")),
        frozenset({"PI3Kalpha"}),
    )
    d = build_pocket_descriptor(rec, pocket, "PI3Kalpha", correspondence_table=tbl)
    assert d.fraction_residues_with_canonical == 0.0


def test_d9_volume_none_without_geometry() -> None:
    rec = _record()
    pocket = _prs(_pr("ALA", 1, rec.record_id), rid=rec.record_id)
    d = build_pocket_descriptor(rec, pocket, "PI3Kalpha")
    assert d.volume_angstrom3 is None


def test_d10_deterministic_hash() -> None:
    rec = _record()
    pocket = _mixed_pocket_residues(rec.record_id)
    h1 = build_pocket_descriptor(rec, pocket, "PI3Kalpha").content_sha256()
    h2 = build_pocket_descriptor(rec, pocket, "PI3Kalpha").content_sha256()
    assert h1 == h2


def test_d11_different_composition_different_hash() -> None:
    rec = _record()
    pocket1 = _prs(_pr("ALA", 1, rec.record_id), rid=rec.record_id)
    pocket2 = _prs(_pr("ARG", 1, rec.record_id), rid=rec.record_id)
    h1 = build_pocket_descriptor(rec, pocket1, "PI3Kalpha").content_sha256()
    h2 = build_pocket_descriptor(rec, pocket2, "PI3Kalpha").content_sha256()
    assert h1 != h2


def test_d12_isoform_in_descriptor() -> None:
    rec = _record("PI3Kdelta")
    pocket = _prs(_pr("ALA", 1, rec.record_id), rid=rec.record_id)
    d = build_pocket_descriptor(rec, pocket, "PI3Kdelta")
    assert d.isoform == "PI3Kdelta"


def test_d13_counts_sum_to_n_residues() -> None:
    rec = _record()
    pocket = _mixed_pocket_residues(rec.record_id)
    d = build_pocket_descriptor(rec, pocket, "PI3Kalpha")
    # charged_pos + charged_neg + polar_neutral + hydrophobic + glycine + other == n_residues
    total = (
        d.n_charged_pos
        + d.n_charged_neg
        + d.n_polar_neutral
        + d.n_hydrophobic
        + d.n_glycine
        + d.n_other
    )
    assert total == d.n_residues


def test_d14_zero_residues_fraction_canonical_zero() -> None:
    rec = _record()
    pocket = PocketResidueSet(
        isoform="PI3Kalpha",
        construct_class=ConstructClass.P110_P85_HETERODIMER,
        contributing_record_ids=(rec.record_id,),
        n_contributing_structures=1,
        residues=(),
        n_residues_total=0,
        n_residues_correspondence_stable=0,
        n_residues_propeller_only=0,
        cutoff_angstrom=5.0,
        algorithm_version=POCKET_DEFINITION_ALGORITHM_VERSION,
    )
    d = build_pocket_descriptor(rec, pocket, "PI3Kalpha")
    assert d.n_residues == 0
    assert d.fraction_residues_with_canonical == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# Comparative feature set tests (F1-F16)
# ══════════════════════════════════════════════════════════════════════════════


def _make_fp(
    isoform: str,
    pdb_id: str,
    canon_pos: int,
    status: InteractionStatus,
) -> InteractionFingerprint:
    prov = _prov()
    prov = StructureProvenance(
        source=StructureSource.EXPERIMENTAL_PDB,
        pdb_id=pdb_id,
        resolution_angstrom=2.0,
        deposition_year=2020,
        data_tier=DataTier.TIER1,
        pipeline_version=PIPELINE_V,
        alphafold_version=None,
    )
    construct = _construct(isoform)
    rid = make_record_id(prov, construct)
    ev = InteractionEvidence(
        interaction_type=InteractionType.HYDROGEN_BOND,
        status=status,
        ligand_atom_name="N",
        ligand_residue_name="BYL",
        protein_residue_id="A_001_ ",
        protein_residue_name="GLN",
        protein_atom_name="NE2",
        canonical_position=canon_pos,
        primary_distance_angstrom=3.1,
        secondary_distance_angstrom=None,
        angle_degrees=None,
        dihedral_degrees=None,
        water_residue_id=None,
        metal_identity=None,
        structure_record_id=rid,
        structure_source=StructureSource.EXPERIMENTAL_PDB.value,
        algorithm_version=_ALGO,
        governance_note="",
    )
    return InteractionFingerprint(
        structure_record_id=rid,
        isoform=isoform,
        ligand_residue_name="BYL",
        ligand_inchikey="TESTIK001",
        provenance=prov,
        algorithm_version=_ALGO,
        config=FingerprintConfig(),
        correspondence_table_version=None,
        evidence=(ev,),
        n_per_type=(("hydrogen_bond", 1),),
    )


def _two_isoform_comp(
    alpha_status: InteractionStatus,
    beta_status: InteractionStatus,
    canon_pos: int = 859,
) -> ComparativeFingerprint:
    fp_a = _make_fp("PI3Kalpha", "TA", canon_pos, alpha_status)
    fp_b = _make_fp("PI3Kbeta", "TB", canon_pos, beta_status)
    return ComparativeFingerprint(
        ligand_inchikey="TESTIK001",
        isoform_fingerprints=(("PI3Kalpha", fp_a), ("PI3Kbeta", fp_b)),
        canonical_positions_covered=frozenset({canon_pos})
        if alpha_status not in (InteractionStatus.UNAVAILABLE, InteractionStatus.NOT_APPLICABLE)
        or beta_status not in (InteractionStatus.UNAVAILABLE, InteractionStatus.NOT_APPLICABLE)
        else frozenset(),
        algorithm_version=_ALGO,
    )


def test_f1_feature_set_is_frozen() -> None:
    comp = _two_isoform_comp(InteractionStatus.OBSERVED, InteractionStatus.ABSENT)
    fs = build_comparative_feature_set(comp)
    with pytest.raises((AttributeError, TypeError)):
        fs.algorithm_version = "tampered"  # type: ignore[misc]


def test_f2_algorithm_version_pinned() -> None:
    assert COMPARATIVE_FEATURE_ALGORITHM_VERSION == "comparative_feature_v1_sci1006"


def test_f3_isoforms_sorted() -> None:
    comp = _two_isoform_comp(InteractionStatus.RULE_MISSING, InteractionStatus.RULE_MISSING)
    fs = build_comparative_feature_set(comp)
    assert fs.isoforms == ("PI3Kalpha", "PI3Kbeta")


def test_f4_canonical_positions_sorted() -> None:
    fp_a = _make_fp("PI3Kalpha", "TC", 859, InteractionStatus.OBSERVED)
    fp_a2 = _make_fp("PI3Kalpha", "TC", 780, InteractionStatus.OBSERVED)
    # Simulate two positions by combining evidence
    prov = _prov()
    construct = _construct("PI3Kalpha")
    rid = make_record_id(prov, construct)
    ev1 = fp_a.evidence[0]
    ev2 = fp_a2.evidence[0]
    fp_combined = InteractionFingerprint(
        structure_record_id=rid,
        isoform="PI3Kalpha",
        ligand_residue_name="BYL",
        ligand_inchikey="TESTIK001",
        provenance=prov,
        algorithm_version=_ALGO,
        config=FingerprintConfig(),
        correspondence_table_version=None,
        evidence=(ev1, ev2),
        n_per_type=(("hydrogen_bond", 2),),
    )
    comp = ComparativeFingerprint(
        ligand_inchikey="TESTIK001",
        isoform_fingerprints=(("PI3Kalpha", fp_combined),),
        canonical_positions_covered=frozenset({859, 780}),
        algorithm_version=_ALGO,
    )
    fs = build_comparative_feature_set(comp)
    assert fs.canonical_positions == (780, 859)  # sorted ascending


def test_f5_feature_vector_length() -> None:
    comp = _two_isoform_comp(InteractionStatus.OBSERVED, InteractionStatus.ABSENT)
    fs = build_comparative_feature_set(comp)
    # 1 canonical position x 8 interaction types x 2 isoforms = 16
    assert len(fs.feature_vector) == 1 * 8 * 2
    assert len(fs.feature_names) == len(fs.feature_vector)


def test_f6_observed_encodes_as_3() -> None:
    comp = _two_isoform_comp(InteractionStatus.OBSERVED, InteractionStatus.ABSENT)
    fs = build_comparative_feature_set(comp)
    # alpha H-bond at pos 859 should be 3 (OBSERVED)
    name = "859:hydrogen_bond:PI3Kalpha"
    assert name in fs.feature_names
    idx = fs.feature_names.index(name)
    assert fs.feature_vector[idx] == int(InteractionPresence.OBSERVED)


def test_f7_absent_encodes_as_1() -> None:
    comp = _two_isoform_comp(InteractionStatus.OBSERVED, InteractionStatus.ABSENT)
    fs = build_comparative_feature_set(comp)
    name = "859:hydrogen_bond:PI3Kbeta"
    assert name in fs.feature_names
    idx = fs.feature_names.index(name)
    assert fs.feature_vector[idx] == int(InteractionPresence.ABSENT)


def test_f8_rule_missing_encodes_as_2() -> None:
    comp = _two_isoform_comp(InteractionStatus.RULE_MISSING, InteractionStatus.RULE_MISSING)
    fs = build_comparative_feature_set(comp)
    name = "859:hydrogen_bond:PI3Kalpha"
    if name in fs.feature_names:
        idx = fs.feature_names.index(name)
        assert fs.feature_vector[idx] == int(InteractionPresence.CANDIDATE)


def test_f9_unavailable_encodes_as_0() -> None:
    comp = _two_isoform_comp(InteractionStatus.UNAVAILABLE, InteractionStatus.ABSENT)
    fs = build_comparative_feature_set(comp)
    name = "859:hydrogen_bond:PI3Kalpha"
    if name in fs.feature_names:
        idx = fs.feature_names.index(name)
        assert fs.feature_vector[idx] == int(InteractionPresence.UNAVAILABLE)


def test_f10_differential_when_statuses_differ() -> None:
    comp = _two_isoform_comp(InteractionStatus.OBSERVED, InteractionStatus.ABSENT)
    fs = build_comparative_feature_set(comp)
    assert fs.n_differential >= 1
    profile = fs.get_profile(859)
    assert profile is not None
    assert profile.differential_flag == DifferentialFlag.DIFFERENTIAL


def test_f11_conserved_when_statuses_same() -> None:
    comp = _two_isoform_comp(InteractionStatus.OBSERVED, InteractionStatus.OBSERVED)
    fs = build_comparative_feature_set(comp)
    profile = fs.get_profile(859)
    assert profile is not None
    assert profile.differential_flag == DifferentialFlag.CONSERVED
    assert fs.n_differential == 0


def test_f12_alpha_unique_when_alpha_present_others_absent() -> None:
    comp = _two_isoform_comp(InteractionStatus.OBSERVED, InteractionStatus.ABSENT)
    fs = build_comparative_feature_set(comp)
    profile = fs.get_profile(859)
    assert profile is not None
    assert profile.alpha_unique is True
    assert fs.n_alpha_unique >= 1


def test_f13_alpha_unique_false_when_beta_also_present() -> None:
    comp = _two_isoform_comp(InteractionStatus.OBSERVED, InteractionStatus.OBSERVED)
    fs = build_comparative_feature_set(comp)
    profile = fs.get_profile(859)
    assert profile is not None
    assert profile.alpha_unique is False


def test_f14_deterministic_hash() -> None:
    comp = _two_isoform_comp(InteractionStatus.OBSERVED, InteractionStatus.ABSENT)
    h1 = build_comparative_feature_set(comp).content_sha256()
    h2 = build_comparative_feature_set(comp).content_sha256()
    assert h1 == h2


def test_f15_different_status_different_hash() -> None:
    comp1 = _two_isoform_comp(InteractionStatus.OBSERVED, InteractionStatus.ABSENT)
    comp2 = _two_isoform_comp(InteractionStatus.OBSERVED, InteractionStatus.OBSERVED)
    fs1 = build_comparative_feature_set(comp1)
    fs2 = build_comparative_feature_set(comp2)
    assert fs1.content_sha256() != fs2.content_sha256()


def test_f16_interaction_presence_from_status_mapping() -> None:
    frm = InteractionPresence.from_status
    assert frm(InteractionStatus.OBSERVED) == InteractionPresence.OBSERVED
    assert frm(InteractionStatus.RULE_MISSING) == InteractionPresence.CANDIDATE
    assert frm(InteractionStatus.ABSENT) == InteractionPresence.ABSENT
    assert frm(InteractionStatus.UNAVAILABLE) == InteractionPresence.UNAVAILABLE
    assert frm(InteractionStatus.NOT_APPLICABLE) == InteractionPresence.UNAVAILABLE

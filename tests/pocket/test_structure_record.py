"""Tests for SCI1-001 Milestone 2: StructureRecord and provenance models.

Exit criteria:
  (1) StructureRecord and all sub-types are frozen (immutable after creation).
  (2) AlphaFold provenance requires alphafold_version != None.
  (3) Experimental provenance must have alphafold_version == None.
  (4) LIGAND_BOUND state with no ATP-site ligands is a construction error.
  (5) record_id must be non-empty.
  (6) content_sha256 is deterministic (same inputs -> same hash).
  (7) Different records produce different hashes.
  (8) has_propeller_ligand works correctly.
  (9) make_record_id is deterministic and stable.
  (10) is_wild_type works correctly.
"""

from __future__ import annotations

import json

import pytest

from orthosteric.pocket import (
    ConformationalState,
    ConstructClass,
    ConstructDescriptor,
    DataTier,
    LigandRecord,
    LigandShapeClass,
    ResidueRecord,
    StructureProvenance,
    StructureRecord,
    StructureSource,
    make_record_id,
)

PIPELINE_V = "sci1001_v1"


def _prov(
    source: StructureSource = StructureSource.EXPERIMENTAL_PDB,
    pdb_id: str = "2RD0",
    alphafold_version: str | None = None,
) -> StructureProvenance:
    return StructureProvenance(
        source=source,
        pdb_id=pdb_id,
        resolution_angstrom=2.2,
        deposition_year=2007,
        data_tier=DataTier.TIER1,
        pipeline_version=PIPELINE_V,
        alphafold_version=alphafold_version,
    )


def _construct(
    isoform: str = "PI3Kalpha",
    mutations: tuple[str, ...] = (),
    construct_class: ConstructClass = ConstructClass.P110_P85_HETERODIMER,
) -> ConstructDescriptor:
    return ConstructDescriptor(
        isoform=isoform,
        uniprot_id="P42336",
        construct_class=construct_class,
        mutations=mutations,
        species="Homo sapiens",
        construct_description="p110alpha/p85 complex",
    )


def _ligand(
    shape: LigandShapeClass = LigandShapeClass.FLAT,
    residue_name: str = "BYL",
) -> LigandRecord:
    return LigandRecord(
        chain_id="A",
        residue_seq=900,
        insertion_code=" ",
        residue_name=residue_name,
        shape_class=shape,
        is_atp_site=True,
        smiles="CC1=CC=CC=C1",
        inchikey="TESTINCHIKEY0001234",
    )


def _record(
    prov: StructureProvenance | None = None,
    construct: ConstructDescriptor | None = None,
    ligands: tuple[LigandRecord, ...] = (),
    state: ConformationalState = ConformationalState.APO,
) -> StructureRecord:
    p = prov or _prov()
    c = construct or _construct()
    rid = make_record_id(p, c)
    return StructureRecord(
        record_id=rid,
        provenance=p,
        construct=c,
        conformational_state=state,
        chains=(),
        atp_site_ligands=ligands,
        all_ligands=ligands,
        preprocessing_flags=(),
    )


# ── Exit criterion 1: immutability ───────────────────────────────────────────


def test_structure_record_is_frozen() -> None:
    r = _record()
    with pytest.raises((AttributeError, TypeError)):
        r.record_id = "tampered"  # type: ignore[misc]


def test_provenance_is_frozen() -> None:
    p = _prov()
    with pytest.raises((AttributeError, TypeError)):
        p.pdb_id = "tampered"  # type: ignore[misc]


def test_construct_descriptor_is_frozen() -> None:
    c = _construct()
    with pytest.raises((AttributeError, TypeError)):
        c.isoform = "tampered"  # type: ignore[misc]


# ── Exit criterion 2: AlphaFold provenance validation ────────────────────────


def test_alphafold_source_requires_alphafold_version() -> None:
    with pytest.raises(ValueError, match="alphafold_version must not be None"):
        StructureProvenance(
            source=StructureSource.ALPHAFOLD_GOVERNED_FALLBACK,
            pdb_id="AF-P42336-F1",
            resolution_angstrom=None,
            deposition_year=2022,
            data_tier=DataTier.TIER1,
            pipeline_version=PIPELINE_V,
            alphafold_version=None,  # missing!
        )


def test_alphafold_provenance_with_version_is_valid() -> None:
    prov = StructureProvenance(
        source=StructureSource.ALPHAFOLD_GOVERNED_FALLBACK,
        pdb_id="AF-P42336-F1",
        resolution_angstrom=None,
        deposition_year=2022,
        data_tier=DataTier.TIER1,
        pipeline_version=PIPELINE_V,
        alphafold_version="v4",
    )
    assert prov.alphafold_version == "v4"


# ── Exit criterion 3: experimental provenance must not have alphafold_version ─


def test_experimental_provenance_must_not_have_alphafold_version() -> None:
    with pytest.raises(ValueError, match="must be None for experimental"):
        StructureProvenance(
            source=StructureSource.EXPERIMENTAL_PDB,
            pdb_id="2RD0",
            resolution_angstrom=2.2,
            deposition_year=2007,
            data_tier=DataTier.TIER1,
            pipeline_version=PIPELINE_V,
            alphafold_version="v4",  # must be None for experimental!
        )


# ── Exit criterion 4: LIGAND_BOUND requires ATP-site ligands ─────────────────


def test_ligand_bound_state_requires_atp_site_ligands() -> None:
    with pytest.raises(ValueError, match="must have at least one ATP-site ligand"):
        _record(state=ConformationalState.LIGAND_BOUND, ligands=())


def test_ligand_bound_state_with_ligand_is_valid() -> None:
    r = _record(
        state=ConformationalState.LIGAND_BOUND,
        ligands=(_ligand(),),
    )
    assert len(r.atp_site_ligands) == 1


# ── Exit criterion 5: record_id validation ────────────────────────────────────


def test_empty_record_id_is_rejected() -> None:
    p = _prov()
    c = _construct()
    with pytest.raises(ValueError, match="record_id must be non-empty"):
        StructureRecord(
            record_id="   ",  # whitespace only
            provenance=p,
            construct=c,
            conformational_state=ConformationalState.APO,
            chains=(),
            atp_site_ligands=(),
            all_ligands=(),
            preprocessing_flags=(),
        )


# ── Exit criterion 6: deterministic content hash ─────────────────────────────


def test_content_sha256_is_deterministic() -> None:
    r = _record()
    assert r.content_sha256() == r.content_sha256()


def test_make_record_id_is_deterministic() -> None:
    p = _prov()
    c = _construct()
    assert make_record_id(p, c) == make_record_id(p, c)


# ── Exit criterion 7: different records produce different hashes ──────────────


def test_different_structures_different_hash() -> None:
    r1 = _record(prov=_prov(pdb_id="2RD0"))
    r2 = _record(prov=_prov(pdb_id="3HHM"))
    assert r1.content_sha256() != r2.content_sha256()


def test_different_mutations_different_hash() -> None:
    r1 = _record(construct=_construct(mutations=()))
    r2 = _record(construct=_construct(mutations=("H1047R",)))
    assert r1.content_sha256() != r2.content_sha256()


# ── Exit criterion 8: has_propeller_ligand ────────────────────────────────────


def test_has_propeller_ligand_false_for_flat() -> None:
    r = _record(
        state=ConformationalState.LIGAND_BOUND,
        ligands=(_ligand(shape=LigandShapeClass.FLAT),),
    )
    assert not r.has_propeller_ligand


def test_has_propeller_ligand_true_for_propeller() -> None:
    r = _record(
        state=ConformationalState.LIGAND_BOUND,
        ligands=(_ligand(shape=LigandShapeClass.PROPELLER),),
    )
    assert r.has_propeller_ligand


def test_has_propeller_ligand_true_when_mixed() -> None:
    r = _record(
        state=ConformationalState.LIGAND_BOUND,
        ligands=(
            _ligand(shape=LigandShapeClass.FLAT),
            _ligand(shape=LigandShapeClass.PROPELLER, residue_name="PIK"),
        ),
    )
    assert r.has_propeller_ligand


# ── Exit criterion 9: make_record_id stability ────────────────────────────────


def test_make_record_id_stable_across_construct_order_changes() -> None:
    """Mutations tuple is sorted in make_record_id; order-independence."""
    p = _prov()
    c1 = _construct(mutations=("H1047R", "E545K"))
    c2 = _construct(mutations=("E545K", "H1047R"))
    # Sorted in make_record_id so both produce the same id
    assert make_record_id(p, c1) == make_record_id(p, c2)


def test_make_record_id_length_is_16() -> None:
    p = _prov()
    c = _construct()
    assert len(make_record_id(p, c)) == 16


# ── Exit criterion 10: is_wild_type ──────────────────────────────────────────


def test_wild_type_when_no_mutations() -> None:
    r = _record(construct=_construct(mutations=()))
    assert r.is_wild_type


def test_not_wild_type_when_has_mutations() -> None:
    r = _record(construct=_construct(mutations=("H1047R",)))
    assert not r.is_wild_type


# ── Residue validation ────────────────────────────────────────────────────────


def test_residue_name_must_be_three_letters() -> None:
    with pytest.raises(ValueError, match="3-letter code"):
        ResidueRecord(
            chain_id="A",
            residue_seq=1,
            insertion_code=" ",
            residue_name="GLUTAMINE",  # too long
            canonical_position=None,
            is_missing=False,
            missing_modelled=False,
        )


def test_residue_id_format() -> None:
    r = ResidueRecord(
        chain_id="A",
        residue_seq=859,
        insertion_code=" ",
        residue_name="GLN",
        canonical_position=859,
        is_missing=False,
        missing_modelled=False,
    )
    assert r.residue_id() == "A_859_ "


# ── Canonical dict serialisation ─────────────────────────────────────────────


def test_canonical_dict_is_json_serializable() -> None:
    r = _record(
        state=ConformationalState.LIGAND_BOUND,
        ligands=(_ligand(),),
    )
    d = json.loads(json.dumps(r.to_canonical_dict()))
    assert d["record_id"] == r.record_id

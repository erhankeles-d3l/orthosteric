"""SCI1-009/010/011: Path A pipeline and compliance verification.

SCI1-009: features/ scaffold complete (all modules present and importable).
SCI1-010: Path A representation -- correspondence-free input interface.
SCI1-011: Path A verification on mutated and unseen ATP sites.
"""

from __future__ import annotations

import numpy as np
import pytest
from Bio.PDB.StructureBuilder import StructureBuilder

from orthosteric.features import (
    COMPARATIVE_FEATURE_ALGORITHM_VERSION,
    CONTACT_MAP_ALGORITHM_VERSION,
    FEATURE_CONFIG_ALGORITHM_VERSION,
    FINGERPRINT_ALGORITHM_VERSION,
    MD_INTERFACE_ALGORITHM_VERSION,
    PIPELINE_ALGORITHM_VERSION,
    POCKET_DESCRIPTOR_ALGORITHM_VERSION,
    STRUCTURAL_GRAPH_ALGORITHM_VERSION,
    FeaturePipelineResult,
    MDStatus,
    build_comparative_features,
    compute_features,
    is_path_a_compliant,
)
from orthosteric.features._interaction_fingerprint import InteractionStatus
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

PIPELINE_V = "sci1011_test"


def _build(residues: list[dict]) -> object:  # type: ignore[type-arg]
    sb = StructureBuilder()
    sb.init_structure("T")
    sb.init_model(0)
    cur = None
    for r in residues:
        chain = str(r["chain"])
        if chain != cur:
            sb.init_chain(chain)
            cur = chain
        sb.init_residue(str(r["name"]), str(r.get("het", " ")),
                        int(r["seq"]), str(r.get("ins", " ")))  # type: ignore[arg-type]
        for aname, (x, y, z) in dict(r["atoms"]).items():  # type: ignore[arg-type]
            el = dict(r.get("elements", {})).get(aname, aname[0])  # type: ignore[arg-type]
            sb.init_atom(aname, np.array([x, y, z], dtype=np.float64),
                         1.0, 1.0, " ", aname, None, element=el)
    return sb.get_structure()


def _prov(pdb_id: str = "TST") -> StructureProvenance:
    return StructureProvenance(
        source=StructureSource.EXPERIMENTAL_PDB, pdb_id=pdb_id,
        resolution_angstrom=2.0, deposition_year=2020,
        data_tier=DataTier.TIER1, pipeline_version=PIPELINE_V, alphafold_version=None,
    )


def _record(isoform: str = "PI3Kalpha", pdb_id: str = "TST") -> StructureRecord:
    prov = _prov(pdb_id)
    construct = ConstructDescriptor(
        isoform=isoform, uniprot_id="P42336",
        construct_class=ConstructClass.P110_P85_HETERODIMER, mutations=(),
        species="Homo sapiens", construct_description="test",
    )
    rid = make_record_id(prov, construct)
    lig = LigandRecord(
        chain_id="A", residue_seq=900, insertion_code=" ", residue_name="LIG",
        shape_class=LigandShapeClass.FLAT, is_atp_site=True, smiles=None, inchikey="TK001",
    )
    return StructureRecord(
        record_id=rid, provenance=prov, construct=construct,
        conformational_state=ConformationalState.LIGAND_BOUND,
        chains=(), atp_site_ligands=(lig,), all_ligands=(lig,), preprocessing_flags=(),
    )


def _pr(name: str, seq: int, rid: str) -> PocketResidue:
    rr = ResidueRecord(chain_id="A", residue_seq=seq, insertion_code=" ",
                       residue_name=name, canonical_position=None,
                       is_missing=False, missing_modelled=False)
    return PocketResidue(residue=rr, structure_record_id=rid,
                         minimum_distance_to_ligand=2.5, sub_region=SubRegion.AFFINITY_POCKET,
                         observed_in_n_structures=2, correspondence_stable=True,
                         present_with_propeller_ligand=False)


def _prs(*prs: PocketResidue, rid: str, isoform: str = "PI3Kalpha") -> PocketResidueSet:
    return PocketResidueSet(
        isoform=isoform, construct_class=ConstructClass.P110_P85_HETERODIMER,
        contributing_record_ids=(rid,), n_contributing_structures=1,
        residues=prs, n_residues_total=len(prs),
        n_residues_correspondence_stable=len(prs), n_residues_propeller_only=0,
        cutoff_angstrom=5.0, algorithm_version=POCKET_DEFINITION_ALGORITHM_VERSION,
    )


def _run(
    isoform: str = "PI3Kalpha",
    prot_name: str = "ALA",
    prot_seq: int = 1,
    pdb_id: str = "TST",
    with_table: bool = False,
) -> FeaturePipelineResult:
    bio = _build([
        {"chain": "A", "seq": 900, "het": "H_LIG", "name": "LIG",
         "atoms": {"N": (0.0, 0.0, 0.0), "C": (1.0, 0.0, 0.0)}},
        {"chain": "A", "seq": prot_seq, "name": prot_name,
         "atoms": {"N": (3.5, 0.0, 0.0), "CA": (4.5, 0.0, 0.0),
                   "C": (5.5, 0.0, 0.0), "O": (6.0, 1.0, 0.0), "CB": (4.5, 1.0, 0.0)}},
    ])
    rec = _record(isoform, pdb_id)
    pr = _pr(prot_name, prot_seq, rec.record_id)
    pocket = _prs(pr, rid=rec.record_id, isoform=isoform)
    lig = LigandRecord(chain_id="A", residue_seq=900, insertion_code=" ", residue_name="LIG",
                       shape_class=LigandShapeClass.FLAT, is_atp_site=True,
                       smiles=None, inchikey="TK001")
    tbl = None
    if with_table:
        tbl = build_correspondence_table(
            list(make_anchor_assignments(isoform, "A_1_ ", "A_780_ ", "A_772_ ", "test")),
            frozenset({isoform}),
        )
    return compute_features(bio, rec, pocket, lig, isoform, correspondence_table=tbl)


# ── P1-P4: Basic pipeline integrity ─────────────────────────────────────────

def test_p1_result_is_frozen() -> None:
    with pytest.raises((AttributeError, TypeError)):
        _run().isoform = "tampered"  # type: ignore[misc]


def test_p2_algorithm_version_pinned() -> None:
    assert PIPELINE_ALGORITHM_VERSION == "feature_pipeline_v1_sci1010"


def test_p3_all_components_present() -> None:
    r = _run()
    assert r.fingerprint is not None
    assert r.contact_map is not None
    assert r.structural_graph is not None
    assert r.descriptor is not None
    assert r.md_placeholder is not None


def test_p4_is_path_a_compliant() -> None:
    assert is_path_a_compliant(_run())


# ── P5-P8: Path A — no correspondence table required ─────────────────────────

def test_p5_runs_without_correspondence_table() -> None:
    r = _run(isoform="mTOR", pdb_id="MTOR_TST", with_table=False)
    assert r.correspondence_provided is False


def test_p6_canonical_positions_none_without_table() -> None:
    r = _run(with_table=False)
    for ev in r.fingerprint.evidence:
        assert ev.canonical_position is None


def test_p7_canonical_positions_annotated_with_table() -> None:
    r = _run(prot_seq=1, with_table=True)
    hb_at_859 = [e for e in r.fingerprint.evidence if e.canonical_position == 859]
    assert len(hb_at_859) > 0


def test_p8_path_a_note_present() -> None:
    r = _run()
    assert "Path A" in r.path_a_note
    assert len(r.path_a_note) > 50


# ── P9-P11: SCI1-011 -- mutated and unseen structures ─────────────────────────

def test_p9_mutated_structure_accepted() -> None:
    """H1047R simulated: ARG at 1047 instead of HIS. Must succeed."""
    bio = _build([
        {"chain": "A", "seq": 900, "het": "H_LIG", "name": "LIG",
         "atoms": {"N": (0.0, 0.0, 0.0), "C": (1.0, 0.0, 0.0)}},
        {"chain": "A", "seq": 1047, "name": "ARG",
         "atoms": {"N": (3.5, 0.0, 0.0), "CA": (4.5, 0.0, 0.0),
                   "C": (5.5, 0.0, 0.0), "O": (6.0, 1.0, 0.0), "CB": (4.5, 1.0, 0.0),
                   "CG": (4.5, 2.0, 0.0), "CD": (4.5, 3.0, 0.0),
                   "NE": (4.5, 4.0, 0.0), "CZ": (4.5, 5.0, 0.0),
                   "NH1": (3.5, 5.5, 0.0), "NH2": (5.5, 5.5, 0.0)}},
    ])
    rec = _record("PI3Kalpha_H1047R")
    pr = _pr("ARG", 1047, rec.record_id)
    pocket = _prs(pr, rid=rec.record_id, isoform="PI3Kalpha_H1047R")
    lig = LigandRecord(chain_id="A", residue_seq=900, insertion_code=" ", residue_name="LIG",
                       shape_class=LigandShapeClass.FLAT, is_atp_site=True,
                       smiles=None, inchikey="TK001")
    result = compute_features(bio, rec, pocket, lig, "PI3Kalpha_H1047R")
    assert is_path_a_compliant(result)


def test_p10_unseen_atp_site_accepted() -> None:
    """Tier 2 / second-family: Vps34. Must run without error."""
    r = _run(isoform="Vps34", pdb_id="VPS34_TST")
    assert r.isoform == "Vps34"
    assert is_path_a_compliant(r)
    assert r.correspondence_provided is False


def test_p11_variable_pocket_size() -> None:
    """14 pocket residues -- no fixed-size assumption."""
    recs: list[dict] = [
        {"chain": "A", "seq": 900, "het": "H_LIG", "name": "LIG",
         "atoms": {"N": (0.0, 0.0, 0.0), "C": (1.0, 0.0, 0.0)}},
    ]
    for i in range(1, 15):
        recs.append({
            "chain": "A", "seq": i, "name": "ALA",
            "atoms": {"N": (float(i) * 3, 0.0, 0.0), "CA": (float(i) * 3 + 1, 0.0, 0.0),
                      "C": (float(i) * 3 + 2, 0.0, 0.0), "O": (float(i) * 3 + 2.5, 1.0, 0.0)},
        })
    bio = _build(recs)
    rec = _record()
    prs = [_pr("ALA", i, rec.record_id) for i in range(1, 15)]
    pocket = _prs(*prs, rid=rec.record_id)
    lig = LigandRecord(chain_id="A", residue_seq=900, insertion_code=" ", residue_name="LIG",
                       shape_class=LigandShapeClass.FLAT, is_atp_site=True,
                       smiles=None, inchikey="TK001")
    result = compute_features(bio, rec, pocket, lig, "PI3Kalpha")
    assert result.descriptor.n_residues == 14
    assert is_path_a_compliant(result)


# ── P12-P14: Comparative features integration ─────────────────────────────────

def test_p12_comparative_features_from_two_isoforms() -> None:
    ra = _run("PI3Kalpha", with_table=True)
    rb = _run("PI3Kbeta", with_table=True, pdb_id="TST2")
    comp = build_comparative_features(
        [("PI3Kalpha", ra), ("PI3Kbeta", rb)], ligand_inchikey="TK001"
    )
    assert "PI3Kalpha" in comp.isoforms
    assert "PI3Kbeta" in comp.isoforms


def test_p13_md_placeholder_not_computed() -> None:
    r = _run()
    assert r.md_placeholder.ensemble_metadata.status == MDStatus.NOT_COMPUTED
    assert not r.md_placeholder.is_computed()


def test_p14_feature_config_all_rule_missing() -> None:
    assert _run().feature_config.all_thresholds_rule_missing()


# ── P15-P16: SCI1-009 scaffold completeness ──────────────────────────────────

def test_p15_scaffold_all_version_constants_present() -> None:
    """SCI1-009: all features/ module version constants importable."""
    assert PIPELINE_ALGORITHM_VERSION.startswith("feature_pipeline_v1")
    assert FINGERPRINT_ALGORITHM_VERSION.startswith("interaction_fp_v1")
    assert CONTACT_MAP_ALGORITHM_VERSION.startswith("contact_map_v1")
    assert STRUCTURAL_GRAPH_ALGORITHM_VERSION.startswith("structural_graph_v1")
    assert POCKET_DESCRIPTOR_ALGORITHM_VERSION.startswith("pocket_descriptor_v1")
    assert COMPARATIVE_FEATURE_ALGORITHM_VERSION.startswith("comparative_feature_v1")
    assert MD_INTERFACE_ALGORITHM_VERSION.startswith("md_interface_v1")
    assert FEATURE_CONFIG_ALGORITHM_VERSION.startswith("feature_config_v1")


def test_p16_unavailable_distinct_from_absent() -> None:
    """UNAVAILABLE != ABSENT (Constitution §4.2 item 5: must distinguish)."""
    assert InteractionStatus.UNAVAILABLE.value == "unavailable"
    assert InteractionStatus.ABSENT.value == "absent"

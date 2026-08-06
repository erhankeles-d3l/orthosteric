"""SCI1-005 tests: contact maps and structural graph.

All structures synthetic (no PDB files). Values explicitly stated.
Exit criteria C1-C14 (contact map) and G1-G16 (graph).
"""

from __future__ import annotations

import numpy as np
import pytest
from Bio.PDB.StructureBuilder import StructureBuilder

from orthosteric.features import (
    CONTACT_MAP_ALGORITHM_VERSION,
    STRUCTURAL_GRAPH_ALGORITHM_VERSION,
    ContactMapConfig,
    ContactStatus,
    EdgeType,
    NodeType,
    StructuralGraphConfig,
    compute_contact_map,
    compute_structural_graph,
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

PIPELINE_V = "sci1005_test_v1"


# ── Shared synthetic structure helpers ───────────────────────────────────────


def _add(
    sb: StructureBuilder,
    _chain: str,
    het: str,
    seq: int,
    ins: str,
    name: str,
    atoms: dict[str, tuple[float, float, float]],
    elements: dict[str, str] | None = None,
) -> None:
    sb.init_residue(name, het, seq, ins)
    overrides = elements or {}
    for aname, (x, y, z) in atoms.items():
        el = overrides.get(aname, aname[0])
        sb.init_atom(
            aname, np.array([x, y, z], dtype=np.float64), 1.0, 1.0, " ", aname, None, element=el
        )


def _build(residues: list[dict]) -> object:  # type: ignore[type-arg]
    sb = StructureBuilder()
    sb.init_structure("T")
    sb.init_model(0)
    cur: str | None = None
    for r in residues:
        chain = str(r["chain"])
        if chain != cur:
            sb.init_chain(chain)
            cur = chain
        _add(
            sb,
            chain,
            str(r.get("het", " ")),
            int(r["seq"]),  # type: ignore[arg-type]
            str(r.get("ins", " ")),
            str(r["name"]),
            dict(r["atoms"]),  # type: ignore[arg-type]
            dict(r.get("elements", {})),
        )  # type: ignore[arg-type]
    return sb.get_structure()


def _prov() -> StructureProvenance:
    return StructureProvenance(
        source=StructureSource.EXPERIMENTAL_PDB,
        pdb_id="TEST",
        resolution_angstrom=2.0,
        deposition_year=2020,
        data_tier=DataTier.TIER1,
        pipeline_version=PIPELINE_V,
        alphafold_version=None,
    )


def _construct(isoform: str = "PI3Kalpha") -> ConstructDescriptor:
    return ConstructDescriptor(
        isoform=isoform,
        uniprot_id="P42336",
        construct_class=ConstructClass.P110_P85_HETERODIMER,
        mutations=(),
        species="Homo sapiens",
        construct_description="test",
    )


def _record() -> StructureRecord:
    prov = _prov()
    construct = _construct()
    rid = make_record_id(prov, construct)
    dummy_lig = _ligand("LIG")
    return StructureRecord(
        record_id=rid,
        provenance=prov,
        construct=construct,
        conformational_state=ConformationalState.LIGAND_BOUND,
        chains=(),
        atp_site_ligands=(dummy_lig,),
        all_ligands=(dummy_lig,),
        preprocessing_flags=(),
    )


def _ligand(rname: str = "LIG") -> LigandRecord:
    return LigandRecord(
        chain_id="A",
        residue_seq=900,
        insertion_code=" ",
        residue_name=rname,
        shape_class=LigandShapeClass.FLAT,
        is_atp_site=True,
        smiles=None,
        inchikey="TESTINCHI00000001",
    )


def _pr(chain: str = "A", seq: int = 1, name: str = "ALA", rid: str = "test") -> PocketResidue:
    rr = ResidueRecord(
        chain_id=chain,
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


def _two_residue_structure() -> tuple[object, StructureRecord, PocketResidueSet]:
    """Two residues: ALA at (0,0,0) and GLY at (5,0,0) -> min dist = ~4.0 A (CB-CA)."""
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 1,
                "name": "ALA",
                "atoms": {
                    "N": (0.0, 0.0, 0.0),
                    "CA": (1.0, 0.0, 0.0),
                    "C": (2.0, 0.0, 0.0),
                    "O": (2.5, 1.0, 0.0),
                    "CB": (1.0, 1.0, 0.0),
                },
            },
            {
                "chain": "A",
                "seq": 2,
                "name": "GLY",
                "atoms": {
                    "N": (5.0, 0.0, 0.0),
                    "CA": (6.0, 0.0, 0.0),
                    "C": (7.0, 0.0, 0.0),
                    "O": (7.5, 1.0, 0.0),
                },
            },
        ]
    )
    rec = _record()
    pr1 = _pr("A", 1, "ALA", rid=rec.record_id)
    pr2 = _pr("A", 2, "GLY", rid=rec.record_id)
    pocket = _prs(pr1, pr2, rid=rec.record_id)
    return bio, rec, pocket


# ══════════════════════════════════════════════════════════════════════════════
# Contact map tests (C1-C14)
# ══════════════════════════════════════════════════════════════════════════════


def test_c1_contact_map_is_frozen() -> None:
    bio, rec, pocket = _two_residue_structure()
    cm = compute_contact_map(bio, rec, pocket, isoform="PI3Kalpha")
    with pytest.raises((AttributeError, TypeError)):
        cm.algorithm_version = "tampered"  # type: ignore[misc]


def test_c2_algorithm_version_pinned() -> None:
    assert CONTACT_MAP_ALGORITHM_VERSION == "contact_map_v1_sci1005"


def test_c3_res_res_distance_between_two_residues() -> None:
    bio, rec, pocket = _two_residue_structure()
    cm = compute_contact_map(bio, rec, pocket, isoform="PI3Kalpha")
    # ALA_N at (0,0,0) to GLY_N at (5,0,0): dist = 5.0 A (minimum heavy-atom)
    d = cm.res_res.distance("A_1_ ", "A_2_ ")
    assert d is not None
    assert d <= 5.0  # N-N at 5.0 A


def test_c4_res_res_rule_missing_without_threshold() -> None:
    bio, rec, pocket = _two_residue_structure()
    cm = compute_contact_map(bio, rec, pocket, isoform="PI3Kalpha")
    statuses = {st for _, _, _, st in cm.res_res.entries}
    assert ContactStatus.RULE_MISSING.value in statuses


def test_c5_res_res_contact_with_threshold() -> None:
    bio, rec, pocket = _two_residue_structure()
    cfg = ContactMapConfig(contact_cutoff_angstrom=6.0)
    cm = compute_contact_map(bio, rec, pocket, isoform="PI3Kalpha", config=cfg)
    statuses = {st for _, _, _, st in cm.res_res.entries}
    assert ContactStatus.CONTACT.value in statuses


def test_c6_res_res_noncontact_tight_threshold() -> None:
    bio, rec, pocket = _two_residue_structure()
    cfg = ContactMapConfig(contact_cutoff_angstrom=1.0)  # all pairs > 1.0 A
    cm = compute_contact_map(bio, rec, pocket, isoform="PI3Kalpha", config=cfg)
    statuses = {st for _, _, _, st in cm.res_res.entries}
    assert ContactStatus.NONCONTACT.value in statuses


def test_c7_ligand_residue_map_present_when_ligand_found() -> None:
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"C1": (3.0, 0.0, 0.0), "N1": (4.0, 0.0, 0.0)},
            },
            {
                "chain": "A",
                "seq": 1,
                "name": "ALA",
                "atoms": {
                    "N": (0.0, 0.0, 0.0),
                    "CA": (1.0, 0.0, 0.0),
                    "C": (2.0, 0.0, 0.0),
                    "O": (2.5, 1.0, 0.0),
                    "CB": (1.0, 1.0, 0.0),
                },
            },
        ]
    )
    rec = _record()
    pr = _pr("A", 1, "ALA", rid=rec.record_id)
    pocket = _prs(pr, rid=rec.record_id)
    cm = compute_contact_map(bio, rec, pocket, ligand_record=_ligand("LIG"), isoform="PI3Kalpha")
    assert cm.lig_res is not None
    assert len(cm.lig_res.ligand_atom_names) == 2  # C1 and N1


def test_c8_ligand_residue_map_none_when_absent() -> None:
    bio, rec, pocket = _two_residue_structure()
    cm = compute_contact_map(bio, rec, pocket, ligand_record=None, isoform="PI3Kalpha")
    assert cm.lig_res is None


def test_c9_lig_res_distance_preserved() -> None:
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"C1": (0.0, 0.0, 0.0)},
            },
            {
                "chain": "A",
                "seq": 1,
                "name": "ALA",
                "atoms": {
                    "N": (4.0, 0.0, 0.0),
                    "CA": (5.0, 0.0, 0.0),
                    "C": (6.0, 0.0, 0.0),
                    "O": (6.5, 1.0, 0.0),
                    "CB": (5.0, 1.0, 0.0),
                },
            },
        ]
    )
    rec = _record()
    pr = _pr("A", 1, "ALA", rid=rec.record_id)
    pocket = _prs(pr, rid=rec.record_id)
    cm = compute_contact_map(bio, rec, pocket, ligand_record=_ligand("LIG"), isoform="PI3Kalpha")
    assert cm.lig_res is not None
    d = cm.lig_res.distance("C1", "A_1_ ")
    assert d is not None
    assert abs(d - 4.0) < 0.01  # C1(0,0,0) to N(4,0,0) = 4.0 A


def test_c10_canonical_position_in_res_res() -> None:
    bio, rec, pocket = _two_residue_structure()
    tbl = build_correspondence_table(
        list(make_anchor_assignments("PI3Kalpha", "A_1_ ", "A_780_ ", "A_772_ ", "test")),
        frozenset({"PI3Kalpha"}),
    )
    cm = compute_contact_map(bio, rec, pocket, isoform="PI3Kalpha", correspondence_table=tbl)
    # A_1_ should have canonical position = 859 (the alpha_859 anchor)
    idx = list(cm.res_res.residue_ids).index("A_1_ ")
    assert cm.res_res.canonical_positions[idx] == 859


def test_c11_symmetric_distance() -> None:
    bio, rec, pocket = _two_residue_structure()
    cm = compute_contact_map(bio, rec, pocket, isoform="PI3Kalpha")
    d_ab = cm.res_res.distance("A_1_ ", "A_2_ ")
    d_ba = cm.res_res.distance("A_2_ ", "A_1_ ")
    assert d_ab == d_ba


def test_c12_deterministic_hash() -> None:
    bio, rec, pocket = _two_residue_structure()
    h1 = compute_contact_map(bio, rec, pocket, isoform="PI3Kalpha").content_sha256()
    h2 = compute_contact_map(bio, rec, pocket, isoform="PI3Kalpha").content_sha256()
    assert h1 == h2


def test_c13_different_structure_different_hash() -> None:
    bio1, rec, pocket = _two_residue_structure()
    bio2 = _build(
        [
            {
                "chain": "A",
                "seq": 1,
                "name": "ALA",
                "atoms": {
                    "N": (0.0, 0.0, 0.0),
                    "CA": (1.0, 0.0, 0.0),
                    "C": (2.0, 0.0, 0.0),
                    "O": (2.5, 1.0, 0.0),
                    "CB": (1.0, 1.0, 0.0),
                },
            },
            {
                "chain": "A",
                "seq": 2,
                "name": "GLY",
                "atoms": {
                    "N": (3.0, 0.0, 0.0),
                    "CA": (4.0, 0.0, 0.0),  # moved
                    "C": (5.0, 0.0, 0.0),
                    "O": (5.5, 1.0, 0.0),
                },
            },
        ]
    )
    h1 = compute_contact_map(bio1, rec, pocket, isoform="PI3Kalpha").content_sha256()
    h2 = compute_contact_map(bio2, rec, pocket, isoform="PI3Kalpha").content_sha256()
    assert h1 != h2


def test_c14_n_residues_correct() -> None:
    bio, rec, pocket = _two_residue_structure()
    cm = compute_contact_map(bio, rec, pocket, isoform="PI3Kalpha")
    assert cm.res_res.n_residues() == 2


# ══════════════════════════════════════════════════════════════════════════════
# Structural graph tests (G1-G16)
# ══════════════════════════════════════════════════════════════════════════════


def _standard_graph_structure() -> tuple[object, StructureRecord, PocketResidueSet, LigandRecord]:
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"C1": (0.0, 0.0, 0.0), "N1": (1.0, 0.0, 0.0)},
            },
            {
                "chain": "A",
                "seq": 1,
                "name": "ALA",
                "atoms": {
                    "N": (4.0, 0.0, 0.0),
                    "CA": (5.0, 0.0, 0.0),
                    "C": (6.0, 0.0, 0.0),
                    "O": (6.5, 1.0, 0.0),
                    "CB": (5.0, 1.0, 0.0),
                },
            },
            {
                "chain": "A",
                "seq": 2,
                "name": "GLY",
                "atoms": {
                    "N": (8.0, 0.0, 0.0),
                    "CA": (9.0, 0.0, 0.0),
                    "C": (10.0, 0.0, 0.0),
                    "O": (10.5, 1.0, 0.0),
                },
            },
        ]
    )
    rec = _record()
    pr1 = _pr("A", 1, "ALA", rid=rec.record_id)
    pr2 = _pr("A", 2, "GLY", rid=rec.record_id)
    pocket = _prs(pr1, pr2, rid=rec.record_id)
    lig = _ligand("LIG")
    return bio, rec, pocket, lig


def test_g1_graph_is_frozen() -> None:
    bio, rec, pocket, lig = _standard_graph_structure()
    g = compute_structural_graph(bio, rec, pocket, lig, isoform="PI3Kalpha")
    with pytest.raises((AttributeError, TypeError)):
        g.algorithm_version = "tampered"  # type: ignore[misc]


def test_g2_algorithm_version_pinned() -> None:
    assert STRUCTURAL_GRAPH_ALGORITHM_VERSION == "structural_graph_v1_sci1005"


def test_g3_residue_nodes_created() -> None:
    bio, rec, pocket, lig = _standard_graph_structure()
    g = compute_structural_graph(bio, rec, pocket, lig, isoform="PI3Kalpha")
    assert g.n_residue_nodes == 2


def test_g4_ligand_atom_nodes_created() -> None:
    bio, rec, pocket, lig = _standard_graph_structure()
    g = compute_structural_graph(bio, rec, pocket, lig, isoform="PI3Kalpha")
    assert g.n_ligand_atom_nodes == 2  # C1 and N1


def test_g5_no_ligand_nodes_when_ligand_absent() -> None:
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 1,
                "name": "ALA",
                "atoms": {
                    "N": (0.0, 0.0, 0.0),
                    "CA": (1.0, 0.0, 0.0),
                    "C": (2.0, 0.0, 0.0),
                    "O": (2.5, 1.0, 0.0),
                },
            },
        ]
    )
    rec = _record()
    pr = _pr("A", 1, "ALA", rid=rec.record_id)
    pocket = _prs(pr, rid=rec.record_id)
    g = compute_structural_graph(bio, rec, pocket, ligand_record=None, isoform="PI3Kalpha")
    assert g.n_ligand_atom_nodes == 0


def test_g6_water_node_created_for_hoh() -> None:
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"C1": (0.0, 0.0, 0.0)},
            },
            {
                "chain": "A",
                "seq": 1,
                "name": "ALA",
                "atoms": {
                    "N": (4.0, 0.0, 0.0),
                    "CA": (5.0, 0.0, 0.0),
                    "C": (6.0, 0.0, 0.0),
                    "O": (6.5, 1.0, 0.0),
                },
            },
            {"chain": "A", "seq": 300, "het": "W", "name": "HOH", "atoms": {"O": (2.0, 0.0, 0.0)}},
        ]
    )
    rec = _record()
    pr = _pr("A", 1, "ALA", rid=rec.record_id)
    pocket = _prs(pr, rid=rec.record_id)
    g = compute_structural_graph(bio, rec, pocket, _ligand("LIG"), isoform="PI3Kalpha")
    assert g.n_water_nodes == 1
    water_nodes = g.get_nodes_by_type(NodeType.WATER)
    assert len(water_nodes) == 1
    assert water_nodes[0].element == "O"


def test_g7_spatial_edges_created() -> None:
    bio, rec, pocket, lig = _standard_graph_structure()
    g = compute_structural_graph(bio, rec, pocket, lig, isoform="PI3Kalpha")
    assert g.n_spatial_edges > 0


def test_g8_spatial_edge_rule_missing_without_threshold() -> None:
    bio, rec, pocket, lig = _standard_graph_structure()
    g = compute_structural_graph(bio, rec, pocket, lig, isoform="PI3Kalpha")
    spatial = g.get_edges_by_type(EdgeType.SPATIAL)
    assert all(e.status == "rule_missing" for e in spatial)


def test_g9_spatial_edge_contact_with_threshold() -> None:
    bio, rec, pocket, lig = _standard_graph_structure()
    cfg = StructuralGraphConfig(spatial_cutoff_angstrom=8.0)
    g = compute_structural_graph(bio, rec, pocket, lig, isoform="PI3Kalpha", config=cfg)
    spatial = g.get_edges_by_type(EdgeType.SPATIAL)
    assert any(e.status == "contact" for e in spatial)


def test_g10_nodes_sorted_by_node_id() -> None:
    bio, rec, pocket, lig = _standard_graph_structure()
    g = compute_structural_graph(bio, rec, pocket, lig, isoform="PI3Kalpha")
    ids = [n.node_id for n in g.nodes]
    assert ids == sorted(ids)


def test_g11_edges_sorted() -> None:
    bio, rec, pocket, lig = _standard_graph_structure()
    g = compute_structural_graph(bio, rec, pocket, lig, isoform="PI3Kalpha")
    keys = [(e.node_id_a, e.node_id_b, e.edge_type) for e in g.edges]
    assert keys == sorted(keys)


def test_g12_no_self_loop_edges() -> None:
    bio, rec, pocket, lig = _standard_graph_structure()
    g = compute_structural_graph(bio, rec, pocket, lig, isoform="PI3Kalpha")
    for e in g.edges:
        assert e.node_id_a != e.node_id_b


def test_g13_canonical_position_in_residue_node() -> None:
    bio, rec, pocket, lig = _standard_graph_structure()
    tbl = build_correspondence_table(
        list(make_anchor_assignments("PI3Kalpha", "A_1_ ", "A_780_ ", "A_772_ ", "test")),
        frozenset({"PI3Kalpha"}),
    )
    g = compute_structural_graph(
        bio, rec, pocket, lig, isoform="PI3Kalpha", correspondence_table=tbl
    )
    res_nodes = g.get_nodes_by_type(NodeType.RESIDUE)
    a1 = next((n for n in res_nodes if n.residue_id == "A_1_ "), None)
    assert a1 is not None
    assert a1.canonical_position == 859


def test_g14_deterministic_hash() -> None:
    bio, rec, pocket, lig = _standard_graph_structure()
    h1 = compute_structural_graph(bio, rec, pocket, lig, isoform="PI3Kalpha").content_sha256()
    h2 = compute_structural_graph(bio, rec, pocket, lig, isoform="PI3Kalpha").content_sha256()
    assert h1 == h2


def test_g15_adjacency_matches_edge_count() -> None:
    bio, rec, pocket, lig = _standard_graph_structure()
    g = compute_structural_graph(bio, rec, pocket, lig, isoform="PI3Kalpha")
    adj = g.adjacency()
    assert len(adj) == len(g.edges)


def test_g16_node_types_present() -> None:
    bio, rec, pocket, lig = _standard_graph_structure()
    g = compute_structural_graph(bio, rec, pocket, lig, isoform="PI3Kalpha")
    ntypes = {n.node_type for n in g.nodes}
    assert NodeType.RESIDUE in ntypes
    assert NodeType.LIGAND_ATOM in ntypes

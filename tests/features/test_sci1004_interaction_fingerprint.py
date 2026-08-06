"""SCI1-004 tests: protein-ligand interaction fingerprints.

All structures are synthetic (no PDB files required). Values explicitly stated.
Exit criteria I1-I32 documented inline.
"""

from __future__ import annotations

import numpy as np
import pytest
from Bio.PDB.StructureBuilder import StructureBuilder

from orthosteric.features import (
    FINGERPRINT_ALGORITHM_VERSION,
    FingerprintConfig,
    InteractionEvidence,
    InteractionFingerprint,
    InteractionStatus,
    InteractionType,
    build_comparative_fingerprint,
    compute_interaction_fingerprint,
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

PIPELINE_V = "sci1004_test_v1"

# Known 2-char element symbols that cannot be inferred from first character alone.
_TWO_CHAR_ELEMENTS = {
    "CL",
    "BR",
    "MG",
    "ZN",
    "CA",
    "FE",
    "CU",
    "NI",
    "CO",
    "MN",
}


# ── Synthetic structure builder ───────────────────────────────────────────────


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
    """Add one residue. elements overrides auto-detected element for named atoms."""
    sb.init_residue(name, het, seq, ins)
    overrides = elements or {}
    for aname, (x, y, z) in atoms.items():
        el = overrides.get(aname, aname[0])
        sb.init_atom(
            aname,
            np.array([x, y, z], dtype=np.float64),
            1.0,
            1.0,
            " ",
            aname,
            None,
            element=el,
        )


def _build(residues: list[dict]) -> object:
    sb = StructureBuilder()
    sb.init_structure("T")
    sb.init_model(0)
    cur: str | None = None
    for r in residues:
        if r["chain"] != cur:
            sb.init_chain(r["chain"])
            cur = r["chain"]
        _add(
            sb,
            r["chain"],
            r.get("het", " "),
            r["seq"],
            r.get("ins", " "),
            r["name"],
            r["atoms"],
            r.get("elements"),
        )
    return sb.get_structure()


def _prov(
    source: StructureSource = StructureSource.EXPERIMENTAL_PDB,
    pdb_id: str = "TEST",
) -> StructureProvenance:
    return StructureProvenance(
        source=source,
        pdb_id=pdb_id,
        resolution_angstrom=2.0 if source == StructureSource.EXPERIMENTAL_PDB else None,
        deposition_year=2020,
        data_tier=DataTier.TIER1,
        pipeline_version=PIPELINE_V,
        alphafold_version="v4" if source == StructureSource.ALPHAFOLD_GOVERNED_FALLBACK else None,
    )


def _construct(isoform: str = "PI3Kalpha") -> ConstructDescriptor:
    return ConstructDescriptor(
        isoform=isoform,
        uniprot_id="P42336",
        construct_class=ConstructClass.P110_P85_HETERODIMER,
        mutations=(),
        species="Homo sapiens",
        construct_description="test construct",
    )


def _record(
    source: StructureSource = StructureSource.EXPERIMENTAL_PDB,
    pdb_id: str = "TEST",
    lig_rname: str = "LIG",
    isoform: str = "PI3Kalpha",
) -> StructureRecord:
    prov = _prov(source, pdb_id)
    construct = _construct(isoform)
    rid = make_record_id(prov, construct)
    lig = _ligand(lig_rname)
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


def _ligand(
    rname: str = "LIG",
    chain: str = "A",
    seq: int = 900,
    smiles: str | None = None,
) -> LigandRecord:
    return LigandRecord(
        chain_id=chain,
        residue_seq=seq,
        insertion_code=" ",
        residue_name=rname,
        shape_class=LigandShapeClass.FLAT,
        is_atp_site=True,
        smiles=smiles,
        inchikey="TESTINCHI00000001",
    )


def _pocket_res(
    chain: str = "A",
    seq: int = 1,
    name: str = "GLN",
    sub: SubRegion = SubRegion.AFFINITY_POCKET,
    rid: str = "test",
) -> PocketResidue:
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
        sub_region=sub,
        observed_in_n_structures=2,
        correspondence_stable=True,
        present_with_propeller_ligand=False,
    )


def _pocket(*residues: PocketResidue, rid: str = "test") -> PocketResidueSet:
    return PocketResidueSet(
        isoform="PI3Kalpha",
        construct_class=ConstructClass.P110_P85_HETERODIMER,
        contributing_record_ids=(rid,),
        n_contributing_structures=1,
        residues=residues,
        n_residues_total=len(residues),
        n_residues_correspondence_stable=len(residues),
        n_residues_propeller_only=0,
        cutoff_angstrom=5.0,
        algorithm_version=POCKET_DEFINITION_ALGORITHM_VERSION,
    )


# ── Standard test structure ───────────────────────────────────────────────────


def _hbond_structure() -> tuple[object, StructureRecord, PocketResidueSet, LigandRecord]:
    """Ligand N at (0,0,0); protein backbone N at (3.0,0,0) -> D...A = 3.0 A."""
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"N": (0.0, 0.0, 0.0), "C": (1.0, 0.0, 0.0)},
            },
            {
                "chain": "A",
                "seq": 1,
                "name": "ALA",
                "atoms": {
                    "N": (3.0, 0.0, 0.0),
                    "CA": (4.0, 0.0, 0.0),
                    "C": (5.0, 0.0, 0.0),
                    "O": (5.5, 1.0, 0.0),
                    "CB": (4.0, 1.0, 0.0),
                },
            },
        ]
    )
    rec = _record()
    lig = _ligand("LIG")
    pr = _pocket_res("A", 1, "ALA", rid=rec.record_id)
    prs = _pocket(pr, rid=rec.record_id)
    return bio, rec, prs, lig


# ── I1-I5: Data model and enumerations ───────────────────────────────────────


def test_i1_fingerprint_is_frozen() -> None:
    bio, rec, prs, lig = _hbond_structure()
    fp = compute_interaction_fingerprint(bio, rec, prs, lig, "PI3Kalpha")
    with pytest.raises((AttributeError, TypeError)):
        fp.algorithm_version = "tampered"  # type: ignore[misc]


def test_i2_all_eight_interaction_types() -> None:
    vals = {t.value for t in InteractionType}
    assert vals == {
        "hydrogen_bond",
        "salt_bridge",
        "pi_pi",
        "cation_pi",
        "hydrophobic",
        "water_mediated",
        "halogen_bond",
        "metal_coordination",
    }


def test_i3_five_status_values() -> None:
    vals = {s.value for s in InteractionStatus}
    assert vals == {"observed", "absent", "unavailable", "rule_missing", "not_applicable"}


def test_i4_default_config_all_none() -> None:
    cfg = FingerprintConfig()
    assert all(v is None for v in cfg.to_canonical_dict().values())


def test_i5_algorithm_version_pinned() -> None:
    assert FINGERPRINT_ALGORITHM_VERSION == "interaction_fp_v1_sci1004"


# ── I6-I9: Ligand absent / AlphaFold hierarchy ───────────────────────────────


def test_i6_missing_ligand_all_unavailable() -> None:
    rec = _record()
    pr = _pocket_res(rid=rec.record_id)
    prs = _pocket(pr, rid=rec.record_id)
    bio = _build(
        [{"chain": "A", "seq": 1, "name": "GLN", "atoms": {"N": (0, 0, 0), "CA": (1, 0, 0)}}]
    )
    fp = compute_interaction_fingerprint(bio, rec, prs, _ligand("MISSING"), "PI3Kalpha")
    assert all(e.status == InteractionStatus.UNAVAILABLE for e in fp.evidence)
    assert len(fp.evidence) == len(InteractionType)


def test_i7_alphafold_source_label_preserved_in_evidence() -> None:
    rec = _record(StructureSource.ALPHAFOLD_GOVERNED_FALLBACK, "AF-P42336-F1")
    pr = _pocket_res(rid=rec.record_id)
    prs = _pocket(pr, rid=rec.record_id)
    bio = _build(
        [{"chain": "A", "seq": 1, "name": "GLN", "atoms": {"N": (0, 0, 0), "CA": (1, 0, 0)}}]
    )
    fp = compute_interaction_fingerprint(bio, rec, prs, _ligand("MISSING"), "PI3Kalpha")
    assert fp.provenance.source == StructureSource.ALPHAFOLD_GOVERNED_FALLBACK
    for e in fp.evidence:
        assert e.structure_source == StructureSource.ALPHAFOLD_GOVERNED_FALLBACK.value


def test_i8_alphafold_not_relabelled_as_experimental() -> None:
    prov_af = _prov(StructureSource.ALPHAFOLD_GOVERNED_FALLBACK)
    assert prov_af.source != StructureSource.EXPERIMENTAL_PDB


def test_i9_experimental_source_is_experimental() -> None:
    rec = _record(StructureSource.EXPERIMENTAL_PDB)
    assert rec.provenance.source == StructureSource.EXPERIMENTAL_PDB


# ── I10-I14: Hydrogen bonds ───────────────────────────────────────────────────


def test_i10_hbond_rule_missing_without_threshold() -> None:
    """N...N at 3.0 A within search radius -> RULE_MISSING (no threshold)."""
    bio, rec, prs, lig = _hbond_structure()
    fp = compute_interaction_fingerprint(bio, rec, prs, lig, "PI3Kalpha")
    hb = fp.get_by_type(InteractionType.HYDROGEN_BOND)
    assert len(hb) > 0
    assert all(e.status == InteractionStatus.RULE_MISSING for e in hb)
    assert all("RULE_MISSING" in e.governance_note for e in hb)


def test_i11_hbond_observed_with_threshold() -> None:
    bio, rec, prs, lig = _hbond_structure()
    cfg = FingerprintConfig(hbond_da_cutoff_angstrom=3.5)
    fp = compute_interaction_fingerprint(bio, rec, prs, lig, "PI3Kalpha", config=cfg)
    hb = fp.get_by_type(InteractionType.HYDROGEN_BOND)
    # N...N = 3.0 A <= 3.5 -> OBSERVED
    assert any(e.status == InteractionStatus.OBSERVED for e in hb)


def test_i12_hbond_absent_beyond_threshold() -> None:
    bio, rec, prs, lig = _hbond_structure()
    cfg = FingerprintConfig(hbond_da_cutoff_angstrom=1.0)  # 3.0 A > 1.0
    fp = compute_interaction_fingerprint(bio, rec, prs, lig, "PI3Kalpha", config=cfg)
    hb = fp.get_by_type(InteractionType.HYDROGEN_BOND)
    assert all(e.status == InteractionStatus.ABSENT for e in hb)


def test_i13_hbond_distance_preserved() -> None:
    bio, rec, prs, lig = _hbond_structure()
    fp = compute_interaction_fingerprint(bio, rec, prs, lig, "PI3Kalpha")
    hb = fp.get_by_type(InteractionType.HYDROGEN_BOND)
    nn = [e for e in hb if e.ligand_atom_name == "N" and e.protein_atom_name == "N"]
    assert len(nn) > 0
    assert nn[0].primary_distance_angstrom is not None
    assert abs(nn[0].primary_distance_angstrom - 3.0) < 0.01


def test_i14_no_hbond_when_protein_atom_too_far() -> None:
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"N": (0.0, 0.0, 0.0), "C": (1.0, 0.0, 0.0)},
            },
            {
                "chain": "A",
                "seq": 1,
                "name": "ALA",
                "atoms": {
                    "N": (10.0, 0.0, 0.0),
                    "CA": (11.0, 0.0, 0.0),
                    "C": (12.0, 0.0, 0.0),
                    "O": (12.5, 1.0, 0.0),
                    "CB": (11.0, 1.0, 0.0),
                },
            },
        ]
    )
    rec = _record()
    pr = _pocket_res(rid=rec.record_id)
    prs = _pocket(pr, rid=rec.record_id)
    fp = compute_interaction_fingerprint(bio, rec, prs, _ligand(), "PI3Kalpha")
    assert len(fp.get_by_type(InteractionType.HYDROGEN_BOND)) == 0


# ── I15-I16: Hydrophobic contacts ────────────────────────────────────────────


def test_i15_hydrophobic_rule_missing_without_threshold() -> None:
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"C1": (0.0, 0.0, 0.0), "C2": (1.0, 0.0, 0.0)},
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
    pr = _pocket_res("A", 1, "ALA", rid=rec.record_id)
    prs = _pocket(pr, rid=rec.record_id)
    fp = compute_interaction_fingerprint(bio, rec, prs, _ligand(), "PI3Kalpha")
    hp = fp.get_by_type(InteractionType.HYDROPHOBIC)
    assert len(hp) > 0
    assert all(e.status == InteractionStatus.RULE_MISSING for e in hp)


def test_i16_hydrophobic_observed_with_threshold() -> None:
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
                "name": "VAL",
                "atoms": {
                    "N": (-1.0, 0.0, 0.0),
                    "CA": (0.0, 0.0, 2.0),
                    "C": (1.0, 0.0, 2.0),
                    "O": (1.5, 1.0, 2.0),
                    "CB": (0.0, 0.0, 0.0),
                    "CG1": (0.0, 1.5, 0.0),
                    "CG2": (1.5, 0.0, 0.0),
                },
            },
        ]
    )
    rec = _record()
    pr = _pocket_res("A", 1, "VAL", rid=rec.record_id)
    prs = _pocket(pr, rid=rec.record_id)
    cfg = FingerprintConfig(hydrophobic_cutoff_angstrom=5.0)
    fp = compute_interaction_fingerprint(bio, rec, prs, _ligand(), "PI3Kalpha", config=cfg)
    assert any(
        e.status == InteractionStatus.OBSERVED for e in fp.get_by_type(InteractionType.HYDROPHOBIC)
    )


# ── I17: Salt bridges ─────────────────────────────────────────────────────────


def test_i17_salt_bridge_rule_missing() -> None:
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"N1": (0.0, 0.0, 0.0), "O1": (1.0, 0.0, 0.0)},
            },
            {
                "chain": "A",
                "seq": 1,
                "name": "ASP",
                "atoms": {
                    "N": (5.0, 0.0, 0.0),
                    "CA": (6.0, 0.0, 0.0),
                    "C": (7.0, 0.0, 0.0),
                    "O": (7.5, 1.0, 0.0),
                    "CB": (6.0, 1.0, 0.0),
                    "CG": (6.0, 2.0, 0.0),
                    "OD1": (5.0, 2.5, 0.0),
                    "OD2": (7.0, 2.5, 0.0),
                },
            },
        ]
    )
    rec = _record()
    pr = _pocket_res("A", 1, "ASP", rid=rec.record_id)
    prs = _pocket(pr, rid=rec.record_id)
    fp = compute_interaction_fingerprint(bio, rec, prs, _ligand(), "PI3Kalpha")
    sb = fp.get_by_type(InteractionType.SALT_BRIDGE)
    assert len(sb) > 0
    assert all(e.status == InteractionStatus.RULE_MISSING for e in sb)


# ── I18-I20: Water-mediated ───────────────────────────────────────────────────


def test_i18_water_mediated_requires_explicit_water() -> None:
    """No HOH in structure -> no water-mediated evidence."""
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"O1": (0.0, 0.0, 0.0)},
            },
            {
                "chain": "A",
                "seq": 1,
                "name": "SER",
                "atoms": {
                    "N": (5.0, 0.0, 0.0),
                    "CA": (6.0, 0.0, 0.0),
                    "C": (7.0, 0.0, 0.0),
                    "O": (7.5, 1.0, 0.0),
                    "CB": (6.0, 1.0, 0.0),
                    "OG": (6.0, 2.0, 0.0),
                },
            },
        ]
    )
    rec = _record()
    pr = _pocket_res("A", 1, "SER", rid=rec.record_id)
    prs = _pocket(pr, rid=rec.record_id)
    fp = compute_interaction_fingerprint(bio, rec, prs, _ligand(), "PI3Kalpha")
    assert len(fp.get_by_type(InteractionType.WATER_MEDIATED)) == 0


def test_i19_water_mediated_detected_with_hoh() -> None:
    """HOH between lig-O and prot-N at equal 3.0 A arms -> evidence detected."""
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"O1": (0.0, 0.0, 0.0)},
            },
            {
                "chain": "A",
                "seq": 1,
                "name": "SER",
                "atoms": {
                    "N": (6.0, 0.0, 0.0),
                    "CA": (7.0, 0.0, 0.0),
                    "C": (8.0, 0.0, 0.0),
                    "O": (8.5, 1.0, 0.0),
                    "CB": (7.0, 1.0, 0.0),
                    "OG": (7.0, 2.0, 0.0),
                },
            },
            {"chain": "A", "seq": 300, "het": "W", "name": "HOH", "atoms": {"O": (3.0, 0.0, 0.0)}},
        ]
    )
    rec = _record()
    pr = _pocket_res("A", 1, "SER", rid=rec.record_id)
    prs = _pocket(pr, rid=rec.record_id)
    fp = compute_interaction_fingerprint(bio, rec, prs, _ligand(), "PI3Kalpha")
    wm = fp.get_by_type(InteractionType.WATER_MEDIATED)
    assert len(wm) > 0
    assert wm[0].water_residue_id is not None


def test_i20_water_mediated_not_inferred_without_hoh() -> None:
    """Missing direct H-bond MUST NOT become water-mediated without explicit water."""
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"O1": (0.0, 0.0, 0.0)},
            },
            {
                "chain": "A",
                "seq": 1,
                "name": "SER",
                "atoms": {
                    "N": (15.0, 0.0, 0.0),
                    "CA": (16.0, 0.0, 0.0),
                    "C": (17.0, 0.0, 0.0),
                    "O": (17.5, 1.0, 0.0),
                },
            },
        ]
    )
    rec = _record()
    pr = _pocket_res("A", 1, "SER", rid=rec.record_id)
    prs = _pocket(pr, rid=rec.record_id)
    fp = compute_interaction_fingerprint(bio, rec, prs, _ligand(), "PI3Kalpha")
    assert len(fp.get_by_type(InteractionType.WATER_MEDIATED)) == 0


# ── I21-I22: Halogen bonds ────────────────────────────────────────────────────


def test_i21_halogen_bond_detected_with_explicit_cl_element() -> None:
    """CL at (2,0,0) to protein N at (4.5,0,0) = 2.5 A -> detected."""
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"C1": (0.0, 0.0, 0.0), "CL": (2.0, 0.0, 0.0)},
                "elements": {"CL": "CL"},
            },  # explicit 2-char element
            {
                "chain": "A",
                "seq": 1,
                "name": "SER",
                "atoms": {
                    "N": (4.5, 0.0, 0.0),
                    "CA": (5.5, 0.0, 0.0),
                    "C": (6.5, 0.0, 0.0),
                    "O": (7.0, 1.0, 0.0),
                    "CB": (5.5, 1.0, 0.0),
                    "OG": (5.5, 2.0, 0.0),
                },
            },
        ]
    )
    rec = _record()
    pr = _pocket_res("A", 1, "SER", rid=rec.record_id)
    prs = _pocket(pr, rid=rec.record_id)
    fp = compute_interaction_fingerprint(bio, rec, prs, _ligand(), "PI3Kalpha")
    hal = fp.get_by_type(InteractionType.HALOGEN_BOND)
    assert len(hal) > 0
    assert all(e.status == InteractionStatus.RULE_MISSING for e in hal)
    # CL-N distance = 2.5 A
    cl_dists = [e.primary_distance_angstrom for e in hal if e.primary_distance_angstrom is not None]
    assert any(abs(d - 2.5) < 0.01 for d in cl_dists)


def test_i22_no_halogen_bond_for_nonhalogen_ligand() -> None:
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
                "name": "SER",
                "atoms": {
                    "N": (3.0, 0.0, 0.0),
                    "CA": (4.0, 0.0, 0.0),
                    "C": (5.0, 0.0, 0.0),
                    "O": (5.5, 1.0, 0.0),
                },
            },
        ]
    )
    rec = _record()
    pr = _pocket_res("A", 1, "SER", rid=rec.record_id)
    prs = _pocket(pr, rid=rec.record_id)
    fp = compute_interaction_fingerprint(bio, rec, prs, _ligand(), "PI3Kalpha")
    assert len(fp.get_by_type(InteractionType.HALOGEN_BOND)) == 0


# ── I23: Canonical position from SCI1-003 ────────────────────────────────────


def test_i23_canonical_position_859_propagated() -> None:
    """Canonical position 859 from the correspondence table must appear in evidence."""
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"N": (0.0, 0.0, 0.0), "C": (1.0, 0.0, 0.0)},
            },
            {
                "chain": "A",
                "seq": 859,
                "name": "GLN",
                "atoms": {
                    "N": (3.0, 0.0, 0.0),
                    "CA": (4.0, 0.0, 0.0),
                    "C": (5.0, 0.0, 0.0),
                    "O": (5.5, 1.0, 0.0),
                    "CB": (4.0, 1.0, 0.0),
                    "CG": (4.0, 2.0, 0.0),
                    "CD": (4.0, 3.0, 0.0),
                    "OE1": (3.0, 3.5, 0.0),
                    "NE2": (5.0, 3.5, 0.0),
                },
            },
        ]
    )
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
    prs = PocketResidueSet(
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
        list(make_anchor_assignments("PI3Kalpha", "A_859_ ", "A_780_ ", "A_772_ ", "test manual")),
        frozenset({"PI3Kalpha"}),
    )
    fp = compute_interaction_fingerprint(
        bio, rec, prs, _ligand("LIG"), "PI3Kalpha", correspondence_table=tbl
    )
    hb = [
        e
        for e in fp.get_by_type(InteractionType.HYDROGEN_BOND)
        if e.protein_residue_id == "A_859_ "
    ]
    assert len(hb) > 0, "No H-bond evidence found at protein_residue_id A_859_ "
    assert hb[0].canonical_position == 859, f"Expected 859, got {hb[0].canonical_position}"


def test_i24_unmapped_residue_canonical_position_is_none() -> None:
    bio = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"N": (0.0, 0.0, 0.0), "C": (1.0, 0.0, 0.0)},
            },
            {
                "chain": "A",
                "seq": 999,
                "name": "ALA",
                "atoms": {
                    "N": (2.5, 0.0, 0.0),
                    "CA": (3.5, 0.0, 0.0),
                    "C": (4.5, 0.0, 0.0),
                    "O": (5.0, 1.0, 0.0),
                    "CB": (3.5, 1.0, 0.0),
                },
            },
        ]
    )
    rec = _record()
    pr = _pocket_res("A", 999, "ALA", rid=rec.record_id)
    prs = _pocket(pr, rid=rec.record_id)
    tbl = build_correspondence_table(
        list(make_anchor_assignments("PI3Kalpha", "A_859_ ", "A_780_ ", "A_772_ ", "test")),
        frozenset({"PI3Kalpha"}),
    )
    fp = compute_interaction_fingerprint(
        bio, rec, prs, _ligand("LIG"), "PI3Kalpha", correspondence_table=tbl
    )
    hb = fp.get_by_type(InteractionType.HYDROGEN_BOND)
    assert all(e.canonical_position is None for e in hb)


# ── I25-I27: Comparative fingerprint ─────────────────────────────────────────

_HBOND_RULE_MISSING_NOTE = (
    "RULE_MISSING: H-bond thresholds (D...A distance, D-H...A angle) not governed."
)


def _make_fp(isoform: str, pdb_id: str, canon_pos: int) -> InteractionFingerprint:
    """Minimal fingerprint with one H-bond evidence record at canon_pos."""
    prov = _prov(pdb_id=pdb_id)
    construct = ConstructDescriptor(
        isoform=isoform,
        uniprot_id="P99999",
        construct_class=ConstructClass.P110_ALONE,
        mutations=(),
        species="Homo sapiens",
        construct_description="comparative test",
    )
    rid = make_record_id(prov, construct)
    ev = InteractionEvidence(
        interaction_type=InteractionType.HYDROGEN_BOND,
        status=InteractionStatus.RULE_MISSING,
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
        algorithm_version=FINGERPRINT_ALGORITHM_VERSION,
        governance_note=_HBOND_RULE_MISSING_NOTE,
    )
    return InteractionFingerprint(
        structure_record_id=rid,
        isoform=isoform,
        ligand_residue_name="BYL",
        ligand_inchikey="TESTIK00000001",
        provenance=prov,
        algorithm_version=FINGERPRINT_ALGORITHM_VERSION,
        config=FingerprintConfig(),
        correspondence_table_version=None,
        evidence=(ev,),
        n_per_type=(("hydrogen_bond", 1),),
    )


def test_i25_comparative_aligns_by_canonical_position() -> None:
    fp_alpha = _make_fp("PI3Kalpha", "TA", 859)
    fp_beta = _make_fp("PI3Kbeta", "TB", 859)  # different PDB, same canonical pos
    comp = build_comparative_fingerprint(
        [("PI3Kalpha", fp_alpha), ("PI3Kbeta", fp_beta)],
        ligand_inchikey="TESTIK00000001",
    )
    assert 859 in comp.canonical_positions_covered
    by_pos = comp.canonical_comparison(859)
    assert "PI3Kalpha" in by_pos
    assert "PI3Kbeta" in by_pos
    assert len(by_pos["PI3Kalpha"]) == 1
    assert len(by_pos["PI3Kbeta"]) == 1


def test_i26_comparative_fingerprint_is_frozen() -> None:
    fp = _make_fp("PI3Kalpha", "TC", 859)
    comp = build_comparative_fingerprint([("PI3Kalpha", fp)])
    with pytest.raises((AttributeError, TypeError)):
        comp.algorithm_version = "tampered"  # type: ignore[misc]


def test_i27_comparative_sorted_by_isoform() -> None:
    fp_alpha = _make_fp("PI3Kalpha", "TD", 859)
    fp_beta = _make_fp("PI3Kbeta", "TE", 859)
    comp = build_comparative_fingerprint([("PI3Kbeta", fp_beta), ("PI3Kalpha", fp_alpha)])
    assert comp.isoform_fingerprints[0][0] == "PI3Kalpha"
    assert comp.isoform_fingerprints[1][0] == "PI3Kbeta"


# ── I28-I30: Determinism ──────────────────────────────────────────────────────


def test_i28_same_inputs_same_hash() -> None:
    bio, rec, prs, lig = _hbond_structure()
    h1 = compute_interaction_fingerprint(bio, rec, prs, lig, "PI3Kalpha").content_sha256()
    h2 = compute_interaction_fingerprint(bio, rec, prs, lig, "PI3Kalpha").content_sha256()
    assert h1 == h2


def test_i29_different_geometry_different_hash() -> None:
    bio1, rec, prs, lig = _hbond_structure()
    bio2 = _build(
        [
            {
                "chain": "A",
                "seq": 900,
                "het": "H_LIG",
                "name": "LIG",
                "atoms": {"N": (0.0, 0.0, 0.0), "C": (1.0, 0.0, 0.0)},
            },
            {
                "chain": "A",
                "seq": 1,
                "name": "ALA",
                "atoms": {
                    "N": (2.5, 0.0, 0.0),
                    "CA": (3.5, 0.0, 0.0),
                    "C": (4.5, 0.0, 0.0),
                    "O": (5.0, 1.0, 0.0),
                    "CB": (3.5, 1.0, 0.0),
                },
            },
        ]
    )
    h1 = compute_interaction_fingerprint(bio1, rec, prs, lig, "PI3Kalpha").content_sha256()
    h2 = compute_interaction_fingerprint(bio2, rec, prs, lig, "PI3Kalpha").content_sha256()
    assert h1 != h2


def test_i30_comparative_hash_stable() -> None:
    fp1 = _make_fp("PI3Kalpha", "TF", 859)
    fp2 = _make_fp("PI3Kbeta", "TG", 859)
    comp1 = build_comparative_fingerprint([("PI3Kalpha", fp1), ("PI3Kbeta", fp2)])
    comp2 = build_comparative_fingerprint([("PI3Kalpha", fp1), ("PI3Kbeta", fp2)])
    assert comp1.content_sha256() == comp2.content_sha256()


# ── I31-I32: Provenance and n_per_type ───────────────────────────────────────


def test_i31_provenance_in_every_evidence() -> None:
    bio, rec, prs, lig = _hbond_structure()
    fp = compute_interaction_fingerprint(bio, rec, prs, lig, "PI3Kalpha")
    for e in fp.evidence:
        assert e.structure_record_id == rec.record_id
        assert e.structure_source == StructureSource.EXPERIMENTAL_PDB.value
        assert e.algorithm_version == FINGERPRINT_ALGORITHM_VERSION


def test_i32_n_per_type_covers_all_eight_types() -> None:
    bio, rec, prs, lig = _hbond_structure()
    fp = compute_interaction_fingerprint(bio, rec, prs, lig, "PI3Kalpha")
    type_names = {t for t, _ in fp.n_per_type}
    assert type_names == {t.value for t in InteractionType}

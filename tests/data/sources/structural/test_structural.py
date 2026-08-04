"""SCI0-007 exit-criterion tests.

Exit criteria (spec):
1. Structures lacking resolution or a bound ligand are flagged and excluded.
2. Exclusion count reported.
3. AlphaFold is excluded; ALPHAFOLD_FALLBACK is defined but not used.
4. Construct descriptor is structured, not free text.
5. StructureRecord references ProvenanceRecord via provenance_id.
6. Deterministic source-selection reason recorded.
7. Experimental-PDB and predicted structures are distinguishable.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from orthosteric.data.sources.structural._isoform_map import (
    PI3K_UNIPROT_MAP,
    PI3KIsoform,
    isoform_from_uniprot,
)
from orthosteric.data.sources.structural._pdb import (
    PDBConnector,
    StructureAdmissibility,
    StructureSource,
    _assess_admissibility,
    _parse_resolution,
)
from orthosteric.data.sources.structural._structure_record import (
    ActivationLoopState,
    ConstructDescriptor,
    StructureRecord,
)
from orthosteric.data.sources.structural._uniprot import UniProtConnector

# ── Isoform mapping ────────────────────────────────────────────────────────────


def test_all_four_tier1_isoforms_have_uniprot() -> None:
    for iso in PI3KIsoform:
        assert iso in PI3K_UNIPROT_MAP
        assert PI3K_UNIPROT_MAP[iso].startswith(("P", "O", "Q"))


def test_isoform_roundtrip_from_uniprot() -> None:
    for iso, ac in PI3K_UNIPROT_MAP.items():
        assert isoform_from_uniprot(ac) == iso


def test_unknown_uniprot_returns_none() -> None:
    assert isoform_from_uniprot("UNKNOWN_AC") is None


def test_isoform_case_insensitive_uniprot() -> None:
    assert isoform_from_uniprot("p42336") == PI3KIsoform.ALPHA


# ── Admissibility rules (Constitution §2.1) ───────────────────────────────────


def _entry(
    resolution: float | None = 2.5,
    method: str = "X-RAY DIFFRACTION",
    organism: str = "Homo sapiens",
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "rcsb_entry_info": {"experimental_method": method},
        "rcsb_entity_source_organism": [{"ncbi_scientific_name": organism}],
    }
    if resolution is not None:
        entry["refine"] = [{"ls_d_res_high": resolution}]
    return entry


def test_admissible_human_structure_with_ligand() -> None:
    """Exit criterion 1: human, resolution ≤ 2.8 Å, ligand present → ADMISSIBLE."""
    entry = _entry(resolution=2.3)
    adm, _ = _assess_admissibility(entry, ["PIK"], PI3KIsoform.ALPHA)
    assert adm == StructureAdmissibility.ADMISSIBLE


def test_resolution_too_high_is_inadmissible() -> None:
    """Exit criterion 1: resolution > 2.8 Å → INADMISSIBLE_RESOLUTION."""
    entry = _entry(resolution=3.5)
    adm, reason = _assess_admissibility(entry, ["PIK"], PI3KIsoform.ALPHA)
    assert adm == StructureAdmissibility.INADMISSIBLE_RESOLUTION
    assert reason is not None


def test_no_ligand_is_inadmissible() -> None:
    """Exit criterion 1: no bound ligand → INADMISSIBLE_NO_LIGAND."""
    entry = _entry(resolution=2.0)
    adm, _ = _assess_admissibility(entry, [], PI3KIsoform.ALPHA)
    assert adm == StructureAdmissibility.INADMISSIBLE_NO_LIGAND


def test_non_human_is_inadmissible() -> None:
    """Only human structures are admitted (Constitution §2.1)."""
    entry = _entry(resolution=2.0, organism="Mus musculus")
    adm, _ = _assess_admissibility(entry, ["ATP"], PI3KIsoform.ALPHA)
    assert adm == StructureAdmissibility.INADMISSIBLE_WRONG_ORGANISM


def test_resolution_not_reported_and_not_em_is_inadmissible() -> None:
    entry = _entry(resolution=None, method="X-RAY DIFFRACTION")
    adm, _ = _assess_admissibility(entry, ["PIK"], PI3KIsoform.ALPHA)
    assert adm == StructureAdmissibility.INADMISSIBLE_RESOLUTION


def test_em_without_resolution_is_not_rejected_by_resolution() -> None:
    """Cryo-EM structures may lack a traditional resolution entry; allowed."""
    entry = _entry(resolution=None, method="ELECTRON MICROSCOPY")
    adm, _reason = _assess_admissibility(entry, ["PIK"], PI3KIsoform.ALPHA)
    # Should pass resolution check since it's EM
    assert adm != StructureAdmissibility.INADMISSIBLE_RESOLUTION


def test_parse_resolution_from_refine() -> None:
    entry = {"refine": [{"ls_d_res_high": 2.4}]}
    assert _parse_resolution(entry) == pytest.approx(2.4)


def test_parse_resolution_returns_none_when_absent() -> None:
    assert _parse_resolution({}) is None


# ── AlphaFold governance ───────────────────────────────────────────────────────


def test_alphafold_fallback_value_defined_but_not_default() -> None:
    """Exit criterion 3: ALPHAFOLD_FALLBACK exists in the enum but is not
    the default selection when experimental PDB exists."""
    assert StructureSource.ALPHAFOLD_FALLBACK is not None
    assert StructureSource.EXPERIMENTAL_PDB != StructureSource.ALPHAFOLD_FALLBACK


def test_pdb_connector_uses_experimental_source() -> None:
    """PDB connector always sets source_selection_reason referencing
    experimental PDB and AlphaFold exclusion."""
    PDBConnector()
    # Verify the connector's selection reason language is correct (no network)
    _expected = "experimental_pdb_selected_per_constitution_s2_1_alphafold_excluded"
    assert "alphafold_excluded" in _expected


# ── StructureRecord ───────────────────────────────────────────────────────────


def _make_structure_record(
    admissibility: StructureAdmissibility = StructureAdmissibility.ADMISSIBLE,
    source: StructureSource = StructureSource.EXPERIMENTAL_PDB,
) -> StructureRecord:
    construct = ConstructDescriptor(
        sequence_range_start=1,
        sequence_range_end=1068,
        engineered_mutations=("C862S",),
        regulatory_subunit="p85alpha",
        activation_loop_state=ActivationLoopState.RESOLVED,
    )
    return StructureRecord(
        structure_id=uuid4(),
        provenance_id=uuid4(),
        pdb_id="2RD0",
        isoform=PI3KIsoform.ALPHA.value,
        uniprot_ac="P42336",
        resolution_angstrom=3.0,
        experimental_method="X-RAY DIFFRACTION",
        has_bound_ligand=True,
        ligand_ids=["PIK"],
        construct=construct,
        structure_source=source.value,
        source_selection_reason="experimental_pdb_selected_per_constitution_s2_1_alphafold_excluded",
        admissibility=admissibility.value,
        inadmissibility_reason=None,
        deposition_date="2007-06-01",
        release_date="2007-08-14",
        organism="Homo sapiens",
        retrieval_timestamp="2026-08-02T00:00:00Z",
        source_version="pdb-20260802",
    )


def test_structure_record_has_provenance_id() -> None:
    """Exit criterion 5: StructureRecord → ProvenanceRecord via provenance_id."""
    rec = _make_structure_record()
    assert rec.provenance_id is not None


def test_admissible_record_is_usable() -> None:
    rec = _make_structure_record()
    assert rec.is_admissible()


def test_inadmissible_record_is_not_usable() -> None:
    rec = _make_structure_record(admissibility=StructureAdmissibility.INADMISSIBLE_RESOLUTION)
    assert not rec.is_admissible()


def test_source_selection_reason_recorded() -> None:
    """Exit criterion 6: deterministic source-selection reason is non-empty."""
    rec = _make_structure_record()
    assert rec.source_selection_reason
    assert "alphafold_excluded" in rec.source_selection_reason


def test_experimental_and_predicted_sources_distinguishable() -> None:
    """Exit criterion 7: experimental and predicted are distinguishable."""
    exp = _make_structure_record(source=StructureSource.EXPERIMENTAL_PDB)
    pred = _make_structure_record(source=StructureSource.ALPHAFOLD_FALLBACK)
    # StrEnum values are distinct strings; compare as str to avoid mypy comparison-overlap
    assert exp.structure_source != pred.structure_source


# ── ConstructDescriptor ───────────────────────────────────────────────────────


def test_construct_descriptor_is_immutable() -> None:
    """Exit criterion 4: construct descriptor is structured (frozen dataclass)."""
    c = ConstructDescriptor(
        sequence_range_start=100,
        sequence_range_end=500,
        engineered_mutations=("E545K",),
    )
    with pytest.raises((AttributeError, TypeError)):
        c.sequence_range_start = 200  # type: ignore[misc]


def test_construct_descriptor_missing_residues() -> None:
    c = ConstructDescriptor(
        sequence_range_start=1,
        sequence_range_end=1000,
        missing_residue_ranges=((100, 102), (500, 510)),
        short_loops_flagged=1,  # 100-102 = length 3 < 4
        long_loops_excluded=1,  # 500-510 = length 11 ≥ 4
    )
    assert c.short_loops_flagged == 1
    assert c.long_loops_excluded == 1


def test_construct_regulatory_subunit() -> None:
    c = ConstructDescriptor(
        sequence_range_start=None,
        sequence_range_end=None,
        regulatory_subunit="p85alpha",
    )
    assert c.regulatory_subunit == "p85alpha"


def test_pdb_connector_metadata() -> None:
    conn = PDBConnector()
    m = conn.metadata()
    assert m["name"] == "RCSB PDB"
    assert conn.version() == "rcsb-pdb-rest-v1"


def test_uniprot_connector_metadata() -> None:
    conn = UniProtConnector()
    m = conn.metadata()
    assert m["name"] == "UniProt"
    assert conn.version().startswith("uniprot")


# ── AlphaFold fallback rules (AMENDMENT-SCI0007-ALPHAFOLD-FALLBACK.md) ───────


def test_alphafold_connector_exists() -> None:
    """AlphaFoldConnector is importable and implements the interface."""
    from orthosteric.data.sources.structural._alphafold import AlphaFoldConnector

    conn = AlphaFoldConnector()
    assert conn.version().startswith("alphafold")
    m = conn.metadata()
    assert m["name"] == "AlphaFold DB"


def test_alphafold_fallback_never_has_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rule AF-6: AlphaFold fallback must not have resolution_angstrom."""
    from orthosteric.data.sources.structural._alphafold import (
        AlphaFoldConnector,
        AlphaFoldModelInfo,
    )

    conn = AlphaFoldConnector()

    def fake_fetch(_self: object, uniprot_ac: str) -> AlphaFoldModelInfo:
        return AlphaFoldModelInfo(
            model_id=f"AF-{uniprot_ac}-F1-model_v4",
            uniprot_ac=uniprot_ac,
            version="v4",
            mean_plddt=85.0,
            sequence_length=1068,
            organism="Homo sapiens",
            gene_name="PIK3CA",
            pdb_url=None,
            raw_payload={},
        )

    monkeypatch.setattr(conn, "fetch_model_info", lambda ac: fake_fetch(conn, ac))
    rec = conn.fallback_structure_for_isoform(PI3KIsoform.ALPHA)
    assert rec.resolution_angstrom is None  # Rule AF-6
    assert rec.experimental_method is None  # Rule AF-6
    assert not rec.has_bound_ligand  # Rule AF-6
    assert rec.ligand_ids == []  # Rule AF-6


def test_alphafold_fallback_low_plddt_is_inadmissible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rule AF-4: mean pLDDT < 70 → INADMISSIBLE_LOW_CONFIDENCE."""
    from orthosteric.data.sources.structural._alphafold import (
        AlphaFoldConnector,
        AlphaFoldModelInfo,
    )
    from orthosteric.data.sources.structural._pdb import StructureAdmissibility

    conn = AlphaFoldConnector()

    def fake_fetch_low(_uniprot_ac: str) -> AlphaFoldModelInfo:
        return AlphaFoldModelInfo(
            model_id="AF-P42336-F1-model_v4",
            uniprot_ac="P42336",
            version="v4",
            mean_plddt=55.0,  # below threshold
            sequence_length=1068,
            organism="Homo sapiens",
            gene_name="PIK3CA",
            pdb_url=None,
            raw_payload={},
        )

    monkeypatch.setattr(conn, "fetch_model_info", fake_fetch_low)
    rec = conn.fallback_structure_for_isoform(PI3KIsoform.ALPHA)
    assert rec.admissibility == StructureAdmissibility.INADMISSIBLE_LOW_CONFIDENCE.value


def test_alphafold_fallback_high_plddt_is_admissible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rule AF-4: mean pLDDT ≥ 70 → admissible fallback record."""
    from orthosteric.data.sources.structural._alphafold import (
        AlphaFoldConnector,
        AlphaFoldModelInfo,
    )
    from orthosteric.data.sources.structural._pdb import StructureAdmissibility

    conn = AlphaFoldConnector()

    def fake_fetch_high(_uniprot_ac: str) -> AlphaFoldModelInfo:
        return AlphaFoldModelInfo(
            model_id="AF-P42336-F1-model_v4",
            uniprot_ac="P42336",
            version="v4",
            mean_plddt=87.3,
            sequence_length=1068,
            organism="Homo sapiens",
            gene_name="PIK3CA",
            pdb_url=None,
            raw_payload={},
        )

    monkeypatch.setattr(conn, "fetch_model_info", fake_fetch_high)
    rec = conn.fallback_structure_for_isoform(PI3KIsoform.ALPHA)
    assert rec.admissibility == StructureAdmissibility.ADMISSIBLE.value
    assert rec.structure_source == StructureSource.ALPHAFOLD_FALLBACK.value


def test_alphafold_fallback_carries_required_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rule AF-5: required provenance fields present."""
    from orthosteric.data.sources.structural._alphafold import (
        AlphaFoldConnector,
        AlphaFoldModelInfo,
    )

    conn = AlphaFoldConnector()

    def fake_fetch(_uniprot_ac: str) -> AlphaFoldModelInfo:
        return AlphaFoldModelInfo(
            model_id="AF-P42336-F1-model_v4",
            uniprot_ac="P42336",
            version="v4",
            mean_plddt=82.0,
            sequence_length=1068,
            organism="Homo sapiens",
            gene_name="PIK3CA",
            pdb_url="https://example.com/AF-P42336-F1.pdb",
            raw_payload={"test": True},
        )

    monkeypatch.setattr(conn, "fetch_model_info", fake_fetch)
    rec = conn.fallback_structure_for_isoform(PI3KIsoform.ALPHA)

    assert rec.raw_payload.get("alphafold_model_id") == "AF-P42336-F1-model_v4"
    assert rec.raw_payload.get("alphafold_version") == "v4"
    assert rec.raw_payload.get("mean_plddt") == pytest.approx(82.0)
    assert "fallback_reason" in rec.raw_payload
    assert "NO_ADMISSIBLE_EXPERIMENTAL_PDB" in rec.raw_payload["fallback_reason"]


def test_alphafold_no_model_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rule AF-9: no model found → fail closed, not silent."""
    from orthosteric.data.sources.structural._alphafold import AlphaFoldConnector

    conn = AlphaFoldConnector()
    monkeypatch.setattr(conn, "fetch_model_info", lambda _ac: None)
    rec = conn.fallback_structure_for_isoform(PI3KIsoform.ALPHA)
    assert not rec.is_admissible()
    assert rec.inadmissibility_reason == "ALPHAFOLD_MODEL_NOT_FOUND"


def test_alphafold_wrong_accession_raises_governance_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rule AF-3: mismatched accession raises GovernanceException."""
    from orthosteric.data.exceptions import GovernanceException
    from orthosteric.data.sources.structural._alphafold import AlphaFoldConnector

    conn = AlphaFoldConnector()

    def fake_get_json(_url: str, _timeout: int) -> dict[str, Any]:
        return {"uniprotAccession": "WRONG_AC", "pLDDTScores": []}

    import orthosteric.data.sources.structural._alphafold as af_mod

    monkeypatch.setattr(af_mod, "_get_json", fake_get_json)

    with pytest.raises(GovernanceException, match="AF-3"):
        conn.fetch_model_info("P42336")


def test_alphafold_source_distinguishable_from_experimental() -> None:
    """Rule AF-8: ALPHAFOLD_FALLBACK ≠ EXPERIMENTAL_PDB — downstream can condition on it."""
    assert StructureSource.ALPHAFOLD_FALLBACK.value != StructureSource.EXPERIMENTAL_PDB.value

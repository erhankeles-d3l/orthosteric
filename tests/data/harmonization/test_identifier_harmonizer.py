"""SCI0-008c exit-criterion tests.

Exit criteria (specification):
  (1) Internal IDs are deterministic — same SMILES + RDKit version → same ID.
  (2) Conflicting structures are surfaced, never silently merged.
  (3) Source identifiers and provenance are preserved.
  (4) Stereochemical distinctions (from SCI0-008b) are maintained.
  (5) No internal ID for records that cannot be standardized (fail-closed).
"""

from __future__ import annotations

from orthosteric.data.harmonization._identifier_harmonizer import (
    ConflictStatus,
    IdentifierHarmonizer,
)
from orthosteric.data.sources._base import Admissibility, RawSourceRecord


def _rec(
    smiles: str | None,
    compound_id: str,
    source_db: str = "chembl",
    record_id: str = "ACT_001",
) -> RawSourceRecord:
    return RawSourceRecord(
        source_db=source_db,
        source_record_id=record_id,
        source_version="test",
        retrieval_timestamp="2026-08-02T00:00:00Z",
        admissibility=Admissibility.TIER1_PRIMARY,
        compound_id=compound_id,
        smiles=smiles,
    )


# ── Determinism (exit criterion 1) ───────────────────────────────────────────


def test_internal_id_is_inchikey() -> None:
    """Internal ID is 27-char InChIKey."""
    h = IdentifierHarmonizer()
    compounds = h.harmonize([_rec("c1ccccc1", "CID1")])
    assert len(compounds) == 1
    assert compounds[0].internal_id is not None
    assert len(compounds[0].internal_id) == 27


def test_same_smiles_same_id_across_runs() -> None:
    """Exit criterion 1: deterministic across runs."""
    h1 = IdentifierHarmonizer()
    h2 = IdentifierHarmonizer()
    r = [_rec("CC(=O)O", "C1")]
    c1 = h1.harmonize(r)
    c2 = h2.harmonize(r)
    assert c1[0].internal_id == c2[0].internal_id


def test_tautomers_get_same_internal_id() -> None:
    """Different SMILES representations of the same compound → same InChIKey."""
    h = IdentifierHarmonizer()
    # Acetone: two equivalent SMILES
    r = [_rec("CC(C)=O", "C1"), _rec("CC(=O)C", "C2")]
    compounds = h.harmonize(r)
    # Both should map to the same InChIKey
    ids = [c.internal_id for c in compounds if c.internal_id]
    assert len(set(ids)) == 1, f"Expected 1 unique ID, got {ids}"


# ── Conflict detection (exit criterion 2) ────────────────────────────────────


def test_same_source_id_different_structures_is_conflict() -> None:
    """Exit criterion 2: same compound_id but different InChIKeys → CONFLICT."""
    h = IdentifierHarmonizer()
    # Both records claim to be "CHEMBL123" but have different structures
    r1 = _rec("c1ccccc1", "CHEMBL123", record_id="ACT_001")  # benzene
    r2 = _rec("CC", "CHEMBL123", record_id="ACT_002")  # ethane, same source ID
    compounds = h.harmonize([r1, r2])
    conflict_compounds = [c for c in compounds if c.conflict_status == ConflictStatus.CONFLICT]
    assert len(conflict_compounds) > 0, "Expected at least one CONFLICT compound"
    all_conflicts = [conf for c in compounds for conf in c.conflicts]
    assert len(all_conflicts) > 0


def test_conflict_is_not_silently_merged() -> None:
    """Exit criterion 2: conflicting records are preserved separately."""
    h = IdentifierHarmonizer()
    r1 = _rec("c1ccccc1", "CID99")  # benzene
    r2 = _rec("CC", "CID99")  # ethane, same compound_id
    _, conflicts = h.harmonize_with_conflicts_report([r1, r2])
    # Both InChIKeys must be present in the conflict report
    all_iks = {c.inchikey_a for c in conflicts} | {c.inchikey_b for c in conflicts}
    assert len(all_iks) == 2, f"Both InChIKeys must be recorded; got {all_iks}"


def test_different_source_ids_same_structure_no_conflict() -> None:
    """Different source IDs that map to the same InChIKey are concordant, not conflict."""
    h = IdentifierHarmonizer()
    # ChEMBL and BindingDB both have benzene under different IDs
    r1 = _rec("c1ccccc1", "CHEMBL_BEN", source_db="chembl")
    r2 = _rec("C1=CC=CC=C1", "BDB_BEN", source_db="bindingdb")
    compounds = h.harmonize([r1, r2])
    ok_compounds = [c for c in compounds if c.conflict_status == ConflictStatus.OK]
    assert len(ok_compounds) == 1
    # Cross-refs contain both source IDs
    c = ok_compounds[0]
    assert "chembl" in c.cross_refs
    assert "bindingdb" in c.cross_refs


# ── Cross-reference preservation (exit criterion 3) ──────────────────────────


def test_source_identifiers_preserved_in_cross_refs() -> None:
    """Exit criterion 3: source IDs retained in cross_refs."""
    h = IdentifierHarmonizer()
    r = [
        _rec("CCO", "CHEMBL_ETH", source_db="chembl", record_id="ACT_ETH_C"),
        _rec("OCC", "BDB_ETH", source_db="bindingdb", record_id="ACT_ETH_B"),
    ]
    compounds = h.harmonize(r)
    c = next(x for x in compounds if x.conflict_status == ConflictStatus.OK)
    assert "CHEMBL_ETH" in c.cross_refs.get("chembl", [])
    assert "BDB_ETH" in c.cross_refs.get("bindingdb", [])


def test_rdkit_version_recorded_in_harmonized_compound() -> None:
    """RDKit version propagated to HarmonizedCompound for SCI0-011."""
    h = IdentifierHarmonizer()
    compounds = h.harmonize([_rec("CC", "C1")])
    assert compounds[0].rdkit_version != ""
    assert compounds[0].rdkit_version != "not_installed"


# ── Stereochemistry (exit criterion 4) ───────────────────────────────────────


def test_enantiomers_get_distinct_internal_ids() -> None:
    """Exit criterion 4: stereoisomers preserved from SCI0-008b."""
    h = IdentifierHarmonizer()
    r_ala = _rec("N[C@@H](C)C(=O)O", "L_ALA")  # L-alanine
    s_ala = _rec("N[C@H](C)C(=O)O", "D_ALA")  # D-alanine
    compounds = h.harmonize([r_ala, s_ala])
    ids = [c.internal_id for c in compounds if c.internal_id]
    assert len(ids) == 2
    assert ids[0] != ids[1], "Enantiomers must have distinct internal IDs"


def test_e_z_isomers_get_distinct_internal_ids() -> None:
    h = IdentifierHarmonizer()
    e_but = _rec(r"C/C=C/C", "E_BUT")
    z_but = _rec(r"C/C=C\C", "Z_BUT")
    compounds = h.harmonize([e_but, z_but])
    ids = [c.internal_id for c in compounds if c.internal_id]
    assert len(ids) == 2
    assert ids[0] != ids[1]


# ── Fail-closed (exit criterion 5) ───────────────────────────────────────────


def test_unresolvable_smiles_is_unresolved_not_dropped() -> None:
    """Exit criterion 5: failed standardization → UNRESOLVED, not silently dropped."""
    h = IdentifierHarmonizer()
    compounds = h.harmonize([_rec("INVALID$$", "BAD_CID")])
    assert len(compounds) == 1
    assert compounds[0].conflict_status == ConflictStatus.UNRESOLVED
    assert compounds[0].internal_id is None


def test_no_smiles_is_unresolved() -> None:
    """Record with no SMILES → UNRESOLVED with provenance."""
    h = IdentifierHarmonizer()
    compounds = h.harmonize([_rec(None, "NO_SMILES_CID")])
    assert len(compounds) == 1
    assert compounds[0].conflict_status == ConflictStatus.UNRESOLVED
    assert "NO_SMILES_PROVIDED" in (compounds[0].provenance.get("failure_reason", ""))


def test_mixed_batch_preserves_all_records() -> None:
    """A batch with valid, invalid, and no-SMILES records returns all three."""
    h = IdentifierHarmonizer()
    records = [
        _rec("c1ccccc1", "GOOD", record_id="R1"),
        _rec("INVALID$$", "BAD", record_id="R2"),
        _rec(None, "NOSMILES", record_id="R3"),
    ]
    compounds = h.harmonize(records)
    assert len(compounds) == 3
    statuses = {c.conflict_status for c in compounds}
    assert ConflictStatus.OK in statuses
    assert ConflictStatus.UNRESOLVED in statuses


# ── Batch reporting ───────────────────────────────────────────────────────────


def test_harmonize_with_conflicts_report_returns_both() -> None:
    h = IdentifierHarmonizer()
    r = [_rec("c1ccccc1", "C1"), _rec("CC", "C2")]
    compounds, conflicts = h.harmonize_with_conflicts_report(r)
    assert isinstance(compounds, list)
    assert isinstance(conflicts, list)


def test_empty_input_returns_empty() -> None:
    h = IdentifierHarmonizer()
    assert h.harmonize([]) == []

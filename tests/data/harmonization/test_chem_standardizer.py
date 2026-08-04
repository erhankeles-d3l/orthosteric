"""SCI0-008b exit-criterion tests.

Exit criteria (spec):
  (1) Stereoisomers remain distinct through the pipeline.
  (2) No descriptor column exists in any output.
  (3) Output is deterministic across runs.
"""

from __future__ import annotations

import dataclasses

import pytest

from orthosteric.data.harmonization._chem_standardizer import (
    RDKIT_VERSION,
    ChemicalStandardizer,
    StandardizationStatus,
    StandardizedStructure,
)


@pytest.fixture(scope="module")
def std() -> ChemicalStandardizer:
    return ChemicalStandardizer()


# ── Basic happy path ──────────────────────────────────────────────────────────


def test_simple_smiles_returns_ok(std: ChemicalStandardizer) -> None:
    r = std.standardize("c1ccccc1")
    assert r.status == StandardizationStatus.OK
    assert r.canonical_smiles is not None
    assert r.inchi is not None
    assert r.inchikey is not None
    assert len(r.inchikey) == 27


def test_rdkit_version_recorded(std: ChemicalStandardizer) -> None:
    """SCI0-011: RDKit version must be recorded in every output."""
    r = std.standardize("CC")
    assert r.rdkit_version == RDKIT_VERSION
    assert r.rdkit_version != "not_installed"


def test_content_hash_is_sha256(std: ChemicalStandardizer) -> None:
    r = std.standardize("CC(=O)O")
    assert r.content_hash is not None
    assert len(r.content_hash) == 64  # SHA-256 hex


# ── Exit criterion 1: stereochemistry preserved ───────────────────────────────


def test_r_and_s_enantiomers_produce_distinct_inchikeys(std: ChemicalStandardizer) -> None:
    """Exit criterion 1: stereoisomers remain distinct through the pipeline."""
    r_alanine = std.standardize("N[C@@H](C)C(=O)O")  # L-alanine
    s_alanine = std.standardize("N[C@H](C)C(=O)O")  # D-alanine
    assert r_alanine.status == StandardizationStatus.OK
    assert s_alanine.status == StandardizationStatus.OK
    assert r_alanine.inchikey != s_alanine.inchikey, "Enantiomers must have distinct InChIKeys"


def test_e_z_isomers_produce_distinct_inchikeys(std: ChemicalStandardizer) -> None:
    """E/Z geometric isomers remain distinct."""
    e_but2ene = std.standardize(r"C/C=C/C")
    z_but2ene = std.standardize(r"C/C=C\C")
    assert e_but2ene.status == StandardizationStatus.OK
    assert z_but2ene.status == StandardizationStatus.OK
    assert e_but2ene.canonical_smiles != z_but2ene.canonical_smiles, (
        "E/Z isomers must remain distinct"
    )


def test_stereochemistry_preserved_flag_always_true(std: ChemicalStandardizer) -> None:
    """stereochemistry_preserved is True even for invalid SMILES."""
    r = std.standardize("INVALID_SMILES_$$$$")
    assert r.stereochemistry_preserved is True


def test_chiral_pi3k_inhibitor_preserves_stereo(std: ChemicalStandardizer) -> None:
    """Alpelisib (PI3Kalpha inhibitor) SMILES retains chirality."""
    # Alpelisib canonical SMILES includes a chiral center
    alpelisib_smiles = "CC1=NC(=C(C=N1)N2CC[C@@H](C2)NS(=O)(=O)C3=CC=C(C=C3)F)C4=CC=C(C=C4)Cl"
    r = std.standardize(alpelisib_smiles)
    assert r.status == StandardizationStatus.OK
    # Canonical SMILES must preserve the @@ stereo notation
    assert "@" in (r.canonical_smiles or ""), "Chiral center must be preserved in canonical SMILES"


# ── Exit criterion 2: no descriptors ─────────────────────────────────────────


def test_standardized_structure_has_no_descriptor_fields(std: ChemicalStandardizer) -> None:
    """Exit criterion 2: no descriptor field exists in StandardizedStructure."""
    r = std.standardize("CC(=O)O")
    # Check that no descriptor-like attributes exist
    descriptor_names = {
        "mol_weight",
        "molecular_weight",
        "mw",
        "logp",
        "log_p",
        "num_rotatable_bonds",
        "rotatable_bonds",
        "num_rings",
        "ring_count",
        "tpsa",
        "hbd",
        "hba",
        "h_bond_donor",
        "h_bond_acceptor",
        "fingerprint",
        "ecfp",
        "morgan",
    }
    record_fields = {f.name for f in r.__class__.__dataclass_fields__.values()}
    overlap = descriptor_names & record_fields
    assert not overlap, f"Descriptor fields found: {overlap}"


def test_standardized_structure_allowed_fields_only() -> None:
    """The allowed output fields are structural identity only."""
    allowed = {
        "original_smiles",
        "canonical_smiles",
        "inchi",
        "inchikey",
        "status",
        "failure_reason",
        "rdkit_version",
        "content_hash",
        "stereochemistry_preserved",
        "salt_stripped",
        "steps_applied",
    }

    actual_fields = {f.name for f in dataclasses.fields(StandardizedStructure)}
    assert actual_fields == allowed, f"Unexpected fields: {actual_fields - allowed}"


# ── Exit criterion 3: determinism ─────────────────────────────────────────────


def test_same_smiles_produces_identical_output(std: ChemicalStandardizer) -> None:
    """Exit criterion 3: deterministic across runs."""
    smiles = "N[C@@H](Cc1ccccc1)C(=O)O"  # L-phenylalanine
    r1 = std.standardize(smiles)
    r2 = std.standardize(smiles)
    assert r1.canonical_smiles == r2.canonical_smiles
    assert r1.inchikey == r2.inchikey
    assert r1.content_hash == r2.content_hash


def test_canonical_smiles_is_idempotent(std: ChemicalStandardizer) -> None:
    """Standardizing a canonical SMILES gives the same canonical SMILES."""
    r1 = std.standardize("CC(=O)Oc1ccccc1C(=O)O")  # aspirin
    assert r1.status == StandardizationStatus.OK
    r2 = std.standardize(r1.canonical_smiles or "")
    assert r1.canonical_smiles == r2.canonical_smiles
    assert r1.inchikey == r2.inchikey


# ── Salt stripping ────────────────────────────────────────────────────────────


def test_salt_is_stripped(std: ChemicalStandardizer) -> None:
    """Sodium salt → free acid; salt_stripped flag set."""
    # Sodium acetate: CC(=O)[O-].[Na+]
    r = std.standardize("CC(=O)[O-].[Na+]")
    assert r.status == StandardizationStatus.OK
    assert r.salt_stripped is True
    # Resulting canonical SMILES should be the organic fragment only
    assert r.canonical_smiles is not None
    assert "Na" not in r.canonical_smiles


def test_single_fragment_not_flagged_as_salt_stripped(std: ChemicalStandardizer) -> None:
    r = std.standardize("CCO")
    assert r.salt_stripped is False


# ── Failure handling ──────────────────────────────────────────────────────────


def test_invalid_smiles_returns_failed_parse(std: ChemicalStandardizer) -> None:
    r = std.standardize("NOT_A_SMILES_$$$$")
    assert r.status == StandardizationStatus.FAILED_PARSE
    assert r.canonical_smiles is None
    assert r.inchikey is None
    assert r.content_hash is None
    assert r.failure_reason is not None
    assert r.original_smiles == "NOT_A_SMILES_$$$$"


def test_failed_record_included_in_batch(std: ChemicalStandardizer) -> None:
    """Failed records are returned, never silently dropped."""
    smiles_list = ["CCO", "INVALID$$", "c1ccccc1"]
    results = std.standardize_batch(smiles_list)
    assert len(results) == 3
    assert results[0].status == StandardizationStatus.OK
    assert results[1].status == StandardizationStatus.FAILED_PARSE
    assert results[2].status == StandardizationStatus.OK


# ── Steps audit trail ─────────────────────────────────────────────────────────


def test_steps_applied_is_non_empty_on_success(std: ChemicalStandardizer) -> None:
    r = std.standardize("CCO")
    assert len(r.steps_applied) > 0
    assert "canonical_smiles" in r.steps_applied
    assert "stereochemistry_preserved" in r.steps_applied


def test_steps_include_salt_strip_when_applicable(std: ChemicalStandardizer) -> None:
    r = std.standardize("CC(=O)[O-].[Na+]")
    assert "salt_strip" in r.steps_applied


# ── Batch ─────────────────────────────────────────────────────────────────────


def test_batch_is_deterministic(std: ChemicalStandardizer) -> None:
    smiles = ["c1ccccc1", "CC(=O)O", "N[C@@H](C)C(=O)O"]
    r1 = std.standardize_batch(smiles)
    r2 = std.standardize_batch(smiles)
    for a, b in zip(r1, r2, strict=True):
        assert a.inchikey == b.inchikey
        assert a.content_hash == b.content_hash

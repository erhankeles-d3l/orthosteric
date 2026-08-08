"""Tests for ligand moiety classification (features._ligand_moiety).

Exit criteria:
  (1) Each moiety class has at least one real-molecule positive test.
  (2) Confirmed-charge moieties (phenolate, protonated amine) are only
      assigned when explicit charge evidence is supplied -- never guessed.
  (3) Priority order is respected (more specific pattern wins).
  (4) Unmatched/ambiguous atoms are UNRESOLVED, never forced into a
      plausible-but-unverified bucket.
  (5) Heavy-atom-count mismatch in the pose-mapping function returns an
      empty dict, never a fabricated partial mapping.
"""

from __future__ import annotations

from rdkit import Chem

from orthosteric.features._ligand_moiety import (
    LigandMoiety,
    classify_ligand_atoms,
    moiety_labels_by_pose_atom_name,
)


def test_carbonyl_oxygen_classified() -> None:
    labels = classify_ligand_atoms("CC(=O)C")  # acetone
    o_idx = next(
        a.GetIdx() for a in Chem.MolFromSmiles("CC(=O)C").GetAtoms() if a.GetSymbol() == "O"
    )
    assert labels[o_idx] == LigandMoiety.CARBONYL_O


def test_phenolic_hydroxyl_classified() -> None:
    labels = classify_ligand_atoms("c1ccccc1O")  # phenol
    mol = Chem.MolFromSmiles("c1ccccc1O")
    o_idx = next(a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "O")
    assert labels[o_idx] == LigandMoiety.HYDROXYL_O


def test_aliphatic_hydroxyl_classified() -> None:
    labels = classify_ligand_atoms("CCO")  # ethanol
    mol = Chem.MolFromSmiles("CCO")
    o_idx = next(a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "O")
    assert labels[o_idx] == LigandMoiety.HYDROXYL_O


def test_ether_oxygen_classified() -> None:
    labels = classify_ligand_atoms("COC")  # dimethyl ether
    mol = Chem.MolFromSmiles("COC")
    o_idx = next(a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "O")
    assert labels[o_idx] == LigandMoiety.ETHER_O


def test_heteroaromatic_nitrogen_classified() -> None:
    labels = classify_ligand_atoms("c1ccncc1")  # pyridine
    mol = Chem.MolFromSmiles("c1ccncc1")
    n_idx = next(a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "N")
    assert labels[n_idx] == LigandMoiety.HETEROAROMATIC_N


def test_aliphatic_amine_classified() -> None:
    labels = classify_ligand_atoms("CCCN")  # propylamine
    mol = Chem.MolFromSmiles("CCCN")
    n_idx = next(a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "N")
    assert labels[n_idx] == LigandMoiety.AMINE_N


def test_sulfonamide_classified() -> None:
    labels = classify_ligand_atoms("CS(=O)(=O)N")  # methanesulfonamide
    mol = Chem.MolFromSmiles("CS(=O)(=O)N")
    n_idx = next(a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "N")
    assert labels[n_idx] == LigandMoiety.SULFONAMIDE


def test_halogen_aromatic_carbon_classified() -> None:
    labels = classify_ligand_atoms("c1ccc(Cl)cc1")  # chlorobenzene
    mol = Chem.MolFromSmiles("c1ccc(Cl)cc1")
    c_idx = next(
        a.GetIdx()
        for a in mol.GetAtoms()
        if a.GetSymbol() == "C" and any(n.GetSymbol() == "Cl" for n in a.GetNeighbors())
    )
    assert labels[c_idx] == LigandMoiety.HALOGEN_AROMATIC_C


def test_hydrophobic_aliphatic_carbon_classified() -> None:
    labels = classify_ligand_atoms("CCCCCC")  # hexane
    mol = Chem.MolFromSmiles("CCCCCC")
    # interior carbons (only C/H neighbours) should be hydrophobic
    for atom in mol.GetAtoms():
        assert labels[atom.GetIdx()] == LigandMoiety.HYDROPHOBIC_ALIPHATIC_C


def test_generic_aromatic_ring_fallback() -> None:
    labels = classify_ligand_atoms("c1ccccc1")  # benzene
    mol = Chem.MolFromSmiles("c1ccccc1")
    for atom in mol.GetAtoms():
        assert labels[atom.GetIdx()] == LigandMoiety.AROMATIC_RING_ATOM


# ── Confirmed-charge-only moieties: never guessed ────────────────────────────


def test_phenolate_requires_confirmed_charge_evidence() -> None:
    """Without confirmed charge evidence, a deprotonated phenol oxygen
    (already anionic in the input SMILES) is NOT auto-labelled
    PHENOLATE_O from SMARTS alone -- only via the confirmed-charge path."""
    smiles = "c1ccc([O-])cc1"
    mol = Chem.MolFromSmiles(smiles)
    o_idx = next(a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "O")
    labels_unconfirmed = classify_ligand_atoms(smiles)
    labels_confirmed = classify_ligand_atoms(smiles, confirmed_charged_indices=frozenset({o_idx}))
    assert labels_unconfirmed.get(o_idx) != LigandMoiety.PHENOLATE_O
    assert labels_confirmed[o_idx] == LigandMoiety.PHENOLATE_O


def test_protonated_amine_requires_confirmed_charge_evidence() -> None:
    smiles = "CC[NH3+]"
    mol = Chem.MolFromSmiles(smiles)
    n_idx = next(a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "N")
    labels_confirmed = classify_ligand_atoms(smiles, confirmed_charged_indices=frozenset({n_idx}))
    assert labels_confirmed[n_idx] == LigandMoiety.PROTONATED_AMINE_N


def test_unparseable_smiles_returns_empty() -> None:
    assert classify_ligand_atoms("not a smiles!!") == {}


# ── Pose-atom-name mapping: anti-fabrication ─────────────────────────────────


class _FakeAtom:
    def __init__(self, name: str, element: str) -> None:
        self.name = name
        self.element = element


def test_pose_mapping_matches_heavy_atom_order() -> None:
    smiles = "CCO"  # ethanol: C, C, O heavy atoms in that order
    pose_atoms = [_FakeAtom("C1", "C"), _FakeAtom("C2", "C"), _FakeAtom("O1", "O")]
    result = moiety_labels_by_pose_atom_name(smiles, pose_atoms)
    assert result["O1"] == LigandMoiety.HYDROXYL_O


def test_pose_mapping_empty_on_heavy_atom_count_mismatch() -> None:
    smiles = "CCO"  # 3 heavy atoms
    pose_atoms = [_FakeAtom("C1", "C")]  # only 1 -- mismatch
    assert moiety_labels_by_pose_atom_name(smiles, pose_atoms) == {}

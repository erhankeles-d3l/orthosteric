"""Ligand functional-group (moiety) classification for docking poses.

Objective: interaction-motif fingerprints workstream. Extends atom-level
interaction identity (element, AutoDock type) with a chemically specific
functional-group label, using a compact RDKit SMARTS vocabulary rather
than a large manually curated ontology.

Reuses the exact heavy-atom-order-alignment technique already
established in this project (ligand_aromatic_atom_names in
analysis/run_docking_interaction_analysis.py; charged_atom_names_from_pose
in features._ligand_protonation) to map RDKit atom indices onto PDBQT
pose atom names.

Moiety vocabulary (bounded, documented -- not exhaustive)
-----------------------------------------------------------
Carbonyl O, hydroxyl O, phenolate O (from confirmed protonation charge,
not guessed), ether O, heteroaromatic N, amine N, protonated amine N
(from confirmed protonation charge), sulfonamide, halogen-bearing
aromatic C, aromatic ring atom (generic, when no more specific pattern
matches), hydrophobic aliphatic C. Matched via RDKit SMARTS in a fixed
priority order (most specific pattern wins); an atom matching none of
these keeps UNRESOLVED rather than being forced into a wrong bucket --
per the mandate's own instruction: "If exact moiety assignment is
uncertain, retain the atom-level identity and mark the higher-level
moiety as unresolved rather than inventing a classification."
"""

from __future__ import annotations

from enum import StrEnum

from rdkit import Chem

MOIETY_CLASSIFIER_POLICY_ID = "ligand_moiety_classifier_v1_rdkit_smarts"


class LigandMoiety(StrEnum):
    CARBONYL_O = "carbonyl_o"
    HYDROXYL_O = "hydroxyl_o"
    PHENOLATE_O = "phenolate_o"  # confirmed-charged only, never guessed
    ETHER_O = "ether_o"
    HETEROAROMATIC_N = "heteroaromatic_n"
    PROTONATED_AMINE_N = "protonated_amine_n"  # confirmed-charged only
    AMINE_N = "amine_n"
    SULFONAMIDE = "sulfonamide"
    HALOGEN_AROMATIC_C = "halogen_aromatic_c"
    AROMATIC_RING_ATOM = "aromatic_ring_atom"
    HYDROPHOBIC_ALIPHATIC_C = "hydrophobic_aliphatic_c"
    UNRESOLVED = "unresolved"


#: (SMARTS, moiety, match_index_of_interest) triples in priority order --
#: first match wins. `match_index_of_interest` names which position in
#: the SMARTS match tuple is the actual atom being classified (RDKit
#: preserves SMARTS atom-writing order in `GetSubstructMatches` output).
_SMARTS_PRIORITY: tuple[tuple[str, LigandMoiety, int], ...] = (
    ("[SX4](=O)(=O)[NX3]", LigandMoiety.SULFONAMIDE, -1),
    ("[CX3]=[OX1]", LigandMoiety.CARBONYL_O, -1),
    ("[cX3][OX2H]", LigandMoiety.HYDROXYL_O, -1),  # phenolic OH (neutral state)
    ("[CX4][OX2H]", LigandMoiety.HYDROXYL_O, -1),  # aliphatic OH
    ("[#6][OX2H0][#6]", LigandMoiety.ETHER_O, 1),  # O is the middle atom
    ("[c][F,Cl,Br,I]", LigandMoiety.HALOGEN_AROMATIC_C, 0),  # the aromatic C, not the halogen
    ("[n]", LigandMoiety.HETEROAROMATIC_N, -1),
    ("[NX3;H2,H1,H0;!$(NC=O);!$(N=*);!a]", LigandMoiety.AMINE_N, -1),
)


def classify_ligand_atoms(
    smiles: str,
    confirmed_charged_indices: frozenset[int] = frozenset(),
) -> dict[int, LigandMoiety]:
    """Classify every heavy atom of `smiles` into a LigandMoiety.

    Returns a dict keyed by RDKit heavy-atom index (0-based, canonical
    atom order of `Chem.MolFromSmiles(smiles)`), NOT PDBQT atom name --
    callers map this to pose atom names separately via
    `moiety_labels_by_pose_atom_name`, mirroring the existing
    aromatic/charge-mapping pattern in this project.

    `confirmed_charged_indices` (from features._ligand_protonation's real
    Dimorphite-DL formal-charge result) is used ONLY to distinguish
    PHENOLATE_O / PROTONATED_AMINE_N from their neutral counterparts --
    never to guess a charge state this function did not receive evidence
    for.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {}

    labels: dict[int, LigandMoiety] = {}
    _apply_confirmed_charge_moieties(mol, confirmed_charged_indices, labels)
    _apply_smarts_moieties(mol, labels)
    _apply_generic_fallback_moieties(mol, labels)
    return labels


def _apply_confirmed_charge_moieties(
    mol: Chem.Mol, confirmed_charged_indices: frozenset[int], labels: dict[int, LigandMoiety]
) -> None:
    """Assign confirmed-charge moieties (highest specificity).

    Requires positive external evidence, never inferred from SMARTS alone.
    """
    for idx in confirmed_charged_indices:
        if idx >= mol.GetNumAtoms():
            continue
        atom = mol.GetAtomWithIdx(idx)
        if atom.GetSymbol() == "O" and atom.GetFormalCharge() < 0:
            labels[idx] = LigandMoiety.PHENOLATE_O
        elif atom.GetSymbol() == "N" and atom.GetFormalCharge() > 0:
            labels[idx] = LigandMoiety.PROTONATED_AMINE_N


def _apply_smarts_moieties(mol: Chem.Mol, labels: dict[int, LigandMoiety]) -> None:
    """Priority-ordered SMARTS pass.

    Never overwrites a confirmed-charge assignment already made.
    """
    for smarts, moiety, target_pos in _SMARTS_PRIORITY:
        pattern = Chem.MolFromSmarts(smarts)
        if pattern is None:
            continue
        for match in mol.GetSubstructMatches(pattern):
            target_idx = match[target_pos]
            if target_idx not in labels:
                labels[target_idx] = moiety


def _apply_generic_fallback_moieties(mol: Chem.Mol, labels: dict[int, LigandMoiety]) -> None:
    """Lowest-priority pass.

    Generic aromatic ring / hydrophobic aliphatic carbon / UNRESOLVED for
    anything not already assigned a specific label.
    """
    for atom in mol.GetAtoms():
        idx = atom.GetIdx()
        if idx in labels:
            continue
        if atom.GetIsAromatic():
            labels[idx] = LigandMoiety.AROMATIC_RING_ATOM
        elif atom.GetSymbol() == "C" and _is_purely_nonpolar_carbon(atom):
            labels[idx] = LigandMoiety.HYDROPHOBIC_ALIPHATIC_C
        else:
            labels[idx] = LigandMoiety.UNRESOLVED


def _is_purely_nonpolar_carbon(atom: Chem.Atom) -> bool:
    """True only for aliphatic carbons with no adjacent heteroatom.

    Never labels a carbon adjacent to O/N/S as hydrophobic, since that
    would misrepresent its chemistry.
    """
    return all(nbr.GetSymbol() in ("C", "H") for nbr in atom.GetNeighbors())


def moiety_labels_by_pose_atom_name(
    smiles: str,
    pose_atoms: list,  # list[PoseAtom] from features._docking_interaction_detector
    confirmed_charged_indices: frozenset[int] = frozenset(),
) -> dict[str, LigandMoiety]:
    """Map RDKit-index moiety labels onto PDBQT pose atom names.

    Returns an empty dict (never fabricated names) if the heavy-atom
    counts don't match between `smiles` and `pose_atoms` -- the same
    safety check already used for aromatic-atom and charged-atom mapping
    elsewhere in this project.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {}
    by_idx = classify_ligand_atoms(smiles, confirmed_charged_indices)
    heavy_pose_atoms = [a for a in pose_atoms if a.element != "H"]
    if len(heavy_pose_atoms) != mol.GetNumHeavyAtoms():
        return {}
    return {
        heavy_pose_atoms[idx].name: moiety
        for idx, moiety in by_idx.items()
        if idx < len(heavy_pose_atoms)
    }

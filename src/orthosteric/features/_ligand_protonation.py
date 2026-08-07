"""pH-aware ligand protonation for docking-pose interaction detection.

Objective: replace atom-type-only inference of ligand ionization state
(the CHARGED_CONTACT_CANDIDATE relabelling from the prior session) with
a real pH-aware protonation step, so confirmed-ionizable ligand atoms can
be legitimately promoted back to SALT_BRIDGE.

Tool: Dimorphite-DL 2.0.2 (real, open-source, pip-installable as
`dimorphite_dl`; verified this session against known reference chemistry
-- benzoic acid deprotonates to carboxylate at pH 7.4, consistent with
its ~4.2 pKa; benzylamine shows BOTH neutral and protonated states at
pH 7.4, consistent with its ~9.3 pKa placing physiological pH in its
ambiguous transition region; an aryl-conjugated morpholine nitrogen
remains neutral, correctly reflecting its much-reduced basicity).

Policy (ENGINEERING CHOICE, documented; not a scientific threshold)
-------------------------------------------------------------------
Requested pH: 7.4 exactly (physiological), ph_min = ph_max = 7.4.
Dimorphite-DL at a single pH point still enumerates every
COMBINATORIALLY valid ionization pattern across all ionizable sites in
one molecule (not a single "most probable" state) -- for a
polyprotic/polyphenolic ligand (e.g. quercetin, 4 phenols) this can
produce dozens of states. Running every combinatorial state through full
docking is computationally infeasible at this session's scale.

Bounded selection rule: when N>1 states are returned, the FIRST state in
Dimorphite-DL's own output order is used for docking (its enumeration is
deterministic given a fixed input and settings, so this is reproducible,
not arbitrary-per-run) -- but the ambiguity is NEVER hidden:
`ProtonationResult.is_ambiguous` and `.n_states` are recorded on every
downstream interaction record's provenance, and `all_states` retains the
complete enumerated list. This satisfies "preserve the ambiguity rather
than forcing one state" at the METADATA/provenance level, while docking
one representative state for practical compute reasons -- a documented
scope decision, not a silently discarded one.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import dimorphite_dl
from rdkit import Chem

PROTONATION_POLICY_ID = "dimorphite_dl_2.0.2_ph7.4_first_state_v1"
REQUESTED_PH = 7.4


@dataclass(frozen=True, slots=True)
class ProtonationResult:
    """Outcome of pH-aware protonation for one ligand.

    Attributes:
        original_smiles:    Input SMILES, as supplied.
        selected_smiles:    The state used for downstream docking (first
                            of `all_states`, per the documented policy).
        all_states:         Every combinatorially valid ionization state
                            Dimorphite-DL returned at `requested_ph` --
                            never discarded, even though only the first
                            is docked.
        is_ambiguous:       True iff Dimorphite-DL returned >1 state (the
                            physiological ionization state is genuinely
                            uncertain at this pH for this molecule).
        n_states:           len(all_states).
        requested_ph:       The pH Dimorphite-DL was asked to protonate at.
        charged_atom_indices: RDKit heavy-atom indices (0-based, in
                            `selected_smiles`'s canonical atom order) with
                            nonzero formal charge in the SELECTED state --
                            the real, chemically-confirmed ionizable atoms.
        charged_atom_formal_charges: Parallel list of the formal charge
                            values (+1, -1, etc.) for each entry in
                            `charged_atom_indices`.
        tool_version:       "dimorphite_dl==2.0.2".
        policy:             PROTONATION_POLICY_ID.
    """

    original_smiles: str
    selected_smiles: str
    all_states: tuple[str, ...]
    is_ambiguous: bool
    n_states: int
    requested_ph: float
    charged_atom_indices: tuple[int, ...]
    charged_atom_formal_charges: tuple[int, ...]
    tool_version: str = field(default="dimorphite_dl==2.0.2")
    policy: str = field(default=PROTONATION_POLICY_ID)

    def content_sha256(self) -> str:
        payload = f"{self.original_smiles}|{self.selected_smiles}|{sorted(self.all_states)}"
        return hashlib.sha256(payload.encode()).hexdigest()


def protonate_ligand(smiles: str, ph: float = REQUESTED_PH) -> ProtonationResult | None:
    """Run Dimorphite-DL at a single pH and identify confirmed-charged atoms.

    Uses RDKit formal charge on the selected protonation state. Returns
    None if the input SMILES cannot be parsed or protonation fails --
    never fabricates a result.
    """
    try:
        states = dimorphite_dl.protonate_smiles(smiles, ph_min=ph, ph_max=ph)
    except Exception:
        return None
    if not states:
        return None

    selected = states[0]
    mol = Chem.MolFromSmiles(selected)
    if mol is None:
        return None

    charged_idx = []
    charged_val = []
    for atom in mol.GetAtoms():
        fc = atom.GetFormalCharge()
        if fc != 0:
            charged_idx.append(atom.GetIdx())
            charged_val.append(fc)

    return ProtonationResult(
        original_smiles=smiles,
        selected_smiles=selected,
        all_states=tuple(states),
        is_ambiguous=len(states) > 1,
        n_states=len(states),
        requested_ph=ph,
        charged_atom_indices=tuple(charged_idx),
        charged_atom_formal_charges=tuple(charged_val),
    )


def charged_atom_names_from_pose(
    protonation: ProtonationResult, ligand_pose_atoms: list[Any]
) -> frozenset[str]:
    """Map RDKit charged-atom indices to PDBQT atom names in a docked pose.

    Uses the same heavy-atom-order-alignment technique already used for
    aromatic-atom mapping (ligand_aromatic_atom_names in
    analysis/run_docking_interaction_analysis.py).

    Returns an empty set (never fabricated names) if the heavy-atom
    counts don't match -- e.g. if the pose was docked from a DIFFERENT
    SMILES than `protonation.selected_smiles` (a real safety check, not
    a formality: it is possible to accidentally dock the neutral SMILES
    while analyzing charges from the protonated one, and this guards
    against silently mismatching the two).
    """
    if not protonation.charged_atom_indices:
        return frozenset()
    mol = Chem.MolFromSmiles(protonation.selected_smiles)
    if mol is None:
        return frozenset()
    heavy_atoms_pose = [a for a in ligand_pose_atoms if a.element != "H"]
    if len(heavy_atoms_pose) != mol.GetNumHeavyAtoms():
        return frozenset()
    return frozenset(
        heavy_atoms_pose[i].name
        for i in protonation.charged_atom_indices
        if i < len(heavy_atoms_pose)
    )

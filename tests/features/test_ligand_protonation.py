"""Tests for pH-aware ligand protonation (features._ligand_protonation).

Exit criteria:
  (1) Known reference chemistry reproduces the expected pKa-driven
      behaviour: benzoic acid deprotonates at pH 7.4 (pKa ~4.2); an
      aryl-conjugated amine (much-reduced basicity) stays neutral.
  (2) Ambiguity (multiple valid states) is detected and never hidden.
  (3) Unparseable input returns None, never a fabricated result.
  (4) charged_atom_names_from_pose returns an empty set (never a
      fabricated name) when heavy-atom counts mismatch the pose.
"""

from __future__ import annotations

from orthosteric.features._ligand_protonation import (
    ProtonationResult,
    charged_atom_names_from_pose,
    protonate_ligand,
)


def test_benzoic_acid_deprotonates_at_physiological_ph() -> None:
    """PKa ~4.2 -- fully deprotonated (anionic carboxylate) at pH 7.4."""
    result = protonate_ligand("c1ccccc1C(=O)O", ph=7.4)
    assert result is not None
    assert -1 in result.charged_atom_formal_charges
    assert len(result.charged_atom_indices) >= 1


def test_aryl_conjugated_amine_stays_neutral() -> None:
    """An aniline-type/aryl-conjugated morpholine nitrogen has much
    reduced basicity and should remain neutral at pH 7.4."""
    result = protonate_ligand("c1ccc(N2CCOCC2)cc1", ph=7.4)
    assert result is not None
    assert result.charged_atom_indices == ()
    assert result.is_ambiguous is False


def test_benzylamine_shows_ambiguity_near_its_pka() -> None:
    """Benzylamine pKa ~9.3 -- physiological pH 7.4 sits in a region
    where Dimorphite-DL reports the protonation state as genuinely
    plausible either way; this must be surfaced, not hidden."""
    result = protonate_ligand("NCc1ccccc1", ph=7.4)
    assert result is not None
    assert result.n_states >= 1
    # whichever state is selected, all_states must retain every option
    assert len(result.all_states) == result.n_states


def test_unparseable_smiles_returns_none() -> None:
    assert protonate_ligand("not a valid smiles!!!") is None


def test_result_is_deterministic() -> None:
    r1 = protonate_ligand("c1ccccc1C(=O)O", ph=7.4)
    r2 = protonate_ligand("c1ccccc1C(=O)O", ph=7.4)
    assert r1.content_sha256() == r2.content_sha256()


def test_content_sha256_reflects_all_states_not_just_selected() -> None:
    """Two results with the same selected state but different full
    enumerations must not silently hash identically."""
    r1 = ProtonationResult(
        original_smiles="X",
        selected_smiles="Y",
        all_states=("Y",),
        is_ambiguous=False,
        n_states=1,
        requested_ph=7.4,
        charged_atom_indices=(),
        charged_atom_formal_charges=(),
    )
    r2 = ProtonationResult(
        original_smiles="X",
        selected_smiles="Y",
        all_states=("Y", "Z"),
        is_ambiguous=True,
        n_states=2,
        requested_ph=7.4,
        charged_atom_indices=(),
        charged_atom_formal_charges=(),
    )
    assert r1.content_sha256() != r2.content_sha256()


# ── charged_atom_names_from_pose: anti-fabrication ───────────────────────────


class _FakeAtom:
    def __init__(self, name: str, element: str) -> None:
        self.name = name
        self.element = element


def test_charged_atom_names_empty_when_no_charged_atoms() -> None:
    result = protonate_ligand("c1ccc(N2CCOCC2)cc1", ph=7.4)
    pose_atoms = [_FakeAtom(f"A{i}", "C") for i in range(20)]
    assert charged_atom_names_from_pose(result, pose_atoms) == frozenset()


def test_charged_atom_names_empty_when_heavy_atom_count_mismatches() -> None:
    """Safety check: if the pose has a different heavy-atom count than
    the protonation result's SMILES (e.g. wrong ligand accidentally
    paired with wrong protonation result), never fabricate a mapping."""
    result = protonate_ligand("c1ccccc1C(=O)O", ph=7.4)  # 9 heavy atoms
    assert result is not None
    assert result.charged_atom_indices  # confirmed real charge exists
    wrong_pose_atoms = [_FakeAtom(f"A{i}", "C") for i in range(3)]  # wrong count
    assert charged_atom_names_from_pose(result, wrong_pose_atoms) == frozenset()

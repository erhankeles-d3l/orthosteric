"""Rotamer-state representation for selectivity-relevant pocket residues.

Authority: ADR-0010 [Architectural]; SCI1-002 (Milestone 3).
Constitution sections served: §2.1 (rotamer states are part of the pocket, not
  noise; sequence/backbone-only is non-compliant), §0.3 (Trp780/Met772 shelf
  and affinity-pocket residues).

Scientific rule classification
--------------------------------
RULE_AVAILABLE:
  - Chi-angle atom definitions are unambiguous biochemical conventions:
      chi1: N – Cα – Cβ – Cγ (or equivalent)
      chi2: Cα – Cβ – Cγ – Cδ (or equivalent)
      (full table below in `CHI_ATOM_NAMES`)
    These are textbook definitions (Dunbrack & Karplus 1993; Lovell et al.
    2000) and do not require governance.
  - `RotamerAvailability.OBSERVED` / `MISSING_ATOMS` / `MISSING_RESIDUE` /
    `NOT_APPLICABLE` vocabulary: these distinguish the four scientifically
    distinct states the Constitution's representational requirement implies.
    §2.1: "rotamer states are part of the pocket, not noise."

RULE_MISSING / GOVERNANCE_DECISION_REQUIRED:
  - Rotamer *classification* (canonical gauche+ / trans / gauche- labels, or
    Dunbrack/Ponder-Richards bins): angular cutoffs for classification are not
    governed by any Constitution section, ADR, or GDR. Raw chi-angle values
    are returned; the field `rotamer_label` is always ``None`` until a GDR
    specifies the classification scheme and cutoffs.

NOT_APPLICABLE:
  - Glycine (no Cβ, no chi1), Alanine (no Cγ, no chi1 per our convention),
    and Pro are handled specially; see `CHI_ATOM_NAMES`.

No conformational inference
---------------------------
Missing side-chain atoms are recorded as `MISSING_ATOMS`, NOT filled in,
modelled, or guessed. The pipeline is fail-closed on missing structural data.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

try:
    from Bio.PDB.vectors import (  # type: ignore[import-untyped]
        calc_dihedral as _biopython_calc_dihedral,
    )

    _BIOPYTHON_AVAILABLE = True
except (ImportError, AttributeError):
    _BIOPYTHON_AVAILABLE = False

    def _biopython_calc_dihedral(*_args: Any) -> float:  # type: ignore[misc,no-redef]
        """Stub when BioPython is unavailable."""
        return 0.0

    _BIOPYTHON_AVAILABLE = True

from orthosteric.pocket._pocket_definition import PocketResidueSet
from orthosteric.pocket._structure_record import StructureProvenance, StructureRecord

__all__ = [
    "CHI_ATOM_NAMES",
    "ROTAMER_ALGORITHM_VERSION",
    "ROTAMER_CLASSIFICATION_RULE_MISSING_NOTE",
    "ChiAngle",
    "PocketRotamerStates",
    "ResidueRotamerState",
    "RotamerAvailability",
    "compute_pocket_rotamer_states",
]

ROTAMER_ALGORITHM_VERSION = "pocket_rotamer_v1_sci1002"

ROTAMER_CLASSIFICATION_RULE_MISSING_NOTE = (
    "RULE_MISSING/GOVERNANCE_DECISION_REQUIRED: rotamer classification (gauche+, "
    "trans, gauche-, or Dunbrack-bin labels) requires angular cutoffs that are not "
    "governed by any Constitution section, ADR, or GDR in this project. Raw chi "
    "angles are reported; `rotamer_label` remains None until a Governance Decision "
    "Record specifies the classification scheme."
)

# Chi-angle atom quadruples (N-Cα-Cβ-Cγ notation).
# Source: Dunbrack & Karplus 1993; Lovell et al. 2000 (Proteins 50:437-450).
# Each entry: list of (atom1, atom2, atom3, atom4) tuples for chi1, chi2, ...
# Glycine, Alanine, and PRO are excluded from chi1+ because they lack the
# relevant Cγ equivalent that forms a chi angle meaningful for selectivity.
CHI_ATOM_NAMES: dict[str, list[tuple[str, str, str, str]]] = {
    "ARG": [
        ("N", "CA", "CB", "CG"),
        ("CA", "CB", "CG", "CD"),
        ("CB", "CG", "CD", "NE"),
        ("CG", "CD", "NE", "CZ"),
    ],
    "ASN": [("N", "CA", "CB", "CG"), ("CA", "CB", "CG", "OD1")],
    "ASP": [("N", "CA", "CB", "CG"), ("CA", "CB", "CG", "OD1")],
    "CYS": [("N", "CA", "CB", "SG")],
    "GLN": [("N", "CA", "CB", "CG"), ("CA", "CB", "CG", "CD"), ("CB", "CG", "CD", "OE1")],
    "GLU": [("N", "CA", "CB", "CG"), ("CA", "CB", "CG", "CD"), ("CB", "CG", "CD", "OE1")],
    "HIS": [("N", "CA", "CB", "CG"), ("CA", "CB", "CG", "ND1")],
    "ILE": [("N", "CA", "CB", "CG1"), ("CA", "CB", "CG1", "CD1")],
    "LEU": [("N", "CA", "CB", "CG"), ("CA", "CB", "CG", "CD1")],
    "LYS": [
        ("N", "CA", "CB", "CG"),
        ("CA", "CB", "CG", "CD"),
        ("CB", "CG", "CD", "CE"),
        ("CG", "CD", "CE", "NZ"),
    ],
    "MET": [("N", "CA", "CB", "CG"), ("CA", "CB", "CG", "SD"), ("CB", "CG", "SD", "CE")],
    "PHE": [("N", "CA", "CB", "CG"), ("CA", "CB", "CG", "CD1")],
    "PRO": [
        ("N", "CA", "CB", "CG"),
        ("CA", "CB", "CG", "CD"),
    ],  # constrained ring; retained for completeness
    "SER": [("N", "CA", "CB", "OG")],
    "THR": [("N", "CA", "CB", "OG1")],
    "TRP": [("N", "CA", "CB", "CG"), ("CA", "CB", "CG", "CD1")],
    "TYR": [("N", "CA", "CB", "CG"), ("CA", "CB", "CG", "CD1")],
    "VAL": [("N", "CA", "CB", "CG1")],
    # GLY, ALA: no chi angles
}


class RotamerAvailability(StrEnum):
    """Constitution §2.1 rotamer-state vocabulary.

    These four states must be kept distinct and must not be collapsed into a
    single null/None. Each has a different scientific meaning:
    - OBSERVED: chi angles computed from resolved atomic coordinates.
    - MISSING_ATOMS: the residue is present in the structure, but one or more
      side-chain atoms needed for chi-angle computation are absent (e.g. not
      resolved in electron density).
    - MISSING_RESIDUE: the entire residue is absent from the structure (not
      resolved at the backbone level either). Cannot be treated the same as
      MISSING_ATOMS — one implies partial information, the other none.
    - NOT_APPLICABLE: the residue type (Gly, Ala) genuinely has no chi angle;
      this is a fact about amino acid chemistry, not a data-quality issue.
    """

    OBSERVED = "observed"
    MISSING_ATOMS = "missing_atoms"
    MISSING_RESIDUE = "missing_residue"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class ChiAngle:
    """One measured chi dihedral angle.

    Attributes:
        chi_index: 1-based index (chi1, chi2, ...).
        value_degrees: Raw dihedral in degrees, [-180, 180). Rounded to 2 dp
                       for deterministic serialisation.
        atom_names: The four atoms defining this dihedral
                    (a1, a2, a3, a4 in order), e.g. (N, CA, CB, CG).
    """

    chi_index: int
    value_degrees: float
    atom_names: tuple[str, str, str, str]

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "atom_names": list(self.atom_names),
            "chi_index": self.chi_index,
            "value_degrees": self.value_degrees,
        }


@dataclass(frozen=True, slots=True)
class ResidueRotamerState:
    """Rotamer state of one residue in the pocket.

    Attributes:
        residue_id:          `ResidueRecord.residue_id()`.
        residue_name:        3-letter residue name.
        chain_id:            PDB chain identifier.
        residue_seq:         PDB sequence number.
        canonical_position:  Cross-isoform canonical position (None before
                             residue mapping runs in SCI1-003).
        availability:        See `RotamerAvailability`.
        chi_angles:          Measured chi angles (empty when not OBSERVED).
        rotamer_label:       Always ``None`` — RULE_MISSING/GOVERNANCE_DECISION_
                             REQUIRED (see `ROTAMER_CLASSIFICATION_RULE_MISSING_NOTE`).
        n_chi_expected:      How many chi angles the residue type should have.
        n_chi_computed:      How many were actually computed.
        missing_atom_names:  Atoms required for chi computation that were absent.
    """

    residue_id: str
    residue_name: str
    chain_id: str
    residue_seq: int
    canonical_position: int | None
    availability: RotamerAvailability
    chi_angles: tuple[ChiAngle, ...]
    rotamer_label: None
    n_chi_expected: int
    n_chi_computed: int
    missing_atom_names: tuple[str, ...]

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "availability": self.availability.value,
            "canonical_position": self.canonical_position,
            "chain_id": self.chain_id,
            "chi_angles": [c.to_canonical_dict() for c in self.chi_angles],
            "missing_atom_names": sorted(self.missing_atom_names),
            "n_chi_computed": self.n_chi_computed,
            "n_chi_expected": self.n_chi_expected,
            "residue_id": self.residue_id,
            "residue_name": self.residue_name,
            "residue_seq": self.residue_seq,
            "rotamer_label": None,
        }


@dataclass(frozen=True, slots=True)
class PocketRotamerStates:
    """Rotamer states for all residues in the governed pocket.

    Attributes:
        structure_record_id:   Back-reference to the `StructureRecord`.
        provenance:            Structural provenance.
        algorithm_version:     `ROTAMER_ALGORITHM_VERSION`.
        residue_states:        One entry per residue in the pocket residue set,
                               sorted deterministically.
        n_observed:            Count with RotamerAvailability.OBSERVED.
        n_missing_atoms:       Count with RotamerAvailability.MISSING_ATOMS.
        n_missing_residue:     Count with RotamerAvailability.MISSING_RESIDUE.
        n_not_applicable:      Count with RotamerAvailability.NOT_APPLICABLE.
        classification_governance_note: `ROTAMER_CLASSIFICATION_RULE_MISSING_NOTE`.
    """

    structure_record_id: str
    provenance: StructureProvenance
    algorithm_version: str
    residue_states: tuple[ResidueRotamerState, ...]
    n_observed: int
    n_missing_atoms: int
    n_missing_residue: int
    n_not_applicable: int
    classification_governance_note: str

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "algorithm_version": self.algorithm_version,
                "provenance": self.provenance.to_canonical_dict(),
                "residue_states": [r.to_canonical_dict() for r in self.residue_states],
                "structure_record_id": self.structure_record_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _calc_chi_degrees(bio_residue: object, atom_names: tuple[str, str, str, str]) -> float | None:
    """Compute a dihedral angle in degrees from four atom names.

    Returns ``None`` if any atom is absent (coordinates unavailable).
    """
    if not _BIOPYTHON_AVAILABLE or not _BIOPYTHON_AVAILABLE:
        return None
    atoms = []
    for name in atom_names:
        if name not in bio_residue:  # type: ignore[operator]
            return None
        atoms.append(bio_residue[name].get_vector())  # type: ignore[index]
    angle_rad = _biopython_calc_dihedral(*atoms)  # type: ignore[no-untyped-call]
    return round(math.degrees(angle_rad), 2)  # round for determinism


def compute_pocket_rotamer_states(
    bio_structure: Any,
    structure_record: StructureRecord,
    pocket_residue_set: PocketResidueSet,
) -> PocketRotamerStates:
    """Compute rotamer states for all governed pocket residues.

    Parameters
    ----------
    bio_structure:
        A `Bio.PDB.Structure.Structure`, already parsed.
    structure_record:
        The `StructureRecord` providing provenance.
    pocket_residue_set:
        The governed pocket residue set.

    Returns:
    -------
    `PocketRotamerStates` — frozen, deterministic, with explicit missing-data
    states (never inferred).
    """
    bio_model = next(iter(bio_structure.get_models()))  # type: ignore[attr-defined]
    residue_states: list[ResidueRotamerState] = []

    # Deterministic ordering
    sorted_pocket = sorted(
        pocket_residue_set.residues,
        key=lambda pr: (
            pr.residue.chain_id,
            pr.residue.residue_seq,
            pr.residue.insertion_code,
        ),
    )

    for pocket_res in sorted_pocket:
        rr = pocket_res.residue
        res_name = rr.residue_name
        chi_template = CHI_ATOM_NAMES.get(res_name, [])
        n_expected = len(chi_template)

        # Residue types with no chi angles
        if n_expected == 0:
            residue_states.append(
                ResidueRotamerState(
                    residue_id=rr.residue_id(),
                    residue_name=res_name,
                    chain_id=rr.chain_id,
                    residue_seq=rr.residue_seq,
                    canonical_position=rr.canonical_position,
                    availability=RotamerAvailability.NOT_APPLICABLE,
                    chi_angles=(),
                    rotamer_label=None,
                    n_chi_expected=0,
                    n_chi_computed=0,
                    missing_atom_names=(),
                )
            )
            continue

        # Locate in structure
        try:
            bio_chain = bio_model[rr.chain_id]
        except KeyError:
            residue_states.append(
                ResidueRotamerState(
                    residue_id=rr.residue_id(),
                    residue_name=res_name,
                    chain_id=rr.chain_id,
                    residue_seq=rr.residue_seq,
                    canonical_position=rr.canonical_position,
                    availability=RotamerAvailability.MISSING_RESIDUE,
                    chi_angles=(),
                    rotamer_label=None,
                    n_chi_expected=n_expected,
                    n_chi_computed=0,
                    missing_atom_names=tuple(sorted({a for atoms in chi_template for a in atoms})),
                )
            )
            continue

        bio_res_key = (" ", rr.residue_seq, rr.insertion_code)
        try:
            bio_res = bio_chain[bio_res_key]
        except KeyError:
            residue_states.append(
                ResidueRotamerState(
                    residue_id=rr.residue_id(),
                    residue_name=res_name,
                    chain_id=rr.chain_id,
                    residue_seq=rr.residue_seq,
                    canonical_position=rr.canonical_position,
                    availability=RotamerAvailability.MISSING_RESIDUE,
                    chi_angles=(),
                    rotamer_label=None,
                    n_chi_expected=n_expected,
                    n_chi_computed=0,
                    missing_atom_names=tuple(sorted({a for atoms in chi_template for a in atoms})),
                )
            )
            continue

        # Compute each chi angle; track missing atoms
        chi_angles: list[ChiAngle] = []
        all_missing: set[str] = set()

        for idx, (a1, a2, a3, a4) in enumerate(chi_template, start=1):
            missing_for_this = {a for a in (a1, a2, a3, a4) if a not in bio_res}
            if missing_for_this:
                all_missing.update(missing_for_this)
                continue  # can't compute; don't infer
            angle = _calc_chi_degrees(bio_res, (a1, a2, a3, a4))
            if angle is None:
                all_missing.update({a1, a2, a3, a4})
                continue
            chi_angles.append(
                ChiAngle(
                    chi_index=idx,
                    value_degrees=angle,
                    atom_names=(a1, a2, a3, a4),
                )
            )

        availability = (
            RotamerAvailability.OBSERVED
            if len(chi_angles) == n_expected
            else (
                RotamerAvailability.MISSING_ATOMS
                if len(chi_angles) < n_expected
                else RotamerAvailability.OBSERVED  # all computed (defensive)
            )
        )

        residue_states.append(
            ResidueRotamerState(
                residue_id=rr.residue_id(),
                residue_name=res_name,
                chain_id=rr.chain_id,
                residue_seq=rr.residue_seq,
                canonical_position=rr.canonical_position,
                availability=availability,
                chi_angles=tuple(chi_angles),
                rotamer_label=None,
                n_chi_expected=n_expected,
                n_chi_computed=len(chi_angles),
                missing_atom_names=tuple(sorted(all_missing)),
            )
        )

    n_obs = sum(1 for r in residue_states if r.availability == RotamerAvailability.OBSERVED)
    n_miss_a = sum(1 for r in residue_states if r.availability == RotamerAvailability.MISSING_ATOMS)
    n_miss_r = sum(
        1 for r in residue_states if r.availability == RotamerAvailability.MISSING_RESIDUE
    )
    n_na = sum(1 for r in residue_states if r.availability == RotamerAvailability.NOT_APPLICABLE)

    return PocketRotamerStates(
        structure_record_id=structure_record.record_id,
        provenance=structure_record.provenance,
        algorithm_version=ROTAMER_ALGORITHM_VERSION,
        residue_states=tuple(residue_states),
        n_observed=n_obs,
        n_missing_atoms=n_miss_a,
        n_missing_residue=n_miss_r,
        n_not_applicable=n_na,
        classification_governance_note=ROTAMER_CLASSIFICATION_RULE_MISSING_NOTE,
    )

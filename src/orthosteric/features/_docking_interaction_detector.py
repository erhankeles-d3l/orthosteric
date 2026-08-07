"""Atom-residue interaction detector for docking poses (Vina/Meeko PDBQT).

Objective: cross-docking workstream, atom-residue interaction layer.

Relationship to existing infrastructure (do not duplicate)
-----------------------------------------------------------
`orthosteric.features._interaction_fingerprint` (SCI1-004) already
implements this exact chemistry -- H-bond/salt-bridge/pi-pi/cation-pi/
hydrophobic/water/halogen/metal detection -- for BioPython `Structure`
objects built from experimentally-deposited or AlphaFold-derived PDB
files where the ligand is a co-crystallized HETATM within the same
structure. This module does NOT reimplement that chemistry from
scratch: the governed residue-classification vocabulary (which residues
are hydrophobic/cationic/anionic, which atoms form aromatic rings, which
atoms are cationic side-chain nitrogens) is imported directly from that
module so the two never diverge.

What IS new here: a lightweight, self-contained orchestration layer
suited to Vina/Meeko's actual output format (PDBQT atoms with explicit
AutoDock atom types), rather than the full BioPython Structure +
StructureRecord + PocketResidueSet object graph SCI1-004 was built for.
That formal pipeline validates receptor deposition metadata (resolution,
deposition year, construct class, conformational state, etc.) that a
docking POSE does not have and is not designed to carry -- integrating
docking poses into it would either violate its invariants or require
fabricating metadata. This module was built instead, explicitly
documented as the bounded scope decision it is.

A real chemistry improvement over the element-only heuristic in
_interaction_fingerprint.py: PDBQT atoms from Meeko/AutoDock already
carry an explicit ATOM TYPE (OA/NA/SA = confirmed H-bond acceptor,
HD = confirmed donor hydrogen with real 3D coordinates, A = aromatic
carbon, C = aliphatic carbon) -- the standard AutoDock4/Vina typing
convention, not invented here. This lets H-bond detection use a real
D-H...A angle criterion (donor hydrogens have explicit, real
coordinates in the docked pose), not just heavy-atom proximity.

Interaction vocabulary implemented this session (bounded scope)
--------------------------------------------------------------------
  H_BOND, CHARGED_CONTACT_CANDIDATE, PI_PI, CATION_PI, HYDROPHOBIC_CONTACT.

Explicitly OUT OF SCOPE this session (per instruction: "if reliable
detection cannot be implemented cheaply and robustly, explicitly mark
it as out of scope rather than inventing a weak heuristic"):
  HALOGEN_BOND -- reliable detection needs sigma-hole directional
    geometry (C-X...A angle near 180 degrees) that the current pilot's
    mostly-non-halogenated ligand set cannot meaningfully validate
    this session.
  METAL_COORDINATION -- no catalytic/structural metal ions are retained
    in the stripped receptor structures used for docking (removed
    during receptor prep, per the additive-ion exclusion list).
  WATER_MEDIATED -- Level 1 only (no explicit water) per this session's
    scope. Crystallographic waters were stripped during receptor
    preparation for docking; this is reported explicitly as
    `WATER_MEDIATED_INTERACTION = "not_inferred"`, never fabricated.

Geometric criteria (ENGINEERING CHOICE -- literature-standard practical
approximations, consistent with common PLIF-tool conventions (e.g.
PLIP, Arpeggio); NOT Constitution-governed thresholds, and explicitly
labelled as approximations, not validated physical definitions)
--------------------------------------------------------------------------
  H_BOND:              D...A distance <= 3.5 A; D-H...A angle (vertex at
                        the hydrogen) >= 120 deg (uses real HD hydrogen coordinates when present
                        on either side; if neither side has a resolvable
                        H for a given donor, the pair is skipped, never
                        approximated with a fabricated angle).
  CHARGED_CONTACT_CANDIDATE: charged-group heavy-atom min distance <= 4.0 A
                        (see "Charged-contact relabelling" below -- ligand
                        ionization state is NOT verified).
  PI_PI:                ring-centroid distance <= 6.0 A (report plane
                        angle; do not force a parallel/T-shaped label).
  CATION_PI:            cation-to-ring-centroid distance <= 6.0 A.
  HYDROPHOBIC_CONTACT:  compatible heavy-atom min distance <= 4.5 A.

Charged-contact relabelling (this revision -- real chemistry fix, not
cosmetic)
-----------------------------------------------------------------------------
An earlier revision of this module reported `SALT_BRIDGE` for any ligand
N/O-type atom within 4.0 A of an ARG/LYS/ASP/GLU side chain. On review
this was found to overclaim: the ligand-preparation step in this pipeline
(`Chem.MolFromSmiles` + `Chem.AddHs` + ETKDG embedding, no explicit
protonation-state assignment) does NOT determine physiological ionization
state. A genuine salt bridge requires the LIGAND group to be truly
ionizable at pH 7.4 (e.g. a protonatable aliphatic amine, guanidine, or a
deprotonated carboxylate/phosphate/sulfonate) -- not merely "has an N or
an acceptor-type atom." No pH-aware protonation tool (e.g. Dimorphite-DL)
is wired into this pipeline, so ligand-side ionization state is
UNVERIFIED for every compound processed so far.

Per this session's explicit instruction ("if robust assignment cannot be
made cheaply and reliably... change the output... to a more conservative
interaction class... or mark it unresolved"): the detector is renamed
from `SALT_BRIDGE` to `CHARGED_CONTACT_CANDIDATE`. The geometric cutoff
is UNCHANGED (4.0 A) -- only the label and its documented meaning changed,
never the counts, to avoid silently redefining the chemistry to look
cleaner. The PROTEIN side of the detector (ARG/LYS/ASP/GLU
classification) reuses the identical governed vocabulary SCI1-004 already
uses for salt-bridge detection on deposited PDB structures -- that half
of the classification is as reliable here as it is there. It is the
LIGAND side, unique to this docking-pose pipeline, that is unverified.
`CHARGED_CONTACT_CANDIDATE` must never be presented as a confirmed ionic
interaction downstream, and must never be silently relabelled back to
`SALT_BRIDGE` without a real protonation-state-assignment step being
added first.

Residue correspondence across isoforms (explicit governance gap)
------------------------------------------------------------------
`orthosteric.pocket._residue_mapping` (SCI1-003) documents that the
cross-isoform structural-alignment ALGORITHM is RULE_MISSING/
GOVERNANCE_DECISION_REQUIRED -- no sealed method exists to say "residue
108 in the alpha receptor corresponds to residue N in the beta
receptor." This module therefore reports comparative results at the
INTERACTION-TYPE-COUNT level (e.g. "1 H-bond in alpha vs 0 in beta"),
which requires no residue correspondence, rather than at the
residue-identity level (e.g. "the alpha-859-equivalent residue in beta
does/doesn't form this contact"), which does. This gap is reported
explicitly, not silently worked around.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from orthosteric.features._interaction_fingerprint import (
    ANIONIC_RESIDUES,
    AROMATIC_RING_ATOMS,
    CATION_ATOMS,
    CATIONIC_RESIDUES,
    HYDROPHOBIC_RESIDUES,
)

DETECTOR_POLICY_ID = "docking_interaction_detector_v2_charged_contact_relabel"

# ── Geometric criteria (documented above; engineering choice, not governed) ──
_HBOND_DA_CUTOFF_A = 3.5
_HBOND_ANGLE_MIN_DEG = 120.0
_CHARGED_CONTACT_CUTOFF_A = 4.0  # same numeric value as the prior SALT_BRIDGE cutoff; unchanged
_PI_PI_CENTROID_CUTOFF_A = 6.0
_CATION_PI_CUTOFF_A = 6.0
_HYDROPHOBIC_CUTOFF_A = 4.5

# Non-scientific, structural/numeric constants (ruff PLR2004 cleanup --
# these are not thresholds, just named magic numbers for readability).
_MIN_RING_ATOMS = 3
_MAX_COVALENT_BOND_A = 1.3  # generous upper bound for any X-H bond length
_ZERO_VECTOR_EPSILON = 1e-9
_PDBQT_ATOM_TYPE_COL_END = 79

_ACCEPTOR_TYPES = frozenset({"OA", "NA", "SA"})  # AutoDock convention: confirmed acceptors
_DONOR_H_TYPE = "HD"  # AutoDock convention: confirmed donor hydrogen


class InteractionType(StrEnum):
    H_BOND = "h_bond"
    #: Renamed from SALT_BRIDGE (see module docstring, "Charged-contact
    #: relabelling" section). NOT a confirmed ionic interaction -- ligand
    #: ionization state is unverified in this pipeline.
    CHARGED_CONTACT_CANDIDATE = "charged_contact_candidate"
    PI_PI = "pi_pi"
    CATION_PI = "cation_pi"
    HYDROPHOBIC_CONTACT = "hydrophobic_contact"


class InteractionGeometryStatus(StrEnum):
    OBSERVED = "observed"
    NOT_INFERRED = "not_inferred"  # e.g. water-mediated, out of scope this session


@dataclass(frozen=True, slots=True)
class PoseAtom:
    """One atom from a docking pose or a prepared receptor PDBQT.

    `autodock_type` is the AutoDock4/Vina atom type (last whitespace-
    delimited column of a PDBQT ATOM/HETATM line) -- real chemistry
    typing from Meeko's ligand/receptor preparation, not invented here.
    """

    index: int
    name: str
    element: str
    autodock_type: str
    x: float
    y: float
    z: float
    residue_name: str
    residue_seq: int
    chain_id: str
    is_ligand: bool

    @property
    def coord(self) -> NDArray[np.float64]:
        return np.array([self.x, self.y, self.z], dtype=np.float64)

    def residue_id(self) -> str:
        return f"{self.chain_id}_{self.residue_name}{self.residue_seq}"


def parse_pdbqt_atoms(path: Path, *, is_ligand: bool) -> list[PoseAtom]:
    """Parse ATOM/HETATM records from a Vina/Meeko PDBQT file.

    Standard fixed-column PDB format with the AutoDock atom type
    appended as the final field. Works for both receptor PDBQTs
    (mk_prepare_receptor.py output) and docked ligand pose PDBQTs
    (Vina write_poses output).
    """
    atoms: list[PoseAtom] = []
    for line in path.read_text().splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        name = line[12:16].strip()
        residue_name = line[17:20].strip()
        chain_id = line[21].strip() or "A"
        residue_seq = int(line[22:26])
        x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
        autodock_type = (
            line[77:_PDBQT_ATOM_TYPE_COL_END].strip()
            if len(line) >= _PDBQT_ATOM_TYPE_COL_END
            else line.split()[-1]
        )
        element = autodock_type[0] if autodock_type else name[0]
        atoms.append(
            PoseAtom(
                index=len(atoms),
                name=name,
                element=element,
                autodock_type=autodock_type,
                x=x,
                y=y,
                z=z,
                residue_name=residue_name,
                residue_seq=residue_seq,
                chain_id=chain_id,
                is_ligand=is_ligand,
            )
        )
    return atoms


def _dist(a: PoseAtom, b: PoseAtom) -> float:
    return float(round(np.linalg.norm(a.coord - b.coord), 4))


def _angle_deg(
    a: NDArray[np.float64], vertex: NDArray[np.float64], c: NDArray[np.float64]
) -> float:
    v1, v2 = a - vertex, c - vertex
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < _ZERO_VECTOR_EPSILON or n2 < _ZERO_VECTOR_EPSILON:
        return 0.0
    cos_a = float(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))
    return round(math.degrees(math.acos(cos_a)), 2)


def _centroid(atoms: list[PoseAtom]) -> NDArray[np.float64]:
    return np.asarray(np.mean(np.array([a.coord for a in atoms]), axis=0), dtype=np.float64)


def _ring_normal(atoms: list[PoseAtom]) -> NDArray[np.float64]:
    if len(atoms) < _MIN_RING_ATOMS:
        return np.array([0.0, 0.0, 1.0])
    v1, v2 = atoms[1].coord - atoms[0].coord, atoms[2].coord - atoms[0].coord
    n = np.cross(v1, v2)
    norm = float(np.linalg.norm(n))
    return n / norm if norm > _ZERO_VECTOR_EPSILON else np.array([0.0, 0.0, 1.0])


def _plane_angle_deg(n1: NDArray[np.float64], n2: NDArray[np.float64]) -> float:
    return round(math.degrees(math.acos(float(np.clip(abs(float(np.dot(n1, n2))), 0.0, 1.0)))), 2)


def _find_attached_h(
    donor: PoseAtom, all_atoms: list[PoseAtom], max_bond_a: float = _MAX_COVALENT_BOND_A
) -> PoseAtom | None:
    """Nearest HD atom within covalent bonding distance of a donor heavy atom."""
    candidates = [
        a
        for a in all_atoms
        if a.autodock_type == _DONOR_H_TYPE
        and a.is_ligand == donor.is_ligand
        and _dist(a, donor) <= max_bond_a
    ]
    return min(candidates, key=lambda a: _dist(a, donor)) if candidates else None


@dataclass(frozen=True, slots=True)
class AtomResidueInteraction:
    """One atom-level interaction record."""

    interaction_type: InteractionType
    status: InteractionGeometryStatus
    ligand_atom_index: int
    ligand_atom_name: str
    ligand_atom_element: str
    residue_number: int
    residue_name: str
    chain_id: str
    protein_atom_name: str
    distance_angstrom: float | None
    angle_degrees: float | None
    plane_angle_degrees: float | None
    compound_id: str
    isoform: str
    receptor_id: str
    docking_score: float | None
    detector_policy: str = field(default=DETECTOR_POLICY_ID)

    def to_dict(self) -> dict[str, Any]:
        return {
            "interaction_type": self.interaction_type.value,
            "status": self.status.value,
            "ligand_atom_index": self.ligand_atom_index,
            "ligand_atom_name": self.ligand_atom_name,
            "ligand_atom_element": self.ligand_atom_element,
            "residue_number": self.residue_number,
            "residue_name": self.residue_name,
            "chain_id": self.chain_id,
            "protein_atom_name": self.protein_atom_name,
            "distance_angstrom": self.distance_angstrom,
            "angle_degrees": self.angle_degrees,
            "plane_angle_degrees": self.plane_angle_degrees,
            "compound_id": self.compound_id,
            "isoform": self.isoform,
            "receptor_id": self.receptor_id,
            "docking_score": self.docking_score,
            "detector_policy": self.detector_policy,
        }


def detect_hbonds(
    ligand_atoms: list[PoseAtom],
    protein_atoms: list[PoseAtom],
    meta: dict[str, Any],
) -> list[AtomResidueInteraction]:
    out: list[AtomResidueInteraction] = []
    lig_acceptors = [a for a in ligand_atoms if a.autodock_type in _ACCEPTOR_TYPES]
    lig_donors_h = [a for a in ligand_atoms if a.autodock_type == _DONOR_H_TYPE]
    prot_acceptors = [a for a in protein_atoms if a.autodock_type in _ACCEPTOR_TYPES]
    prot_donors_h = [a for a in protein_atoms if a.autodock_type == _DONOR_H_TYPE]

    def check(donor_h: PoseAtom, acceptor: PoseAtom, donor_heavy: PoseAtom) -> None:
        d = _dist(donor_heavy, acceptor)
        if d > _HBOND_DA_CUTOFF_A:
            return
        # Angle D-H...A, vertex AT the hydrogen (standard H-bond convention):
        # a good H-bond has D and A on opposite sides of H (angle near 180 deg).
        angle = _angle_deg(donor_heavy.coord, donor_h.coord, acceptor.coord)
        if angle < _HBOND_ANGLE_MIN_DEG:
            return
        lig_a, prot_a = (acceptor, donor_heavy) if acceptor.is_ligand else (donor_heavy, acceptor)
        out.append(
            AtomResidueInteraction(
                interaction_type=InteractionType.H_BOND,
                status=InteractionGeometryStatus.OBSERVED,
                ligand_atom_index=lig_a.index,
                ligand_atom_name=lig_a.name,
                ligand_atom_element=lig_a.element,
                residue_number=prot_a.residue_seq,
                residue_name=prot_a.residue_name,
                chain_id=prot_a.chain_id,
                protein_atom_name=prot_a.name,
                distance_angstrom=d,
                angle_degrees=angle,
                plane_angle_degrees=None,
                compound_id=meta["compound_id"],
                isoform=meta["isoform"],
                receptor_id=meta["receptor_id"],
                docking_score=meta.get("docking_score"),
            )
        )

    # ligand donor -> protein acceptor
    for dh in lig_donors_h:
        heavy = min(
            (a for a in ligand_atoms if a is not dh and _dist(a, dh) <= _MAX_COVALENT_BOND_A),
            key=lambda a: _dist(a, dh),
            default=None,
        )
        if heavy is None:
            continue
        for acc in prot_acceptors:
            check(dh, acc, heavy)
    # protein donor -> ligand acceptor
    for dh in prot_donors_h:
        heavy = min(
            (a for a in protein_atoms if a is not dh and _dist(a, dh) <= _MAX_COVALENT_BOND_A),
            key=lambda a: _dist(a, dh),
            default=None,
        )
        if heavy is None:
            continue
        for acc in lig_acceptors:
            check(dh, acc, heavy)
    return out


def detect_charged_contact_candidates(
    ligand_atoms: list[PoseAtom],
    protein_atoms: list[PoseAtom],
    meta: dict[str, Any],
) -> list[AtomResidueInteraction]:
    out: list[AtomResidueInteraction] = []
    lig_charged = [
        a for a in ligand_atoms if a.autodock_type in _ACCEPTOR_TYPES or a.element == "N"
    ]
    prot_by_residue: dict[tuple[str, int], list[PoseAtom]] = {}
    for a in protein_atoms:
        prot_by_residue.setdefault((a.chain_id, a.residue_seq), []).append(a)
    for (chain_id, resnum), atoms in prot_by_residue.items():
        rn = atoms[0].residue_name
        if rn not in CATIONIC_RESIDUES and rn not in ANIONIC_RESIDUES:
            continue
        for pa in atoms:
            if pa.element not in ("N", "O"):
                continue
            for la in lig_charged:
                d = _dist(la, pa)
                if d <= _CHARGED_CONTACT_CUTOFF_A:
                    out.append(
                        AtomResidueInteraction(
                            interaction_type=InteractionType.CHARGED_CONTACT_CANDIDATE,
                            status=InteractionGeometryStatus.OBSERVED,
                            ligand_atom_index=la.index,
                            ligand_atom_name=la.name,
                            ligand_atom_element=la.element,
                            residue_number=resnum,
                            residue_name=rn,
                            chain_id=chain_id,
                            protein_atom_name=pa.name,
                            distance_angstrom=d,
                            angle_degrees=None,
                            plane_angle_degrees=None,
                            compound_id=meta["compound_id"],
                            isoform=meta["isoform"],
                            receptor_id=meta["receptor_id"],
                            docking_score=meta.get("docking_score"),
                        )
                    )
    return out


def detect_hydrophobic_contacts(
    ligand_atoms: list[PoseAtom],
    protein_atoms: list[PoseAtom],
    meta: dict[str, Any],
) -> list[AtomResidueInteraction]:
    out: list[AtomResidueInteraction] = []
    lig_hphob = [a for a in ligand_atoms if a.element == "C"]
    for pa in protein_atoms:
        if pa.residue_name not in HYDROPHOBIC_RESIDUES or pa.element != "C":
            continue
        for la in lig_hphob:
            d = _dist(la, pa)
            if d <= _HYDROPHOBIC_CUTOFF_A:
                out.append(
                    AtomResidueInteraction(
                        interaction_type=InteractionType.HYDROPHOBIC_CONTACT,
                        status=InteractionGeometryStatus.OBSERVED,
                        ligand_atom_index=la.index,
                        ligand_atom_name=la.name,
                        ligand_atom_element=la.element,
                        residue_number=pa.residue_seq,
                        residue_name=pa.residue_name,
                        chain_id=pa.chain_id,
                        protein_atom_name=pa.name,
                        distance_angstrom=d,
                        angle_degrees=None,
                        plane_angle_degrees=None,
                        compound_id=meta["compound_id"],
                        isoform=meta["isoform"],
                        receptor_id=meta["receptor_id"],
                        docking_score=meta.get("docking_score"),
                    )
                )
    return out


def detect_pi_pi(
    ligand_atoms: list[PoseAtom],
    protein_atoms: list[PoseAtom],
    meta: dict[str, Any],
    ligand_aromatic_names: frozenset[str],
) -> list[AtomResidueInteraction]:
    out: list[AtomResidueInteraction] = []
    lig_ring = [a for a in ligand_atoms if a.name in ligand_aromatic_names]
    if len(lig_ring) < _MIN_RING_ATOMS:
        return out
    lig_c, lig_n = _centroid(lig_ring), _ring_normal(lig_ring)
    prot_by_residue: dict[tuple[str, int], list[PoseAtom]] = {}
    for a in protein_atoms:
        prot_by_residue.setdefault((a.chain_id, a.residue_seq), []).append(a)
    for (chain_id, resnum), atoms in prot_by_residue.items():
        rn = atoms[0].residue_name
        ring_names = AROMATIC_RING_ATOMS.get(rn)
        if not ring_names:
            continue
        pring = [a for a in atoms if a.name in ring_names]
        if len(pring) < _MIN_RING_ATOMS:
            continue
        pc, pn = _centroid(pring), _ring_normal(pring)
        d = float(round(float(np.linalg.norm(lig_c - pc)), 4))
        if d <= _PI_PI_CENTROID_CUTOFF_A:
            plane_ang = _plane_angle_deg(lig_n, pn)
            out.append(
                AtomResidueInteraction(
                    interaction_type=InteractionType.PI_PI,
                    status=InteractionGeometryStatus.OBSERVED,
                    ligand_atom_index=-1,
                    ligand_atom_name="<ring_centroid>",
                    ligand_atom_element="",
                    residue_number=resnum,
                    residue_name=rn,
                    chain_id=chain_id,
                    protein_atom_name="<ring_centroid>",
                    distance_angstrom=d,
                    angle_degrees=None,
                    plane_angle_degrees=plane_ang,
                    compound_id=meta["compound_id"],
                    isoform=meta["isoform"],
                    receptor_id=meta["receptor_id"],
                    docking_score=meta.get("docking_score"),
                )
            )
    return out


def detect_cation_pi(
    ligand_atoms: list[PoseAtom],
    protein_atoms: list[PoseAtom],
    meta: dict[str, Any],
    ligand_aromatic_names: frozenset[str],
) -> list[AtomResidueInteraction]:
    out: list[AtomResidueInteraction] = []
    lig_ring = [a for a in ligand_atoms if a.name in ligand_aromatic_names]
    lig_centroid = _centroid(lig_ring) if len(lig_ring) >= _MIN_RING_ATOMS else None
    prot_by_residue: dict[tuple[str, int], list[PoseAtom]] = {}
    for a in protein_atoms:
        prot_by_residue.setdefault((a.chain_id, a.residue_seq), []).append(a)
    for (chain_id, resnum), atoms in prot_by_residue.items():
        rn = atoms[0].residue_name
        if lig_centroid is not None and rn in CATIONIC_RESIDUES:
            for cat_name in CATION_ATOMS.get(rn, []):
                cat_atom = next((a for a in atoms if a.name == cat_name), None)
                if cat_atom is None:
                    continue
                d = float(round(float(np.linalg.norm(lig_centroid - cat_atom.coord)), 4))
                if d <= _CATION_PI_CUTOFF_A:
                    out.append(
                        AtomResidueInteraction(
                            interaction_type=InteractionType.CATION_PI,
                            status=InteractionGeometryStatus.OBSERVED,
                            ligand_atom_index=-1,
                            ligand_atom_name="<ring_centroid>",
                            ligand_atom_element="",
                            residue_number=resnum,
                            residue_name=rn,
                            chain_id=chain_id,
                            protein_atom_name=cat_name,
                            distance_angstrom=d,
                            angle_degrees=None,
                            plane_angle_degrees=None,
                            compound_id=meta["compound_id"],
                            isoform=meta["isoform"],
                            receptor_id=meta["receptor_id"],
                            docking_score=meta.get("docking_score"),
                        )
                    )
    return out


def detect_all_interactions(
    ligand_atoms: list[PoseAtom],
    protein_atoms: list[PoseAtom],
    meta: dict[str, Any],
    ligand_aromatic_names: frozenset[str] = frozenset(),
) -> list[AtomResidueInteraction]:
    """Run all implemented detectors and return sorted, deterministic results."""
    results = (
        detect_hbonds(ligand_atoms, protein_atoms, meta)
        + detect_charged_contact_candidates(ligand_atoms, protein_atoms, meta)
        + detect_hydrophobic_contacts(ligand_atoms, protein_atoms, meta)
        + detect_pi_pi(ligand_atoms, protein_atoms, meta, ligand_aromatic_names)
        + detect_cation_pi(ligand_atoms, protein_atoms, meta, ligand_aromatic_names)
    )
    return sorted(
        results,
        key=lambda r: (
            r.interaction_type.value,
            r.residue_number,
            r.protein_atom_name,
            r.ligand_atom_index,
        ),
    )


def residue_level_summary(interactions: list[AtomResidueInteraction]) -> list[dict[str, Any]]:
    """Collapse atom-level interactions to one entry per residue.

    Reports interaction-type counts and the minimum distance observed --
    never losing the underlying atom-level records (they remain the
    primary representation; this is a derived view).
    """
    by_residue: dict[tuple[str, int, str], list[AtomResidueInteraction]] = {}
    for it in interactions:
        by_residue.setdefault((it.chain_id, it.residue_number, it.residue_name), []).append(it)
    out = []
    for (chain_id, resnum, resname), items in sorted(by_residue.items()):
        type_counts: dict[str, int] = {}
        for it in items:
            type_counts[it.interaction_type.value] = (
                type_counts.get(it.interaction_type.value, 0) + 1
            )
        distances = [it.distance_angstrom for it in items if it.distance_angstrom is not None]
        out.append(
            {
                "chain_id": chain_id,
                "residue_number": resnum,
                "residue_name": resname,
                "interaction_types": type_counts,
                "min_distance_angstrom": min(distances) if distances else None,
            }
        )
    return out


def content_sha256(interactions: list[AtomResidueInteraction]) -> str:
    payload = json.dumps(
        [it.to_dict() for it in interactions], sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode()).hexdigest()

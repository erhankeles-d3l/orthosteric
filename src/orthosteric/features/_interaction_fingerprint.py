"""Protein-ligand interaction fingerprints (PLIFs) — SCI1-004.

Authority: ADR-0010; SCI1-004 (Milestone 5). Constitution §4.2, §4.6, §2.1.

Scientific mandate: measure structural interaction evidence for comparative
learning (compound + alpha + beta + gamma + delta -> joint representation).
Does NOT determine selectivity, productivity, or favourability.

Scientific rule classification
  RULE_AVAILABLE:  H-bond chemistry (D/A identity from N/O elements); aromatic
    ring atoms per residue type; hydrophobic atom identity; halogen elements;
    metal elements; water identification.
  RULE_MISSING:    All classification thresholds (D...A distance, angle cutoffs,
    pi-pi centroid distance, salt-bridge cutoff, etc.) — not governed by any
    Constitution section, ADR, or GDR.

Implementation candidate-search radii (NOT scientific thresholds; wide enough
to capture any plausible candidate):
  H-bond: 3.9 A  Salt: 6.0 A  pi-pi: 8.0 A  Cation-pi: 7.0 A
  Hydrophobic: 5.5 A  Halogen: 4.5 A  Metal: 3.5 A  Water: 4.0 A
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray

from orthosteric.pocket._pocket_definition import PocketResidueSet
from orthosteric.pocket._residue_mapping import ResidueCorrespondenceTable
from orthosteric.pocket._structure_record import (
    LigandRecord,
    StructureProvenance,
    StructureRecord,
    StructureSource,
)

# Governed residue/atom-chemistry classification vocabulary (RULE_AVAILABLE,
# standard biochemistry), exported below alongside the primary API so
# other modules working with the same chemistry (e.g.
# features._docking_interaction_detector, which operates on docking
# poses rather than deposited PDB structures) reuse this single source
# of truth instead of maintaining a second, potentially divergent copy:
# ANIONIC_RESIDUES, AROMATIC_RING_ATOMS, CATION_ATOMS, CATIONIC_RESIDUES,
# HYDROPHOBIC_RESIDUES.
__all__ = [
    "ANIONIC_RESIDUES",
    "AROMATIC_RING_ATOMS",
    "CATIONIC_RESIDUES",
    "CATION_ATOMS",
    "FINGERPRINT_ALGORITHM_VERSION",
    "HYDROPHOBIC_RESIDUES",
    "ComparativeFingerprint",
    "FingerprintConfig",
    "InteractionEvidence",
    "InteractionFingerprint",
    "InteractionStatus",
    "InteractionType",
    "build_comparative_fingerprint",
    "compute_interaction_fingerprint",
]

FINGERPRINT_ALGORITHM_VERSION = "interaction_fp_v1_sci1004"

# Implementation search radii (efficiency, not science)
_HBOND_SEARCH_A: float = 3.9
_SALT_SEARCH_A: float = 6.0
_PI_SEARCH_A: float = 8.0
_CATPI_SEARCH_A: float = 7.0
_HPHOB_SEARCH_A: float = 5.5
_HALOGEN_SEARCH_A: float = 4.5
_METAL_SEARCH_A: float = 3.5
_WATER_SEARCH_A: float = 4.0

_HB_NOTE = "RULE_MISSING: H-bond thresholds (D...A distance, D-H...A angle) not governed."
_SB_NOTE = "RULE_MISSING: salt-bridge distance cutoff not governed."
_PP_NOTE = "RULE_MISSING: pi-pi thresholds (centroid dist, plane angle) not governed."
_CP_NOTE = "RULE_MISSING: cation-pi distance cutoff not governed."
_HP_NOTE = "RULE_MISSING: hydrophobic contact cutoff not governed."
_WM_NOTE = "RULE_MISSING: water-mediated H-bond thresholds not governed."
_HAL_NOTE = "RULE_MISSING: halogen-bond distance and angle cutoffs not governed."
_MET_NOTE = "RULE_MISSING: metal coordination distance/geometry thresholds not governed."

# Aromatic ring atom names per residue (RULE_AVAILABLE: standard biochemistry)
_AROMATIC_RING_ATOMS: dict[str, list[str]] = {
    "PHE": ["CG", "CD1", "CD2", "CE1", "CE2", "CZ"],
    "TYR": ["CG", "CD1", "CD2", "CE1", "CE2", "CZ"],
    "TRP": ["CG", "CD1", "CD2", "NE1", "CE2", "CE3", "CZ2", "CZ3", "CH2"],
    "HIS": ["CG", "ND1", "CD2", "CE1", "NE2"],
}
_HYDROPHOBIC_RESIDUES: frozenset[str] = frozenset(
    {"ALA", "VAL", "LEU", "ILE", "MET", "PHE", "TRP", "PRO", "TYR", "CYS"}
)
_CATIONIC_RESIDUES: frozenset[str] = frozenset({"ARG", "LYS", "HIS"})
_ANIONIC_RESIDUES: frozenset[str] = frozenset({"ASP", "GLU"})
_METAL_ELEMENTS: frozenset[str] = frozenset(
    {"MG", "ZN", "CA", "MN", "FE", "CU", "NI", "CO", "NA", "K"}
)
_HALOGEN_ELEMENTS: frozenset[str] = frozenset({"CL", "BR", "I"})
_HBOND_ELEMENTS: frozenset[str] = frozenset({"N", "O"})
_CATION_ATOMS: dict[str, list[str]] = {
    "ARG": ["NH1", "NH2", "NE"],
    "LYS": ["NZ"],
    "HIS": ["ND1", "NE2"],
}

# Public aliases for the classification vocabulary above (see __all__ note).
AROMATIC_RING_ATOMS = _AROMATIC_RING_ATOMS
ANIONIC_RESIDUES = _ANIONIC_RESIDUES
CATIONIC_RESIDUES = _CATIONIC_RESIDUES
CATION_ATOMS = _CATION_ATOMS
HYDROPHOBIC_RESIDUES = _HYDROPHOBIC_RESIDUES


class InteractionType(StrEnum):
    """The eight interaction classes mandated by SCI1-004."""

    HYDROGEN_BOND = "hydrogen_bond"
    SALT_BRIDGE = "salt_bridge"
    PI_PI = "pi_pi"
    CATION_PI = "cation_pi"
    HYDROPHOBIC = "hydrophobic"
    WATER_MEDIATED = "water_mediated"
    HALOGEN_BOND = "halogen_bond"
    METAL_COORDINATION = "metal_coordination"


class InteractionStatus(StrEnum):
    """Evidence status — must remain distinct, never collapsed (instruction §21).

    OBSERVED: geometry meets governed threshold.
    ABSENT: geometry present but does not meet threshold.
    UNAVAILABLE: required atoms absent from structure.
    RULE_MISSING: geometry available; threshold not governed; cannot classify.
    NOT_APPLICABLE: wrong chemistry for this interaction at this site.
    """

    OBSERVED = "observed"
    ABSENT = "absent"
    UNAVAILABLE = "unavailable"
    RULE_MISSING = "rule_missing"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class FingerprintConfig:
    """Classification thresholds — ALL default to None (RULE_MISSING).

    No field here is governed by any Constitution section, ADR, or GDR.
    Each will remain None until a Governance Decision Record seals its value.
    """

    hbond_da_cutoff_angstrom: float | None = None
    hbond_angle_min_degrees: float | None = None
    salt_bridge_cutoff_angstrom: float | None = None
    pi_pi_centroid_cutoff_angstrom: float | None = None
    pi_pi_plane_angle_max_degrees: float | None = None
    cation_pi_cutoff_angstrom: float | None = None
    hydrophobic_cutoff_angstrom: float | None = None
    halogen_distance_cutoff_angstrom: float | None = None
    halogen_angle_min_degrees: float | None = None
    metal_distance_cutoff_angstrom: float | None = None
    water_arm_cutoff_angstrom: float | None = None

    def to_canonical_dict(self) -> dict[str, float | None]:
        return {
            "cation_pi_cutoff_angstrom": self.cation_pi_cutoff_angstrom,
            "hbond_angle_min_degrees": self.hbond_angle_min_degrees,
            "hbond_da_cutoff_angstrom": self.hbond_da_cutoff_angstrom,
            "hydrophobic_cutoff_angstrom": self.hydrophobic_cutoff_angstrom,
            "halogen_angle_min_degrees": self.halogen_angle_min_degrees,
            "halogen_distance_cutoff_angstrom": self.halogen_distance_cutoff_angstrom,
            "metal_distance_cutoff_angstrom": self.metal_distance_cutoff_angstrom,
            "pi_pi_centroid_cutoff_angstrom": self.pi_pi_centroid_cutoff_angstrom,
            "pi_pi_plane_angle_max_degrees": self.pi_pi_plane_angle_max_degrees,
            "salt_bridge_cutoff_angstrom": self.salt_bridge_cutoff_angstrom,
            "water_arm_cutoff_angstrom": self.water_arm_cutoff_angstrom,
        }


@dataclass(frozen=True, slots=True)
class InteractionEvidence:
    """Raw geometric evidence for one potential protein-ligand interaction.

    Preserves both continuous geometry AND categorical status.
    Never discards distances/angles because downstream ML may be binary
    -- the interpretation layer needs the raw measurements.

    Traceability: structure_record_id -> StructureRecord -> StructureProvenance
    -> PDB or AlphaFold source. AlphaFold fingerprints always carry
    structure_source = ALPHAFOLD_GOVERNED_FALLBACK, never relabelled.
    """

    interaction_type: InteractionType
    status: InteractionStatus
    ligand_atom_name: str
    ligand_residue_name: str
    protein_residue_id: str
    protein_residue_name: str
    protein_atom_name: str
    canonical_position: int | None
    primary_distance_angstrom: float | None
    secondary_distance_angstrom: float | None
    angle_degrees: float | None
    dihedral_degrees: float | None
    water_residue_id: str | None
    metal_identity: str | None
    structure_record_id: str
    structure_source: str
    algorithm_version: str
    governance_note: str

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "algorithm_version": self.algorithm_version,
            "angle_degrees": self.angle_degrees,
            "canonical_position": self.canonical_position,
            "dihedral_degrees": self.dihedral_degrees,
            "governance_note": self.governance_note,
            "interaction_type": self.interaction_type.value,
            "ligand_atom_name": self.ligand_atom_name,
            "ligand_residue_name": self.ligand_residue_name,
            "metal_identity": self.metal_identity,
            "primary_distance_angstrom": self.primary_distance_angstrom,
            "protein_atom_name": self.protein_atom_name,
            "protein_residue_id": self.protein_residue_id,
            "protein_residue_name": self.protein_residue_name,
            "secondary_distance_angstrom": self.secondary_distance_angstrom,
            "status": self.status.value,
            "structure_record_id": self.structure_record_id,
            "structure_source": self.structure_source,
            "water_residue_id": self.water_residue_id,
        }


@dataclass(frozen=True, slots=True)
class InteractionFingerprint:
    """All interaction evidence for one protein-ligand complex (one isoform)."""

    structure_record_id: str
    isoform: str
    ligand_residue_name: str
    ligand_inchikey: str | None
    provenance: StructureProvenance
    algorithm_version: str
    config: FingerprintConfig
    correspondence_table_version: str | None
    evidence: tuple[InteractionEvidence, ...]
    n_per_type: tuple[tuple[str, int], ...]

    def get_by_type(self, t: InteractionType) -> tuple[InteractionEvidence, ...]:
        return tuple(e for e in self.evidence if e.interaction_type == t)

    def get_observed(self) -> tuple[InteractionEvidence, ...]:
        return tuple(e for e in self.evidence if e.status == InteractionStatus.OBSERVED)

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "algorithm_version": self.algorithm_version,
                "config": self.config.to_canonical_dict(),
                "correspondence_table_version": self.correspondence_table_version,
                "evidence": [e.to_canonical_dict() for e in self.evidence],
                "isoform": self.isoform,
                "ligand_inchikey": self.ligand_inchikey,
                "ligand_residue_name": self.ligand_residue_name,
                "provenance": self.provenance.to_canonical_dict(),
                "structure_record_id": self.structure_record_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ComparativeFingerprint:
    """Interaction fingerprints aligned by canonical position across isoforms.

    Enables the comparative architecture: compound + alpha + beta + gamma + delta
    -> joint structural representation. At each canonical position, one can ask
    "what interaction evidence does this compound form with the 859-equivalent
    residue in each isoform?" without knowing isoform-specific PDB numbering.
    """

    ligand_inchikey: str | None
    isoform_fingerprints: tuple[tuple[str, InteractionFingerprint], ...]
    canonical_positions_covered: frozenset[int]
    algorithm_version: str

    def get_isoform(self, isoform: str) -> InteractionFingerprint | None:
        for iso, fp in self.isoform_fingerprints:
            if iso == isoform:
                return fp
        return None

    def canonical_comparison(self, canonical_pos: int) -> dict[str, list[InteractionEvidence]]:
        """Evidence at one canonical position, per isoform — the comparative view."""
        return {
            iso: [e for e in fp.evidence if e.canonical_position == canonical_pos]
            for iso, fp in self.isoform_fingerprints
        }

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "algorithm_version": self.algorithm_version,
                "canonical_positions_covered": sorted(self.canonical_positions_covered),
                "isoform_fingerprints": [
                    [iso, fp.content_sha256()] for iso, fp in self.isoform_fingerprints
                ],
                "ligand_inchikey": self.ligand_inchikey,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── Geometry helpers ─────────────────────────────────────────────────────────


def _vec(a: Any) -> NDArray[np.float64]:
    return np.array(a.get_vector().get_array(), dtype=np.float64)


def _dist(a: Any, b: Any) -> float:
    return float(round(np.linalg.norm(_vec(a) - _vec(b)), 4))


def _angle_at_b(a: Any, b: Any, c: Any) -> float:
    """Angle at b (a-b-c) in degrees."""
    v1 = _vec(a) - _vec(b)
    v2 = _vec(c) - _vec(b)
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 < 1e-9 or n2 < 1e-9:  # noqa: PLR2004
        return 0.0
    return round(
        float(np.degrees(np.arccos(float(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))))), 2
    )


def _centroid(atoms: list[Any]) -> NDArray[np.float64]:
    return np.array(np.mean(np.array([_vec(a) for a in atoms], dtype=np.float64), axis=0))


def _ring_normal(atoms: list[Any]) -> NDArray[np.float64]:
    if len(atoms) < 3:  # noqa: PLR2004
        return np.array([0.0, 0.0, 1.0])
    v1 = _vec(atoms[1]) - _vec(atoms[0])
    v2 = _vec(atoms[2]) - _vec(atoms[0])
    n = np.cross(v1, v2)
    norm = float(np.linalg.norm(n))
    return n / norm if norm > 1e-9 else np.array([0.0, 0.0, 1.0])  # noqa: PLR2004


def _plane_angle(n1: NDArray[np.float64], n2: NDArray[np.float64]) -> float:
    return round(
        float(np.degrees(np.arccos(float(np.clip(abs(float(np.dot(n1, n2))), 0.0, 1.0))))), 2
    )


def _atom_element(atom: Any) -> str:
    el = (atom.element or "").strip().upper()
    return el if el else (atom.get_name().strip().upper()[:1] if atom.get_name().strip() else "")


def _is_hbond_element(atom: Any) -> bool:
    return _atom_element(atom) in _HBOND_ELEMENTS


def _is_hydrophobic_atom(atom: Any, residue_name: str) -> bool:
    el = _atom_element(atom)
    if el == "C" and residue_name in _HYDROPHOBIC_RESIDUES:
        return True
    return el == "S" and residue_name in {"MET", "CYS"}


def _classify_by_dist(
    dist: float,
    cutoff: float | None,
    rule_note: str,
    angle: float | None = None,
    angle_min: float | None = None,
) -> tuple[InteractionStatus, str]:
    if cutoff is None:
        return InteractionStatus.RULE_MISSING, rule_note
    if dist <= cutoff:
        if angle_min is not None and angle is not None and angle < angle_min:
            return InteractionStatus.ABSENT, ""
        return InteractionStatus.OBSERVED, ""
    return InteractionStatus.ABSENT, ""


def _canon_pos(prot_res_id: str, table: ResidueCorrespondenceTable | None) -> int | None:
    if table is None:
        return None
    a = table.get_canonical_position(prot_res_id)
    return a.canonical_position if a is not None else None


def _ev(
    *,
    itype: InteractionType,
    status: InteractionStatus,
    lig_a: str,
    lig_r: str,
    prot_id: str,
    prot_r: str,
    prot_a: str,
    canon: int | None,
    d1: float | None,
    d2: float | None = None,
    ang: float | None = None,
    dih: float | None = None,
    water: str | None = None,
    metal: str | None = None,
    rec_id: str,
    src: str,
    note: str,
) -> InteractionEvidence:
    return InteractionEvidence(
        interaction_type=itype,
        status=status,
        ligand_atom_name=lig_a,
        ligand_residue_name=lig_r,
        protein_residue_id=prot_id,
        protein_residue_name=prot_r,
        protein_atom_name=prot_a,
        canonical_position=canon,
        primary_distance_angstrom=d1,
        secondary_distance_angstrom=d2,
        angle_degrees=ang,
        dihedral_degrees=dih,
        water_residue_id=water,
        metal_identity=metal,
        structure_record_id=rec_id,
        structure_source=src,
        algorithm_version=FINGERPRINT_ALGORITHM_VERSION,
        governance_note=note,
    )


# ── Ligand aromatic atom detection ───────────────────────────────────────────


def _ligand_aromatic_atom_names(lig_res: Any, smiles: str | None) -> frozenset[str]:
    """Return atom names of aromatic atoms in the ligand using RDKit if available.

    Returns empty set when SMILES unavailable — status becomes UNAVAILABLE upstream.
    """
    if not smiles:
        return frozenset()
    try:
        from rdkit import Chem  # noqa: PLC0415

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:  # mypy: rdkit stubs unavailable; mol CAN be None
            return frozenset()
        arom_idx = frozenset(a.GetIdx() for a in mol.GetAtoms() if a.GetIsAromatic())
        if not arom_idx:
            return frozenset()
        heavy = sorted(
            (a for a in lig_res.get_atoms() if _atom_element(a) not in ("H", "D")),
            key=lambda a: a.get_name(),
        )
        if len(heavy) != mol.GetNumHeavyAtoms():
            return frozenset()
        return frozenset(heavy[i].get_name().strip() for i in arom_idx if i < len(heavy))
    except Exception:
        return frozenset()


# ── Per-interaction-type detection ───────────────────────────────────────────

_PocketList = list[tuple[str, str, Any]]  # (residue_id, residue_name, bio_res)


def _detect_hbonds(
    lig_atoms: list[Any],
    lig_rn: str,
    pocket: _PocketList,
    cfg: FingerprintConfig,
    rid: str,
    src: str,
    tbl: ResidueCorrespondenceTable | None,
    isoform: str,
) -> list[InteractionEvidence]:
    ev: list[InteractionEvidence] = []
    lig_hb = [a for a in lig_atoms if _is_hbond_element(a)]
    for prot_id, prot_rn, prot_res in pocket:
        for pa in sorted(prot_res.get_atoms(), key=lambda a: a.get_name()):
            if not _is_hbond_element(pa):
                continue
            for la in sorted(lig_hb, key=lambda a: a.get_name()):
                d = _dist(la, pa)
                if d > _HBOND_SEARCH_A:
                    continue
                st, note = _classify_by_dist(d, cfg.hbond_da_cutoff_angstrom, _HB_NOTE)
                ev.append(
                    _ev(
                        itype=InteractionType.HYDROGEN_BOND,
                        status=st,
                        lig_a=la.get_name().strip(),
                        lig_r=lig_rn,
                        prot_id=prot_id,
                        prot_r=prot_rn,
                        prot_a=pa.get_name().strip(),
                        canon=_canon_pos(prot_id, tbl),
                        d1=round(d, 4),
                        rec_id=rid,
                        src=src,
                        note=note,
                    )
                )
    return ev


def _detect_salt_bridges(
    lig_atoms: list[Any],
    lig_rn: str,
    pocket: _PocketList,
    cfg: FingerprintConfig,
    rid: str,
    src: str,
    tbl: ResidueCorrespondenceTable | None,
    isoform: str,
) -> list[InteractionEvidence]:
    ev: list[InteractionEvidence] = []
    lig_charged = [a for a in lig_atoms if _is_hbond_element(a)]
    for prot_id, prot_rn, prot_res in pocket:
        if prot_rn not in _CATIONIC_RESIDUES and prot_rn not in _ANIONIC_RESIDUES:
            continue
        for pa in sorted(prot_res.get_atoms(), key=lambda a: a.get_name()):
            if not _is_hbond_element(pa):
                continue
            for la in sorted(lig_charged, key=lambda a: a.get_name()):
                d = _dist(la, pa)
                if d > _SALT_SEARCH_A:
                    continue
                st, note = _classify_by_dist(d, cfg.salt_bridge_cutoff_angstrom, _SB_NOTE)
                ev.append(
                    _ev(
                        itype=InteractionType.SALT_BRIDGE,
                        status=st,
                        lig_a=la.get_name().strip(),
                        lig_r=lig_rn,
                        prot_id=prot_id,
                        prot_r=prot_rn,
                        prot_a=pa.get_name().strip(),
                        canon=_canon_pos(prot_id, tbl),
                        d1=round(d, 4),
                        rec_id=rid,
                        src=src,
                        note=note,
                    )
                )
    return ev


def _detect_pi_pi(
    lig_atoms: list[Any],
    lig_res: Any,
    lig_rn: str,
    smiles: str | None,
    pocket: _PocketList,
    cfg: FingerprintConfig,
    rid: str,
    src: str,
    tbl: ResidueCorrespondenceTable | None,
    isoform: str,
) -> list[InteractionEvidence]:
    ev: list[InteractionEvidence] = []
    arom_names = _ligand_aromatic_atom_names(lig_res, smiles)
    if not arom_names:
        return ev
    la_arom = [a for a in lig_atoms if a.get_name().strip() in arom_names]
    if len(la_arom) < 3:  # noqa: PLR2004
        return ev
    lig_c = _centroid(la_arom)
    lig_n = _ring_normal(la_arom)
    for prot_id, prot_rn, prot_res in pocket:
        rnames = _AROMATIC_RING_ATOMS.get(prot_rn, [])
        if not rnames:
            continue
        pring = [prot_res[n] for n in rnames if n in prot_res]
        if len(pring) < 3:  # noqa: PLR2004
            continue
        pc = _centroid(pring)
        pn = _ring_normal(pring)
        d = float(round(float(np.linalg.norm(lig_c - pc)), 4))
        if d > _PI_SEARCH_A:
            continue
        plane_ang = _plane_angle(lig_n, pn)
        st, note = _classify_by_dist(d, cfg.pi_pi_centroid_cutoff_angstrom, _PP_NOTE)
        ev.append(
            _ev(
                itype=InteractionType.PI_PI,
                status=st,
                lig_a="<ring_centroid>",
                lig_r=lig_rn,
                prot_id=prot_id,
                prot_r=prot_rn,
                prot_a="<ring_centroid>",
                canon=_canon_pos(prot_id, tbl),
                d1=d,
                dih=plane_ang,
                rec_id=rid,
                src=src,
                note=note,
            )
        )
    return ev


def _detect_cation_pi(
    lig_atoms: list[Any],
    lig_res: Any,
    lig_rn: str,
    smiles: str | None,
    pocket: _PocketList,
    cfg: FingerprintConfig,
    rid: str,
    src: str,
    tbl: ResidueCorrespondenceTable | None,
    isoform: str,
) -> list[InteractionEvidence]:
    ev: list[InteractionEvidence] = []
    arom_names = _ligand_aromatic_atom_names(lig_res, smiles)
    la_arom = [a for a in lig_atoms if a.get_name().strip() in arom_names]
    lig_centroid = _centroid(la_arom) if len(la_arom) >= 3 else None  # noqa: PLR2004
    for prot_id, prot_rn, prot_res in pocket:
        # Protein aromatic ring vs ligand N atoms
        rnames = _AROMATIC_RING_ATOMS.get(prot_rn, [])
        if rnames:
            pring = [prot_res[n] for n in rnames if n in prot_res]
            if len(pring) >= 3:  # noqa: PLR2004
                pc = _centroid(pring)
                for la in sorted(lig_atoms, key=lambda a: a.get_name()):
                    if _atom_element(la) != "N":
                        continue
                    d = float(round(float(np.linalg.norm(pc - _vec(la))), 4))
                    if d > _CATPI_SEARCH_A:
                        continue
                    st, note = _classify_by_dist(d, cfg.cation_pi_cutoff_angstrom, _CP_NOTE)
                    ev.append(
                        _ev(
                            itype=InteractionType.CATION_PI,
                            status=st,
                            lig_a=la.get_name().strip(),
                            lig_r=lig_rn,
                            prot_id=prot_id,
                            prot_r=prot_rn,
                            prot_a="<ring_centroid>",
                            canon=_canon_pos(prot_id, tbl),
                            d1=d,
                            rec_id=rid,
                            src=src,
                            note=note,
                        )
                    )
        # Ligand aromatic ring vs protein cationic atoms
        if lig_centroid is not None and prot_rn in _CATIONIC_RESIDUES:
            for cat_name in _CATION_ATOMS.get(prot_rn, []):
                if cat_name not in prot_res:
                    continue
                cat_a = prot_res[cat_name]
                d = float(round(float(np.linalg.norm(lig_centroid - _vec(cat_a))), 4))
                if d > _CATPI_SEARCH_A:
                    continue
                st, note = _classify_by_dist(d, cfg.cation_pi_cutoff_angstrom, _CP_NOTE)
                ev.append(
                    _ev(
                        itype=InteractionType.CATION_PI,
                        status=st,
                        lig_a="<ring_centroid>",
                        lig_r=lig_rn,
                        prot_id=prot_id,
                        prot_r=prot_rn,
                        prot_a=cat_name,
                        canon=_canon_pos(prot_id, tbl),
                        d1=d,
                        rec_id=rid,
                        src=src,
                        note=note,
                    )
                )
    return ev


def _detect_hydrophobic(
    lig_atoms: list[Any],
    lig_rn: str,
    pocket: _PocketList,
    cfg: FingerprintConfig,
    rid: str,
    src: str,
    tbl: ResidueCorrespondenceTable | None,
    isoform: str,
) -> list[InteractionEvidence]:
    ev: list[InteractionEvidence] = []
    lig_hphob = [a for a in lig_atoms if _atom_element(a) == "C"]
    for prot_id, prot_rn, prot_res in pocket:
        if prot_rn not in _HYDROPHOBIC_RESIDUES:
            continue
        for pa in sorted(prot_res.get_atoms(), key=lambda a: a.get_name()):
            if not _is_hydrophobic_atom(pa, prot_rn):
                continue
            for la in sorted(lig_hphob, key=lambda a: a.get_name()):
                d = _dist(la, pa)
                if d > _HPHOB_SEARCH_A:
                    continue
                st, note = _classify_by_dist(d, cfg.hydrophobic_cutoff_angstrom, _HP_NOTE)
                ev.append(
                    _ev(
                        itype=InteractionType.HYDROPHOBIC,
                        status=st,
                        lig_a=la.get_name().strip(),
                        lig_r=lig_rn,
                        prot_id=prot_id,
                        prot_r=prot_rn,
                        prot_a=pa.get_name().strip(),
                        canon=_canon_pos(prot_id, tbl),
                        d1=round(d, 4),
                        rec_id=rid,
                        src=src,
                        note=note,
                    )
                )
    return ev


def _detect_water_mediated(
    lig_atoms: list[Any],
    lig_rn: str,
    bio_model: Any,
    pocket: _PocketList,
    cfg: FingerprintConfig,
    rid: str,
    src: str,
    tbl: ResidueCorrespondenceTable | None,
    isoform: str,
) -> list[InteractionEvidence]:
    """Only reports when explicit HOH molecules are in the structure.

    Does NOT infer missing direct contacts as water-mediated.
    """
    ev: list[InteractionEvidence] = []
    lig_hb = [a for a in lig_atoms if _is_hbond_element(a)]
    prot_hb: list[tuple[str, str, Any]] = [
        (pid, prn, pa) for pid, prn, pr in pocket for pa in pr.get_atoms() if _is_hbond_element(pa)
    ]
    for chain in bio_model:  # type: ignore[attr-defined]
        for res in chain:
            if res.get_resname().strip() not in ("HOH", "WAT"):
                continue
            if "O" not in res:
                continue
            wo = res["O"]
            water_id = f"{chain.id}_{res.get_id()[1]}_{res.get_id()[2]!s}"
            for la in sorted(lig_hb, key=lambda a: a.get_name()):
                d_lig = _dist(wo, la)
                if d_lig > _WATER_SEARCH_A:
                    continue
                for prot_id, prot_rn, pa in sorted(prot_hb, key=lambda x: (x[0], x[2].get_name())):
                    d_prot = _dist(wo, pa)
                    if d_prot > _WATER_SEARCH_A:
                        continue
                    st, note = _classify_by_dist(
                        max(d_lig, d_prot), cfg.water_arm_cutoff_angstrom, _WM_NOTE
                    )
                    ev.append(
                        _ev(
                            itype=InteractionType.WATER_MEDIATED,
                            status=st,
                            lig_a=la.get_name().strip(),
                            lig_r=lig_rn,
                            prot_id=prot_id,
                            prot_r=prot_rn,
                            prot_a=pa.get_name().strip(),
                            canon=_canon_pos(prot_id, tbl),
                            d1=round(d_lig, 4),
                            d2=round(d_prot, 4),
                            water=water_id,
                            rec_id=rid,
                            src=src,
                            note=note,
                        )
                    )
    return ev


def _detect_halogen_bonds(
    lig_atoms: list[Any],
    lig_rn: str,
    pocket: _PocketList,
    cfg: FingerprintConfig,
    rid: str,
    src: str,
    tbl: ResidueCorrespondenceTable | None,
    isoform: str,
) -> list[InteractionEvidence]:
    ev: list[InteractionEvidence] = []
    halogens = [a for a in lig_atoms if _atom_element(a) in _HALOGEN_ELEMENTS]
    if not halogens:
        return ev
    lig_carbons = [a for a in lig_atoms if _atom_element(a) == "C"]
    for prot_id, prot_rn, prot_res in pocket:
        for pa in sorted(prot_res.get_atoms(), key=lambda a: a.get_name()):
            if _atom_element(pa) not in {"N", "O", "S"}:
                continue
            for ha in sorted(halogens, key=lambda a: a.get_name()):
                d = _dist(ha, pa)
                if d > _HALOGEN_SEARCH_A:
                    continue
                ang: float | None = None
                if lig_carbons:
                    nc = min(lig_carbons, key=lambda a: _dist(a, ha))
                    ang = _angle_at_b(nc, ha, pa)
                st, note = _classify_by_dist(
                    d,
                    cfg.halogen_distance_cutoff_angstrom,
                    _HAL_NOTE,
                    angle=ang,
                    angle_min=cfg.halogen_angle_min_degrees,
                )
                ev.append(
                    _ev(
                        itype=InteractionType.HALOGEN_BOND,
                        status=st,
                        lig_a=ha.get_name().strip(),
                        lig_r=lig_rn,
                        prot_id=prot_id,
                        prot_r=prot_rn,
                        prot_a=pa.get_name().strip(),
                        canon=_canon_pos(prot_id, tbl),
                        d1=round(d, 4),
                        ang=ang,
                        rec_id=rid,
                        src=src,
                        note=note,
                    )
                )
    return ev


def _detect_metals(
    lig_atoms: list[Any],
    lig_rn: str,
    bio_model: Any,
    pocket: _PocketList,
    cfg: FingerprintConfig,
    rid: str,
    src: str,
    tbl: ResidueCorrespondenceTable | None,
    isoform: str,
) -> list[InteractionEvidence]:
    ev: list[InteractionEvidence] = []
    lig_coord = [a for a in lig_atoms if _atom_element(a) in {"N", "O", "S"}]
    for chain in bio_model:
        for res in chain:
            for ma in res.get_atoms():
                el = _atom_element(ma)
                if el not in _METAL_ELEMENTS:
                    continue
                metal_id = f"{chain.id}_{res.get_id()[1]}_{res.get_id()[2]!s}"
                for la in sorted(lig_coord, key=lambda a: a.get_name()):
                    d = _dist(la, ma)
                    if d > _METAL_SEARCH_A:
                        continue
                    st, note = _classify_by_dist(d, cfg.metal_distance_cutoff_angstrom, _MET_NOTE)
                    ev.append(
                        _ev(
                            itype=InteractionType.METAL_COORDINATION,
                            status=st,
                            lig_a=la.get_name().strip(),
                            lig_r=lig_rn,
                            prot_id=metal_id,
                            prot_r=res.get_resname().strip(),
                            prot_a=ma.get_name().strip(),
                            canon=None,
                            d1=round(d, 4),
                            metal=el,
                            rec_id=rid,
                            src=src,
                            note=note,
                        )
                    )
    return ev


# ── Main public API ───────────────────────────────────────────────────────────


def compute_interaction_fingerprint(
    bio_structure: Any,
    structure_record: StructureRecord,
    pocket_residue_set: PocketResidueSet,
    ligand_record: LigandRecord,
    isoform: str,
    correspondence_table: ResidueCorrespondenceTable | None = None,
    config: FingerprintConfig | None = None,
) -> InteractionFingerprint:
    """Compute the protein-ligand interaction fingerprint for one structure.

    AlphaFold note: if structure_record.provenance.source is
    ALPHAFOLD_GOVERNED_FALLBACK and the ligand is absent (no experimentally
    observed ligand coordinates), all evidence records are UNAVAILABLE.
    Never fabricates interaction geometry.

    All evidence is sorted deterministically before storage.
    """
    if config is None:
        config = FingerprintConfig()
    bio_model = next(iter(bio_structure.get_models()))
    rec_id = structure_record.record_id
    src_val = structure_record.provenance.source.value
    lig_rn = ligand_record.residue_name
    is_af = structure_record.provenance.source == StructureSource.ALPHAFOLD_GOVERNED_FALLBACK

    # Locate ligand
    lig_res = None
    try:
        bc = bio_model[ligand_record.chain_id]
        for het in (f"H_{lig_rn}", " "):
            k = (het, ligand_record.residue_seq, ligand_record.insertion_code)
            if k in bc:
                lig_res = bc[k]
                break
    except (KeyError, AttributeError):
        pass

    if lig_res is None:
        note = (
            "AlphaFold structure: no experimental ligand coordinates available"
            if is_af
            else f"Ligand {lig_rn!r} not found in structure"
        )
        unavail = tuple(
            _ev(
                itype=t,
                status=InteractionStatus.UNAVAILABLE,
                lig_a="",
                lig_r=lig_rn,
                prot_id="",
                prot_r="",
                prot_a="",
                canon=None,
                d1=None,
                rec_id=rec_id,
                src=src_val,
                note=note,
            )
            for t in sorted(InteractionType, key=lambda x: x.value)
        )
        return _assemble(
            structure_record, isoform, ligand_record, config, correspondence_table, unavail
        )

    lig_atoms = [a for a in lig_res.get_atoms() if _atom_element(a) not in ("H", "D")]
    smiles = ligand_record.smiles

    # Build pocket residue list — sorted for determinism
    pocket: _PocketList = []
    for pr in sorted(
        pocket_residue_set.residues, key=lambda p: (p.residue.chain_id, p.residue.residue_seq)
    ):
        rr = pr.residue
        try:
            pchain = bio_model[rr.chain_id]
            pres = pchain[(" ", rr.residue_seq, rr.insertion_code)]
            pocket.append((rr.residue_id(), rr.residue_name, pres))
        except (KeyError, AttributeError):
            pass

    all_ev: list[InteractionEvidence] = []
    tbl = correspondence_table
    all_ev += _detect_hbonds(lig_atoms, lig_rn, pocket, config, rec_id, src_val, tbl, isoform)
    all_ev += _detect_salt_bridges(lig_atoms, lig_rn, pocket, config, rec_id, src_val, tbl, isoform)
    all_ev += _detect_pi_pi(
        lig_atoms, lig_res, lig_rn, smiles, pocket, config, rec_id, src_val, tbl, isoform
    )
    all_ev += _detect_cation_pi(
        lig_atoms, lig_res, lig_rn, smiles, pocket, config, rec_id, src_val, tbl, isoform
    )
    all_ev += _detect_hydrophobic(lig_atoms, lig_rn, pocket, config, rec_id, src_val, tbl, isoform)
    all_ev += _detect_water_mediated(
        lig_atoms, lig_rn, bio_model, pocket, config, rec_id, src_val, tbl, isoform
    )
    all_ev += _detect_halogen_bonds(
        lig_atoms, lig_rn, pocket, config, rec_id, src_val, tbl, isoform
    )
    all_ev += _detect_metals(
        lig_atoms, lig_rn, bio_model, pocket, config, rec_id, src_val, tbl, isoform
    )

    sorted_ev = tuple(
        sorted(
            all_ev,
            key=lambda e: (
                e.interaction_type.value,
                e.protein_residue_id,
                e.protein_atom_name,
                e.ligand_atom_name,
            ),
        )
    )
    return _assemble(
        structure_record, isoform, ligand_record, config, correspondence_table, sorted_ev
    )


def _assemble(
    structure_record: StructureRecord,
    isoform: str,
    ligand_record: LigandRecord,
    config: FingerprintConfig,
    table: ResidueCorrespondenceTable | None,
    evidence: tuple[InteractionEvidence, ...],
) -> InteractionFingerprint:
    counts: dict[str, int] = {t.value: 0 for t in InteractionType}
    for e in evidence:
        if e.status != InteractionStatus.NOT_APPLICABLE:
            counts[e.interaction_type.value] += 1
    return InteractionFingerprint(
        structure_record_id=structure_record.record_id,
        isoform=isoform,
        ligand_residue_name=ligand_record.residue_name,
        ligand_inchikey=ligand_record.inchikey,
        provenance=structure_record.provenance,
        algorithm_version=FINGERPRINT_ALGORITHM_VERSION,
        config=config,
        correspondence_table_version=(table.table_version if table else None),
        evidence=evidence,
        n_per_type=tuple(sorted(counts.items())),
    )


def build_comparative_fingerprint(
    isoform_fingerprints: list[tuple[str, InteractionFingerprint]],
    ligand_inchikey: str | None = None,
) -> ComparativeFingerprint:
    """Assemble fingerprints aligned by canonical residue position.

    The core of the comparative architecture: for each canonical position,
    `canonical_comparison(pos)` returns what interaction evidence the same
    compound forms at the equivalent residue across all four isoforms.
    """
    if not isoform_fingerprints:
        raise ValueError("At least one fingerprint required")
    sorted_pairs = tuple(sorted(isoform_fingerprints, key=lambda x: x[0]))
    canonical_positions: set[int] = set()
    for _, fp in sorted_pairs:
        for e in fp.evidence:
            if e.canonical_position is not None and e.status not in (
                InteractionStatus.UNAVAILABLE,
                InteractionStatus.NOT_APPLICABLE,
            ):
                canonical_positions.add(e.canonical_position)
    return ComparativeFingerprint(
        ligand_inchikey=ligand_inchikey,
        isoform_fingerprints=sorted_pairs,
        canonical_positions_covered=frozenset(canonical_positions),
        algorithm_version=FINGERPRINT_ALGORITHM_VERSION,
    )

"""Pocket geometry: coordinates, centroid, spatial extent, and atom-level membership.

Authority: ADR-0010 [Architectural]; SCI1-002 (Milestone 3).
Constitution sections served: §2.1 (governed 5 Å cutoff, ligand-ensemble union,
  rotamer states), §0.3 (orthosteric sub-regions), §A.1(4) (correspondence
  stability).

Scientific rule classification
--------------------------------
RULE_AVAILABLE:
  - Centroid of Cα atoms in the pocket (simple mean).
  - Centroid of all heavy atoms in the pocket (simple mean).
  - Bounding box (min/max per Cartesian axis over pocket Cα atoms).
  - Maximum pairwise Cα distance within the pocket.
  - Sub-region membership, carried from `PocketResidueSet`.
  - GOVERNED_DISTANCE_CUTOFF_ANGSTROM = 5.0 (Constitution §2.1) — already
    established in _pocket_definition.py; referenced, not redefined.

RULE_MISSING / GOVERNANCE_DECISION_REQUIRED:
  - Pocket *volume*: multiple algorithms are in common use (alpha-sphere /
    Voronoi / fpocket / ConvexHull approximation) and none is specified by the
    Constitution. `volume_angstrom3` is `None` until a governance decision
    names the algorithm. Do not set it to a bounding-box heuristic and call it
    a volume.

Engineering parameters (not scientific, fully configurable):
  - Rounding precision for floating-point coordinate serialisation: 4 decimal
    places by default. Set via `GeometryConfig.coord_decimal_places`.

Determinism notes
-----------------
Floating-point coordinates are rounded before storage so that serialisation
is byte-stable across platforms. All collections of atoms and residues are
sorted by a deterministic key (chain_id + residue_seq + atom_name) before
being stored in tuples.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from orthosteric.pocket._pocket_definition import (
    PocketResidueSet,
)
from orthosteric.pocket._structure_record import StructureProvenance, StructureRecord

__all__ = [
    "GEOMETRY_ALGORITHM_VERSION",
    "VOLUME_RULE_MISSING_NOTE",
    "AtomCoordinate",
    "GeometryConfig",
    "PocketGeometry",
    "compute_pocket_geometry",
]

GEOMETRY_ALGORITHM_VERSION = "pocket_geometry_v1_sci1002"

VOLUME_RULE_MISSING_NOTE = (
    "RULE_MISSING/GOVERNANCE_DECISION_REQUIRED: pocket volume algorithm not specified. "
    "Candidates include alpha-sphere (FPOCKET), Voronoi, and ConvexHull approximation; "
    "none is governed by Constitution §2.1 or any ADR/GDR. Implement only after a "
    "Governance Decision Record names the algorithm and its parameters."
)

_COORD_ROUND = 4  # default decimal places for deterministic floating-point storage


@dataclass(frozen=True, slots=True)
class GeometryConfig:
    """Engineering configuration for PocketGeometry computation.

    None of these parameters is scientifically governed; they are convergence
    and serialisation choices. Changing them does not require a GDR.

    Attributes:
        coord_decimal_places: Decimal places to round coordinates to before
            storage. Controls byte-stability of the output across platforms
            without affecting scientific accuracy at 4 places (sub-0.1 pm
            precision).
    """

    coord_decimal_places: int = _COORD_ROUND


@dataclass(frozen=True, slots=True)
class AtomCoordinate:
    """One atom's identity and 3-D position in the pocket.

    Attributes:
        residue_id:     `ResidueRecord.residue_id()` of the parent residue,
                        e.g. ``"A_859_ "``.
        residue_name:   3-letter residue name, e.g. ``"GLN"``.
        atom_name:      PDB atom name, e.g. ``"CA"``, ``"NE2"``.
        x:              x coordinate (Å), rounded for determinism.
        y:              y coordinate (Å), rounded for determinism.
        z:              z coordinate (Å), rounded for determinism.
        is_backbone:    True for N, CA, C, O.
        is_calpha:      True only for CA.
        sub_region:     Sub-region tag carried from `PocketResidue`.
        structure_record_id:  Back-reference to the `StructureRecord`.
    """

    residue_id: str
    residue_name: str
    atom_name: str
    x: float
    y: float
    z: float
    is_backbone: bool
    is_calpha: bool
    sub_region: str
    structure_record_id: str

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "atom_name": self.atom_name,
            "is_backbone": self.is_backbone,
            "is_calpha": self.is_calpha,
            "residue_id": self.residue_id,
            "residue_name": self.residue_name,
            "sub_region": self.sub_region,
            "x": self.x,
            "y": self.y,
            "z": self.z,
        }


@dataclass(frozen=True, slots=True)
class PocketGeometry:
    """Geometric description of the ATP-site pocket for one structure.

    Derived from a `PocketResidueSet` (which governs membership) and a
    BioPython `Structure` (which provides coordinates). Every field is
    immutable; coordinates are rounded to `GeometryConfig.coord_decimal_places`
    decimal places for deterministic serialisation.

    Attributes:
        structure_record_id:     Back-reference to the `StructureRecord`.
        provenance:              Structural provenance (carried from the record).
        algorithm_version:       `GEOMETRY_ALGORITHM_VERSION`.
        pocket_definition_algorithm_version:  Version of the pocket-definition
                                 policy that produced the residue set.
        n_pocket_residues:       Count of pocket residues.
        n_pocket_atoms:          Count of all heavy atoms in the pocket.
        n_calpha_atoms:          Count of Cα atoms in the pocket.
        centroid_ca:             Mean Cα position (x, y, z) in Å. ``None`` if
                                 no Cα atoms are resolved.
        centroid_heavy:          Mean heavy-atom position (x, y, z) in Å.
                                 ``None`` if no atoms are resolved.
        bounding_box_min_ca:     Min (x, y, z) over Cα atoms. ``None`` when no Cα.
        bounding_box_max_ca:     Max (x, y, z) over Cα atoms. ``None`` when no Cα.
        max_ca_pairwise_distance_angstrom: Largest Cα–Cα distance within the
                                 pocket. ``None`` when < 2 Cα atoms resolved.
        pocket_atoms:            All heavy atoms in the pocket, sorted
                                 deterministically.
        volume_angstrom3:        Always ``None`` (RULE_MISSING — see
                                 `VOLUME_RULE_MISSING_NOTE`).
        volume_governance_note:  `VOLUME_RULE_MISSING_NOTE`.
        n_atoms_missing_coordinates: Count of pocket residues in the residue
                                 set for which no coordinates were found in the
                                 BioPython structure.
    """

    structure_record_id: str
    provenance: StructureProvenance
    algorithm_version: str
    pocket_definition_algorithm_version: str
    n_pocket_residues: int
    n_pocket_atoms: int
    n_calpha_atoms: int
    centroid_ca: tuple[float, float, float] | None
    centroid_heavy: tuple[float, float, float] | None
    bounding_box_min_ca: tuple[float, float, float] | None
    bounding_box_max_ca: tuple[float, float, float] | None
    max_ca_pairwise_distance_angstrom: float | None
    pocket_atoms: tuple[AtomCoordinate, ...]
    volume_angstrom3: None
    volume_governance_note: str
    n_atoms_missing_coordinates: int

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "algorithm_version": self.algorithm_version,
            "bounding_box_max_ca": self.bounding_box_max_ca,
            "bounding_box_min_ca": self.bounding_box_min_ca,
            "centroid_ca": self.centroid_ca,
            "centroid_heavy": self.centroid_heavy,
            "max_ca_pairwise_distance_angstrom": self.max_ca_pairwise_distance_angstrom,
            "n_atoms_missing_coordinates": self.n_atoms_missing_coordinates,
            "n_calpha_atoms": self.n_calpha_atoms,
            "n_pocket_atoms": self.n_pocket_atoms,
            "n_pocket_residues": self.n_pocket_residues,
            "pocket_definition_algorithm_version": self.pocket_definition_algorithm_version,
            "provenance": self.provenance.to_canonical_dict(),
            "structure_record_id": self.structure_record_id,
            "volume_angstrom3": None,
        }

    def content_sha256(self) -> str:
        payload = json.dumps(
            self.to_canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_BACKBONE_ATOMS = frozenset({"N", "CA", "C", "O"})


def compute_pocket_geometry(  # noqa: PLR0915
    bio_structure: Any,
    structure_record: StructureRecord,
    pocket_residue_set: PocketResidueSet,
    config: GeometryConfig | None = None,
) -> PocketGeometry:
    """Compute pocket geometry from a BioPython structure and governed residue set.

    Parameters
    ----------
    bio_structure:
        A `Bio.PDB.Structure.Structure` object, already parsed (e.g. via
        `Bio.PDB.PDBParser`). The chain/residue numbering must correspond to
        the `ResidueRecord` identifiers in `pocket_residue_set`.
    structure_record:
        The `StructureRecord` for this structure, providing provenance.
    pocket_residue_set:
        The governed `PocketResidueSet` specifying which residues constitute
        the pocket. Membership is determined by the pocket-definition policy,
        not recomputed here.
    config:
        Engineering configuration; defaults are used if ``None``.

    Returns:
    -------
    `PocketGeometry` — frozen, provenance-preserving, deterministic.
    """
    if config is None:
        config = GeometryConfig()
    dp = config.coord_decimal_places

    # Index BioPython atoms by (chain_id, residue_seq, ins_code)
    # Use model 0 (standard for X-ray structures)
    bio_model = next(iter(bio_structure.get_models()))  # type: ignore[union-attr,attr-defined]

    def _rounded(val: float) -> float:
        return round(float(val), dp)

    pocket_atoms: list[AtomCoordinate] = []
    n_missing = 0

    # Sort pocket residues deterministically before processing
    sorted_pocket_residues = sorted(
        pocket_residue_set.residues,
        key=lambda pr: (
            pr.residue.chain_id,
            pr.residue.residue_seq,
            pr.residue.insertion_code,
        ),
    )

    for pocket_res in sorted_pocket_residues:
        rr = pocket_res.residue
        chain_id = rr.chain_id
        res_seq = rr.residue_seq
        ins_code = rr.insertion_code
        sub_region = pocket_res.sub_region.value

        # Try to locate this residue in the BioPython structure
        try:
            bio_chain = bio_model[chain_id]
        except KeyError:
            n_missing += 1
            continue

        # BioPython residue key: (' ', res_seq, ins_code)
        # Hetfield is ' ' for standard residues
        het_flag = " "
        bio_res_key = (het_flag, res_seq, ins_code)
        try:
            bio_res = bio_chain[bio_res_key]
        except KeyError:
            n_missing += 1
            continue

        residue_id = rr.residue_id()

        # Collect all heavy atoms (exclude H/D), sorted for determinism
        for atom in sorted(bio_res.get_atoms(), key=lambda a: a.get_name()):
            aname = atom.get_name().strip()
            # Skip hydrogens
            element = (atom.element or "").strip().upper()
            if element in ("H", "D") or (not element and aname.startswith("H")):
                continue
            coord = atom.get_vector()
            is_bb = aname in _BACKBONE_ATOMS
            pocket_atoms.append(
                AtomCoordinate(
                    residue_id=residue_id,
                    residue_name=rr.residue_name,
                    atom_name=aname,
                    x=_rounded(coord[0]),
                    y=_rounded(coord[1]),
                    z=_rounded(coord[2]),
                    is_backbone=is_bb,
                    is_calpha=(aname == "CA"),
                    sub_region=sub_region,
                    structure_record_id=structure_record.record_id,
                )
            )

    # Compute geometric quantities
    ca_coords: NDArray[np.float64] = np.array(
        [[a.x, a.y, a.z] for a in pocket_atoms if a.is_calpha],
        dtype=np.float64,
    )
    all_coords: NDArray[np.float64] = np.array(
        [[a.x, a.y, a.z] for a in pocket_atoms], dtype=np.float64
    )

    def _tuple3(arr: NDArray[np.float64]) -> tuple[float, float, float]:
        return (
            _rounded(float(arr[0])),
            _rounded(float(arr[1])),
            _rounded(float(arr[2])),
        )

    centroid_ca: tuple[float, float, float] | None = None
    bounding_box_min_ca: tuple[float, float, float] | None = None
    bounding_box_max_ca: tuple[float, float, float] | None = None
    max_ca_dist: float | None = None

    if len(ca_coords) >= 1:
        centroid_ca = _tuple3(ca_coords.mean(axis=0))
        bounding_box_min_ca = _tuple3(ca_coords.min(axis=0))
        bounding_box_max_ca = _tuple3(ca_coords.max(axis=0))

    if len(ca_coords) >= 2:  # noqa: PLR2004 — minimum for a meaningful pairwise distance
        # Pairwise distances — O(N^2) is fine for pocket-sized arrays (< 50 residues)
        diffs = ca_coords[:, None, :] - ca_coords[None, :, :]  # (N,N,3)
        dists = np.sqrt((diffs**2).sum(axis=-1))
        max_ca_dist = _rounded(float(dists.max()))

    centroid_heavy: tuple[float, float, float] | None = None
    if len(all_coords) >= 1:
        centroid_heavy = _tuple3(all_coords.mean(axis=0))

    return PocketGeometry(
        structure_record_id=structure_record.record_id,
        provenance=structure_record.provenance,
        algorithm_version=GEOMETRY_ALGORITHM_VERSION,
        pocket_definition_algorithm_version=pocket_residue_set.algorithm_version,
        n_pocket_residues=len(pocket_residue_set.residues),
        n_pocket_atoms=len(pocket_atoms),
        n_calpha_atoms=len(ca_coords),
        centroid_ca=centroid_ca,
        centroid_heavy=centroid_heavy,
        bounding_box_min_ca=bounding_box_min_ca,
        bounding_box_max_ca=bounding_box_max_ca,
        max_ca_pairwise_distance_angstrom=max_ca_dist,
        pocket_atoms=tuple(pocket_atoms),
        volume_angstrom3=None,
        volume_governance_note=VOLUME_RULE_MISSING_NOTE,
        n_atoms_missing_coordinates=n_missing,
    )

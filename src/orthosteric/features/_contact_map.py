"""Residue-residue and ligand-residue contact maps for orthosteric pockets.

Authority: ADR-0010 [Architectural]; SCI1-005 (part 1 of 2).
Constitution sections served: §2.1 (pocket definition, correspondence),
  §4.2 (comparative feature requirements), §4.6 (Path A representation).

Scientific mandate: measure pairwise atomic proximity as structural evidence.
Does NOT determine which contacts are productive, selective, or favourable.

Scientific rule classification
  RULE_AVAILABLE:  minimum heavy-atom distance as the contact metric — no
    specific biological assumption; pure geometry.
  RULE_AVAILABLE:  ligand and protein heavy atoms identified by element
    (exclude H/D).
  RULE_MISSING:    distance threshold for classifying a pair as "in contact"
    vs "out of contact". Not governed by any Constitution section, ADR, or
    GDR. `ContactMapConfig.contact_cutoff_angstrom` defaults to None.

Implementation search radius
  `_CANDIDATE_RADIUS_A = 10.0` — all pairs within 10 A are enumerated
  regardless of contact classification. This captures the full first and
  second coordination shells around any ATP-site residue.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np

from orthosteric.pocket._pocket_definition import PocketResidueSet
from orthosteric.pocket._residue_mapping import ResidueCorrespondenceTable
from orthosteric.pocket._structure_record import LigandRecord, StructureRecord

__all__ = [
    "CONTACT_MAP_ALGORITHM_VERSION",
    "ContactMapConfig",
    "ContactStatus",
    "LigandResidueContactMap",
    "PocketContactMap",
    "ResidueResidueContactMap",
    "compute_contact_map",
]

CONTACT_MAP_ALGORITHM_VERSION = "contact_map_v1_sci1005"

_CANDIDATE_RADIUS_A: float = 10.0  # implementation parameter; not a science cutoff
_CONTACT_RULE_MISSING = (
    "RULE_MISSING: contact distance cutoff not governed. Raw distance preserved."
)


class ContactStatus(StrEnum):
    """Classification status for one contact entry.

    CONTACT:      distance <= governed cutoff.
    NONCONTACT:   distance >  governed cutoff.
    RULE_MISSING: no governed cutoff; distance preserved but unclassified.
    UNAVAILABLE:  one or both atoms absent from structure.
    """

    CONTACT = "contact"
    NONCONTACT = "noncontact"
    RULE_MISSING = "rule_missing"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ContactMapConfig:
    """Contact classification threshold. Defaults to None (RULE_MISSING)."""

    contact_cutoff_angstrom: float | None = None

    def to_canonical_dict(self) -> dict[str, float | None]:
        return {"contact_cutoff_angstrom": self.contact_cutoff_angstrom}


@dataclass(frozen=True, slots=True)
class ResidueResidueContactMap:
    """Pairwise minimum heavy-atom distances between pocket residues.

    Stored as a symmetric upper-triangular list of (i, j, distance) entries
    for all pairs within the candidate search radius.

    Attributes:
        residue_ids:        Sorted residue_id strings (deterministic order).
        canonical_positions: Canonical position per residue (None if unmapped).
        entries:            (i, j, distance_A, status) for i < j, sorted by
                            (i, j).
        structure_record_id: Source structure.
        isoform:            Target isoform.
        algorithm_version:  Pinned version string.
        config:             Config used for classification.
        correspondence_table_version: From SCI1-003 table if provided.
    """

    residue_ids: tuple[str, ...]
    canonical_positions: tuple[int | None, ...]
    entries: tuple[tuple[int, int, float, str], ...]  # (i, j, dist, status)
    structure_record_id: str
    isoform: str
    algorithm_version: str
    config: ContactMapConfig
    correspondence_table_version: str | None

    def distance(self, res_id_a: str, res_id_b: str) -> float | None:
        """Minimum heavy-atom distance between two residues. None if not enumerated."""
        if res_id_a not in self.residue_ids or res_id_b not in self.residue_ids:
            return None
        i, j = self.residue_ids.index(res_id_a), self.residue_ids.index(res_id_b)
        if i > j:
            i, j = j, i
        for ei, ej, d, _ in self.entries:
            if ei == i and ej == j:
                return d
        return None

    def n_residues(self) -> int:
        return len(self.residue_ids)

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "algorithm_version": self.algorithm_version,
                "canonical_positions": list(self.canonical_positions),
                "config": self.config.to_canonical_dict(),
                "correspondence_table_version": self.correspondence_table_version,
                "entries": [list(e) for e in self.entries],
                "isoform": self.isoform,
                "residue_ids": list(self.residue_ids),
                "structure_record_id": self.structure_record_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class LigandResidueContactMap:
    """Pairwise minimum heavy-atom distances between ligand atoms and pocket residues.

    Attributes:
        ligand_atom_names:  Sorted ligand heavy-atom names.
        residue_ids:        Sorted residue_id strings.
        canonical_positions: Canonical position per residue.
        entries:            (lig_atom_idx, res_idx, distance_A, status) sorted by
                            (lig_atom_idx, res_idx).
        ligand_residue_name: 3-letter PDB name of the ligand.
        structure_record_id: Source structure.
        isoform:            Target isoform.
        algorithm_version:  Pinned version.
        config:             Classification config.
        correspondence_table_version: From SCI1-003 table if provided.
    """

    ligand_atom_names: tuple[str, ...]
    residue_ids: tuple[str, ...]
    canonical_positions: tuple[int | None, ...]
    entries: tuple[tuple[int, int, float, str], ...]  # (la, ri, dist, status)
    ligand_residue_name: str
    structure_record_id: str
    isoform: str
    algorithm_version: str
    config: ContactMapConfig
    correspondence_table_version: str | None

    def distance(self, lig_atom: str, res_id: str) -> float | None:
        if lig_atom not in self.ligand_atom_names or res_id not in self.residue_ids:
            return None
        la = self.ligand_atom_names.index(lig_atom)
        ri = self.residue_ids.index(res_id)
        for eli, eri, d, _ in self.entries:
            if eli == la and eri == ri:
                return d
        return None

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "algorithm_version": self.algorithm_version,
                "canonical_positions": list(self.canonical_positions),
                "config": self.config.to_canonical_dict(),
                "correspondence_table_version": self.correspondence_table_version,
                "entries": [list(e) for e in self.entries],
                "isoform": self.isoform,
                "ligand_atom_names": list(self.ligand_atom_names),
                "ligand_residue_name": self.ligand_residue_name,
                "residue_ids": list(self.residue_ids),
                "structure_record_id": self.structure_record_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PocketContactMap:
    """Combined contact map for one structure: residue-residue and ligand-residue."""

    res_res: ResidueResidueContactMap
    lig_res: LigandResidueContactMap | None  # None when ligand absent
    structure_record_id: str
    isoform: str
    algorithm_version: str

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "algorithm_version": self.algorithm_version,
                "isoform": self.isoform,
                "lig_res_hash": (
                    self.lig_res.content_sha256() if self.lig_res is not None else None
                ),
                "res_res_hash": self.res_res.content_sha256(),
                "structure_record_id": self.structure_record_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── Geometry helpers ──────────────────────────────────────────────────────────


def _atom_element(atom: Any) -> str:
    el = (atom.element or "").strip().upper()
    return el if el else (atom.get_name().strip().upper()[:1] if atom.get_name().strip() else "")


def _heavy_atoms(residue: Any) -> list[Any]:
    return [a for a in residue.get_atoms() if _atom_element(a) not in ("H", "D", "")]


def _min_dist(atoms_a: list[Any], atoms_b: list[Any]) -> float | None:
    """Minimum heavy-atom distance between two residues. None when either empty."""
    if not atoms_a or not atoms_b:
        return None
    vecs_a = np.array([a.get_vector().get_array() for a in atoms_a], dtype=np.float64)
    vecs_b = np.array([a.get_vector().get_array() for a in atoms_b], dtype=np.float64)
    diffs = vecs_a[:, None, :] - vecs_b[None, :, :]  # (Na, Nb, 3)
    dists = np.linalg.norm(diffs, axis=2)
    return float(round(np.min(dists), 4))


def _classify(dist: float | None, cutoff: float | None) -> str:
    if dist is None:
        return ContactStatus.UNAVAILABLE.value
    if cutoff is None:
        return ContactStatus.RULE_MISSING.value
    return ContactStatus.CONTACT.value if dist <= cutoff else ContactStatus.NONCONTACT.value


def _canon_pos(res_id: str, table: ResidueCorrespondenceTable | None) -> int | None:
    if table is None:
        return None
    a = table.get_canonical_position(res_id)
    return a.canonical_position if a is not None else None


# ── Main public API ───────────────────────────────────────────────────────────


def compute_contact_map(  # noqa: PLR0912,PLR0915
    bio_structure: Any,
    structure_record: StructureRecord,
    pocket_residue_set: PocketResidueSet,
    ligand_record: LigandRecord | None = None,
    isoform: str = "",
    correspondence_table: ResidueCorrespondenceTable | None = None,
    config: ContactMapConfig | None = None,
) -> PocketContactMap:
    """Compute pairwise contact maps for one orthosteric pocket.

    Parameters
    ----------
    bio_structure:      Parsed `Bio.PDB.Structure`.
    structure_record:   Provenance.
    pocket_residue_set: Governed pocket residues (ligand-ensemble union).
    ligand_record:      ATP-site ligand. None -> lig_res map is None.
    isoform:            Target isoform name.
    correspondence_table: SCI1-003 table for canonical position annotation.
    config:             Contact classification config. All RULE_MISSING by default.
    """
    if config is None:
        config = ContactMapConfig()
    bio_model = next(iter(bio_structure.get_models()))
    rec_id = structure_record.record_id
    ct_version = correspondence_table.table_version if correspondence_table else None

    # Sort pocket residues for determinism
    sorted_prs = sorted(
        pocket_residue_set.residues,
        key=lambda pr: (pr.residue.chain_id, pr.residue.residue_seq),
    )
    res_ids = tuple(pr.residue.residue_id() for pr in sorted_prs)
    canon_positions = tuple(_canon_pos(rid, correspondence_table) for rid in res_ids)

    # Fetch BioPython residue objects
    def _get_bio_res(rr: Any) -> Any:
        try:
            return bio_model[rr.chain_id][(" ", rr.residue_seq, rr.insertion_code)]
        except (KeyError, AttributeError):
            return None

    bio_residues = [_get_bio_res(pr.residue) for pr in sorted_prs]

    # Residue-residue map: upper triangular
    rr_entries: list[tuple[int, int, float, str]] = []
    for i in range(len(res_ids)):
        for j in range(i + 1, len(res_ids)):
            res_a = bio_residues[i]
            res_b = bio_residues[j]
            if res_a is None or res_b is None:
                rr_entries.append((i, j, float("inf"), ContactStatus.UNAVAILABLE.value))
                continue
            ha = _heavy_atoms(res_a)
            hb = _heavy_atoms(res_b)
            d = _min_dist(ha, hb)
            if d is not None and d > _CANDIDATE_RADIUS_A:
                continue  # outside candidate radius; skip
            rr_entries.append(
                (
                    i,
                    j,
                    d if d is not None else float("inf"),
                    _classify(d, config.contact_cutoff_angstrom),
                )
            )

    res_res = ResidueResidueContactMap(
        residue_ids=res_ids,
        canonical_positions=canon_positions,
        entries=tuple(sorted(rr_entries)),
        structure_record_id=rec_id,
        isoform=isoform,
        algorithm_version=CONTACT_MAP_ALGORITHM_VERSION,
        config=config,
        correspondence_table_version=ct_version,
    )

    # Ligand-residue map
    lig_res_map: LigandResidueContactMap | None = None
    if ligand_record is not None:
        lig_bio_res = None
        try:
            bc = bio_model[ligand_record.chain_id]
            for het in (f"H_{ligand_record.residue_name}", " "):
                k = (het, ligand_record.residue_seq, ligand_record.insertion_code)
                if k in bc:
                    lig_bio_res = bc[k]
                    break
        except (KeyError, AttributeError):
            pass

        if lig_bio_res is not None:
            lig_heavy = _heavy_atoms(lig_bio_res)
            lig_atom_names = tuple(sorted(a.get_name().strip() for a in lig_heavy))
            lig_heavy_sorted = sorted(lig_heavy, key=lambda a: a.get_name().strip())
            lr_entries: list[tuple[int, int, float, str]] = []
            for la_idx, la in enumerate(lig_heavy_sorted):
                la_vec = np.array(la.get_vector().get_array(), dtype=np.float64)
                for ri, _pr in enumerate(sorted_prs):
                    bio_res = bio_residues[ri]
                    if bio_res is None:
                        lr_entries.append(
                            (la_idx, ri, float("inf"), ContactStatus.UNAVAILABLE.value)
                        )
                        continue
                    ha = _heavy_atoms(bio_res)
                    if not ha:
                        continue
                    vecs = np.array([a.get_vector().get_array() for a in ha], dtype=np.float64)
                    d = float(round(float(np.min(np.linalg.norm(vecs - la_vec, axis=1))), 4))
                    if d > _CANDIDATE_RADIUS_A:
                        continue
                    lr_entries.append((la_idx, ri, d, _classify(d, config.contact_cutoff_angstrom)))
            lig_res_map = LigandResidueContactMap(
                ligand_atom_names=lig_atom_names,
                residue_ids=res_ids,
                canonical_positions=canon_positions,
                entries=tuple(sorted(lr_entries)),
                ligand_residue_name=ligand_record.residue_name,
                structure_record_id=rec_id,
                isoform=isoform,
                algorithm_version=CONTACT_MAP_ALGORITHM_VERSION,
                config=config,
                correspondence_table_version=ct_version,
            )

    return PocketContactMap(
        res_res=res_res,
        lig_res=lig_res_map,
        structure_record_id=rec_id,
        isoform=isoform,
        algorithm_version=CONTACT_MAP_ALGORITHM_VERSION,
    )

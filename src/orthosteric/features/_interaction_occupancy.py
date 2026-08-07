"""Occupancy/recurrence aggregation across multiple docking poses.

Objective: interaction-motif fingerprints workstream, section 5. A single
docking pose is NOT evidence of a stable interaction; this module
aggregates interaction events across multiple independently-generated
poses for the SAME compound x isoform docking run into an occupancy
fraction.

Terminology (binding, per this session's explicit instruction): this is
DOCKING-POSE recurrence/occupancy, never "residence time" or "MD
persistence" -- no kinetic claim is made anywhere in this module.

Occupancy threshold (ENGINEERING CHOICE, documented, not tuned on any
experimental label)
-----------------------------------------------------------------------
  OBSERVED_SINGLE_POSE: occupancy == 1/n_poses (present in exactly one
    evaluated pose).
  RECURRENT:            occupancy >= 0.4 (present in at least 2 of 5
    poses at the default n_poses=5 protocol).
  HIGH_OCCUPANCY:       occupancy >= 0.8 (present in at least 4 of 5).
These thresholds are deterministic, disclosed, and never selected to
make any particular result look better -- set before this module was
run on real data. Sensitivity to these exact cutoffs is reported
separately (see docs/ for the analysis); the raw, continuous occupancy
value is ALWAYS retained regardless of which categorical bucket it
falls into, so the thresholds can be revised later without rerunning
docking.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

OCCUPANCY_POLICY_ID = "pose_occupancy_v1"

_RECURRENT_THRESHOLD = 0.4
_HIGH_OCCUPANCY_THRESHOLD = 0.8


class OccupancyClass(StrEnum):
    OBSERVED_SINGLE_POSE = "observed_single_pose"
    RECURRENT = "recurrent"
    HIGH_OCCUPANCY = "high_occupancy"


def classify_occupancy(occupancy: float, n_poses: int) -> OccupancyClass:
    """Deterministic bucket for a raw occupancy fraction.

    `n_poses` is accepted (not just occupancy) so a single-pose
    evaluation (n_poses=1) is never miscategorized as anything but
    OBSERVED_SINGLE_POSE, even if its fraction happens to equal 1.0.
    """
    if n_poses <= 1:
        return OccupancyClass.OBSERVED_SINGLE_POSE
    if occupancy >= _HIGH_OCCUPANCY_THRESHOLD:
        return OccupancyClass.HIGH_OCCUPANCY
    if occupancy >= _RECURRENT_THRESHOLD:
        return OccupancyClass.RECURRENT
    return OccupancyClass.OBSERVED_SINGLE_POSE


@dataclass(frozen=True, slots=True)
class InteractionOccupancy:
    """Aggregated occupancy for one (residue, ligand_atom, interaction_type) key.

    Covers all evaluated poses of one compound x isoform docking run.
    """

    interaction_type: str
    residue_number: int
    residue_name: str
    chain_id: str
    ligand_atom_name: str
    n_poses_evaluated: int
    n_poses_with_interaction: int
    occupancy: float
    occupancy_class: OccupancyClass
    distances: tuple[float, ...]  # one per pose in which it occurred, in pose order

    @property
    def mean_distance(self) -> float | None:
        return sum(self.distances) / len(self.distances) if self.distances else None

    @property
    def median_distance(self) -> float | None:
        if not self.distances:
            return None
        s = sorted(self.distances)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "interaction_type": self.interaction_type,
            "residue_number": self.residue_number,
            "residue_name": self.residue_name,
            "chain_id": self.chain_id,
            "ligand_atom_name": self.ligand_atom_name,
            "n_poses_evaluated": self.n_poses_evaluated,
            "n_poses_with_interaction": self.n_poses_with_interaction,
            "occupancy": self.occupancy,
            "occupancy_class": self.occupancy_class.value,
            "mean_distance_angstrom": self.mean_distance,
            "median_distance_angstrom": self.median_distance,
            "policy": OCCUPANCY_POLICY_ID,
        }


def aggregate_occupancy(
    per_pose_interactions: list[
        list[Any]
    ],  # list[list[AtomResidueInteraction]], one inner list per pose
) -> list[InteractionOccupancy]:
    """Aggregate atom-residue interactions across multiple poses.

    All poses must be from the SAME compound x isoform docking run.

    `per_pose_interactions[i]` must be the full interaction list for pose
    i (from features._docking_interaction_detector.detect_all_interactions
    called once per pose). Never fabricates an interaction absent from
    every pose; an interaction present in 0 poses simply never appears
    in the output (there is nothing to report -- this is not the same as
    zero-filling a MEASURED quantity, since no measurement claim is made
    about interactions that never occurred).
    """
    n_poses = len(per_pose_interactions)
    counts: dict[tuple[str, int, str, str], int] = defaultdict(int)
    distances: dict[tuple[str, int, str, str], list[float]] = defaultdict(list)
    meta: dict[tuple[str, int, str, str], tuple[str, str]] = {}

    for pose_interactions in per_pose_interactions:
        seen_this_pose: set[tuple[str, int, str, str]] = set()
        for it in pose_interactions:
            key = (it.interaction_type.value, it.residue_number, it.chain_id, it.ligand_atom_name)
            if key in seen_this_pose:
                continue  # count each interaction at most once per pose (avoid double count if a
                # detector ever returns >1 geometric record for the same atom-residue-type triple)
            seen_this_pose.add(key)
            counts[key] += 1
            if it.distance_angstrom is not None:
                distances[key].append(it.distance_angstrom)
            meta[key] = (it.residue_name, it.ligand_atom_name)

    results = []
    for key, n_with in counts.items():
        interaction_type, residue_number, chain_id, ligand_atom_name = key
        residue_name, _ = meta[key]
        occupancy = n_with / n_poses if n_poses > 0 else 0.0
        results.append(
            InteractionOccupancy(
                interaction_type=interaction_type,
                residue_number=residue_number,
                residue_name=residue_name,
                chain_id=chain_id,
                ligand_atom_name=ligand_atom_name,
                n_poses_evaluated=n_poses,
                n_poses_with_interaction=n_with,
                occupancy=occupancy,
                occupancy_class=classify_occupancy(occupancy, n_poses),
                distances=tuple(distances.get(key, [])),
            )
        )
    return sorted(results, key=lambda r: (r.interaction_type, r.residue_number, r.ligand_atom_name))


@dataclass(frozen=True, slots=True)
class ResidueLevelOccupancy:
    """Aggregated occupancy for one (residue, interaction_type) key.

    MARGINALIZED over which specific ligand atom carries the interaction.

    Added per the SIFt/ProLIF-established interaction-fingerprint
    convention (Deng et al. 2004; Bouysset & Fiorucci 2021) after the
    atom-level primary key was identified as the likely dominant cause
    of the 93-99% "lost" classification rate observed in the 24- and
    50-compound runs (commits eafe327, 2f26c5c) -- ligand-atom-name-level
    keying is finer than any established interaction-fingerprint method
    uses, and residue-level is the field-standard granularity.

    Computed directly from the raw per-pose interaction lists (the same
    already-saved pose PDBQT files, re-parsed -- no new docking), NOT
    approximated from the already-aggregated atom-level occupancy, so
    that "did ANY atom hit this residue via this interaction type in
    this pose" is counted correctly per pose rather than derived
    after the fact from per-atom occupancy fractions (which would
    under-count cases where different atoms carry the interaction in
    different, non-overlapping poses).
    """

    interaction_type: str
    residue_number: int
    residue_name: str
    chain_id: str
    n_poses_evaluated: int
    n_poses_with_interaction: int
    occupancy: float
    occupancy_class: OccupancyClass
    contributing_atom_names: frozenset[str]  # provenance only, never the comparative key
    distances: tuple[float, ...]

    @property
    def mean_distance(self) -> float | None:
        return sum(self.distances) / len(self.distances) if self.distances else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "interaction_type": self.interaction_type,
            "residue_number": self.residue_number,
            "residue_name": self.residue_name,
            "chain_id": self.chain_id,
            "n_poses_evaluated": self.n_poses_evaluated,
            "n_poses_with_interaction": self.n_poses_with_interaction,
            "occupancy": self.occupancy,
            "occupancy_class": self.occupancy_class.value,
            "contributing_atom_names": sorted(self.contributing_atom_names),
            "mean_distance_angstrom": self.mean_distance,
            "policy": OCCUPANCY_POLICY_ID + "_residue_level",
        }


def aggregate_residue_level_occupancy(
    per_pose_interactions: list[list[Any]],
) -> list[ResidueLevelOccupancy]:
    """Residue-level counterpart of `aggregate_occupancy`.

    Identical pose-counting discipline (never fabricates an absent
    interaction; counts each interaction at most once per pose), but the
    key drops `ligand_atom_name` -- if atom O7 and atom O9 both form an
    H-bond with the same residue in the same pose, that pose counts once
    toward that residue's H-bond occupancy, not twice, and it is the
    SAME single count whether one atom or several carried it.
    """
    n_poses = len(per_pose_interactions)
    counts: dict[tuple[str, int, str], int] = defaultdict(int)
    distances: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    contributing_atoms: dict[tuple[str, int, str], set[str]] = defaultdict(set)
    residue_names: dict[tuple[str, int, str], str] = {}

    for pose_interactions in per_pose_interactions:
        seen_this_pose: set[tuple[str, int, str]] = set()
        for it in pose_interactions:
            key = (it.interaction_type.value, it.residue_number, it.chain_id)
            contributing_atoms[key].add(it.ligand_atom_name)
            residue_names[key] = it.residue_name
            if key in seen_this_pose:
                continue
            seen_this_pose.add(key)
            counts[key] += 1
            if it.distance_angstrom is not None:
                distances[key].append(it.distance_angstrom)

    results = []
    for key, n_with in counts.items():
        interaction_type, residue_number, chain_id = key
        occupancy = n_with / n_poses if n_poses > 0 else 0.0
        results.append(
            ResidueLevelOccupancy(
                interaction_type=interaction_type,
                residue_number=residue_number,
                residue_name=residue_names[key],
                chain_id=chain_id,
                n_poses_evaluated=n_poses,
                n_poses_with_interaction=n_with,
                occupancy=occupancy,
                occupancy_class=classify_occupancy(occupancy, n_poses),
                contributing_atom_names=frozenset(contributing_atoms[key]),
                distances=tuple(distances.get(key, [])),
            )
        )
    return sorted(results, key=lambda r: (r.interaction_type, r.residue_number))

"""Representations 2 and 3: chemically role-aware interaction fingerprints.

Per the Representation-3 validation mandate.

Representation 2 (SS9): ligand_pharmacophore_class x residue_functional_class
x interaction_type. Residue identity, canonical position, ligand atom
identity, and pose identity are METADATA ONLY -- never components of
this comparison key (mandatory exclusion, SS9). This is what allows a
chemically-equivalent interaction carried by different residues (e.g.
Asp vs Glu, both ANIONIC_CAPABLE) to merge into one comparative bin.

Representation 3 (SS10): Representation 2 plus a coarse, chemically
motivated geometry descriptor, added to the key. Bins are deliberately
broad (interaction-type-specific, not fine numeric Angstrom windows) to
avoid recreating atom-level fragmentation under a new name.

Occupancy discipline (SS12, unchanged from the project's established
convention): a bin contributes occupancy at most once per pose,
regardless of how many ligand atoms, residues, or canonical positions
map to the same key within that pose.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from orthosteric.features._docking_interaction_detector import (
    AtomResidueInteraction,
    InteractionType,
)
from orthosteric.features._interaction_occupancy import OccupancyClass, classify_occupancy
from orthosteric.features._ligand_moiety import LigandMoiety
from orthosteric.features._residue_functional_class import (
    ResidueFunctionalClass,
    residue_functional_class,
)

REPRESENTATION_23_POLICY_ID = "representation_2_3_v1_role_aware"


# ── Representation-3 coarse geometry bins (SS10) ─────────────────────────────
# Deliberately broad, interaction-type-specific, documented BEFORE any
# result was inspected (this file is authored before Phase 3's reparse
# is run). No 0.1-0.2 A bins anywhere.


class GeometryBin(StrEnum):
    H_BOND_OPTIMAL_OR_STRONG = "h_bond_optimal_or_strong"
    H_BOND_LONG_OR_WEAK = "h_bond_long_or_weak"
    HYDROPHOBIC_CLOSE = "hydrophobic_close"
    HYDROPHOBIC_PERIPHERAL = "hydrophobic_peripheral"
    AROMATIC_FAVORABLE_CLOSE = "aromatic_favorable_close"
    AROMATIC_WEAKER_PERIPHERAL = "aromatic_weaker_peripheral"
    CHARGED_CLOSE = "charged_close"
    CHARGED_PERIPHERAL = "charged_peripheral"
    CATION_PI_CLOSE = "cation_pi_close"
    CATION_PI_PERIPHERAL = "cation_pi_peripheral"
    NOT_APPLICABLE = "not_applicable"  # geometry omitted from key by design (SS10.2 fallback)


#: SS10.1 -- H-bond boundary. The existing detector's own D...A cutoff is
#: 3.5 A (see _docking_interaction_detector.py); this splits that single
#: window into two broad chemically-motivated halves (near-ideal
#: covalent-adjacent geometry vs the longer, weaker tail), not a new,
#: finer-grained scale. Documented before inspecting any result.
_HBOND_OPTIMAL_MAX_A = 3.0

#: SS10.2 -- hydrophobic contacts. The existing detector's cutoff is
#: 4.5 A; split at its midpoint-ish into "close packing" vs "peripheral
#: van der Waals contact," a defensible coarse split, not a numeric
#: guess made after seeing results.
_HYDROPHOBIC_CLOSE_MAX_A = 4.0

#: SS10.3 -- aromatic/pi-pi. Uses DISTANCE ONLY for the primary
#: Representation-3 bin (documented choice, per the mandate's explicit
#: requirement to state which variable is used). The detector's own
#: cutoff is 6.0 A; split at a chemically reasonable close-stacking
#: threshold. Ring-plane ANGLE is retained as metadata and is the
#: subject of a SEPARATE joint-geometry sensitivity variant (Geometry D
#: stress test), never silently folded into this primary bin.
_AROMATIC_CLOSE_MAX_A = 4.5

#: SS10.4 -- cation-pi, same coarse-distance logic as hydrophobic.
#: Detector cutoff is 6.0 A.
_CATION_PI_CLOSE_MAX_A = 4.5

#: SS10.2 -- charged contacts (SALT_BRIDGE / CHARGED_CONTACT_CANDIDATE).
#: Detector cutoff is 4.0 A.
_CHARGED_CLOSE_MAX_A = 3.2


#: Per-interaction-type (close_max_distance_a, close_bin, peripheral_bin)
#: dispatch table. One row per type with a defensible coarse split
#: (SS10.1-10.4); a type with no row falls through to NOT_APPLICABLE
#: (SS10.2's explicit fallback -- never invent a split for a type this
#: table doesn't document a chemical rationale for).
_GEOMETRY_DISPATCH: dict[InteractionType, tuple[float, GeometryBin, GeometryBin]] = {
    InteractionType.H_BOND: (
        _HBOND_OPTIMAL_MAX_A,
        GeometryBin.H_BOND_OPTIMAL_OR_STRONG,
        GeometryBin.H_BOND_LONG_OR_WEAK,
    ),
    InteractionType.HYDROPHOBIC_CONTACT: (
        _HYDROPHOBIC_CLOSE_MAX_A,
        GeometryBin.HYDROPHOBIC_CLOSE,
        GeometryBin.HYDROPHOBIC_PERIPHERAL,
    ),
    InteractionType.PI_PI: (
        _AROMATIC_CLOSE_MAX_A,
        GeometryBin.AROMATIC_FAVORABLE_CLOSE,
        GeometryBin.AROMATIC_WEAKER_PERIPHERAL,
    ),
    InteractionType.SALT_BRIDGE: (
        _CHARGED_CLOSE_MAX_A,
        GeometryBin.CHARGED_CLOSE,
        GeometryBin.CHARGED_PERIPHERAL,
    ),
    InteractionType.CHARGED_CONTACT_CANDIDATE: (
        _CHARGED_CLOSE_MAX_A,
        GeometryBin.CHARGED_CLOSE,
        GeometryBin.CHARGED_PERIPHERAL,
    ),
    InteractionType.CATION_PI: (
        _CATION_PI_CLOSE_MAX_A,
        GeometryBin.CATION_PI_CLOSE,
        GeometryBin.CATION_PI_PERIPHERAL,
    ),
}


def geometry_bin(interaction: AtomResidueInteraction) -> GeometryBin:
    """Coarse, chemically motivated, interaction-type-specific geometry bin.

    Distance-only for aromatic (documented, SS10.3); no bin invented for
    interaction types with no scientifically defensible coarse split
    (SS10.2's explicit fallback).
    """
    d = interaction.distance_angstrom
    row = _GEOMETRY_DISPATCH.get(interaction.interaction_type)
    if d is None or row is None:
        return GeometryBin.NOT_APPLICABLE
    close_max, close_bin, peripheral_bin = row
    return close_bin if d <= close_max else peripheral_bin


# ── Geometry-sensitivity ladder (frozen BEFORE any Rep3b/Rep3c result is
# computed) ------------------------------------------------------------------
#
# Boundaries are derived DETERMINISTICALLY from the already-committed
# coarse boundary above and each type's own detector outer cutoff -- no
# new number is chosen by inspecting results, and no boundary already
# committed for "coarse" is ever moved.
#
# Rule, frozen once, applied identically to every interaction type:
#   coarse (existing, 1 cutpoint):        close_max
#   intermediate (2 cutpoints):           close_max UNCHANGED, plus
#                                          midpoint(close_max, outer_cutoff)
#   fine (3 cutpoints):                   both intermediate cutpoints
#                                          UNCHANGED, plus
#                                          midpoint(0, close_max)
#
# Aromatic/pi-pi remains DISTANCE-ONLY at every rung of this ladder --
# ring-plane angle is deliberately NOT introduced here (that would be
# "opportunistic" per the mandate's own instruction); a joint
# distance x angle variant is a separate, explicitly deferred
# sensitivity check, never silently folded into this ladder.
_OUTER_CUTOFF_A: dict[InteractionType, float] = {
    InteractionType.H_BOND: 3.5,  # _HBOND_DA_CUTOFF_A in the detector
    InteractionType.HYDROPHOBIC_CONTACT: 4.5,  # _HYDROPHOBIC_CUTOFF_A
    InteractionType.PI_PI: 6.0,  # _PI_PI_CENTROID_CUTOFF_A
    InteractionType.CATION_PI: 6.0,  # _CATION_PI_CUTOFF_A
    InteractionType.SALT_BRIDGE: 4.0,  # _CHARGED_CONTACT_CUTOFF_A
    InteractionType.CHARGED_CONTACT_CANDIDATE: 4.0,
}

_COARSE_CLOSE_MAX_A: dict[InteractionType, float] = {
    InteractionType.H_BOND: _HBOND_OPTIMAL_MAX_A,
    InteractionType.HYDROPHOBIC_CONTACT: _HYDROPHOBIC_CLOSE_MAX_A,
    InteractionType.PI_PI: _AROMATIC_CLOSE_MAX_A,
    InteractionType.CATION_PI: _CATION_PI_CLOSE_MAX_A,
    InteractionType.SALT_BRIDGE: _CHARGED_CLOSE_MAX_A,
    InteractionType.CHARGED_CONTACT_CANDIDATE: _CHARGED_CLOSE_MAX_A,
}


def frozen_ladder_boundaries(interaction_type: InteractionType) -> dict[str, list[float]]:
    """Return the sorted interior cutpoints for each ladder rung.

    One interaction type at a time. Pure function of already-committed
    constants -- no free parameter, so this cannot be tuned after seeing
    a result.
    """
    close_max = _COARSE_CLOSE_MAX_A.get(interaction_type)
    outer = _OUTER_CUTOFF_A.get(interaction_type)
    if close_max is None or outer is None:
        return {"coarse": [], "intermediate": [], "fine": []}
    mid_peripheral = close_max + (outer - close_max) / 2
    mid_close = close_max / 2
    return {
        "coarse": [close_max],
        "intermediate": [close_max, mid_peripheral],
        "fine": [mid_close, close_max, mid_peripheral],
    }


def geometry_bin_at_resolution(interaction: AtomResidueInteraction, resolution: str) -> str:
    """Geometry bin at one of "coarse" / "intermediate" / "fine" ladder rungs.

    Uses `frozen_ladder_boundaries`'s deterministic cutpoints.

    Returns a self-describing string label
    "{interaction_type}__{resolution}__bin{i}of{n}" rather than a fixed
    enum member (the ladder has no principled reason to hand-name every
    intermediate/fine bin the way the original coarse bins were
    hand-named) -- deterministic, sortable, and traceable back to
    `frozen_ladder_boundaries` for the exact numeric range.
    """
    d = interaction.distance_angstrom
    itype = interaction.interaction_type
    boundaries: list[float] = frozen_ladder_boundaries(itype).get(resolution, [])
    if d is None or (not boundaries and itype not in _COARSE_CLOSE_MAX_A):
        return "not_applicable"
    n_bins = len(boundaries) + 1
    bin_index = sum(1 for b in boundaries if d > b)
    return f"{itype.value}__{resolution}__bin{bin_index}of{n_bins}"


def aggregate_representation_3_at_resolution(
    per_pose_interactions: list[list[AtomResidueInteraction]],
    ligand_moiety_by_atom_name: dict[str, LigandMoiety],
    canonical_position_lookup: dict[tuple[str, int], int | None],
    resolution: str,
) -> list[Representation3Occupancy]:
    """Representation 3 at a specified ladder resolution.

    "coarse" == identical output to `aggregate_representation_3`;
    "intermediate" / "fine" use `geometry_bin_at_resolution`'s finer,
    deterministically derived bins. Same occupancy/pooling discipline
    throughout.
    """
    n_poses = len(per_pose_interactions)
    counts: dict[Rep3Key, int] = defaultdict(int)
    residue_ids: dict[Rep3Key, set[str]] = defaultdict(set)
    canonical_positions: dict[Rep3Key, set[int]] = defaultdict(set)

    for pose_interactions in per_pose_interactions:
        seen_this_pose: set[Rep3Key] = set()
        for it in pose_interactions:
            moiety = ligand_moiety_by_atom_name.get(it.ligand_atom_name)
            if moiety is None:
                continue
            rfc = residue_functional_class(it)
            if rfc == ResidueFunctionalClass.UNRESOLVED_FUNCTIONAL_ROLE:
                continue
            gbin = geometry_bin_at_resolution(it, resolution)
            key: Rep3Key = (moiety.value, rfc.value, it.interaction_type.value, gbin)
            residue_ids[key].add(f"{it.residue_name}{it.residue_number}")
            canon = canonical_position_lookup.get((it.chain_id, it.residue_number))
            if canon is not None:
                canonical_positions[key].add(canon)
            if key in seen_this_pose:
                continue
            seen_this_pose.add(key)
            counts[key] += 1

    results = []
    for key, n_with in counts.items():
        moiety_val, rfc_val, itype_val, gbin_val = key
        occupancy = n_with / n_poses if n_poses > 0 else 0.0
        results.append(
            Representation3Occupancy(
                ligand_pharmacophore_class=moiety_val,
                residue_functional_class=rfc_val,
                interaction_type=itype_val,
                geometry_bin=gbin_val,
                n_poses_evaluated=n_poses,
                n_poses_with_interaction=n_with,
                occupancy=occupancy,
                occupancy_class=classify_occupancy(occupancy, n_poses),
                contributing_residue_identities=frozenset(residue_ids[key]),
                contributing_canonical_positions=frozenset(canonical_positions[key]),
            )
        )
    return sorted(
        results,
        key=lambda r: (
            r.ligand_pharmacophore_class,
            r.residue_functional_class,
            r.interaction_type,
            r.geometry_bin,
        ),
    )


#: Rep2Key: (ligand_pharmacophore_class, residue_functional_class, interaction_type).
#: Rep3Key: Rep2Key + (geometry_bin,).
Rep2Key = tuple[str, str, str]
Rep3Key = tuple[str, str, str, str]


@dataclass(frozen=True, slots=True)
class Representation2Occupancy:
    """Occupancy for one Representation-2 bin, aggregated across poses."""

    ligand_pharmacophore_class: str
    residue_functional_class: str
    interaction_type: str
    n_poses_evaluated: int
    n_poses_with_interaction: int
    occupancy: float
    occupancy_class: OccupancyClass
    #: Metadata only, per SS7/SS9 -- never part of the comparison key.
    contributing_residue_identities: frozenset[str]
    contributing_canonical_positions: frozenset[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ligand_pharmacophore_class": self.ligand_pharmacophore_class,
            "residue_functional_class": self.residue_functional_class,
            "interaction_type": self.interaction_type,
            "n_poses_evaluated": self.n_poses_evaluated,
            "n_poses_with_interaction": self.n_poses_with_interaction,
            "occupancy": self.occupancy,
            "occupancy_class": self.occupancy_class.value,
            "contributing_residue_identities": sorted(self.contributing_residue_identities),
            "contributing_canonical_positions": sorted(self.contributing_canonical_positions),
            "policy": REPRESENTATION_23_POLICY_ID,
        }


@dataclass(frozen=True, slots=True)
class Representation3Occupancy:
    """Occupancy for one Representation-3 bin (Rep 2 + geometry)."""

    ligand_pharmacophore_class: str
    residue_functional_class: str
    interaction_type: str
    geometry_bin: str
    n_poses_evaluated: int
    n_poses_with_interaction: int
    occupancy: float
    occupancy_class: OccupancyClass
    contributing_residue_identities: frozenset[str]
    contributing_canonical_positions: frozenset[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ligand_pharmacophore_class": self.ligand_pharmacophore_class,
            "residue_functional_class": self.residue_functional_class,
            "interaction_type": self.interaction_type,
            "geometry_bin": self.geometry_bin,
            "n_poses_evaluated": self.n_poses_evaluated,
            "n_poses_with_interaction": self.n_poses_with_interaction,
            "occupancy": self.occupancy,
            "occupancy_class": self.occupancy_class.value,
            "contributing_residue_identities": sorted(self.contributing_residue_identities),
            "contributing_canonical_positions": sorted(self.contributing_canonical_positions),
            "policy": REPRESENTATION_23_POLICY_ID,
        }


def aggregate_representation_2(
    per_pose_interactions: list[list[AtomResidueInteraction]],
    ligand_moiety_by_atom_name: dict[str, LigandMoiety],
    canonical_position_lookup: dict[tuple[str, int], int | None],
) -> list[Representation2Occupancy]:
    """Build Representation-2 occupancy records.

    `canonical_position_lookup[(chain_id, residue_number)]` supplies the
    canonical (alpha-referenced) position for provenance ONLY (SS7) --
    it plays no role in the comparison key (SS9's mandatory exclusion).
    A missing/None lookup entry is preserved as None metadata, never
    fabricated.

    Occupancy discipline (SS12): a bin counts at most once per pose,
    even when several ligand atoms, several residues, or several
    canonical positions all map to the same Rep2Key within one pose --
    this is the mandatory multi-position pooling behavior (SS16),
    tested explicitly in tests/features/test_representation_2_3.py.
    """
    n_poses = len(per_pose_interactions)
    counts: dict[Rep2Key, int] = defaultdict(int)
    residue_ids: dict[Rep2Key, set[str]] = defaultdict(set)
    canonical_positions: dict[Rep2Key, set[int]] = defaultdict(set)

    for pose_interactions in per_pose_interactions:
        seen_this_pose: set[Rep2Key] = set()
        for it in pose_interactions:
            moiety = ligand_moiety_by_atom_name.get(it.ligand_atom_name)
            if moiety is None:
                continue  # never fabricate a moiety for an unresolved ligand atom
            rfc = residue_functional_class(it)
            if rfc == ResidueFunctionalClass.UNRESOLVED_FUNCTIONAL_ROLE:
                continue  # never force an unresolved role into a comparative bin
            key: Rep2Key = (moiety.value, rfc.value, it.interaction_type.value)
            residue_ids[key].add(f"{it.residue_name}{it.residue_number}")
            canon = canonical_position_lookup.get((it.chain_id, it.residue_number))
            if canon is not None:
                canonical_positions[key].add(canon)
            if key in seen_this_pose:
                continue
            seen_this_pose.add(key)
            counts[key] += 1

    results = []
    for key, n_with in counts.items():
        moiety_val, rfc_val, itype_val = key
        occupancy = n_with / n_poses if n_poses > 0 else 0.0
        results.append(
            Representation2Occupancy(
                ligand_pharmacophore_class=moiety_val,
                residue_functional_class=rfc_val,
                interaction_type=itype_val,
                n_poses_evaluated=n_poses,
                n_poses_with_interaction=n_with,
                occupancy=occupancy,
                occupancy_class=classify_occupancy(occupancy, n_poses),
                contributing_residue_identities=frozenset(residue_ids[key]),
                contributing_canonical_positions=frozenset(canonical_positions[key]),
            )
        )
    return sorted(
        results,
        key=lambda r: (
            r.ligand_pharmacophore_class,
            r.residue_functional_class,
            r.interaction_type,
        ),
    )


def aggregate_representation_3(
    per_pose_interactions: list[list[AtomResidueInteraction]],
    ligand_moiety_by_atom_name: dict[str, LigandMoiety],
    canonical_position_lookup: dict[tuple[str, int], int | None],
) -> list[Representation3Occupancy]:
    """Representation 3: Representation 2's key plus the SS10 geometry bin.

    Same occupancy/pooling discipline as Representation 2.
    """
    n_poses = len(per_pose_interactions)
    counts: dict[Rep3Key, int] = defaultdict(int)
    residue_ids: dict[Rep3Key, set[str]] = defaultdict(set)
    canonical_positions: dict[Rep3Key, set[int]] = defaultdict(set)

    for pose_interactions in per_pose_interactions:
        seen_this_pose: set[Rep3Key] = set()
        for it in pose_interactions:
            moiety = ligand_moiety_by_atom_name.get(it.ligand_atom_name)
            if moiety is None:
                continue
            rfc = residue_functional_class(it)
            if rfc == ResidueFunctionalClass.UNRESOLVED_FUNCTIONAL_ROLE:
                continue
            gbin = geometry_bin(it)
            key: Rep3Key = (moiety.value, rfc.value, it.interaction_type.value, gbin.value)
            residue_ids[key].add(f"{it.residue_name}{it.residue_number}")
            canon = canonical_position_lookup.get((it.chain_id, it.residue_number))
            if canon is not None:
                canonical_positions[key].add(canon)
            if key in seen_this_pose:
                continue
            seen_this_pose.add(key)
            counts[key] += 1

    results = []
    for key, n_with in counts.items():
        moiety_val, rfc_val, itype_val, gbin_val = key
        occupancy = n_with / n_poses if n_poses > 0 else 0.0
        results.append(
            Representation3Occupancy(
                ligand_pharmacophore_class=moiety_val,
                residue_functional_class=rfc_val,
                interaction_type=itype_val,
                geometry_bin=gbin_val,
                n_poses_evaluated=n_poses,
                n_poses_with_interaction=n_with,
                occupancy=occupancy,
                occupancy_class=classify_occupancy(occupancy, n_poses),
                contributing_residue_identities=frozenset(residue_ids[key]),
                contributing_canonical_positions=frozenset(canonical_positions[key]),
            )
        )
    return sorted(
        results,
        key=lambda r: (
            r.ligand_pharmacophore_class,
            r.residue_functional_class,
            r.interaction_type,
            r.geometry_bin,
        ),
    )

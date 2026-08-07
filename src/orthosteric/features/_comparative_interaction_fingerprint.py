"""Compound x isoform comparative interaction fingerprints.

Objective: interaction-motif fingerprints workstream, sections 6-7. Ties
together occupancy (features._interaction_occupancy), residue
correspondence (pocket._sequence_correspondence), and ligand moiety
identity (features._ligand_moiety) into the comparative representation
this whole workstream exists to build:

    compound x isoform x residue x ligand-moiety x interaction-type
        -> occupancy, geometry statistics
    then, cross-isoform:
        conserved / alpha-favored / other-favored / lost

This module does NOT compute a reward or penalty score. It produces the
raw comparative feature vector the mandate explicitly asks for and stops
there (section 15's reward/penalty boundary).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from orthosteric.features._interaction_occupancy import InteractionOccupancy
from orthosteric.pocket._sequence_correspondence import CorrespondenceTable

FINGERPRINT_POLICY_ID = "comparative_interaction_fingerprint_v1"

#: Occupancy-difference threshold for calling an interaction
#: "isoform-favored" rather than merely "differential." ENGINEERING
#: CHOICE, documented, deterministic, not tuned on any experimental
#: selectivity label -- matches the same 0.4 granularity already used
#: for the RECURRENT occupancy threshold, for consistency, not because
#: it was fit to any outcome.
_FAVORED_OCCUPANCY_DELTA = 0.4
#: Below this, both isoforms' occupancy are close enough to call the
#: interaction conserved (non-selective structural compatibility).
_CONSERVED_OCCUPANCY_DELTA = 0.15

_ISOFORMS = ("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta")


class CrossIsoformPattern(StrEnum):
    CONSERVED = "conserved"  # present at similar occupancy across all isoforms with data
    ALPHA_FAVORED = "alpha_favored"  # substantially higher occupancy in alpha
    OTHER_FAVORED = "other_favored"  # substantially higher occupancy in a non-alpha isoform
    LOST = "lost"  # present (occupancy > 0) in one isoform, absent (0) in another
    DIFFERENTIAL_UNCLASSIFIED = (
        "differential_unclassified"  # differs, but not by enough to call favored/lost
    )


@dataclass(frozen=True, slots=True)
class CompoundIsoformFingerprint:
    """One compound's occupancy records for one isoform.

    Keyed by (interaction_type, canonical_residue_position or raw
    residue_number when no correspondence is available, ligand_atom_name).
    """

    compound_id: str
    isoform: str
    occupancies: tuple[InteractionOccupancy, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "compound_id": self.compound_id,
            "isoform": self.isoform,
            "occupancies": [o.to_dict() for o in self.occupancies],
        }


def _canonical_key(
    occ: InteractionOccupancy,
    isoform: str,
    reference_isoform: str,
    table: CorrespondenceTable | None,
) -> tuple[str, int | None, str]:
    """Key an occupancy record by interaction_type, canonical alpha position, and atom name.

    Uses the sequence-correspondence table when available. Returns
    canonical_position=None (never a fabricated guess) when no
    correspondence table was supplied or the residue has no mapped
    correspondence.
    """
    if table is None:
        return (occ.interaction_type, None, occ.ligand_atom_name)
    if isoform == reference_isoform:
        canon = occ.residue_number
    else:
        canon = None
        for rec in table.by_target_isoform.get(isoform, []):
            if rec.target_resnum == occ.residue_number:
                canon = rec.reference_resnum
                break
    return (occ.interaction_type, canon, occ.ligand_atom_name)


@dataclass(frozen=True, slots=True)
class ComparativeInteractionRecord:
    """One canonical (interaction_type, alpha-referenced position, atom) key.

    Tracks occupancy across all four isoforms, plus the derived
    cross-isoform pattern.
    """

    compound_id: str
    interaction_type: str
    canonical_position: int | None
    ligand_atom_name: str
    occupancy_by_isoform: dict[
        str, float
    ]  # isoform -> occupancy (0.0 if genuinely absent, not missing)
    pattern: CrossIsoformPattern

    def to_dict(self) -> dict[str, Any]:
        return {
            "compound_id": self.compound_id,
            "interaction_type": self.interaction_type,
            "canonical_position": self.canonical_position,
            "ligand_atom_name": self.ligand_atom_name,
            "occupancy_by_isoform": self.occupancy_by_isoform,
            "pattern": self.pattern.value,
        }


def _classify_pattern(occupancy_by_isoform: dict[str, float]) -> CrossIsoformPattern:
    present = {iso: occ for iso, occ in occupancy_by_isoform.items() if occ > 0}
    absent_isoforms = [iso for iso, occ in occupancy_by_isoform.items() if occ == 0]
    if present and absent_isoforms:
        return CrossIsoformPattern.LOST
    values = list(occupancy_by_isoform.values())
    spread = max(values) - min(values)
    if spread <= _CONSERVED_OCCUPANCY_DELTA:
        return CrossIsoformPattern.CONSERVED
    alpha_occ = occupancy_by_isoform.get("PI3Kalpha", 0.0)
    others = [occ for iso, occ in occupancy_by_isoform.items() if iso != "PI3Kalpha"]
    if others and alpha_occ - max(others) >= _FAVORED_OCCUPANCY_DELTA:
        return CrossIsoformPattern.ALPHA_FAVORED
    if others and max(others) - alpha_occ >= _FAVORED_OCCUPANCY_DELTA:
        return CrossIsoformPattern.OTHER_FAVORED
    return CrossIsoformPattern.DIFFERENTIAL_UNCLASSIFIED


def build_comparative_fingerprint(
    compound_id: str,
    fingerprints_by_isoform: dict[str, CompoundIsoformFingerprint],
    correspondence_table: CorrespondenceTable | None = None,
    reference_isoform: str = "PI3Kalpha",
) -> list[ComparativeInteractionRecord]:
    """Build the cross-isoform comparative record set for one compound.

    Every canonical key observed in ANY isoform's fingerprint gets a
    record; isoforms where that key was never observed get occupancy 0.0
    -- a REAL, DERIVED zero (the interaction genuinely did not occur in
    that isoform's evaluated poses), never a fabricated placeholder for
    missing data. This is distinct from a missing isoform (e.g. no
    receptor available), which is simply absent from
    `fingerprints_by_isoform` and produces no record contribution at all
    for that isoform -- callers must check `fingerprints_by_isoform.keys()`
    against `_ISOFORMS` to distinguish "genuinely zero" from "not evaluated."
    """
    all_keys: set[tuple[str, int | None, str]] = set()
    key_to_occ: dict[str, dict[tuple[str, int | None, str], float]] = {}

    for isoform, fp in fingerprints_by_isoform.items():
        key_to_occ[isoform] = {}
        for occ in fp.occupancies:
            key = _canonical_key(occ, isoform, reference_isoform, correspondence_table)
            all_keys.add(key)
            key_to_occ[isoform][key] = occ.occupancy

    records = []
    for key in sorted(all_keys, key=lambda k: (k[0], k[1] if k[1] is not None else -1, k[2])):
        interaction_type, canonical_position, ligand_atom_name = key
        occupancy_by_isoform = {
            isoform: key_to_occ.get(isoform, {}).get(key, 0.0)
            for isoform in fingerprints_by_isoform
        }
        records.append(
            ComparativeInteractionRecord(
                compound_id=compound_id,
                interaction_type=interaction_type,
                canonical_position=canonical_position,
                ligand_atom_name=ligand_atom_name,
                occupancy_by_isoform=occupancy_by_isoform,
                pattern=_classify_pattern(occupancy_by_isoform),
            )
        )
    return records

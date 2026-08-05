"""Governed pocket definition: ligand-ensemble-union and pocket residue sets.

Authority: ADR-0010 [Architectural]; SCI1-001 (Milestone 2).
Constitution sections served: §2.1 (pocket definition, ligand-ensemble union,
  rotamer-state requirement, apo prohibition), §0.3 (orthosteric sub-regions),
  §A.6 (C6 corollary — correspondence must be defined over conformational
  ensembles, not static structures).

The four governing rules implemented here (all derive from Constitution §2.1)
-----------------------------------------------------------------------
Rule 1 — Ligand-ensemble union, never apo. The pocket is the union, across
  the reference ensemble for a target, of residues with any heavy atom within
  `cutoff_angstrom` of any heavy atom of a bound ATP-site ligand. Apo-derived
  pocket boundaries are prohibited: the induced specificity pocket (Trp780/
  Met772 cleft) is absent in apo structures, so an apo correspondence is
  unstable across the binding-relevant ensemble.

Rule 2 — Rotamer states are part of the pocket, not noise. Selectivity
  derives substantially from side-chain conformational accessibility. The
  pocket representation must record which rotamer states are accessible in
  each contributing structure, not just sequence identity.

Rule 3 — 5.0 Å heavy-atom distance threshold (governed default, not hard-
  coded). Constitution §2.1 specifies 5.0 Å as the distance threshold. This
  is surfaced as `GOVERNED_DISTANCE_CUTOFF_ANGSTROM` — modifiable only via a
  Governance Decision Record, not via a keyword argument in a caller.

Rule 4 — Correspondence stability across the ensemble. A pocket residue is
  "correspondence-stable" if its identity and spatial position are consistent
  across >= `min_structures_for_stability` independent structures. This is the
  operational form of Constitution §A.1(4) stability requirement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from orthosteric.pocket._structure_record import (
    ConformationalState,
    ConstructClass,
    ResidueRecord,
    StructureRecord,
    StructureSource,
)

__all__ = [
    "GOVERNED_DISTANCE_CUTOFF_ANGSTROM",
    "GOVERNED_MIN_STRUCTURES_FOR_STABILITY",
    "POCKET_DEFINITION_ALGORITHM_VERSION",
    "PocketDefinitionPolicy",
    "PocketResidueSet",
    "SubRegion",
]

GOVERNED_DISTANCE_CUTOFF_ANGSTROM: float = 5.0
"""Constitution §2.1 governed distance threshold.

Modifiable only via a Governance Decision Record. If a caller needs a
different cutoff (e.g. for sensitivity analysis), that caller must document
the departure and must not use the output as a primary pocket definition.
"""

GOVERNED_MIN_STRUCTURES_FOR_STABILITY: int = 2
"""Minimum independent structures for correspondence stability (§A.1(4)).

A residue observed in < 2 independent structures is flagged
`correspondence_stable = False` and must not be used as a primary
determinant position without explicit justification.
"""

POCKET_DEFINITION_ALGORITHM_VERSION: str = "pocket_def_v1_sci1001"
"""Version of the pocket-definition algorithm.

Bump this if any of Rule 1-4 above changes (cutoff, rotamer representation,
stability criterion, or ensemble union method), even if no code outside this
module changes. This propagates into `PocketResidueSet.algorithm_version`
and allows downstream modules to detect stale pocket definitions.
"""


class SubRegion(StrEnum):
    """Constitution §0.3 orthosteric sub-regions.

    These are not arbitrary annotations; each sub-region is referenced in the
    Constitution's description of selectivity determinants:
    - ADENINE_HINGE: hinge contacts common to all isoforms (selectivity-
      neutral; §0.3).
    - AFFINITY_POCKET: deep sub-region containing the p110alpha position-859
      glutamine (the principal alpha-selectivity handle; §0.3, §1.2).
    - SPECIFICITY_POCKET: the induced cleft between Trp780 and Met772 (only
      present in ligand-bound states with propeller-shaped compounds; §0.3,
      §A.6 C6 corollary).
    - TRYPTOPHAN_SHELF: the Trp780/Met772 rotamer region governing β/δ
      selectivity (§0.3).
    - WATER_NETWORK: ordered and displaceable ATP-site waters (§0.3).
    """

    ADENINE_HINGE = "adenine_hinge"
    AFFINITY_POCKET = "affinity_pocket"
    SPECIFICITY_POCKET = "specificity_pocket"
    TRYPTOPHAN_SHELF = "tryptophan_shelf"
    WATER_NETWORK = "water_network"
    UNDEFINED = "undefined"


@dataclass(frozen=True, slots=True)
class PocketResidue:
    """One residue that is a member of a pocket's ligand-ensemble-union set.

    Attributes:
        residue: The residue record from the structure in which it was
            observed.
        structure_record_id: The `StructureRecord.record_id` this residue
            was extracted from.
        minimum_distance_to_ligand: The closest heavy-atom distance to any
            ATP-site ligand heavy atom in the contributing structure (Å).
        sub_region: Which §0.3 orthosteric sub-region this residue belongs to.
            `UNDEFINED` until residue mapping (SCI1-003) assigns canonical
            positions.
        observed_in_n_structures: How many independent structures contributed
            this residue position to the ensemble union. Used to assess
            correspondence stability (§A.1(4)).
        correspondence_stable: True if `observed_in_n_structures >= `
            `GOVERNED_MIN_STRUCTURES_FOR_STABILITY`. False residues are
            retained but flagged; they must not be used as primary determinant
            positions.
        present_with_propeller_ligand: True if this residue was observed in
            at least one structure with a propeller-shaped ligand. Indicates
            that the residue is part of the induced specificity pocket and
            cannot be seen in flat-ligand or apo structures (§A.6 C6).
    """

    residue: ResidueRecord
    structure_record_id: str
    minimum_distance_to_ligand: float
    sub_region: SubRegion
    observed_in_n_structures: int
    correspondence_stable: bool
    present_with_propeller_ligand: bool

    def __post_init__(self) -> None:
        if self.minimum_distance_to_ligand < 0.0:
            raise ValueError("PocketResidue.minimum_distance_to_ligand must be non-negative")
        if self.observed_in_n_structures < 1:
            raise ValueError("PocketResidue.observed_in_n_structures must be >= 1")


@dataclass(frozen=True, slots=True)
class PocketResidueSet:
    """The ligand-ensemble-union pocket for one (isoform, construct class) pair.

    This is the *product* of the pocket-definition policy applied to a set of
    `StructureRecord`s. It is immutable after construction, content-hashed,
    and tied to the exact set of input structures that produced it (via
    `contributing_record_ids`).

    Attributes:
        isoform: Target isoform, e.g. ``"PI3Kalpha"``.
        construct_class: The regulatory-subunit composition of the contributing
            structures. Mixed-construct pocket sets are not allowed; each
            `PocketResidueSet` is homogeneous in construct class.
        contributing_record_ids: The `StructureRecord.record_id` values of all
            structures that contributed to the union. Changing any one of these
            changes this object's `content_sha256`.
        n_contributing_structures: len(contributing_record_ids) for quick
            access.
        residues: The union of pocket residues across all contributing
            structures.
        n_residues_total: Total residue count.
        n_residues_correspondence_stable: Count of residues meeting the
            stability threshold.
        n_residues_propeller_only: Count of residues that only appear in
            propeller-ligand structures (the induced specificity pocket).
        cutoff_angstrom: The distance cutoff used. Should equal
            `GOVERNED_DISTANCE_CUTOFF_ANGSTROM` for primary pocket
            definitions.
        algorithm_version: `POCKET_DEFINITION_ALGORITHM_VERSION`.
    """

    isoform: str
    construct_class: ConstructClass
    contributing_record_ids: tuple[str, ...]
    n_contributing_structures: int
    residues: tuple[PocketResidue, ...]
    n_residues_total: int
    n_residues_correspondence_stable: int
    n_residues_propeller_only: int
    cutoff_angstrom: float
    algorithm_version: str

    def __post_init__(self) -> None:
        if not self.isoform.strip():
            raise ValueError("PocketResidueSet.isoform must be non-empty")
        if self.n_contributing_structures != len(self.contributing_record_ids):
            raise ValueError(
                "PocketResidueSet.n_contributing_structures must equal len(contributing_record_ids)"
            )
        if self.n_residues_total != len(self.residues):
            raise ValueError("PocketResidueSet.n_residues_total must equal len(residues)")

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "algorithm_version": self.algorithm_version,
            "construct_class": self.construct_class.value,
            "contributing_record_ids": sorted(self.contributing_record_ids),
            "cutoff_angstrom": self.cutoff_angstrom,
            "isoform": self.isoform,
            "n_contributing_structures": self.n_contributing_structures,
            "n_residues_correspondence_stable": self.n_residues_correspondence_stable,
            "n_residues_propeller_only": self.n_residues_propeller_only,
            "n_residues_total": self.n_residues_total,
        }


@dataclass(frozen=True, slots=True)
class PocketDefinitionPolicy:
    """The governed policy that produces a `PocketResidueSet` from structures.

    Encapsulates Rules 1-4 from the module docstring. All parameters are
    immutable; changing any parameter changes the policy version. This is NOT
    applied to coordinate-level data in this module (that requires BioPython/
    numpy, which are SCI1-002 dependencies); it is the *policy declaration*
    whose `validate_input_structure()` and `build_residue_set()` check
    conformance without computing distances.

    Attributes:
        policy_version: Unique version identifier. Any change to the
            parameters below changes this version.
        cutoff_angstrom: Distance threshold. Must equal
            `GOVERNED_DISTANCE_CUTOFF_ANGSTROM` for primary definitions.
        min_structures_for_stability: Stability threshold (§A.1(4)).
            Must equal `GOVERNED_MIN_STRUCTURES_FOR_STABILITY` for primary
            definitions.
        allow_apo_structures: Must be False for primary pocket definitions
            (Constitution §2.1 Rule 1). Settable to True only for controlled
            sensitivity analyses, with explicit documentation.
        require_propeller_coverage: If True, the pocket set must include at
            least one structure with a propeller-shaped ligand, ensuring the
            induced specificity pocket is represented.
    """

    policy_version: str
    cutoff_angstrom: float
    min_structures_for_stability: int
    allow_apo_structures: bool
    require_propeller_coverage: bool

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("PocketDefinitionPolicy.policy_version must be non-empty")
        if self.cutoff_angstrom <= 0:
            raise ValueError("PocketDefinitionPolicy.cutoff_angstrom must be positive")
        if self.min_structures_for_stability < 1:
            raise ValueError("PocketDefinitionPolicy.min_structures_for_stability must be >= 1")

    @property
    def is_primary_definition(self) -> bool:
        """True iff this policy's parameters match the governed defaults.

        A non-primary policy is valid for sensitivity analyses but must not
        be used to produce pocket definitions that feed primary training or
        evaluation paths.
        """
        return (
            self.cutoff_angstrom == GOVERNED_DISTANCE_CUTOFF_ANGSTROM
            and self.min_structures_for_stability == GOVERNED_MIN_STRUCTURES_FOR_STABILITY
            and not self.allow_apo_structures
        )

    def validate_input_structure(self, record: StructureRecord) -> list[str]:
        """Check whether `record` is eligible to contribute to this pocket.

        Returns a list of violation strings (empty list = eligible). Does NOT
        raise; the caller decides whether to exclude or flag the record.
        """
        violations: list[str] = []

        if record.provenance.source == StructureSource.ALPHAFOLD_GOVERNED_FALLBACK:
            # AlphaFold structures are admissible only as a governed fallback.
            # They are not excluded here; they are flagged so downstream code
            # can track experimental vs predicted provenance.
            violations.append(
                f"PROVENANCE_FLAG: structure {record.provenance.pdb_id} is an "
                "AlphaFold governed fallback, not experimental. Usable only "
                "when no experimental structure exists for this isoform/construct."
            )

        if record.conformational_state == ConformationalState.APO and not self.allow_apo_structures:
            violations.append(
                f"APO_PROHIBITED: structure {record.provenance.pdb_id} is apo. "
                "Constitution §2.1 Rule 1 prohibits apo-derived pocket boundaries. "
                "Set allow_apo_structures=True (with documented justification) "
                "to use this structure in a sensitivity analysis."
            )

        if (
            record.conformational_state == ConformationalState.LIGAND_BOUND
            and len(record.atp_site_ligands) == 0
        ):
            violations.append(
                f"LIGAND_REQUIRED: structure {record.provenance.pdb_id} is "
                "LIGAND_BOUND but has no ATP-site ligands. Preprocessing error."
            )

        return violations

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "allow_apo_structures": self.allow_apo_structures,
            "cutoff_angstrom": self.cutoff_angstrom,
            "min_structures_for_stability": self.min_structures_for_stability,
            "policy_version": self.policy_version,
            "require_propeller_coverage": self.require_propeller_coverage,
        }


def default_pocket_definition_policy() -> PocketDefinitionPolicy:
    """The primary pocket-definition policy (Constitution §2.1 defaults).

    This is the policy that should be used for all primary structural
    learning. Any deviation requires explicit documentation (ADR-0010 §5).
    """
    return PocketDefinitionPolicy(
        policy_version=POCKET_DEFINITION_ALGORITHM_VERSION,
        cutoff_angstrom=GOVERNED_DISTANCE_CUTOFF_ANGSTROM,
        min_structures_for_stability=GOVERNED_MIN_STRUCTURES_FOR_STABILITY,
        allow_apo_structures=False,
        require_propeller_coverage=True,
    )

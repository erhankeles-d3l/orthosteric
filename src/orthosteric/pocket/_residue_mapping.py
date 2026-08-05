"""Cross-isoform residue correspondence for the Tier 1 Class I PI3K ATP sites.

Authority: ADR-0010 [Architectural]; SCI1-003 (Milestone 4).
Constitution sections served: §2.1 (residue correspondence within Tier 1,
  α-859 and Trp780/Met772 positions explicitly named), §0.3 (orthosteric
  sub-regions), §A.1(1)–(4) (correspondence requirements), A.2 (structural
  correspondence required).

Scientific rule classification
--------------------------------
RULE_AVAILABLE:
  - "Structure-based alignment, not sequence-only" (Constitution §2.1).
    The requirement for structural alignment is explicit and unambiguous.
  - The three named anchor positions: α-859 (GLN), Trp780 (TRP), Met772
    (MET). These are stated explicitly in §0.3 and §2.1 and must be
    "explicitly recorded and manually verified."
  - The Tier 1 isoform set: PI3Kalpha, PI3Kbeta, PI3Kgamma, PI3Kdelta
    (Constitution §0.1).
  - `CorrespondenceStatus` vocabulary: MAPPED / UNMAPPED / PROVISIONAL /
    MANUALLY_VERIFIED. The Constitution's "manually verified" requirement
    implies a status distinction between computationally-proposed and
    human-reviewed correspondences.

RULE_MISSING / GOVERNANCE_DECISION_REQUIRED:
  - Structural superimposition algorithm. Constitution §2.1 requires
    "structure-based alignment" but does not name an algorithm (MUSTANG,
    TM-align, BioPython Superimposer, CE-Align, etc.). This is a genuine
    scientific methodology decision that requires an Auditor-sealed choice
    — per Constitution §2.1, alignment involves "manually verified"
    positions and the choice affects which residues are declared equivalent.
    `apply_structural_alignment()` is declared as an interface; no algorithm
    is executed here. A future GDR will name the algorithm and its
    parameters, at which point the function below will receive a real
    implementation.
  - Canonical position numbering scheme across isoforms: the Constitution
    uses p110α UniProt position numbers as the reference (e.g., "position
    859 in p110α"), but the cross-isoform mapping (what is "859-equivalent"
    in p110β) requires a structure-based alignment result. Provisional
    canonical positions are assigned by the caller, not invented here.

Design note
-----------
This module defines WHAT cross-isoform correspondence looks like (the data
model) and establishes the three Constitution-named anchor positions. HOW the
correspondence is computed (structural superimposition) is a deliberate RULE_
MISSING whose placeholder interface is declared here.

The `apply_correspondence_to_pocket_residue_set()` function accepts an
already-computed `ResidueCorrespondenceTable` and annotates the
`canonical_position` fields of pocket residues. It does not compute the
alignment itself — that computation requires a governed algorithm choice.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from orthosteric.pocket._pocket_definition import PocketResidueSet

__all__ = [
    "ALIGNMENT_ALGORITHM_RULE_MISSING_NOTE",
    "CORRESPONDENCE_TABLE_VERSION",
    "TIER1_ISOFORMS",
    "AnchorPosition",
    "CorrespondenceAssignment",
    "CorrespondenceStatus",
    "ResidueCorrespondenceTable",
    "annotate_pocket_residue_set",
    "make_anchor_assignments",
]

CORRESPONDENCE_TABLE_VERSION = "residue_correspondence_v1_sci1003"

ALIGNMENT_ALGORITHM_RULE_MISSING_NOTE = (
    "RULE_MISSING/GOVERNANCE_DECISION_REQUIRED: the structural superimposition "
    "algorithm for cross-isoform residue correspondence is not governed. "
    "Constitution §2.1 requires 'structure-based alignment, not sequence-only' "
    "and that the α-859-equivalent and Trp780/Met772-equivalent positions "
    "'must be explicitly recorded and manually verified'. The algorithm choice "
    "(MUSTANG, TM-align, CE-Align, BioPython Superimposer, etc.) requires an "
    "Auditor-sealed Governance Decision Record before automated correspondence "
    "computation can begin. Correspondence tables produced before that GDR is "
    "sealed must be flagged as PROVISIONAL and human-reviewed."
)

TIER1_ISOFORMS: frozenset[str] = frozenset({"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"})
"""The four Tier 1 Class I PI3K isoforms (Constitution §0.1)."""


class AnchorPosition(StrEnum):
    """Constitution-named anchor positions in the ATP-site pocket.

    These three positions are explicitly named in Constitution §0.3 and §2.1
    as selectivity-determining positions that "must be explicitly recorded
    and manually verified." They are the minimum set required for a
    scientifically valid correspondence; a mapping that does not assign
    canonical positions to all three is incomplete.

    ALPHA_859 (GLN in p110α): the principal α-selectivity handle — the
      affinity-pocket glutamine that differentiates p110α from the other
      paralogs (§0.3, §1.2).
    TRP780 (TRP): the tryptophan shelf governing β/δ selectivity; one jaw
      of the induced specificity pocket (§0.3, §A.6 C6).
    MET772 (MET): the methionine shelf; the other jaw of the induced
      specificity pocket (§0.3, §A.6 C6).
    """

    ALPHA_859 = "alpha_859"
    TRP780 = "trp780"
    MET772 = "met772"


class CorrespondenceStatus(StrEnum):
    """Status of one residue's cross-isoform canonical-position assignment.

    MAPPED: canonical position assigned by a governed structural alignment
      (i.e., a GDR has sealed the algorithm and the assignment was produced
      by it).
    PROVISIONAL: canonical position assigned by a pre-governance method (e.g.
      a preliminary sequence-based heuristic, or a human provisional call
      before manual verification is complete). Downstream determinant claims
      must not rest solely on PROVISIONAL assignments.
    MANUALLY_VERIFIED: canonical position independently verified by a human
      reviewer against the reference structure, per Constitution §2.1's
      explicit "manually verified" requirement. Highest reliability.
    UNMAPPED: no canonical position has been assigned; residue falls outside
      any governed correspondence.
    ANCHOR: one of the three Constitution-named anchor positions (AnchorPosition).
      Always MANUALLY_VERIFIED by definition — they are the reference.
    """

    MAPPED = "mapped"
    PROVISIONAL = "provisional"
    MANUALLY_VERIFIED = "manually_verified"
    UNMAPPED = "unmapped"
    ANCHOR = "anchor"


@dataclass(frozen=True, slots=True)
class CorrespondenceAssignment:
    """Cross-isoform canonical position for one residue in one structure.

    Attributes:
        residue_id:         `ResidueRecord.residue_id()` of the residue
                            being assigned.
        isoform:            Which Tier 1 isoform this residue belongs to.
        canonical_position: The cross-isoform canonical position number
                            (using p110α UniProt numbering as the reference).
                            ``None`` when `status == UNMAPPED`.
        status:             Reliability of the assignment.
        anchor_position:    If this residue is one of the three Constitution-
                            named anchors, which one. ``None`` otherwise.
        reference_isoform:  The isoform whose numbering is used as the
                            canonical reference (always "PI3Kalpha" per
                            Constitution §2.1).
        provenance_note:    How this assignment was produced (algorithm, manual
                            review, heuristic). Never empty for non-UNMAPPED.
    """

    residue_id: str
    isoform: str
    canonical_position: int | None
    status: CorrespondenceStatus
    anchor_position: AnchorPosition | None
    reference_isoform: str
    provenance_note: str

    def __post_init__(self) -> None:
        if self.status != CorrespondenceStatus.UNMAPPED and self.canonical_position is None:
            raise ValueError(
                f"CorrespondenceAssignment for {self.residue_id!r}: "
                f"canonical_position must not be None when status is {self.status}"
            )
        if self.status == CorrespondenceStatus.UNMAPPED and self.canonical_position is not None:
            raise ValueError(
                f"CorrespondenceAssignment for {self.residue_id!r}: "
                "canonical_position must be None when status is UNMAPPED"
            )
        if self.reference_isoform != "PI3Kalpha":
            raise ValueError(
                "CorrespondenceAssignment.reference_isoform must be 'PI3Kalpha' "
                "(Constitution §2.1: p110α UniProt position numbers are the reference). "
                f"Got: {self.reference_isoform!r}"
            )

    @property
    def is_anchor(self) -> bool:
        return self.anchor_position is not None

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "anchor_position": (self.anchor_position.value if self.anchor_position else None),
            "canonical_position": self.canonical_position,
            "isoform": self.isoform,
            "provenance_note": self.provenance_note,
            "reference_isoform": self.reference_isoform,
            "residue_id": self.residue_id,
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class ResidueCorrespondenceTable:
    """Cross-isoform correspondence table for a set of pocket residues.

    Produced by a governed structural alignment (or manually, per Constitution
    §2.1's "manually verified" requirement). Immutable after construction;
    content-hashed for traceability.

    When the alignment algorithm has not been governed yet (RULE_MISSING),
    a table may still be constructed with PROVISIONAL or MANUALLY_VERIFIED
    assignments — the Constitution explicitly allows human curation as a
    primary method for the named anchor positions.

    Attributes:
        table_version:      `CORRESPONDENCE_TABLE_VERSION`.
        alignment_algorithm: Name of the structural alignment algorithm used,
                             or ``"RULE_MISSING"`` when no governed algorithm
                             exists yet.
        alignment_governance_note: The algorithm RULE_MISSING note when
                             `alignment_algorithm == "RULE_MISSING"`.
        isoforms_covered:   The Tier 1 isoforms for which correspondence
                             was established.
        assignments:        All residue-level correspondence assignments.
        n_mapped:           Count with status MAPPED or MANUALLY_VERIFIED
                             or ANCHOR.
        n_provisional:      Count with status PROVISIONAL.
        n_unmapped:         Count with status UNMAPPED.
        anchor_positions_covered: Which AnchorPosition values have an
                             assignment with status ANCHOR or MANUALLY_VERIFIED.
        all_anchors_covered: True iff all three Constitution anchor positions
                             are in `anchor_positions_covered`.
    """

    table_version: str
    alignment_algorithm: str
    alignment_governance_note: str
    isoforms_covered: frozenset[str]
    assignments: tuple[CorrespondenceAssignment, ...]
    n_mapped: int
    n_provisional: int
    n_unmapped: int
    anchor_positions_covered: frozenset[str]
    all_anchors_covered: bool

    def __post_init__(self) -> None:
        expected_n = len(self.assignments)
        actual_n = self.n_mapped + self.n_provisional + self.n_unmapped
        if actual_n != expected_n:
            raise ValueError(
                f"ResidueCorrespondenceTable: n_mapped ({self.n_mapped}) + "
                f"n_provisional ({self.n_provisional}) + n_unmapped ({self.n_unmapped}) "
                f"= {actual_n}, but len(assignments) = {expected_n}"
            )

    def get_canonical_position(self, residue_id: str) -> CorrespondenceAssignment | None:
        """Look up the correspondence assignment for a residue by its id."""
        for a in self.assignments:
            if a.residue_id == residue_id:
                return a
        return None

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "alignment_algorithm": self.alignment_algorithm,
                "assignments": [
                    a.to_canonical_dict()
                    for a in sorted(
                        self.assignments,
                        key=lambda x: (x.isoform, x.residue_id),
                    )
                ],
                "isoforms_covered": sorted(self.isoforms_covered),
                "table_version": self.table_version,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "alignment_algorithm": self.alignment_algorithm,
            "alignment_governance_note": self.alignment_governance_note,
            "all_anchors_covered": self.all_anchors_covered,
            "anchor_positions_covered": sorted(self.anchor_positions_covered),
            "assignments": [a.to_canonical_dict() for a in self.assignments],
            "isoforms_covered": sorted(self.isoforms_covered),
            "n_mapped": self.n_mapped,
            "n_provisional": self.n_provisional,
            "n_unmapped": self.n_unmapped,
            "table_version": self.table_version,
        }


def make_anchor_assignments(
    isoform: str,
    alpha_859_residue_id: str,
    trp780_residue_id: str,
    met772_residue_id: str,
    provenance_note: str,
) -> tuple[CorrespondenceAssignment, ...]:
    """Construct the three Constitution-named anchor assignments for one isoform.

    These are the minimum required assignments. Constitution §2.1: "The
    α-859-equivalent and Trp780/Met772-equivalent positions must be
    explicitly recorded and manually verified."

    Parameters
    ----------
    isoform:
        One of the Tier 1 isoforms.
    alpha_859_residue_id:
        `ResidueRecord.residue_id()` of the residue in `isoform` equivalent
        to p110α position 859 (GLN in p110α, typically a different residue
        in the other paralogs).
    trp780_residue_id:
        `ResidueRecord.residue_id()` of the Trp780-equivalent residue
        (TRP in p110α; may differ in p110β/γ).
    met772_residue_id:
        `ResidueRecord.residue_id()` of the Met772-equivalent residue.
    provenance_note:
        How these assignments were established (manual curation, preliminary
        alignment, etc.).

    Returns:
    -------
    Tuple of three `CorrespondenceAssignment` objects (ANCHOR status).
    """
    return (
        CorrespondenceAssignment(
            residue_id=alpha_859_residue_id,
            isoform=isoform,
            canonical_position=859,
            status=CorrespondenceStatus.ANCHOR,
            anchor_position=AnchorPosition.ALPHA_859,
            reference_isoform="PI3Kalpha",
            provenance_note=provenance_note,
        ),
        CorrespondenceAssignment(
            residue_id=trp780_residue_id,
            isoform=isoform,
            canonical_position=780,
            status=CorrespondenceStatus.ANCHOR,
            anchor_position=AnchorPosition.TRP780,
            reference_isoform="PI3Kalpha",
            provenance_note=provenance_note,
        ),
        CorrespondenceAssignment(
            residue_id=met772_residue_id,
            isoform=isoform,
            canonical_position=772,
            status=CorrespondenceStatus.ANCHOR,
            anchor_position=AnchorPosition.MET772,
            reference_isoform="PI3Kalpha",
            provenance_note=provenance_note,
        ),
    )


def build_correspondence_table(
    assignments: list[CorrespondenceAssignment],
    isoforms_covered: frozenset[str],
    alignment_algorithm: str = "RULE_MISSING",
) -> ResidueCorrespondenceTable:
    """Construct a validated `ResidueCorrespondenceTable` from a list of assignments.

    Parameters
    ----------
    assignments:
        All cross-isoform assignments to include. Sorted internally for
        determinism; duplicates (same residue_id + isoform) raise an error.
    isoforms_covered:
        The set of Tier 1 isoforms for which correspondence was established.
    alignment_algorithm:
        Name of the structural alignment algorithm, or ``"RULE_MISSING"`` when
        the algorithm has not been governed yet.
    """
    # Check for duplicate (residue_id, isoform) pairs
    seen: set[tuple[str, str]] = set()
    for a in assignments:
        key = (a.residue_id, a.isoform)
        if key in seen:
            raise ValueError(
                f"Duplicate assignment for (residue_id={a.residue_id!r}, isoform={a.isoform!r})"
            )
        seen.add(key)

    # Counts
    reliable_statuses = {
        CorrespondenceStatus.MAPPED,
        CorrespondenceStatus.MANUALLY_VERIFIED,
        CorrespondenceStatus.ANCHOR,
    }
    n_mapped = sum(1 for a in assignments if a.status in reliable_statuses)
    n_provisional = sum(1 for a in assignments if a.status == CorrespondenceStatus.PROVISIONAL)
    n_unmapped = sum(1 for a in assignments if a.status == CorrespondenceStatus.UNMAPPED)

    # Which anchors are covered?
    anchor_positions_covered = frozenset(
        a.anchor_position.value
        for a in assignments
        if a.anchor_position is not None
        and a.status in (CorrespondenceStatus.ANCHOR, CorrespondenceStatus.MANUALLY_VERIFIED)
    )
    all_anchor_values = {ap.value for ap in AnchorPosition}
    all_anchors_covered = all_anchor_values <= anchor_positions_covered

    governance_note = (
        ALIGNMENT_ALGORITHM_RULE_MISSING_NOTE if alignment_algorithm == "RULE_MISSING" else ""
    )

    return ResidueCorrespondenceTable(
        table_version=CORRESPONDENCE_TABLE_VERSION,
        alignment_algorithm=alignment_algorithm,
        alignment_governance_note=governance_note,
        isoforms_covered=isoforms_covered,
        assignments=tuple(sorted(assignments, key=lambda a: (a.isoform, a.residue_id))),
        n_mapped=n_mapped,
        n_provisional=n_provisional,
        n_unmapped=n_unmapped,
        anchor_positions_covered=anchor_positions_covered,
        all_anchors_covered=all_anchors_covered,
    )


def annotate_pocket_residue_set(
    pocket_residue_set: PocketResidueSet,
    correspondence_table: ResidueCorrespondenceTable,
) -> list[tuple[str, int | None, CorrespondenceStatus]]:
    """Report canonical-position annotations for all pocket residues.

    Does NOT mutate the frozen `PocketResidueSet` or its `ResidueRecord`
    objects. Instead, returns a list of `(residue_id, canonical_position,
    status)` triples that callers can use to record or log assignments.

    The annotated `canonical_position` values should be stored on the
    `ResidueRecord` objects when building a new `PocketResidueSet` that
    incorporates correspondence information — this function does not produce
    that new set; it reports what the correspondence table says.

    Parameters
    ----------
    pocket_residue_set:
        The pocket whose residues will be looked up.
    correspondence_table:
        The correspondence table to query.

    Returns:
    -------
    List of ``(residue_id, canonical_position, status)`` tuples, one per
    pocket residue, sorted by residue_id for determinism.
    """
    results: list[tuple[str, int | None, CorrespondenceStatus]] = []
    for pocket_res in sorted(
        pocket_residue_set.residues,
        key=lambda pr: (pr.residue.chain_id, pr.residue.residue_seq),
    ):
        rid = pocket_res.residue.residue_id()
        assignment = correspondence_table.get_canonical_position(rid)
        if assignment is not None:
            results.append((rid, assignment.canonical_position, assignment.status))
        else:
            results.append((rid, None, CorrespondenceStatus.UNMAPPED))
    return results

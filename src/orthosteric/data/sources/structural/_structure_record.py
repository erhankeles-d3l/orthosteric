"""StructureRecord and ConstructDescriptor types.

Objective: SCI0-007.
Constitution §2.1: every structural record carries a full construct descriptor.

A StructureRecord references a ProvenanceRecord via provenance_id, consistent
with the ActivityRecord architecture (SCI0-003/004).  The two record types
can be co-indexed by provenance_id in the evidence graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID


class ActivationLoopState(StrEnum):
    """Activation-loop state of the kinase domain."""

    MODIFIED = "modified"  # phosphorylated or otherwise modified
    RESOLVED = "resolved"  # present and ordered
    DISORDERED = "disordered"  # present but disordered
    ABSENT = "absent"  # not modelled


@dataclass(frozen=True, slots=True)
class ConstructDescriptor:
    """Structured construct metadata for a PDB entry.

    Constitution §2.1: construct mismatches threaten correspondence stability
    under A.1(4).  Every field is explicit; absence is recorded as None,
    not inferred.

    Attributes:
        sequence_range_start:   First residue included (UniProt numbering).
        sequence_range_end:     Last residue included (UniProt numbering).
        engineered_mutations:   List of "posWT>Mut" strings, e.g. "C862S".
        fusion_tags:            Free-text description of tags/linkers.
        regulatory_subunit:     Regulatory subunit present, e.g. "p85alpha".
        activation_loop_state:  State of the activation loop.
        missing_residue_ranges: List of (start, end) ranges absent from model.
        short_loops_flagged:    Number of missing loops < 4 residues (flagged).
        long_loops_excluded:    Number of missing loops ≥ 4 residues (excluded).
        notes:                  Free-text notes from PDB REMARK or annotation.
    """

    sequence_range_start: int | None
    sequence_range_end: int | None
    engineered_mutations: tuple[str, ...] = ()
    fusion_tags: str | None = None
    regulatory_subunit: str | None = None
    activation_loop_state: ActivationLoopState = ActivationLoopState.RESOLVED
    missing_residue_ranges: tuple[tuple[int, int], ...] = ()
    short_loops_flagged: int = 0
    long_loops_excluded: int = 0
    notes: str | None = None


@dataclass
class StructureRecord:
    """A single experimental PDB structure with full provenance.

    Follows the same compositional architecture as ActivityRecord:
    references a ProvenanceRecord via provenance_id, enabling co-indexing
    in the evidence graph.

    The structure_source field distinguishes experimental from predicted
    structures — they must never be treated as equivalent evidence downstream.

    Attributes:
        structure_id:         Internal unique ID for this record.
        provenance_id:        Foreign key into the ProvenanceRecord.
        pdb_id:               4-character PDB identifier.
        isoform:              PI3K isoform this structure represents.
        uniprot_ac:           UniProt accession of the protein chain.
        resolution_angstrom:  Crystal/cryo-EM resolution. None if not applicable.
        experimental_method:  "X-RAY DIFFRACTION", "ELECTRON MICROSCOPY", etc.
        has_bound_ligand:     True if an ATP-site ligand is present.
        ligand_ids:           PDB ligand IDs present in the ATP site.
        construct:            Structured construct descriptor.
        structure_source:     EXPERIMENTAL_PDB or ALPHAFOLD_FALLBACK.
        source_selection_reason: Deterministic reason for source selection.
        admissibility:        Result of the §2.1 admissibility check.
        inadmissibility_reason: Set when inadmissible; None otherwise.
        deposition_date:      PDB deposition date (YYYY-MM-DD).
        release_date:         PDB release date (YYYY-MM-DD).
        organism:             Source organism.
        retrieval_timestamp:  When this record was fetched.
        source_version:       PDB data version or snapshot date.
        raw_payload:          Unmodified source API response.
    """

    structure_id: UUID
    provenance_id: UUID
    pdb_id: str
    isoform: str  # PI3KIsoform value
    uniprot_ac: str
    resolution_angstrom: float | None
    experimental_method: str | None
    has_bound_ligand: bool
    ligand_ids: list[str]
    construct: ConstructDescriptor
    structure_source: str  # StructureSource value
    source_selection_reason: str
    admissibility: str  # StructureAdmissibility value
    inadmissibility_reason: str | None
    deposition_date: str | None
    release_date: str | None
    organism: str | None
    retrieval_timestamp: str
    source_version: str
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def is_admissible(self) -> bool:
        """Return True only for structures that pass §2.1 admissibility."""
        return self.admissibility == "admissible"

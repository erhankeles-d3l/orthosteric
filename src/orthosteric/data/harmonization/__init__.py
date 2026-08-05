"""orthosteric.data.harmonization — record harmonization pipeline.

Objective: SCI0-008b onwards.
This package converts raw source records into harmonized corpus records.

SCI0-008  — Cheng–Prusoff IC50 → Ki (BLOCKED: AUDITOR-5 INSUFFICIENT_EVIDENCE)
SCI0-008b — Chemical standardization (this module)
SCI0-008c — Identifier harmonization
SCI0-009  — Duplicate and conflict resolution
SCI0-010  — Confidence scoring

Public API (SCI0-008b)
----------------------
Standardizer          :class:`ChemicalStandardizer`
Standardized record   :class:`StandardizedStructure`
"""

from orthosteric.data.harmonization._chem_standardizer import (
    ChemicalStandardizer,
    StandardizationStatus,
    StandardizedStructure,
)
from orthosteric.data.harmonization._confidence import (
    ConfidenceComponent,
    ConfidenceScorer,
    CurationConfidence,
    EvidenceContext,
)
from orthosteric.data.harmonization._deduplicator import (
    CompoundEvidenceMatrix,
    Deduplicator,
    EvidenceGroup,
    GroupConflictStatus,
)
from orthosteric.data.harmonization._deduplicator import (
    EvidenceRecord as DeduplicationRecord,
)
from orthosteric.data.harmonization._identifier_harmonizer import (
    ConflictStatus,
    HarmonizedCompound,
    IdentifierHarmonizer,
    SourceRef,
    StructureConflict,
)
from orthosteric.data.harmonization._scaffold import (
    SCAFFOLD_RULE_VERSION,
    ScaffoldAssigner,
    ScaffoldFamilyType,
    ScaffoldRecord,
    ScaffoldStatus,
    scaffold_family_report,
)

__all__ = [
    "SCAFFOLD_RULE_VERSION",
    "ChemicalStandardizer",
    "CompoundEvidenceMatrix",
    "ConfidenceComponent",
    "ConfidenceScorer",
    "ConflictStatus",
    "CurationConfidence",
    "DeduplicationRecord",
    "Deduplicator",
    "EvidenceContext",
    "EvidenceGroup",
    "GroupConflictStatus",
    "HarmonizedCompound",
    "IdentifierHarmonizer",
    "ScaffoldAssigner",
    "ScaffoldFamilyType",
    "ScaffoldRecord",
    "ScaffoldStatus",
    "SourceRef",
    "StandardizationStatus",
    "StandardizedStructure",
    "StructureConflict",
    "scaffold_family_report",
]

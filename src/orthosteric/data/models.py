"""orthosteric.data shared domain types.

Objective: SCI0-002 (enums and lightweight types); SCI0-003 adds
ActivityRecord and re-exports the canonical measurement types.

Architecture note (resolved at SCI0-003)
-----------------------------------------
Constitution §2.3(3) requires that biochemical and cellular selectivity
are separate targets, never pooled.  This is enforced at the type level
by keeping MeasurementType (IC50/Ki/Kd/EC50) and MeasurementClass
(biochemical/cellular) as separate enums.  The earlier collapsed
MeasurementKind enum is removed; downstream code must use the pair.
Both types are defined canonically in orthosteric.data.provenance.enums
and re-exported from here for convenience.

Engineering decision: DataTier (tier1/tier2) is kept alongside the
provenance Tier enum (tier_1/tier_2/tier_3) because they serve different
roles.  DataTier is the lightweight two-value form used in corpus/
adjudication code; Tier is the full provenance-schema enum.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

# Re-export canonical measurement types from the SCI0-003 provenance schema
from orthosteric.data.provenance.enums import MeasurementClass, MeasurementType

__all__ = [
    "ActivityRecord",
    "CensoringKind",
    "DataTier",
    "MeasurementClass",
    "MeasurementType",
    "RecordStatus",
    "SourceDB",
]


class DataTier(StrEnum):
    """Scope tier for a data record (Constitution §0.1).

    TIER1  — Class I PI3K orthosteric ATP pockets; primary learning scope.
    TIER2  — External validation panel; never enters a training path
             (Constitution §0.4, enforced by tier2_gate.py).
    """

    TIER1 = "tier1"
    TIER2 = "tier2"


class SourceDB(StrEnum):
    """Approved source databases for internal corpus keys (ADR-0003 §2).

    Uses lowercase keys for internal indexing.  The corresponding
    SourceType enum in orthosteric.data.provenance.enums uses the
    publication-standard names for provenance records.
    """

    CHEMBL = "chembl"
    BINDINGDB = "bindingdb"
    PUBCHEM = "pubchem"
    PDB = "pdb"
    LITERATURE = "literature"


class CensoringKind(StrEnum):
    """Censoring status for an activity value.

    Right-censored inactives are retained; they are never discarded or
    imputed to the threshold (Constitution §3.3).
    """

    EXACT = "exact"
    RIGHT_CENSORED = "right_censored"
    LEFT_CENSORED = "left_censored"


class RecordStatus(StrEnum):
    """Lifecycle status of a corpus record."""

    ACCEPTED = "accepted"
    EXCLUDED = "excluded"  # exclusion_reason must be populated
    AUXILIARY = "auxiliary"  # low-reliability; never primary training target


# ─────────────────────────────────────────────────────────────────────────────
# SCI0-003 — ActivityRecord
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ActivityRecord:
    """Single activity measurement with attached provenance.

    Links every measurement to a ProvenanceRecord via provenance_id.
    A measurement without provenance may not exist (Constitution §3.3).

    The value field uses Decimal (not float) so that content hashes are
    byte-reproducible across platforms (SCI0-003 writer rationale).

    Attributes:
        activity_id:       Globally unique identifier for this measurement.
        provenance_id:     Foreign key into the ProvenanceRecord.
        data_tier:         Scope tier (Constitution §0.1).
        value:             Activity measurement as Decimal.
        censoring:         Exact / right-censored / left-censored.
        measurement_type:  IC50 / Ki / Kd / EC50.
        measurement_class: Biochemical or cellular (never pooled, §2.3(3)).
        source_db:         Database of origin.
    """

    activity_id: UUID
    provenance_id: UUID
    data_tier: DataTier
    value: Decimal
    censoring: CensoringKind
    measurement_type: MeasurementType
    measurement_class: MeasurementClass
    source_db: SourceDB

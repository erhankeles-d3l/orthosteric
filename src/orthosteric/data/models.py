"""orthosteric.data shared domain types.

Objective: SCI0-002.
Provides the lightweight typed building blocks used across the data layer
before the full provenance schema (SCI0-003) is imported.

Design constraints
------------------
* No scientific constants, URLs, paths or numeric thresholds here (ENG §5).
* No descriptors or molecular features — those belong to ``features/`` at
  SCI-1 (Protocol §16; SCI0-001-refinement defect 3).
* No database or network calls.
"""

from __future__ import annotations

from enum import StrEnum


class DataTier(StrEnum):
    """Scope tier for a data record.

    Constitution §0.1 defines the three tiers.  Tier 2 is gated by
    ``tier2_gate.py``; Tier 3 is explicitly out of scope.
    """

    TIER1 = "tier1"  # Class I PI3K orthosteric ATP pockets — primary learning scope
    TIER2 = "tier2"  # External validation panel — never enters training


class SourceDB(StrEnum):
    """Approved source databases (ADR-0003 §2)."""

    CHEMBL = "chembl"
    BINDINGDB = "bindingdb"
    PUBCHEM = "pubchem"
    PDB = "pdb"
    LITERATURE = "literature"


class MeasurementKind(StrEnum):
    """Measurement quantity kind.

    EC50 is cellular only and is never pooled with biochemical quantities
    (SCI0-001-refinement defect 5; Constitution §2.3(3)).
    """

    IC50_BIOCHEMICAL = "IC50_biochemical"
    KI = "Ki"
    KD = "Kd"
    EC50_CELLULAR = "EC50_cellular"  # never pooled with biochemical


class CensoringKind(StrEnum):
    """Censoring status for an activity value.

    Right-censored inactives are retained; they are never discarded or
    imputed to the threshold (Constitution §3.3).
    """

    EXACT = "exact"
    RIGHT_CENSORED = "right_censored"  # > threshold
    LEFT_CENSORED = "left_censored"  # < threshold


class RecordStatus(StrEnum):
    """Lifecycle status of a corpus record."""

    ACCEPTED = "accepted"
    EXCLUDED = "excluded"  # exclusion_reason must be populated
    AUXILIARY = "auxiliary"  # low-reliability; never primary training target

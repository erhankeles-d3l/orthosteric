"""orthosteric.data.
================
Pre-ADR Empirical Evidence Acquisition and Computational Adjudication.

Implements the computational evidence-adjudication framework specified by
AMENDMENT-ADR-0003-COMPUTATIONAL-ADJUDICATION.

Governance boundary
-------------------
This package constructs a non-exhaustive empirical evidence corpus from
approved public sources (ADR-0003 §2), characterises it, and applies
deterministic decision procedures to derive the five ADR-0003 methodological
parameters.  It does NOT:
  - seal final thresholds without completing the full adjudication;
  - retrain or evaluate the selectivity model;
  - modify ADR-0003 substantive content;
  - silently alter a rule when new evidence is inconvenient.

Governance exceptions (INSUFFICIENT_EVIDENCE / GOVERNANCE_EXCEPTION) are
raised as structured exceptions rather than silently replaced with guesses.
"""

from orthosteric.data.adjudication import (
    AdjudicationResult,
    AdjudicationStatus,
    run_adr0003_adjudication,
)
from orthosteric.data.corpus import (
    CorpusSnapshot,
    EvidenceRecord,
    SnapshotManifest,
)

__all__ = [
    "AdjudicationResult",
    "AdjudicationStatus",
    "CorpusSnapshot",
    "EvidenceRecord",
    "SnapshotManifest",
    "run_adr0003_adjudication",
]

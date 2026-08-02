"""orthosteric.data package exceptions.

Objective: SCI0-002.
All domain exceptions for the data acquisition and adjudication layer.

Design rule: never raise a bare Exception in this package.  Raise a specific
subclass from this module so callers can discriminate without catching broadly.
"""

from __future__ import annotations


class OrthoDataError(Exception):
    """Base for all orthosteric.data errors."""


class ProvenanceError(OrthoDataError):
    """A record is missing required provenance fields."""


class TierViolationError(OrthoDataError):
    """A Tier 2 record attempted to enter a training path.

    Constitution §0.4: the Tier 2 information barrier is enforced in code,
    not only by policy.  This exception is raised by ``tier2_gate.py`` when
    a Tier 2 record is passed to a training-path component.
    """


class SnapshotIntegrityError(OrthoDataError):
    """A snapshot's content hash does not match its manifest."""


class GovernanceException(OrthoDataError):
    """Evidence falls outside a predefined adjudication rule.

    Per AMENDMENT-ADR-0003-COMPUTATIONAL-ADJUDICATION §7, the pipeline
    must stop the affected operation and raise this exception rather than
    silently modify a rule or invent a value.

    Attributes:
    ----------
    rule_id:
        Identifier of the rule that could not be satisfied.
    evidence_summary:
        Brief description of the evidence that triggered the exception.
    """

    def __init__(self, rule_id: str, evidence_summary: str) -> None:
        self.rule_id = rule_id
        self.evidence_summary = evidence_summary
        super().__init__(f"GOVERNANCE_EXCEPTION [{rule_id}]: {evidence_summary}")


class NormalizationError(OrthoDataError):
    """A record cannot be Cheng–Prusoff normalized.

    Raised when [ATP] or isoform Km is unknown and the record is required
    in the primary normalized target.  Per ADR-0003 §4, the record is then
    excluded from the primary target (but may be kept as low-reliability
    auxiliary evidence).
    """


class ConfigurationError(OrthoDataError):
    """An external configuration value is missing or invalid.

    Raised by ``config.py`` when a required environment variable or Hydra
    key is absent.  Never raised when a sensible default exists — only when
    the absence is unrecoverable.
    """

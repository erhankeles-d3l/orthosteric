"""Corpus lifecycle primitives — CurrentCorpus, CorpusDataMode, CorpusLifecycleStage.

This module formalises the distinction that the corpus lifecycle must never
collapse:

    Current Corpus  (updateable)
          |
          freeze
          |
          v
    Immutable Snapshot  (CorpusSnapshotV2)
          |
          CorpusProfile
          |
          CorpusQualityAssessment        <- quality/
          |
          GateDecision                   <- policy/
          |
          Eligible for Model Generation  <- learning/

Authority: SCI2-001 lifecycle requirements; ADR-0003; GDR-004.

Layer note
----------
This module is in ``data/`` (lowest importable layer). It may not import from
``quality/``, ``policy/``, ``eval/``, ``learning/``, or above.  The full
lifecycle pipeline (which must chain all four stages) lives in
``policy._lifecycle_pipeline``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from orthosteric.data.snapshots._builder import CorpusSnapshotV2, SnapshotBuilder

__all__ = [
    "CorpusDataMode",
    "CorpusLifecycleStage",
    "CurrentCorpus",
    "DataModeViolation",
]


# ── Data mode ------------------------------------------------------------------


class CorpusDataMode(StrEnum):
    """Mandatory classification preventing synthetic fixtures from contaminating
    the scientific training corpus.

    Every snapshot must carry a data mode.  Training interfaces MUST reject
    SYNTHETIC_FIXTURE and DEVELOPMENT_REAL modes at the model-generation
    registration boundary.

    SYNTHETIC_FIXTURE  — unit tests, pathological cases, deterministic fixtures.
                         NEVER enters scientific training.
    DEVELOPMENT_REAL   — small real sample from governed sources for integration
                         testing.  May be used to exercise the full pipeline but
                         MUST NOT be claimed as scientific training data.
    SCIENTIFIC_CORPUS  — full production corpus from governed external sources.
                         The only mode permitted for Model Generation creation
                         that claims scientific validity.
    """

    SYNTHETIC_FIXTURE = "synthetic_fixture"
    DEVELOPMENT_REAL = "development_real"
    SCIENTIFIC_CORPUS = "scientific_corpus"


# ── Lifecycle stage ------------------------------------------------------------


class CorpusLifecycleStage(StrEnum):
    """Stage marker for a corpus or snapshot in the acquisition-to-training pipeline.

    Stages are ordered: a snapshot must reach GATE_DECIDED_PROCEED before a
    Model Generation may be registered against it.  The policy layer enforces
    this ordering; this enum only names the stages.
    """

    CURRENT_CORPUS = "current_corpus"  # mutable; not trainable
    SNAPSHOT_FROZEN = "snapshot_frozen"  # immutable; not yet profiled
    PROFILE_COMPUTED = "profile_computed"  # CorpusProfile attached
    QUALITY_ASSESSED = "quality_assessed"  # CorpusQualityAssessment attached
    GATE_DECIDED_PROCEED = "gate_decided_proceed"  # eligible for training
    GATE_DECIDED_WARNING = "gate_decided_warning"  # eligible but flagged
    GATE_DECIDED_REDESIGN = "gate_decided_redesign"  # ineligible
    GATE_DECIDED_STOP = "gate_decided_stop"  # ineligible (fatal)
    MODEL_GENERATION_REGISTERED = "model_generation_registered"


# ── Error type -----------------------------------------------------------------


class DataModeViolation(ValueError):
    """Raised when an operation attempts to use data in a prohibited mode.

    Examples:
    - Training on SYNTHETIC_FIXTURE data.
    - Presenting DEVELOPMENT_REAL data as a scientific corpus snapshot.
    """


# ── CurrentCorpus --------------------------------------------------------------


@dataclass
class CurrentCorpus:
    """Updateable, mutable corpus layer sitting between raw source records and
    the immutable snapshot.

    INVARIANT: A ``CurrentCorpus`` instance is NEVER directly trainable.
    Only the ``CorpusSnapshotV2`` produced by ``freeze()`` may serve as a
    training input.

    ``CurrentCorpus`` is deliberately NOT frozen (unlike every downstream type).
    It is the one place in the pipeline where mutation is expected: new records
    arrive from sources, harmonization updates records, curation adds or removes
    them. Once ``freeze()`` is called, the snapshot is immutable and
    ``CurrentCorpus`` may continue accumulating records for the next freeze
    without affecting any previously produced snapshot.

    Attributes:
    ----------
    data_mode:
        Classification of the data in this corpus.  Enforced at freeze time.
    records:
        Serialised evidence records (list of dicts) accumulated so far.
        Never contains synthetic measurements when data_mode is SCIENTIFIC.
    source_metadata:
        ``{source_name: version_string}`` for each data source contributing
        to this corpus.
    created_at_utc:
        ISO-8601 UTC timestamp of corpus initialisation (provenance only).
    """

    data_mode: CorpusDataMode
    records: list[dict[str, Any]] = field(default_factory=list)
    source_metadata: dict[str, str] = field(default_factory=dict)
    created_at_utc: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )

    # ── Mutation (allowed here, nowhere else in the pipeline) ─────────────────

    def add_records(self, new_records: list[dict[str, Any]]) -> None:
        """Append records to the current corpus.

        Records must be serialisable dicts carrying full provenance.  Adding
        records after a previous ``freeze()`` call does NOT affect any
        snapshot produced before this call — each ``freeze()`` captures the
        corpus state at that instant.
        """
        self.records.extend(new_records)

    def update_source_version(self, source_name: str, version: str) -> None:
        """Record or update the version of a contributing source database."""
        self.source_metadata[source_name] = version

    # ── Inspection ────────────────────────────────────────────────────────────

    @property
    def record_count(self) -> int:
        return len(self.records)

    def validate_data_mode(self, expected: CorpusDataMode) -> None:
        """Raise DataModeViolation if mode does not match expected."""
        if self.data_mode != expected:
            msg = (
                f"DataModeViolation: expected {expected.value!r}, "
                f"got {self.data_mode.value!r}. "
                "Synthetic fixtures must not enter scientific training."
            )
            raise DataModeViolation(msg)

    # ── Snapshot production ────────────────────────────────────────────────────

    def freeze(
        self,
        builder: SnapshotBuilder,
        parent_snapshot_sha256: str | None = None,
    ) -> CorpusSnapshotV2:
        """Produce an immutable content-hashed snapshot of the current state.

        The resulting ``CorpusSnapshotV2`` is independent of this
        ``CurrentCorpus`` object.  Subsequent ``add_records()`` or
        ``update_source_version()`` calls will NOT affect the returned
        snapshot.

        Parameters
        ----------
        builder:
            Configured ``SnapshotBuilder`` carrying ``PolicyManifest`` and
            ``SoftwareProvenance`` for this freeze operation.
        parent_snapshot_sha256:
            SHA-256 of the immediately preceding snapshot, or ``None`` for a
            genesis snapshot.

        Returns:
        -------
        CorpusSnapshotV2
            Immutable, content-hashed snapshot.  Its SHA-256 identity encodes
            records + policy + software; the data mode is *not* part of the
            hash (it is governance metadata, not logical content).
        """
        return builder.build(
            activity_records=list(self.records),  # copy — not a reference
            structural_records=[],
            source_versions=dict(self.source_metadata),
            parent_sha256=parent_snapshot_sha256,
        )

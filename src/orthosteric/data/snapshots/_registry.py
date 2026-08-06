"""Corpus snapshot registry — track, index, and query known snapshots.

The registry answers: "Which snapshots exist, what mode are they, and which
have passed the quality gate?"  It does not store snapshot content — only
the identity and metadata needed for lifecycle tracking.

Authority: corpus-lifecycle requirements.

Layer note
----------
Pure ``data/`` types.  Imports from ``data.snapshots._builder`` via direct
import (not through ``data.snapshots.__init__``) to avoid circular
initialisation.  ``CorpusDataMode`` and ``CorpusLifecycleStage`` are
imported under ``TYPE_CHECKING`` only — the entry stores their `.value`
string at runtime.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orthosteric.data.corpus_lifecycle import CorpusDataMode, CorpusLifecycleStage
    from orthosteric.data.snapshots._builder import CorpusSnapshotV2

__all__ = [
    "CorpusSnapshotRegistry",
    "CorpusSnapshotRegistryEntry",
    "RegistryError",
]


class RegistryError(RuntimeError):
    """Raised for registry integrity violations."""


# ── Stage/mode string constants (mirrors CorpusLifecycleStage/DataMode values) ─

_ELIGIBLE_STAGES = frozenset(
    {
        "gate_decided_proceed",
        "gate_decided_warning",
        "model_generation_registered",
    }
)


@dataclass(frozen=True, slots=True)
class CorpusSnapshotRegistryEntry:
    """Metadata record for one snapshot in the registry.

    All mode/stage values are stored as plain strings (the `.value` of their
    respective StrEnum) to avoid a circular import at module initialisation
    time.  Callers that need the enum types should compare to ``.value``.
    """

    snapshot_sha: str
    snapshot_id: str
    parent_snapshot_sha: str | None
    data_mode: str  # CorpusDataMode.value
    lifecycle_stage: str  # CorpusLifecycleStage.value
    record_count: int
    accepted_count: int
    source_versions: dict[str, str]
    registered_at_utc: str
    model_generation_ids: tuple[str, ...] = ()

    @property
    def is_eligible_for_training(self) -> bool:
        """True iff the lifecycle stage indicates the gate decided PROCEED."""
        return self.lifecycle_stage in _ELIGIBLE_STAGES

    @property
    def is_scientific(self) -> bool:
        return self.data_mode == "scientific_corpus"

    def with_model_generation(self, model_generation_id: str) -> CorpusSnapshotRegistryEntry:
        return CorpusSnapshotRegistryEntry(
            snapshot_sha=self.snapshot_sha,
            snapshot_id=self.snapshot_id,
            parent_snapshot_sha=self.parent_snapshot_sha,
            data_mode=self.data_mode,
            lifecycle_stage="model_generation_registered",
            record_count=self.record_count,
            accepted_count=self.accepted_count,
            source_versions=dict(self.source_versions),
            registered_at_utc=self.registered_at_utc,
            model_generation_ids=(*self.model_generation_ids, model_generation_id),
        )

    def with_stage(self, new_stage: str | CorpusLifecycleStage) -> CorpusSnapshotRegistryEntry:
        """Return a new entry with an updated lifecycle stage (accepts str or enum)."""
        stage_val = new_stage if isinstance(new_stage, str) else new_stage.value
        return CorpusSnapshotRegistryEntry(
            snapshot_sha=self.snapshot_sha,
            snapshot_id=self.snapshot_id,
            parent_snapshot_sha=self.parent_snapshot_sha,
            data_mode=self.data_mode,
            lifecycle_stage=stage_val,
            record_count=self.record_count,
            accepted_count=self.accepted_count,
            source_versions=dict(self.source_versions),
            registered_at_utc=self.registered_at_utc,
            model_generation_ids=self.model_generation_ids,
        )


class CorpusSnapshotRegistry:
    """In-memory registry of known corpus snapshots."""

    def __init__(self) -> None:
        self._entries: dict[str, CorpusSnapshotRegistryEntry] = {}

    def register(
        self,
        snapshot: CorpusSnapshotV2,
        data_mode: CorpusDataMode,
    ) -> CorpusSnapshotRegistryEntry:
        sha = snapshot.manifest.snapshot_sha256
        if sha in self._entries:
            return self._entries[sha]
        entry = CorpusSnapshotRegistryEntry(
            snapshot_sha=sha,
            snapshot_id=snapshot.manifest.snapshot_id,
            parent_snapshot_sha=snapshot.manifest.parent_snapshot_sha256,
            data_mode=data_mode.value,
            lifecycle_stage="snapshot_frozen",
            record_count=snapshot.manifest.record_count,
            accepted_count=snapshot.manifest.accepted_count,
            source_versions=dict(snapshot.manifest.source_versions),
            registered_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self._entries[sha] = entry
        return entry

    def advance_stage(
        self,
        snapshot_sha: str,
        new_stage: str | CorpusLifecycleStage,
    ) -> CorpusSnapshotRegistryEntry:
        if snapshot_sha not in self._entries:
            msg = f"Snapshot {snapshot_sha[:16]}… not registered"
            raise RegistryError(msg)
        updated = self._entries[snapshot_sha].with_stage(new_stage)
        self._entries[snapshot_sha] = updated
        return updated

    def register_model_generation(
        self, snapshot_sha: str, model_generation_id: str
    ) -> CorpusSnapshotRegistryEntry:
        if snapshot_sha not in self._entries:
            msg = f"Snapshot {snapshot_sha[:16]}… not registered — cannot bind model generation"
            raise RegistryError(msg)
        updated = self._entries[snapshot_sha].with_model_generation(model_generation_id)
        self._entries[snapshot_sha] = updated
        return updated

    def get(self, snapshot_sha: str) -> CorpusSnapshotRegistryEntry | None:
        return self._entries.get(snapshot_sha)

    def is_known(self, snapshot_sha: str) -> bool:
        return snapshot_sha in self._entries

    def list_all(self) -> list[CorpusSnapshotRegistryEntry]:
        return list(self._entries.values())

    def list_eligible_for_training(self) -> list[CorpusSnapshotRegistryEntry]:
        return [e for e in self._entries.values() if e.is_eligible_for_training]

    def lineage(self, snapshot_sha: str) -> list[str]:
        chain: list[str] = []
        current: str | None = snapshot_sha
        seen: set[str] = set()
        while current is not None and current not in seen:
            entry = self._entries.get(current)
            if entry is None:
                break
            chain.append(current)
            seen.add(current)
            current = entry.parent_snapshot_sha
        chain.reverse()
        return chain

    def __len__(self) -> int:
        return len(self._entries)

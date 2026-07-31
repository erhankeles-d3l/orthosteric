"""Experiment record written before any run produces results.

Objective: FND-10.
Owner: ENG §6.

Scientific rationale:
    A run without a complete record is not an experiment and its outputs are not citable
    (ENG §6). The record is written *before* results so that a crashed or abandoned run
    leaves evidence of what was attempted rather than silence.

    Serialization is deterministic for the same reason as the provenance writer: run
    records contribute to reproducibility claims, and float repr varies across platforms.

Fields absent at Foundation:
    ``model_generation_hash``, ``data_snapshot_ids``, ``sealed_threshold_hash``,
    ``tier2_query_ref`` and ``tool_versions`` are Optional and remain ``None`` until the
    scientific states populate them. They are declared now because the schema enters
    reproducibility claims and is expensive to migrate (SI9 immutability).
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

__all__ = [
    "RunRecord",
    "SoftwareProvenance",
    "collect_software_provenance",
    "serialize_run_record",
    "write_run_record",
]

SCHEMA_VERSION = "1.0.0"
"""Run-record schema version. A change is a new version, never an in-place edit."""


def _git(*args: str) -> str | None:
    """Run a git command, returning stripped output or None if unavailable."""
    try:
        out = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = out.stdout.strip()
    return value or None


@dataclass(frozen=True, slots=True)
class SoftwareProvenance:
    """Toolchain identity for a run.

    The toolchain is part of a result's identity, not context: standardization libraries
    change canonicalisation between releases, so the same inputs can yield different
    outputs under a different version.
    """

    python_version: str
    platform: str
    git_sha: str | None
    git_dirty: bool
    dependency_lock_hash: str | None
    pipeline_version: str


def collect_software_provenance(pipeline_version: str) -> SoftwareProvenance:
    """Collect toolchain identity from the running environment.

    Args:
        pipeline_version: Version of the pipeline producing the run.

    Returns:
        A populated :class:`SoftwareProvenance`.
    """
    status = _git("status", "--porcelain")
    return SoftwareProvenance(
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        git_sha=_git("rev-parse", "HEAD"),
        git_dirty=bool(status),
        dependency_lock_hash=None,
        pipeline_version=pipeline_version,
    )


@dataclass(frozen=True, slots=True)
class RunRecord:
    """Complete identity of one run.

    Attributes:
        run_id: Unique identifier for the run.
        utc_started: Timezone-aware UTC start time.
        utc_finished: Completion time, or ``None`` while in progress.
        config_hash: Hash of the fully resolved configuration, not the template.
        seeds: Every stochastic component's seed, explicitly supplied.
        software: Toolchain identity.
        constitution_version: Governing Constitution version.
        adr_versions: ADRs in force for this run.
        phase: Committed Constitution phase, or ``None`` before commitment.
        lifecycle_stage: Engineering Standards §16 stage.
        model_generation_hash: Populated by the scientific states.
        data_snapshot_ids: Populated by the scientific states.
        sealed_threshold_hash: Populated when thresholds are consumed.
        tier2_query_ref: Log line reference if Tier 2 was accessed.
        tool_versions: Scientific tool versions, populated later.
        constituent_run_ids: Present only for manifest runs (ENG §6).
    """

    run_id: UUID
    utc_started: datetime
    utc_finished: datetime | None
    config_hash: str | None
    seeds: dict[str, int]
    software: SoftwareProvenance
    constitution_version: str
    adr_versions: tuple[str, ...]
    phase: str | None
    lifecycle_stage: str
    model_generation_hash: str | None = None
    data_snapshot_ids: tuple[str, ...] = ()
    sealed_threshold_hash: str | None = None
    tier2_query_ref: str | None = None
    tool_versions: dict[str, str] = field(default_factory=dict)
    constituent_run_ids: tuple[str, ...] = ()


def new_run_id() -> UUID:
    """Return a fresh run identifier."""
    return uuid4()


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


def _encode(obj: Any) -> Any:  # noqa: ANN401, PLR0911 - recursive encoder, one branch per type
    if obj is None or isinstance(obj, bool | int | str):
        return obj
    if isinstance(obj, float):
        msg = "float is prohibited in run records; use Decimal or str"
        raise TypeError(msg)
    if isinstance(obj, Decimal):
        return format(obj.normalize(), "f")
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            msg = "naive datetime is not serializable"
            raise TypeError(msg)
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _encode(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list | tuple):
        return [_encode(v) for v in obj]
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _encode(getattr(obj, f.name)) for f in fields(obj)}
    msg = f"unsupported type: {type(obj).__name__}"
    raise TypeError(msg)


def serialize_run_record(record: RunRecord) -> str:
    """Serialize a run record to canonical JSON.

    Args:
        record: The record to serialize.

    Returns:
        Canonical JSON with sorted keys, explicit nulls and no insignificant whitespace.
    """
    payload = {"schema_version": SCHEMA_VERSION, "run": _encode(record)}
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def write_run_record(record: RunRecord, runs_dir: Path) -> Path:
    """Write a run record to disk before results are produced.

    Args:
        record: The record to write.
        runs_dir: Directory holding run records, typically ``logs/runs``.

    Returns:
        Path of the written record.

    Raises:
        FileExistsError: If a record for this run already exists. Run records are
            append-only artefacts and are never overwritten (SI9).
    """
    runs_dir.mkdir(parents=True, exist_ok=True)
    target = runs_dir / f"{record.run_id}.json"
    if target.exists():
        msg = f"run record already exists and is immutable: {target}"
        raise FileExistsError(msg)
    target.write_text(serialize_run_record(record), encoding="utf-8")
    return target

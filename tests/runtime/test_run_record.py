"""Tests for the run record (FND-10)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from orthosteric.runtime.run_record import (
    RunRecord,
    SoftwareProvenance,
    collect_software_provenance,
    new_run_id,
    serialize_run_record,
    utc_now,
    write_run_record,
)


@pytest.fixture
def software() -> SoftwareProvenance:
    """Fixed toolchain identity."""
    return SoftwareProvenance(
        python_version="3.12.3",
        platform="Linux-test",
        git_sha="0" * 40,
        git_dirty=False,
        dependency_lock_hash=None,
        pipeline_version="0.1.0",
    )


@pytest.fixture
def record(software: SoftwareProvenance) -> RunRecord:
    """A minimal complete run record."""
    return RunRecord(
        run_id=new_run_id(),
        utc_started=datetime(2026, 7, 31, 9, 0, tzinfo=UTC),
        utc_finished=None,
        config_hash="abc123",
        seeds={"numpy": 0, "python": 1},
        software=software,
        constitution_version="4.6",
        adr_versions=("ADR-0001", "ADR-0004", "ADR-0005"),
        phase=None,
        lifecycle_stage="Research",
    )


def test_serialization_is_deterministic(record: RunRecord) -> None:
    """Identical records serialize to identical text."""
    assert serialize_run_record(record) == serialize_run_record(record)


def test_keys_are_sorted(record: RunRecord) -> None:
    """Key order is lexicographic, so insertion order cannot leak in."""
    payload = json.loads(serialize_run_record(record))
    assert list(payload) == sorted(payload)
    assert list(payload["run"]) == sorted(payload["run"])


def test_timestamp_carries_utc_offset(record: RunRecord) -> None:
    """Timestamps serialize with an explicit +00:00 offset."""
    payload = json.loads(serialize_run_record(record))
    assert payload["run"]["utc_started"].endswith("+00:00")


def test_scientific_fields_default_to_absent(record: RunRecord) -> None:
    """Fields owned by later states are declared but empty at Foundation."""
    assert record.model_generation_hash is None
    assert record.data_snapshot_ids == ()
    assert record.sealed_threshold_hash is None
    assert record.tier2_query_ref is None


def test_float_is_rejected(software: SoftwareProvenance) -> None:
    """A float anywhere in the record is refused; float repr varies across platforms."""
    bad = RunRecord(
        run_id=new_run_id(),
        utc_started=utc_now(),
        utc_finished=None,
        config_hash=None,
        seeds={"numpy": 0},
        software=software,
        constitution_version="4.6",
        adr_versions=(),
        phase=None,
        lifecycle_stage="Research",
        tool_versions={"bad": 1.0},  # type: ignore[dict-item]
    )
    with pytest.raises(TypeError, match="float is prohibited"):
        serialize_run_record(bad)


def test_write_then_rewrite_refused(record: RunRecord, tmp_path: Path) -> None:
    """A run record is immutable once written (SI9)."""
    written = write_run_record(record, tmp_path)
    assert written.exists()
    with pytest.raises(FileExistsError, match="immutable"):
        write_run_record(record, tmp_path)


def test_record_written_before_results(record: RunRecord, tmp_path: Path) -> None:
    """The record exists on disk while the run is still in progress."""
    write_run_record(record, tmp_path)
    payload = json.loads((tmp_path / f"{record.run_id}.json").read_text(encoding="utf-8"))
    assert payload["run"]["utc_finished"] is None


def test_collect_software_provenance_reports_python() -> None:
    """Toolchain collection reports the running interpreter."""
    prov = collect_software_provenance("0.1.0")
    assert prov.python_version.startswith("3.12")
    assert prov.pipeline_version == "0.1.0"

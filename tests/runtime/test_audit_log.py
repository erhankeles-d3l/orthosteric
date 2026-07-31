"""Tests for the scientific audit logger (FND-10)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from orthosteric.runtime.audit_log import LOGGER_NAME, AuditEvent, AuditEventType, log_audit_event


def _reset() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


def test_event_is_appended(tmp_path: Path) -> None:
    """An event lands in the audit stream as one JSON line."""
    _reset()
    event = AuditEvent(
        event_type=AuditEventType.SEAL_READ,
        run_id="run-1",
        detail={"artefact": "thresholds.json", "verified": True},
    )
    line = log_audit_event(event, tmp_path)
    _reset()
    written = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").strip()
    assert written == line
    assert json.loads(line)["event_type"] == "seal_read"


def test_stream_is_append_only(tmp_path: Path) -> None:
    """A second event appends rather than truncating."""
    _reset()
    for i in range(3):
        log_audit_event(
            AuditEvent(AuditEventType.RECORD_DROPPED, "run-1", {"reason": "no_atp", "n": i}),
            tmp_path,
        )
    _reset()
    lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3


def test_detail_keys_sorted(tmp_path: Path) -> None:
    """Detail keys are sorted so audit lines are byte-stable."""
    _reset()
    line = log_audit_event(
        AuditEvent(AuditEventType.AD_FLAG_FIRED, "run-1", {"z": 1, "a": 2}),
        tmp_path,
    )
    _reset()
    assert list(json.loads(line)["detail"]) == ["a", "z"]

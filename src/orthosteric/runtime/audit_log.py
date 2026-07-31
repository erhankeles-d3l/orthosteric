"""Scientific audit logging.

Objective: FND-10 (channel established), FND-4 (log tree).
Owner: ENG §8.

Scientific rationale:
    A separate named logger rather than a syslog level, because retention and
    immutability requirements differ from debug output. It records anything a reviewer
    would need to reconstruct why a number came out as it did: threshold applications,
    records dropped by filters and why, censored-data decisions, seal reads, Tier 2 gate
    invocations, applicability-domain flags, and every Indeterminate classification.

    Append-only. Rotation is by archiving, never truncation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum, unique
from pathlib import Path
from typing import Any

__all__ = ["AuditEvent", "AuditEventType", "audit_logger", "log_audit_event"]

LOGGER_NAME = "orthosteric.audit"


@unique
class AuditEventType(StrEnum):
    """Kinds of scientifically material event.

    Extended by later objectives; each addition names the Constitution section it serves.
    """

    THRESHOLD_APPLIED = "threshold_applied"
    RECORD_DROPPED = "record_dropped"
    CENSORED_HANDLED = "censored_handled"
    SEAL_READ = "seal_read"
    TIER2_GATE_INVOKED = "tier2_gate_invoked"
    AD_FLAG_FIRED = "applicability_domain_flag_fired"
    INDETERMINATE_EMITTED = "indeterminate_emitted"
    RUN_STARTED = "run_started"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """One scientifically material event.

    Attributes:
        event_type: What happened.
        run_id: Run during which it happened.
        detail: Structured context. Values must be JSON-encodable and must not include
            floats, so that audit lines are byte-stable.
    """

    event_type: AuditEventType
    run_id: str
    detail: dict[str, str | int | bool | None]


def audit_logger(audit_dir: Path) -> logging.Logger:
    """Return the append-only audit logger, configuring it once.

    Args:
        audit_dir: Directory for audit output, typically ``logs/audit``.

    Returns:
        The configured logger. Repeated calls do not add duplicate handlers.
    """
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger
    audit_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(audit_dir / "audit.jsonl", mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def log_audit_event(event: AuditEvent, audit_dir: Path) -> str:
    """Append one event to the audit stream.

    Args:
        event: The event to record.
        audit_dir: Directory for audit output.

    Returns:
        The JSON line written, for test assertion.
    """
    payload: dict[str, Any] = {
        "utc": datetime.now(UTC).isoformat(),
        "event_type": event.event_type.value,
        "run_id": event.run_id,
        "detail": dict(sorted(event.detail.items())),
    }
    line = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    audit_logger(audit_dir).info(line)
    return line

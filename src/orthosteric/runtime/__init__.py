"""Runtime infrastructure: run identity, experiment records, scientific audit logging.

Objective: FND-10 (Foundation first production module, per ADR-0004).
Owner: ENG §6 (experiment record), ENG §8 (audit logging).

This package holds no domain schema and no scientific logic. It exists so that every run
records what produced it *before* producing results, which ENG §6 requires and without
which a result is not citable.
"""

from __future__ import annotations

from .audit_log import AuditEvent, AuditEventType, audit_logger, log_audit_event
from .config import (
    ConfigurationError,
    SealedConfigError,
    SealedThresholds,
    load_sealed_thresholds,
    resolved_config_hash,
)
from .run_record import RunRecord, SoftwareProvenance, serialize_run_record, write_run_record

__all__ = [
    "AuditEvent",
    "AuditEventType",
    "ConfigurationError",
    "RunRecord",
    "SealedConfigError",
    "SealedThresholds",
    "SoftwareProvenance",
    "audit_logger",
    "load_sealed_thresholds",
    "log_audit_event",
    "resolved_config_hash",
    "serialize_run_record",
    "write_run_record",
]

"""Sealed retrospective-validation label barrier.

Objective: Rev. 5 computational-only mandate, SS0.6.3 / SS1 / SS12.
Modeled directly on `data/tier2_gate.py`'s existing, working pattern for
the Tier-2 information barrier -- same shape, same discipline, applied
to a different sealed set.

The Rev. 5 mandate seals a retrospective validation subset of A4 (SS1)
and a literature reference panel (SS2), and requires that neither be
read by any label-blinded discovery-phase code (SS5-SS11: corpus
assembly, motif enumeration, eligibility, permutation nulls,
generalization) before the one-time unblinding event at SS12.

Two physically separate artifacts exist:
  - sealed_validation_structures.json (compound_id, SMILES, isoform
    panel identifiers) -- lives under data/structural_evidence/, freely
    readable by discovery-phase code, since it needs structures to dock.
  - sealed_validation_labels.json (compound_id, pAct per isoform,
    selectivity stratum) -- lives under data/sealed/, reachable ONLY
    through this module's load_sealed_labels_for_unblinding().

The barrier is enforced two ways: (1) in code, via the guard function
below, and (2) in import structure, via `.importlinter` Contract 5,
which forbids `orthosteric.discovery` from importing this module AT
ALL. A discovery-phase module that needs this module imported is
already a violation before it ever calls anything in it -- including
calling the legitimate loading function, which exists for the SS12
unblinding event alone.

Every read of the sealed labels, wherever legitimately permitted (SS12
unblinding only), is logged via
`runtime.audit_log.AuditEventType.SEAL_READ` -- that event type already
exists and is reused here, not reinvented. Signature verified directly
against the real audit_log module before use, not assumed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orthosteric.runtime.audit_log import AuditEvent, AuditEventType, log_audit_event

_REPO_ROOT = Path("/home/ubuntu/Documents/orthosteric")
_SEALED_LABELS_PATH = _REPO_ROOT / "data" / "sealed" / "sealed_validation_labels.json"
_AUDIT_DIR = _REPO_ROOT / "data" / "audit"


class SealedLabelViolationError(Exception):
    """Raised when a sealed retrospective label reaches discovery-phase code."""


def assert_not_discovery_phase(context: str = "") -> None:
    """Raise ``SealedLabelViolationError`` unconditionally.

    Call this at the single legitimate entry point for reading a sealed
    label (SS12 unblinding) is NOT what this guards -- this guards the
    *discovery-phase* call sites, which must never reach here at all.
    Any call to this function from SS5-SS11 code is itself the
    violation; the function's only job is to make that failure loud
    and immediate rather than a silently wrong number downstream.

    Parameters
    ----------
    context:
        Optional caller description included in the error message for
        easier tracing in logs.
    """
    ctx = f" (context: {context})" if context else ""
    raise SealedLabelViolationError(
        f"A sealed retrospective label was reached from a call site that "
        f"must not have access to it{ctx}. Rev. 5 SS1/SS2/SS12: sealed "
        "labels may only be read once, at the SS12 unblinding event, and "
        "every read must be logged via AuditEventType.SEAL_READ. Check "
        "the call site -- this function existing on the call stack at "
        "all is the violation, independent of its return value."
    )


def load_sealed_labels_for_unblinding(
    unblinding_context: str, model_generation_hash: str, run_id: str
) -> dict[str, Any]:
    """Load the sealed validation labels. SS12 ONLY -- one-time event.

    This is a real, working loader, not a stub -- but it is only
    reachable at all by code that is permitted to import this module,
    which Contract 5 (.importlinter) guarantees excludes every
    discovery-phase module. Calling this from anywhere other than the
    single SS12 unblinding step is a governance violation even though
    the import barrier does not block it structurally within
    non-discovery code -- the barrier here is the audit log record,
    which makes every call visible and dated, not silent.

    Parameters
    ----------
    unblinding_context:
        Free-text description of what is being tested (e.g. "SS12
        baseline ladder, B7 vs B2, frozen signature hash ...").
    model_generation_hash:
        The frozen B7 definition hash (SS11.5), or another appropriate
        frozen-artifact hash, logged so this call can be tied to a
        specific, already-frozen decision rather than an ad hoc query.
    run_id:
        Identifier for this unblinding run, per AuditEvent's schema.
    """
    log_audit_event(
        AuditEvent(
            event_type=AuditEventType.SEAL_READ,
            run_id=run_id,
            detail={
                "artifact": "sealed_validation_labels",
                "unblinding_context": unblinding_context,
                "model_generation_hash": model_generation_hash,
            },
        ),
        audit_dir=_AUDIT_DIR,
    )
    loaded: dict[str, Any] = json.loads(_SEALED_LABELS_PATH.read_text())
    return loaded

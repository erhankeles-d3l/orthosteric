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

This module provides a single guard function that raises
``SealedLabelViolationError`` if a sealed label is passed to any
discovery-phase component. It is invoked at the boundary between
sealing (SS1/SS2) and discovery (SS5-SS11).

The barrier is *not* a policy document -- it is enforced in code, and
additionally in import structure via `.importlinter` Contract 5, which
forbids `orthosteric.discovery` from importing this module at all. A
discovery-phase module that needs this module imported is already a
violation before it ever calls anything in it.

Every read of a sealed label, wherever legitimately permitted (SS12
unblinding only), must be logged via
`runtime.audit_log.AuditEventType.SEAL_READ` -- that event type already
exists and is reused here, not reinvented.
"""

from __future__ import annotations


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

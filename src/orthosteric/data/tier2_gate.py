"""Tier 2 information barrier.

Objective: SCI0-002 (FND-4 wrote the empty gate; this populates it for data/).
Constitution §0.4: Tier 2 data may never enter training, pre-training,
fine-tuning, hyperparameter search, model selection, early stopping, feature
engineering, threshold setting, or any decision shaping the model.

This module provides a single guard function that raises ``TierViolationError``
if a Tier 2 record is passed to any training-path component.  It is invoked at
the boundary between data acquisition (SCI0) and modelling (SCI1+).

The gate is *not* a policy document — it is enforced in code.
"""

from __future__ import annotations

from orthosteric.data.exceptions import TierViolationError
from orthosteric.data.models import DataTier


def assert_tier1(tier: DataTier, context: str = "") -> None:
    """Raise ``TierViolationError`` unless *tier* is ``DataTier.TIER1``.

    Parameters
    ----------
    tier:
        The tier of the record or batch being checked.
    context:
        Optional caller description included in the error message for
        easier tracing in logs.
    """
    if tier != DataTier.TIER1:
        ctx = f" (context: {context})" if context else ""
        raise TierViolationError(
            f"Tier 2 record reached a training-path component{ctx}. "
            "Constitution §0.4: Tier 2 records are read-only and may only be "
            "evaluated, never trained on.  Check the call site."
        )

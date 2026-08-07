"""Tests for data.sealed_labels -- the Rev. 5 sealed-label barrier.

Modeled on the existing tier2_gate test pattern. Exit criteria:
  (1) The guard always raises, unconditionally -- reaching it at all is
      the violation, independent of any value.
  (2) The error message identifies itself clearly enough to trace the
      call site (context string included when given).
  (3) The import-linter barrier (Contract 5) is a SEPARATE, independent
      layer of protection -- this module's own tests do not substitute
      for verifying the contract fires (that was done directly via
      import-linter in the Stage A audit, not via pytest).
"""

from __future__ import annotations

import pytest

from orthosteric.data.sealed_labels import SealedLabelViolationError, assert_not_discovery_phase


def test_assert_not_discovery_phase_always_raises() -> None:
    with pytest.raises(SealedLabelViolationError):
        assert_not_discovery_phase()


def test_context_included_in_error_message() -> None:
    with pytest.raises(SealedLabelViolationError, match="motif_eligibility_check"):
        assert_not_discovery_phase(context="motif_eligibility_check")


def test_no_context_still_raises_with_generic_message() -> None:
    with pytest.raises(SealedLabelViolationError, match=r"Rev\. 5"):
        assert_not_discovery_phase()

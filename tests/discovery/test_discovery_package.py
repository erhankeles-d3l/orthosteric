"""Tests for the label-blinded discovery package (Rev. 5 SS5-SS11).

The package itself is intentionally empty pending Stage E execution --
it exists now so that `.importlinter` Contract 5 protects it from its
first real module onward, rather than being bolted on reactively after
discovery code already exists.

These tests assert the property that makes the package meaningful: that
it does NOT reach the sealed retrospective labels. Contract 5 enforces
this structurally in the import graph; this asserts it at runtime as an
independent second layer, so a future refactor that somehow satisfies
the import graph while still pulling the module in is still caught.
"""

from __future__ import annotations

import sys


def test_discovery_package_imports_cleanly() -> None:
    import orthosteric.discovery  # noqa: PLC0415

    assert orthosteric.discovery is not None


def test_discovery_import_does_not_pull_in_sealed_labels() -> None:
    """Importing the discovery package must not transitively import the
    sealed-label module -- the runtime counterpart to Contract 5 (SS0.6.3)."""
    for mod in ("orthosteric.discovery", "orthosteric.data.sealed_labels"):
        sys.modules.pop(mod, None)

    import orthosteric.discovery  # noqa: F401, PLC0415

    assert "orthosteric.data.sealed_labels" not in sys.modules, (
        "orthosteric.discovery transitively imported the sealed-label module -- "
        "Rev. 5 SS0.6.3 forbids any discovery-phase path from reaching sealed labels."
    )

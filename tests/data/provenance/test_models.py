"""Construction and immutability tests for provenance models (SCI0-003)."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from orthosteric.data.provenance import (
    ProvenanceRecord,
    Quantity,
    SourceMetadata,
    SourceType,
    Tier,
    Unit,
)
from orthosteric.data.provenance.enums import LicenseType


def test_record_constructs(record: ProvenanceRecord) -> None:
    """A complete record constructs and exposes its parts."""
    assert record.source.tier is Tier.TIER_1
    assert record.assay.target == "PI3K p110alpha"


@pytest.mark.parametrize(
    "obj_name",
    ["source", "publication", "assay", "extraction", "record"],
)
def test_frozen_rejects_mutation(obj_name: str, request: pytest.FixtureRequest) -> None:
    """Every provenance dataclass is frozen (SI9, CLAUDE.md §8)."""
    obj: Any = request.getfixturevalue(obj_name)
    field_name = dataclasses.fields(obj)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(obj, field_name, None)


def test_tier_has_no_default() -> None:
    """``tier`` is mandatory and non-defaultable.

    A default would silently mark Tier 2 data as Tier 1 and defeat the Constitution
    §0.4 barrier at the point it originates.
    """
    tier_field = next(f for f in dataclasses.fields(SourceMetadata) if f.name == "tier")
    assert tier_field.default is dataclasses.MISSING
    assert tier_field.default_factory is dataclasses.MISSING

    with pytest.raises(TypeError):
        SourceMetadata(  # type: ignore[call-arg]
            source_type=SourceType.CHEMBL,
            accession="X",
            source_version="1",
            downloaded_utc=datetime(2026, 1, 1, tzinfo=UTC),
            license=LicenseType.UNKNOWN,
            tdm_permission=None,
        )


def test_record_has_no_snapshot_reference() -> None:
    """Records never reference a snapshot.

    A snapshot hash is computed over its records, so the reverse reference would be
    circular. Direction is manifest -> record.
    """
    names = {f.name for f in dataclasses.fields(ProvenanceRecord)}
    assert not {n for n in names if "snapshot" in n}


def test_quantity_requires_unit() -> None:
    """A concentration cannot be constructed without a unit."""
    with pytest.raises(TypeError):
        Quantity(value=Decimal("10"))  # type: ignore[call-arg]


def test_quantity_equality_ignores_trailing_zeros() -> None:
    """Decimal equality means 10 and 10.0 are the same quantity."""
    assert Quantity(Decimal("10"), Unit.MICROMOLAR) == Quantity(Decimal("10.0"), Unit.MICROMOLAR)

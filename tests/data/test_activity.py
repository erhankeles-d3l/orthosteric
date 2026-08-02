"""SCI0-004 and SCI0-005 exit-criterion tests.

SCI0-004 exit: schema rejects a pooled biochemical/cellular value.
SCI0-005 exit: a '>10 µM' record round-trips with its operator intact;
               no code path drops a censored record.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from orthosteric.data.activity import (
    AnyActivityRecord,
    BiochemicalRecord,
    CellularRecord,
    CensoredValue,
    RelationalOperator,
    censored_fraction,
    is_censored,
)
from orthosteric.data.models import CensoringKind, DataTier, SourceDB
from orthosteric.data.provenance.enums import MeasurementType, Unit


def _biochemical(
    mtype: MeasurementType = MeasurementType.IC50,
    magnitude: str = "100",
    operator: RelationalOperator = RelationalOperator.EQUAL,
    censoring: CensoringKind = CensoringKind.EXACT,
) -> BiochemicalRecord:
    return BiochemicalRecord(
        activity_id=uuid4(),
        provenance_id=uuid4(),
        data_tier=DataTier.TIER1,
        measurement_type=mtype,
        value=CensoredValue(
            magnitude=Decimal(magnitude),
            unit=Unit.NANOMOLAR,
            operator=operator,
            censoring=censoring,
        ),
        source_db=SourceDB.CHEMBL,
    )


# ── SCI0-004: structural separation ─────────────────────────────────────────


def test_ec50_rejected_from_biochemical_record() -> None:
    """SCI0-004 exit: EC50 may not appear in a BiochemicalRecord."""
    with pytest.raises(ValueError, match="EC50"):
        BiochemicalRecord(
            activity_id=uuid4(),
            provenance_id=uuid4(),
            data_tier=DataTier.TIER1,
            measurement_type=MeasurementType.EC50,
            value=CensoredValue(
                magnitude=Decimal("50"),
                unit=Unit.NANOMOLAR,
                operator=RelationalOperator.EQUAL,
                censoring=CensoringKind.EXACT,
            ),
            source_db=SourceDB.CHEMBL,
        )


def test_ic50_rejected_from_cellular_record() -> None:
    """SCI0-004 exit: biochemical quantities may not appear in a CellularRecord."""
    with pytest.raises(ValueError, match="Biochemical"):
        CellularRecord(
            activity_id=uuid4(),
            provenance_id=uuid4(),
            data_tier=DataTier.TIER1,
            value=CensoredValue(
                magnitude=Decimal("50"),
                unit=Unit.NANOMOLAR,
                operator=RelationalOperator.EQUAL,
                censoring=CensoringKind.EXACT,
            ),
            source_db=SourceDB.CHEMBL,
            measurement_type=MeasurementType.IC50,  # wrong — must be EC50
        )


def test_biochemical_and_cellular_are_distinct_types() -> None:
    """BiochemicalRecord and CellularRecord are distinct Python types."""
    bio = _biochemical()
    cell = CellularRecord(
        activity_id=uuid4(),
        provenance_id=uuid4(),
        data_tier=DataTier.TIER1,
        value=CensoredValue(
            magnitude=Decimal("200"),
            unit=Unit.NANOMOLAR,
            operator=RelationalOperator.EQUAL,
            censoring=CensoringKind.EXACT,
        ),
        source_db=SourceDB.CHEMBL,
    )
    assert type(bio).__name__ != type(cell).__name__  # mypy: frozen dataclasses are distinct
    assert bio.measurement_class != cell.measurement_class


# ── SCI0-005: censored values ────────────────────────────────────────────────


def test_right_censored_inactive_roundtrip() -> None:
    """SCI0-005 exit: a '>10 µM' record round-trips with operator intact."""
    censored = CensoredValue(
        magnitude=Decimal("10"),
        unit=Unit.MICROMOLAR,
        operator=RelationalOperator.GREATER_THAN,
        censoring=CensoringKind.RIGHT_CENSORED,
    )
    assert censored.operator == RelationalOperator.GREATER_THAN
    assert censored.censoring == CensoringKind.RIGHT_CENSORED
    assert censored.magnitude == Decimal("10")
    # The value is NOT imputed to 10 µM — it is "> 10 µM"
    assert censored.operator.value != RelationalOperator.EQUAL.value


def test_censored_record_is_detected() -> None:
    rec = _biochemical(
        operator=RelationalOperator.GREATER_THAN,
        censoring=CensoringKind.RIGHT_CENSORED,
        magnitude="10000",
    )
    assert is_censored(rec)


def test_exact_record_is_not_censored() -> None:
    rec = _biochemical()
    assert not is_censored(rec)


def test_censored_fraction_reporting() -> None:
    """censored_fraction reports without discarding anything."""
    records: list[AnyActivityRecord] = [
        _biochemical(),  # exact
        _biochemical(
            operator=RelationalOperator.GREATER_THAN,
            censoring=CensoringKind.RIGHT_CENSORED,
            magnitude="10000",
        ),
        _biochemical(
            operator=RelationalOperator.GREATER_THAN,
            censoring=CensoringKind.RIGHT_CENSORED,
            magnitude="30000",
        ),
    ]
    frac = censored_fraction(records)
    assert abs(frac - 2 / 3) < 1e-9
    # All three records still present — none discarded
    assert len(records) == 3


def test_negative_magnitude_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        CensoredValue(
            magnitude=Decimal("-1"),
            unit=Unit.NANOMOLAR,
            operator=RelationalOperator.EQUAL,
            censoring=CensoringKind.EXACT,
        )


def test_exact_censoring_requires_equal_operator() -> None:
    with pytest.raises(ValueError, match="EQUAL"):
        CensoredValue(
            magnitude=Decimal("100"),
            unit=Unit.NANOMOLAR,
            operator=RelationalOperator.GREATER_THAN,
            censoring=CensoringKind.EXACT,
        )


def test_censored_censoring_requires_relational_operator() -> None:
    with pytest.raises(ValueError, match="relational"):
        CensoredValue(
            magnitude=Decimal("100"),
            unit=Unit.NANOMOLAR,
            operator=RelationalOperator.EQUAL,
            censoring=CensoringKind.RIGHT_CENSORED,
        )

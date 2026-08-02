"""Activity record schema — separate typed quantities per measurement class.

Objective: SCI0-004 + SCI0-005.
Constitution §2.3(3): biochemical and cellular selectivity are separate targets,
never pooled.  Constitution §3.3: right-censored inactives are retained and
never imputed to the threshold.

Design
------
Two record types enforce the biochemical/cellular separation at the type level:

  BiochemicalRecord — IC50, Ki, Kd
  CellularRecord    — EC50 only

They share no measurement-value field.  A function that accepts one type
cannot silently receive the other.

CensoredValue wraps a Decimal measurement with its operator (=, >, <, >=, <=)
and an optional threshold.  A right-censored "> 10 µM" record is never
collapsed to "10 µM".
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from orthosteric.data.models import CensoringKind, DataTier, SourceDB
from orthosteric.data.provenance.enums import MeasurementClass, MeasurementType, Unit

# ─────────────────────────────────────────────────────────────────────────────
# Censored value
# ─────────────────────────────────────────────────────────────────────────────


class RelationalOperator(StrEnum):
    """Relational operator on a measurement."""

    EQUAL = "="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN_OR_EQUAL = "<="


@dataclass(frozen=True, slots=True)
class CensoredValue:
    """A measurement value with explicit censoring semantics.

    Attributes:
        magnitude:  Reported numeric magnitude as Decimal.
        unit:       Concentration unit; never inferred.
        operator:   Relational operator.  EQUAL for exact measurements;
                    GREATER_THAN / LESS_THAN for censored inactives/actives.
        censoring:  Redundant with operator but explicit for downstream
                    filtering without operator inspection.

    Example — a right-censored inactive reported as "> 10 µM":
        CensoredValue(
            magnitude=Decimal("10"),
            unit=Unit.MICROMOLAR,
            operator=RelationalOperator.GREATER_THAN,
            censoring=CensoringKind.RIGHT_CENSORED,
        )

    This value is never imputed to 10 µM (Constitution §3.3).
    """

    magnitude: Decimal
    unit: Unit
    operator: RelationalOperator
    censoring: CensoringKind

    def __post_init__(self) -> None:
        """Validate magnitude and operator/censoring consistency."""
        if self.magnitude < 0:
            raise ValueError(f"Activity magnitude must be non-negative; got {self.magnitude}")
        # Consistency check: operator and censoring kind must agree
        censored_ops = {
            RelationalOperator.GREATER_THAN,
            RelationalOperator.LESS_THAN,
            RelationalOperator.GREATER_THAN_OR_EQUAL,
            RelationalOperator.LESS_THAN_OR_EQUAL,
        }
        if self.censoring == CensoringKind.EXACT and self.operator != RelationalOperator.EQUAL:
            raise ValueError(f"EXACT censoring requires EQUAL operator; got {self.operator}")
        if self.censoring != CensoringKind.EXACT and self.operator not in censored_ops:
            raise ValueError(f"Censored record requires a relational operator; got {self.operator}")


# ─────────────────────────────────────────────────────────────────────────────
# Separate record types — biochemical and cellular never share a field
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class BiochemicalRecord:
    """A single biochemical activity measurement.

    Covers IC50, Ki, and Kd.  Explicitly excludes EC50 (cellular only).
    The measurement_class field is always BIOCHEMICAL; it is present for
    downstream code that accepts the abstract base rather than a concrete type.

    Attributes:
        activity_id:      Globally unique identifier for this record.
        provenance_id:    Foreign key into the ProvenanceRecord.
        data_tier:        Scope tier (Constitution §0.1).
        measurement_type: IC50, Ki, or Kd.  EC50 is not admissible here.
        value:            Activity value with explicit censoring.
        source_db:        Database of origin.
    """

    activity_id: UUID
    provenance_id: UUID
    data_tier: DataTier
    measurement_type: MeasurementType
    value: CensoredValue
    source_db: SourceDB
    measurement_class: MeasurementClass = MeasurementClass.BIOCHEMICAL

    def __post_init__(self) -> None:
        """Reject EC50 and enforce BIOCHEMICAL class."""
        if self.measurement_type == MeasurementType.EC50:
            raise ValueError(
                "EC50 is a cellular quantity and may not appear in a "
                "BiochemicalRecord.  Use CellularRecord instead."
            )
        if self.measurement_class != MeasurementClass.BIOCHEMICAL:
            raise ValueError("BiochemicalRecord.measurement_class must be BIOCHEMICAL.")


@dataclass(frozen=True, slots=True)
class CellularRecord:
    """A single cellular activity measurement.

    Covers EC50 only.  IC50, Ki, Kd are not admissible here.

    Attributes:
        activity_id:      Globally unique identifier for this record.
        provenance_id:    Foreign key into the ProvenanceRecord.
        data_tier:        Scope tier (Constitution §0.1).
        value:            Activity value with explicit censoring.
        source_db:        Database of origin.
    """

    activity_id: UUID
    provenance_id: UUID
    data_tier: DataTier
    value: CensoredValue
    source_db: SourceDB
    measurement_type: MeasurementType = MeasurementType.EC50
    measurement_class: MeasurementClass = MeasurementClass.CELLULAR

    def __post_init__(self) -> None:
        """Reject non-EC50 types and enforce CELLULAR class."""
        if self.measurement_type != MeasurementType.EC50:
            raise ValueError(
                "CellularRecord.measurement_type must be EC50.  "
                "Biochemical quantities (IC50, Ki, Kd) belong in BiochemicalRecord."
            )
        if self.measurement_class != MeasurementClass.CELLULAR:
            raise ValueError("CellularRecord.measurement_class must be CELLULAR.")


# ─────────────────────────────────────────────────────────────────────────────
# SCI0-005: censored-record interface
# ─────────────────────────────────────────────────────────────────────────────

#: Union of the two concrete record types for code that handles both classes.
AnyActivityRecord = BiochemicalRecord | CellularRecord


def is_censored(record: AnyActivityRecord) -> bool:
    """Return True if the record carries a censored (non-exact) value."""
    return record.value.censoring != CensoringKind.EXACT


def censored_fraction(records: list[AnyActivityRecord]) -> float:
    """Fraction of records that are censored.

    Used to report the censored fraction at Stage 0 Q3 (SCI0-017) and to
    verify no code path discards censored records.  Never used to decide
    whether to discard them.
    """
    if not records:
        return 0.0
    return sum(1 for r in records if is_censored(r)) / len(records)

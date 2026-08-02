"""Deterministic serialization of provenance records.

Objective: SCI0-003.
Owner: Constitution §3.3; ENG §6, §13.

Scientific rationale:
    Snapshot identity is a content hash computed over serialized records (SCI0-011).
    Serialization must therefore be byte-identical for structurally identical input,
    across runs, platforms and interpreter builds. Three properties make that true:

    * keys are sorted recursively, so dictionary insertion order cannot leak in;
    * numeric fields are Decimal rendered in canonical fixed-point form, never float —
      float repr varies and ``0.1 + 0.2`` is the classic corpus-hash defect;
    * timestamps carry an explicit ``+00:00`` offset, never a local one.

    Keys are never omitted: an absent value serializes as explicit ``null`` so that the
    difference between "unknown" and "not recorded in this schema version" survives.
"""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from .enums import (
    ExtractionTier,
    LicenseType,
    LocatorType,
    MeasurementClass,
    MeasurementType,
    SourceConfidence,
    SourceType,
    Tier,
    Unit,
)
from .models import (
    SCHEMA_VERSION,
    AssayMetadata,
    ExtractionMetadata,
    ProvenanceRecord,
    PublicationMetadata,
    Quantity,
    SourceMetadata,
    SpanAnchor,
)

__all__ = ["ProvenanceSerializationError", "deserialize", "serialize", "to_json_bytes"]


class ProvenanceSerializationError(ValueError):
    """Raised when a payload cannot be serialized or deserialized."""


def _canonical_decimal(value: Decimal) -> str:
    """Render a Decimal canonically in fixed-point form.

    ``Decimal("10")`` and ``Decimal("10.0")`` compare equal and must serialize
    identically, so trailing zeros are normalized away. Exponent notation is avoided
    because it is not stable across magnitudes.

    Args:
        value: The decimal to render.

    Returns:
        Canonical fixed-point string.
    """
    if not value.is_finite():
        raise ProvenanceSerializationError(f"non-finite Decimal: {value!r}")
    normalized = value.normalize()
    return format(normalized, "f")


def _encode(obj: Any) -> Any:
    if obj is None or isinstance(obj, bool | int | str):
        return obj
    if isinstance(obj, Decimal):
        return _canonical_decimal(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            raise ProvenanceSerializationError("naive datetime is not serializable")
        return obj.isoformat()
    if isinstance(obj, float):
        raise ProvenanceSerializationError(
            "float is prohibited in provenance records; use Decimal (writer docstring)"
        )
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _encode(getattr(obj, f.name)) for f in fields(obj)}
    raise ProvenanceSerializationError(f"unsupported type: {type(obj).__name__}")


def serialize(record: ProvenanceRecord) -> str:
    """Serialize a provenance record to canonical JSON text.

    Args:
        record: The record to serialize.

    Returns:
        Canonical JSON: sorted keys, no insignificant whitespace, explicit nulls,
        schema version included.
    """
    payload = {"schema_version": SCHEMA_VERSION, "record": _encode(record)}
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def to_json_bytes(record: ProvenanceRecord) -> bytes:
    """Serialize to UTF-8 bytes, the form entering a snapshot hash.

    Args:
        record: The record to serialize.

    Returns:
        UTF-8 encoded canonical JSON with no BOM and no trailing newline.
    """
    return serialize(record).encode("utf-8")


def _quantity(raw: dict[str, Any] | None) -> Quantity | None:
    if raw is None:
        return None
    return Quantity(value=Decimal(raw["value"]), unit=Unit(raw["unit"]))


def _span(raw: dict[str, Any] | None) -> SpanAnchor | None:
    if raw is None:
        return None
    return SpanAnchor(
        locator_type=LocatorType(raw["locator_type"]),
        locator_id=raw["locator_id"],
        row_or_line=raw["row_or_line"],
        verified=raw["verified"],
    )


def _publication(raw: dict[str, Any] | None) -> PublicationMetadata | None:
    if raw is None:
        return None
    return PublicationMetadata(
        doi=raw["doi"],
        pmid=raw["pmid"],
        pmcid=raw["pmcid"],
        journal=raw["journal"],
        publication_year=raw["publication_year"],
    )


def deserialize(text: str) -> ProvenanceRecord:
    """Reconstruct a provenance record from canonical JSON text.

    Args:
        text: Output of :func:`serialize`.

    Returns:
        The reconstructed record.

    Raises:
        ProvenanceSerializationError: If the payload is malformed or its schema version
            is unknown.
    """
    try:
        payload = json.loads(text)
        version = payload["schema_version"]
        if version != SCHEMA_VERSION:
            raise ProvenanceSerializationError(
                f"schema version {version!r} != supported {SCHEMA_VERSION!r}"
            )
        raw = payload["record"]
        src = raw["source"]
        assay = raw["assay"]
        ext = raw["extraction"]
        return ProvenanceRecord(
            provenance_id=UUID(raw["provenance_id"]),
            source=SourceMetadata(
                source_type=SourceType(src["source_type"]),
                accession=src["accession"],
                source_version=src["source_version"],
                downloaded_utc=datetime.fromisoformat(src["downloaded_utc"]),
                license=LicenseType(src["license"]),
                tdm_permission=src["tdm_permission"],
                tier=Tier(src["tier"]),
            ),
            publication=_publication(raw["publication"]),
            assay=AssayMetadata(
                assay_id=assay["assay_id"],
                assay_description=assay["assay_description"],
                organism=assay["organism"],
                target=assay["target"],
                isoform=assay["isoform"],
                construct=assay["construct"],
                atp_concentration=_quantity(assay["atp_concentration"]),
                measurement_type=MeasurementType(assay["measurement_type"]),
                measurement_class=MeasurementClass(assay["measurement_class"]),
            ),
            extraction=ExtractionMetadata(
                curator_version=ext["curator_version"],
                pipeline_version=ext["pipeline_version"],
                extraction_tier=(
                    None
                    if ext["extraction_tier"] is None
                    else ExtractionTier(ext["extraction_tier"])
                ),
                span_anchor=_span(ext["span_anchor"]),
                source_confidence=SourceConfidence(ext["source_confidence"]),
            ),
        )
    except ProvenanceSerializationError:
        raise
    except (KeyError, ValueError, TypeError) as exc:
        raise ProvenanceSerializationError(f"malformed provenance payload: {exc}") from exc

"""Deterministic serialization tests (SCI0-003)."""

from __future__ import annotations

import dataclasses
import json
from decimal import Decimal

import pytest

from orthosteric.data.provenance import (
    ExtractionMetadata,
    ProvenanceRecord,
    ProvenanceSerializationError,
    Quantity,
    SourceMetadata,
    Unit,
    deserialize,
    serialize,
    to_json_bytes,
)
from orthosteric.data.provenance.models import SCHEMA_VERSION


def test_round_trip_is_identity(record: ProvenanceRecord) -> None:
    """Serialize -> deserialize reproduces an equal object."""
    assert deserialize(serialize(record)) == record


def test_round_trip_is_byte_stable(record: ProvenanceRecord) -> None:
    """Serialize -> deserialize -> serialize reproduces identical bytes."""
    once = to_json_bytes(record)
    twice = to_json_bytes(deserialize(once.decode("utf-8")))
    assert once == twice


def test_structurally_identical_records_serialize_identically(
    record: ProvenanceRecord,
) -> None:
    """Two equal records produce byte-identical output."""
    clone = dataclasses.replace(record)
    assert to_json_bytes(record) == to_json_bytes(clone)


def test_decimal_trailing_zeros_canonicalised(record: ProvenanceRecord) -> None:
    """Decimal('10') and Decimal('10.0') are equal and must serialize identically.

    Without canonicalisation the same corpus would hash differently depending on how a
    source formatted its numbers.
    """
    a = dataclasses.replace(
        record,
        assay=dataclasses.replace(
            record.assay, atp_concentration=Quantity(Decimal("10"), Unit.MICROMOLAR)
        ),
    )
    b = dataclasses.replace(
        record,
        assay=dataclasses.replace(
            record.assay, atp_concentration=Quantity(Decimal("10.000"), Unit.MICROMOLAR)
        ),
    )
    assert a == b
    assert to_json_bytes(a) == to_json_bytes(b)


def test_decimal_precision_survives_round_trip(record: ProvenanceRecord) -> None:
    """Small concentrations retain precision and avoid exponent notation."""
    q = Quantity(Decimal("0.000012500"), Unit.MOLAR)
    r = dataclasses.replace(record, assay=dataclasses.replace(record.assay, atp_concentration=q))
    rendered = json.loads(serialize(r))["record"]["assay"]["atp_concentration"]["value"]
    assert rendered == "0.0000125", "fixed-point form, never exponent notation"
    back = deserialize(serialize(r))
    assert back.assay.atp_concentration is not None
    assert back.assay.atp_concentration.value == Decimal("0.0000125")


def test_keys_are_sorted(record: ProvenanceRecord) -> None:
    """Key order is lexicographic at every level, so insertion order cannot leak in."""
    payload = json.loads(serialize(record))
    assert list(payload) == sorted(payload)
    assert list(payload["record"]) == sorted(payload["record"])
    assert list(payload["record"]["source"]) == sorted(payload["record"]["source"])


def test_nulls_are_explicit(record: ProvenanceRecord) -> None:
    """Absent values serialize as null; keys are never omitted."""
    payload = json.loads(serialize(record))
    assert payload["record"]["extraction"]["span_anchor"] is None
    assert "span_anchor" in payload["record"]["extraction"]


def test_timestamp_carries_utc_offset(record: ProvenanceRecord) -> None:
    """Timestamps serialize with an explicit +00:00 offset."""
    payload = json.loads(serialize(record))
    assert payload["record"]["source"]["downloaded_utc"].endswith("+00:00")


def test_schema_version_present(record: ProvenanceRecord) -> None:
    """Every payload declares its schema version."""
    assert json.loads(serialize(record))["schema_version"] == SCHEMA_VERSION


def test_unknown_schema_version_rejected(record: ProvenanceRecord) -> None:
    """A payload from an unsupported schema version is refused, not guessed at."""
    payload = json.loads(serialize(record))
    payload["schema_version"] = "9.9.9"
    with pytest.raises(ProvenanceSerializationError, match="schema version"):
        deserialize(json.dumps(payload))


def test_malformed_payload_rejected() -> None:
    """A structurally broken payload raises rather than partially constructing."""
    with pytest.raises(ProvenanceSerializationError, match="malformed"):
        deserialize(json.dumps({"schema_version": SCHEMA_VERSION, "record": {}}))


def test_output_is_utf8_without_bom(record: ProvenanceRecord) -> None:
    """Bytes are UTF-8, no BOM, no trailing newline."""
    raw = to_json_bytes(record)
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert not raw.endswith(b"\n")
    raw.decode("utf-8")


def test_float_is_rejected(record: ProvenanceRecord) -> None:
    """A float anywhere in the record is refused.

    Float repr varies across platforms, which would make snapshot hashes
    non-reproducible.
    """
    assert record.publication is not None
    bad_pub = dataclasses.replace(
        record.publication,
        publication_year=2013.0,  # type: ignore[arg-type]
    )
    bad = dataclasses.replace(record, publication=bad_pub)
    with pytest.raises(ProvenanceSerializationError, match="float is prohibited"):
        serialize(bad)


def test_literature_record_round_trips(
    record: ProvenanceRecord,
    literature_source: SourceMetadata,
    literature_extraction: ExtractionMetadata,
) -> None:
    """A literature record with a verified anchor round-trips intact."""
    r = dataclasses.replace(record, source=literature_source, extraction=literature_extraction)
    assert deserialize(serialize(r)) == r

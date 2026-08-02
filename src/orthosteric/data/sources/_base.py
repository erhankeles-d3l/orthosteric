"""Common source-connector interface and ingested-record type.

Objective: SCI0-006.

Design rules
------------
* No connector-specific type leaves its module — all connectors return
  RawSourceRecord.  Downstream code is source-agnostic.
* Tier is assigned inside the connector, before the record leaves the
  sources layer.  A record whose tier is unknown is INADMISSIBLE; it
  must not enter the corpus even as Tier 2.
* Every connector stores the raw API response unmodified alongside the
  parsed fields so provenance is fully reconstructable.
* A source record that cannot be tier-classified or structurally
  validated is returned with admissibility=INADMISSIBLE and a reason
  code; it is never silently discarded.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Admissibility(StrEnum):
    """Admissibility of a source record under ADR-0003 §2 / §4.

    TIER1_PRIMARY    — Tier 1 target; admissible for training/evaluation.
    TIER2_GATED      — Tier 2 target; must travel via the Tier 2 path only.
    INADMISSIBLE     — Cannot enter the corpus in any path.
    """

    TIER1_PRIMARY = "tier1_primary"
    TIER2_GATED = "tier2_gated"
    INADMISSIBLE = "inadmissible"


@dataclass
class RawSourceRecord:
    """A source record as returned by a connector, with Tier already assigned.

    This is the single type all three connectors return.  No connector-
    specific fields appear after this boundary.

    Attributes:
        source_db:         Source database name (matches SourceDB enum values).
        source_record_id:  Native record identifier in the source database.
        source_version:    Database version/release at time of download.
        retrieval_timestamp: ISO-8601 UTC timestamp of retrieval.
        admissibility:     Tier assignment / admissibility decision.
        inadmissibility_reason: Set when admissibility is INADMISSIBLE.
        target_id:         Source-native target identifier.
        target_name:       Human-readable target name as reported by source.
        compound_id:       Source-native compound identifier.
        smiles:            SMILES as returned by the source (not yet canonical).
        inchikey:          InChIKey as returned by the source, if available.
        activity_type:     Measurement type string from source (e.g. "IC50").
        activity_value:    Numeric activity value as a string (preserves precision).
        activity_units:    Units string from source (e.g. "nM").
        activity_relation: Operator string from source (e.g. "=", ">").
        assay_id:          Source-native assay identifier.
        assay_description: Free-text assay description as reported.
        assay_type:        Assay type code from source.
        atp_concentration_um: ATP concentration in µM if reported; None otherwise.
        organism:          Organism string as reported.
        publication_id:    PMID, DOI, or ChEMBL document ID as reported.
        raw_payload:       Unmodified source API response for full provenance.
    """

    source_db: str
    source_record_id: str
    source_version: str
    retrieval_timestamp: str
    admissibility: Admissibility

    # Optional fields — None means not reported, not unknown
    inadmissibility_reason: str | None = None
    target_id: str | None = None
    target_name: str | None = None
    compound_id: str | None = None
    smiles: str | None = None
    inchikey: str | None = None
    activity_type: str | None = None
    activity_value: str | None = None
    activity_units: str | None = None
    activity_relation: str = "="
    assay_id: str | None = None
    assay_description: str | None = None
    assay_type: str | None = None
    atp_concentration_um: float | None = None
    organism: str | None = None
    publication_id: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


class SourceConnector(abc.ABC):
    """Common interface for all source connectors.

    Concrete connectors must implement all abstract methods.  Return types
    must be identical across all connectors: RawSourceRecord for individual
    records, list[RawSourceRecord] for batches, str for version/metadata.

    Methods:
    -------
    version() -> str
        Database version or release identifier; recorded per download.
    metadata() -> dict[str, str]
        Source-level metadata: name, url, license, last_updated where available.
    search(query: str, **kwargs) -> list[RawSourceRecord]
        Search by target name or identifier.
    fetch(record_id: str) -> RawSourceRecord
        Fetch a single record by its source-native identifier.
    download(target_ids: list[str], **kwargs) -> list[RawSourceRecord]
        Bulk download for a list of source-native target identifiers.
    """

    @abc.abstractmethod
    def version(self) -> str:
        """Return the source database version or release identifier."""

    @abc.abstractmethod
    def metadata(self) -> dict[str, str]:
        """Return source-level metadata."""

    @abc.abstractmethod
    def search(self, query: str, **kwargs: Any) -> list[RawSourceRecord]:
        """Search for records by target name or identifier."""

    @abc.abstractmethod
    def fetch(self, record_id: str) -> RawSourceRecord:
        """Fetch a single record by its source-native identifier."""

    @abc.abstractmethod
    def download(self, target_ids: list[str], **kwargs: Any) -> list[RawSourceRecord]:
        """Bulk download records for a list of source-native target identifiers."""

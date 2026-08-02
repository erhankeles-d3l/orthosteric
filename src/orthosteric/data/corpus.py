"""Corpus schema, immutable snapshot system, and source manifest.

Every record is append-only.  Snapshots are content-hashed and immutable.
Parent-snapshot lineage is preserved for continuous refresh.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum, StrEnum
from typing import Any

from orthosteric.data.provenance.enums import MeasurementType

# ──────────────────────────────────────────────────────────────────────────────
# Provenance tiers  (AUDITOR-4 framework)
# ──────────────────────────────────────────────────────────────────────────────


class ProvenanceTier(StrEnum):
    """T1  Primary publication + reconstructable assay context.
    T2  Publication-linked database record + adequate metadata.
    T3  Database record without primary publication but with sufficient
        structured metadata ([ATP], construct, organism traceable).
    T4  Insufficient provenance — cannot undergo Cheng–Prusoff normalization
        because [ATP] or primary source is unknown.  Excluded from primary
        training/evaluation graph by definition (ADR-0003 §4).
    """

    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4_EXCLUDED"


class Isoform(StrEnum):
    ALPHA = "PI3Kalpha"
    BETA = "PI3Kbeta"
    GAMMA = "PI3Kgamma"
    DELTA = "PI3Kdelta"


# ──────────────────────────────────────────────────────────────────────────────
# Evidence record
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class EvidenceRecord:
    """Single activity observation with full provenance."""

    # Compound
    source_compound_id: str
    inchikey: str | None = None
    canonical_smiles: str | None = None
    original_smiles: str | None = None

    # Target
    isoform: Isoform | None = None
    species: str | None = None  # e.g. "Homo sapiens"
    construct: str | None = None  # e.g. "p110alpha/p85alpha"
    mutation_status: str = "WT"

    # Assay
    assay_id: str | None = None
    assay_type: str | None = None  # e.g. "biochemical_HTRF"
    atp_concentration_um: float | None = None
    atp_km_source: str | None = None  # citation if Km was recorded

    # Measurement
    measurement_type: MeasurementType | None = None
    value: float | None = None
    value_relation: str = "="  # "=", "<", ">"
    units: str | None = None

    # Publication / provenance
    publication_doi: str | None = None
    publication_pmid: str | None = None
    source_db: str = ""  # "chembl", "bindingdb", "pubchem"
    source_record_id: str = ""
    provenance_tier: ProvenanceTier = ProvenanceTier.T4
    retrieval_timestamp: str = ""

    # Scaffold
    bemis_murcko_scaffold: str | None = None
    scaffold_family_id: str | None = None

    # Internal
    exclusion_reason: str | None = None  # set when excluded, else None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # convert enums to their string values
        for k, v in d.items():
            if isinstance(v, Enum):
                d[k] = v.value
        return d


# ──────────────────────────────────────────────────────────────────────────────
# Snapshot
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class SnapshotManifest:
    snapshot_id: str
    parent_snapshot_id: str | None
    created_at: str
    source_versions: dict[str, str]  # {"chembl": "34", ...}
    retrieval_timestamp: str
    record_count: int
    accepted_count: int
    excluded_count: int
    sha256: str
    git_sha: str = ""
    schema_version: str = "1.0"
    adjudication_procedure_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CorpusSnapshot:
    """Immutable in-memory view of a corpus snapshot."""

    manifest: SnapshotManifest
    records: list[EvidenceRecord] = field(default_factory=list)

    def accepted(self) -> list[EvidenceRecord]:
        return [r for r in self.records if r.exclusion_reason is None]

    def excluded(self) -> list[EvidenceRecord]:
        return [r for r in self.records if r.exclusion_reason is not None]

    def by_isoform(self, iso: Isoform) -> list[EvidenceRecord]:
        return [r for r in self.accepted() if r.isoform == iso]

    @staticmethod
    def compute_hash(records: list[EvidenceRecord]) -> str:
        """Deterministic SHA-256 of the accepted record list."""
        payload = json.dumps(
            sorted(
                [r.to_dict() for r in records],
                key=lambda x: (x["source_db"], x["source_record_id"]),
            ),
            sort_keys=True,
            default=str,
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def create(
        cls,
        records: list[EvidenceRecord],
        parent_id: str | None = None,
        source_versions: dict[str, str] | None = None,
        git_sha: str = "",
    ) -> CorpusSnapshot:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        accepted = [r for r in records if r.exclusion_reason is None]
        excluded = [r for r in records if r.exclusion_reason is not None]
        sha = cls.compute_hash(accepted)
        snap_id = f"PEEAP-{now[:10].replace('-', '')}-{sha[:8]}"
        manifest = SnapshotManifest(
            snapshot_id=snap_id,
            parent_snapshot_id=parent_id,
            created_at=now,
            source_versions=source_versions or {},
            retrieval_timestamp=now,
            record_count=len(records),
            accepted_count=len(accepted),
            excluded_count=len(excluded),
            sha256=sha,
            git_sha=git_sha,
        )
        return cls(manifest=manifest, records=records)

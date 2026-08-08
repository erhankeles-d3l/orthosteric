"""Immutable content-hashed corpus snapshot builder.

Objective: SCI0-011.
Exit criterion (spec): two builds from the same cache yield the same hash;
a snapshot cannot be modified in place (SI9).

Hash identity (GDR-010, accepted — Option A)
---------------------------------------------
Scientific snapshot identity and build/environment provenance are two
separate hashes.  `SoftwareProvenance` (RDKit, Python, git SHA, git-dirty,
OS, lockfile) does NOT enter scientific identity: an environment change
must never make otherwise-identical scientific data acquire a new identity.

  content_sha256 = SHA256( stable_json(content_view(sorted_records))
                          + stable_json(policy.to_canonical_dict()) )

  build_provenance_sha256 = SHA256( stable_json(software.to_canonical_dict()) )

  snapshot_sha256 := content_sha256   # scientific identity — this is what
                                       # parent_snapshot_sha256 lineage and
                                       # SnapshotDiff key on
  snapshot_id      = "SNAP-" + content_sha256[:12]

`content_view(record)` additionally strips per-record fields that are
retrieval provenance rather than scientific content — currently
`retrieval_timestamp` — following the GDR-002 precedent that a timestamp
must never make otherwise-identical data non-deterministic.  Re-downloading
byte-identical upstream data at a different time therefore yields the same
`content_sha256`.

`build_provenance_sha256` is recorded on every manifest and is fully
reportable, but it is not identity-defining: two snapshots with identical
`content_sha256` and different `build_provenance_sha256` describe the SAME
scientific corpus built on different machines/toolchains.

Neither timestamps nor random UUIDs enter either hash.  Both hashes are
content-addressed and reproducible — from data + policy (content), or from
software (provenance) — alone.

Immutability
------------
CorpusSnapshotV2 is a frozen dataclass.  The builder returns a new instance
per call; it never mutates existing snapshots.  Parent-snapshot lineage is
preserved via parent_snapshot_sha256.

Positive + negative evidence
-----------------------------
The hash covers ALL records, not just accepted ones.  Excluded, conflicted,
censored, RULE_MISSING, and GOVERNANCE_EXCEPTION records all enter the hash.
The snapshot is invalid if it contains only accepted records.

Serialization
-------------
Uses the existing provenance writer conventions (sorted keys, Decimal to
fixed-point, explicit UTC, no repr()).  Every nested dict is sorted before
hashing to guarantee ordering invariance.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from orthosteric.data.snapshots._manifest import (
    PolicyManifest,
    SoftwareProvenance,
)

# ── Canonical serialization ────────────────────────────────────────────────────

_SNAPSHOT_SCHEMA_VERSION = "sci0011_v1"

#: Record fields that are retrieval provenance, not scientific content
#: (GDR-010, accepted).  Excluded from `content_sha256` so that re-acquiring
#: byte-identical upstream data at a different time does not change
#: scientific snapshot identity.  Mirrors the GDR-002 timestamp precedent.
_PROVENANCE_ONLY_RECORD_FIELDS: frozenset[str] = frozenset({"retrieval_timestamp"})


def _content_view(record: dict[str, Any]) -> dict[str, Any]:
    """Return `record` with provenance-only fields removed, for hashing only.

    Does not mutate `record` and is never used for storage — the stored
    snapshot retains every field, including `retrieval_timestamp`.
    """
    return {k: v for k, v in record.items() if k not in _PROVENANCE_ONLY_RECORD_FIELDS}


def _canonical_default(obj: Any) -> Any:
    """JSON default serializer for corpus types."""
    if isinstance(obj, Decimal):
        return format(obj, "f")
    if hasattr(obj, "value"):  # StrEnum
        return obj.value
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def _stable_json(obj: Any) -> str:
    """Deterministic JSON — sorted keys, no unordered dicts, Decimal fixed-point."""
    return json.dumps(
        obj, sort_keys=True, default=_canonical_default, separators=(",", ":"), ensure_ascii=True
    )


def _hash_payload(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── Snapshot types ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SnapshotManifestV2:
    """Snapshot manifest with full provenance per SCI0-011.

    Attributes:
    ----------
    schema_version:             Snapshot schema version.
    snapshot_sha256:            Scientific content identity — SHA-256 over
                                all records (minus provenance-only fields)
                                + policy.  Does NOT include software/
                                environment (GDR-010, accepted, Option A).
    build_provenance_sha256:    SHA-256 over software/environment provenance
                                alone.  Reportable but not identity-defining:
                                two snapshots may share snapshot_sha256 while
                                differing here (built on different machines).
    snapshot_id:                Human-readable ID derived from snapshot_sha256.
    parent_snapshot_sha256:     SHA-256 of the parent snapshot, if any.
    created_at_utc:             Creation timestamp (provenance metadata only;
                                does NOT enter the hash).
    record_count:               Total records (accepted + excluded).
    accepted_count:             Records with no exclusion_reason.
    excluded_count:             Records excluded for any reason.
    censored_count:             Records with a censored activity value.
    unresolved_count:           Records with UNRESOLVED conflict status.
    conflict_count:             Records flagged as WITHIN_GROUP_CONFLICT.
    rule_missing_count:         Records carrying a RULE_MISSING classification.
    governance_exception_count: Records carrying a GOVERNANCE_EXCEPTION.
    structural_records_total:   Total structural evidence records.
    structural_experimental_pdb:Experimental PDB records (admissible).
    structural_alphafold_fallback: AlphaFold fallback records (admissible).
    structural_inadmissible:    Structural records failing §2.1.
    source_versions:            {source_db: version_string}.
    policy:                     PolicyManifest instance.
    software:                   SoftwareProvenance instance.
    """

    schema_version: str
    snapshot_sha256: str
    build_provenance_sha256: str
    snapshot_id: str
    parent_snapshot_sha256: str | None
    created_at_utc: str
    record_count: int
    accepted_count: int
    excluded_count: int
    censored_count: int
    unresolved_count: int
    conflict_count: int
    rule_missing_count: int
    governance_exception_count: int
    structural_records_total: int
    structural_experimental_pdb: int
    structural_alphafold_fallback: int
    structural_inadmissible: int
    source_versions: dict[str, str]
    policy: PolicyManifest
    software: SoftwareProvenance

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_count": self.accepted_count,
            "build_provenance_sha256": self.build_provenance_sha256,
            "censored_count": self.censored_count,
            "conflict_count": self.conflict_count,
            "created_at_utc": self.created_at_utc,
            "excluded_count": self.excluded_count,
            "governance_exception_count": self.governance_exception_count,
            "parent_snapshot_sha256": self.parent_snapshot_sha256,
            "policy": self.policy.to_canonical_dict(),
            "record_count": self.record_count,
            "rule_missing_count": self.rule_missing_count,
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "snapshot_sha256": self.snapshot_sha256,
            "software": self.software.to_canonical_dict(),
            "source_versions": dict(sorted(self.source_versions.items())),
            "structural_alphafold_fallback": self.structural_alphafold_fallback,
            "structural_experimental_pdb": self.structural_experimental_pdb,
            "structural_inadmissible": self.structural_inadmissible,
            "structural_records_total": self.structural_records_total,
            "unresolved_count": self.unresolved_count,
        }


@dataclass(frozen=True, slots=True)
class CorpusSnapshotV2:
    """Immutable content-hashed corpus snapshot.

    Frozen dataclass — cannot be modified after creation.
    All mutations produce a new snapshot with a new SHA-256 identity.

    Attributes:
    ----------
    manifest:   SnapshotManifestV2 with full provenance.
    records:    Tuple of all records (frozen, ordered deterministically).
                Includes BOTH accepted AND excluded/conflicted/unresolved
                records — the hash covers all of them.
    """

    manifest: SnapshotManifestV2
    records: tuple[dict[str, Any], ...]  # serialized record dicts, sorted

    def is_admissible(self) -> bool:
        """False if the snapshot contains only accepted records (provenance gap)."""
        return self.manifest.record_count >= self.manifest.accepted_count

    def accepted_records(self) -> list[dict[str, Any]]:
        return [r for r in self.records if not r.get("exclusion_reason")]

    def excluded_records(self) -> list[dict[str, Any]]:
        return [r for r in self.records if r.get("exclusion_reason")]


# ── Builder ────────────────────────────────────────────────────────────────────


class SnapshotBuilder:
    """Builds deterministic, immutable, content-hashed corpus snapshots.

    Usage
    -----
    ```python
    builder = SnapshotBuilder(
        software=SoftwareProvenance.collect(),
        policy=PolicyManifest.current(),
    )
    snapshot = builder.build(
        activity_records=...,
        structural_records=...,
        source_versions={"chembl": "34", ...},
        parent_sha256=None,
    )
    ```

    `snapshot_sha256` (scientific content identity, GDR-010 Option A) is
    computed over:
      - all activity + structural records, minus provenance-only fields
        (currently `retrieval_timestamp`)
      - the PolicyManifest

    `build_provenance_sha256` (recorded separately, NOT identity-defining)
    is computed over the SoftwareProvenance alone.

    Timestamps do NOT enter either hash.  Two builds from the same inputs
    produce the same `snapshot_sha256` (exit criterion 1) regardless of the
    software/environment they were built under.
    """

    def __init__(
        self,
        software: SoftwareProvenance,
        policy: PolicyManifest,
    ) -> None:
        self._software = software
        self._policy = policy

    def build(
        self,
        activity_records: list[dict[str, Any]],
        structural_records: list[dict[str, Any]] | None = None,
        source_versions: dict[str, str] | None = None,
        parent_sha256: str | None = None,
    ) -> CorpusSnapshotV2:
        """Build an immutable snapshot from the provided records.

        Both activity_records and structural_records should include ALL records
        (accepted + excluded + conflicted + unresolved + RULE_MISSING).

        Parameters
        ----------
        activity_records:
            List of serialized activity records (any mix of statuses).
        structural_records:
            Structural evidence records from SCI0-007.  None if not yet built.
        source_versions:
            {source_db: version_string} map.
        parent_sha256:
            SHA-256 of the parent snapshot for lineage tracking.

        Returns:
        -------
        CorpusSnapshotV2 (frozen, immutable).
        """
        if structural_records is None:
            structural_records = []

        all_records = activity_records + structural_records

        # ── Deterministic sort ──────────────────────────────────────────────
        # Sort by a stable composite key: record_type, then source_db,
        # then source_record_id.  This ensures ordering independence.
        def _sort_key(r: dict[str, Any]) -> tuple[str, str, str]:
            return (
                str(r.get("record_type", "activity")),
                str(r.get("source_db", "")),
                str(r.get("source_record_id", r.get("pdb_id", ""))),
            )

        sorted_records = sorted(all_records, key=_sort_key)

        # ── Compute hashes (GDR-010, accepted — Option A) ────────────────────
        # Scientific identity = records (minus provenance-only fields) + policy.
        # Software/environment provenance is hashed separately and does NOT
        # enter scientific identity.  Neither hash includes timestamps.
        content_records = [_content_view(r) for r in sorted_records]
        records_payload = _stable_json(content_records)
        policy_payload = _stable_json(self._policy.to_canonical_dict())
        content_composite = records_payload + "\n" + policy_payload
        content_sha256 = _hash_payload(content_composite)

        software_payload = _stable_json(self._software.to_canonical_dict())
        build_provenance_sha256 = _hash_payload(software_payload)

        sha256 = content_sha256  # snapshot_sha256 := content_sha256
        snapshot_id = f"SNAP-{sha256[:12]}"

        # ── Count record categories ─────────────────────────────────────────
        accepted = sum(1 for r in activity_records if not r.get("exclusion_reason"))
        excluded = sum(1 for r in activity_records if r.get("exclusion_reason"))
        censored = sum(
            1
            for r in activity_records
            if str(r.get("censoring", "")) in ("right_censored", "left_censored")
        )
        unresolved = sum(
            1 for r in activity_records if "UNRESOLVED" in str(r.get("conflict_status", ""))
        )
        conflict = sum(
            1
            for r in activity_records
            if "CONFLICT" in str(r.get("conflict_status", ""))
            and "UNRESOLVED" not in str(r.get("conflict_status", ""))
        )
        rule_missing = sum(
            1
            for r in all_records
            if "RULE_MISSING" in str(r.get("status", ""))
            or "RULE_MISSING" in str(r.get("notes", ""))
        )
        gov_exception = sum(
            1 for r in all_records if "GOVERNANCE_EXCEPTION" in str(r.get("status", ""))
        )

        # Structural record breakdown
        str_total = len(structural_records)
        str_exp_pdb = sum(
            1
            for r in structural_records
            if str(r.get("structure_source", "")) == "experimental_pdb"
            and str(r.get("admissibility", "")) == "admissible"
        )
        str_af = sum(
            1
            for r in structural_records
            if str(r.get("structure_source", "")) == "alphafold_fallback"
            and str(r.get("admissibility", "")) == "admissible"
        )
        str_inadm = sum(
            1 for r in structural_records if str(r.get("admissibility", "")) != "admissible"
        )

        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        manifest = SnapshotManifestV2(
            schema_version=_SNAPSHOT_SCHEMA_VERSION,
            snapshot_sha256=sha256,
            build_provenance_sha256=build_provenance_sha256,
            snapshot_id=snapshot_id,
            parent_snapshot_sha256=parent_sha256,
            created_at_utc=created_at,
            record_count=len(all_records),
            accepted_count=accepted,
            excluded_count=excluded,
            censored_count=censored,
            unresolved_count=unresolved,
            conflict_count=conflict,
            rule_missing_count=rule_missing,
            governance_exception_count=gov_exception,
            structural_records_total=str_total,
            structural_experimental_pdb=str_exp_pdb,
            structural_alphafold_fallback=str_af,
            structural_inadmissible=str_inadm,
            source_versions=dict(sorted((source_versions or {}).items())),
            policy=self._policy,
            software=self._software,
        )

        return CorpusSnapshotV2(
            manifest=manifest,
            records=tuple(sorted_records),
        )

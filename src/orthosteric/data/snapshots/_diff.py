"""Deterministic snapshot diff — what changed between two corpus snapshots.

Given snapshots A and B, ``compute_snapshot_diff`` answers:

    "Exactly which data changed between the corpus used for Model
     Generation N and the corpus used for Model Generation N+1?"

Diff identity is content-hashed so that the same pair (A, B) always
produces the same ``SnapshotDiff`` regardless of when it is computed.

Authority: corpus-lifecycle requirements (see ``data.corpus_lifecycle``).

Layer note
----------
Pure ``data/`` types only.  No imports from ``quality/`` or ``policy/``.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

from orthosteric.data.snapshots._builder import CorpusSnapshotV2

__all__ = ["SnapshotDiff", "compute_snapshot_diff"]


# ── Canonical serialisation (mirrors _builder.py) ─────────────────────────────


def _canonical_default(obj: Any) -> Any:
    if hasattr(obj, "value"):
        return obj.value
    return str(obj)


def _stable_json(obj: Any) -> str:
    return json.dumps(
        obj,
        sort_keys=True,
        default=_canonical_default,
        separators=(",", ":"),
        ensure_ascii=True,
    )


# ── Record keying ──────────────────────────────────────────────────────────────


def _record_key(rec: dict[str, Any]) -> str:
    """Deterministic key for a record used in diff set operations.

    A record's logical identity is its compound identifier × isoform ×
    study × assay.  We use the first available identifier field rather than
    a serialisation hash so that records changed in metadata (e.g. a curator
    note) but not in measurement value are still keyed identically.
    """
    return _stable_json(
        {
            "compound_id": rec.get("compound_id") or rec.get("source_compound_id", ""),
            "isoform": rec.get("isoform", ""),
            "assay_id": rec.get("assay_id", ""),
            "source_db": rec.get("source_db", ""),
            "source_record_id": rec.get("source_record_id", ""),
        }
    )


def _record_value_hash(rec: dict[str, Any]) -> str:
    """SHA-256 of the full record content (used to detect value changes)."""
    return hashlib.sha256(_stable_json(rec).encode("utf-8")).hexdigest()


# ── SnapshotDiff ───────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SnapshotDiff:
    """Deterministic, content-hashed diff between two corpus snapshots.

    Attributes:
    ----------
    snapshot_a_sha:
        SHA-256 of the 'before' snapshot.
    snapshot_b_sha:
        SHA-256 of the 'after' snapshot.
    records_added:
        Count of records in B not present in A (new compounds or assays).
    records_removed:
        Count of records in A not present in B (retracted or excluded).
    records_changed:
        Count of records with the same logical key but different content
        (value update, curation change, etc.).
    records_unchanged:
        Count of records identical in A and B.
    net_record_change:
        ``records_added - records_removed`` (signed).
    source_version_changes:
        ``{source_name: (version_in_A, version_in_B)}`` for sources whose
        version string changed.  Sources that appear in only one snapshot are
        included as ``(None, version)`` or ``(version, None)``.
    policy_changed:
        True if the PolicyManifest SHA-256 changed.
    software_changed:
        True if the SoftwareProvenance canonical hash changed.
    parent_lineage_valid:
        True if ``B.parent_snapshot_sha256 == A.snapshot_sha256`` — i.e. B
        was produced from A.  False when the diff spans a non-adjacent pair.
    diff_sha256:
        Content hash of this diff object (excluding ``created_at_utc``).
    created_at_utc:
        ISO-8601 UTC timestamp (provenance only; does not enter ``diff_sha256``).
    """

    snapshot_a_sha: str
    snapshot_b_sha: str
    records_added: int
    records_removed: int
    records_changed: int
    records_unchanged: int
    net_record_change: int
    source_version_changes: dict[str, tuple[str | None, str | None]]
    policy_changed: bool
    software_changed: bool
    parent_lineage_valid: bool
    diff_sha256: str
    created_at_utc: str

    @property
    def has_any_change(self) -> bool:
        return bool(
            self.records_added > 0
            or self.records_removed > 0
            or self.records_changed > 0
            or len(self.source_version_changes) > 0
            or self.policy_changed
            or self.software_changed
        )


# ── Compute ────────────────────────────────────────────────────────────────────


def compute_snapshot_diff(a: CorpusSnapshotV2, b: CorpusSnapshotV2) -> SnapshotDiff:
    """Compute a deterministic diff between two corpus snapshots.

    Parameters
    ----------
    a:
        'Before' snapshot.
    b:
        'After' snapshot.

    Returns:
    -------
    SnapshotDiff
        Content-hashed diff.  The same pair (a, b) always produces the same
        diff regardless of when this function is called.
    """
    sha_a = a.manifest.snapshot_sha256
    sha_b = b.manifest.snapshot_sha256

    # ── Record-level diff ──────────────────────────────────────────────────────

    keys_a = {_record_key(r): _record_value_hash(r) for r in a.records}
    keys_b = {_record_key(r): _record_value_hash(r) for r in b.records}

    only_in_a = set(keys_a) - set(keys_b)
    only_in_b = set(keys_b) - set(keys_a)
    in_both = set(keys_a) & set(keys_b)

    changed = sum(1 for k in in_both if keys_a[k] != keys_b[k])
    unchanged = len(in_both) - changed

    # ── Source version diff ────────────────────────────────────────────────────

    sv_a = dict(a.manifest.source_versions)
    sv_b = dict(b.manifest.source_versions)
    all_sources = set(sv_a) | set(sv_b)
    source_version_changes: dict[str, tuple[str | None, str | None]] = {}
    for src in sorted(all_sources):
        va, vb = sv_a.get(src), sv_b.get(src)
        if va != vb:
            source_version_changes[src] = (va, vb)

    # ── Policy / software diff ─────────────────────────────────────────────────

    policy_sha_a = hashlib.sha256(
        _stable_json(a.manifest.policy.to_canonical_dict()).encode()
    ).hexdigest()
    policy_sha_b = hashlib.sha256(
        _stable_json(b.manifest.policy.to_canonical_dict()).encode()
    ).hexdigest()
    policy_changed = policy_sha_a != policy_sha_b

    sw_a = hashlib.sha256(
        _stable_json(a.manifest.software.to_canonical_dict()).encode()
    ).hexdigest()
    sw_b = hashlib.sha256(
        _stable_json(b.manifest.software.to_canonical_dict()).encode()
    ).hexdigest()
    software_changed = sw_a != sw_b

    parent_lineage_valid = b.manifest.parent_snapshot_sha256 == sha_a

    # ── Content hash of the diff (timestamp excluded) ─────────────────────────

    diff_payload = _stable_json(
        {
            "changed": changed,
            "net_record_change": len(only_in_b) - len(only_in_a),
            "parent_lineage_valid": parent_lineage_valid,
            "policy_changed": policy_changed,
            "records_added": len(only_in_b),
            "records_removed": len(only_in_a),
            "records_unchanged": unchanged,
            "snapshot_a_sha": sha_a,
            "snapshot_b_sha": sha_b,
            "software_changed": software_changed,
            "source_version_changes": {
                k: list(v) for k, v in sorted(source_version_changes.items())
            },
        }
    )
    diff_sha = hashlib.sha256(diff_payload.encode("utf-8")).hexdigest()

    return SnapshotDiff(
        snapshot_a_sha=sha_a,
        snapshot_b_sha=sha_b,
        records_added=len(only_in_b),
        records_removed=len(only_in_a),
        records_changed=changed,
        records_unchanged=unchanged,
        net_record_change=len(only_in_b) - len(only_in_a),
        source_version_changes=source_version_changes,
        policy_changed=policy_changed,
        software_changed=software_changed,
        parent_lineage_valid=parent_lineage_valid,
        diff_sha256=diff_sha,
        created_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

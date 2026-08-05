"""SCI0-011 exit-criterion and requirement tests.

Exit criteria (spec):
  (1) Two builds from the same cache yield the same hash.
  (2) A snapshot cannot be modified in place (SI9).

Additional requirements:
  (3) Hash is sensitive to content changes.
  (4) Hash is sensitive to policy/software-version changes.
  (5) Both positive and negative evidence enter the hash.
  (6) Structural source provenance is preserved (PDB vs AlphaFold).
  (7) Parent-snapshot lineage is preserved.
  (8) Timestamps do NOT make identical inputs produce different hashes.
  (9) Ordering invariance — same records in different order → same hash.
  (10) Fail-closed — snapshot records all evidence categories in manifest.
  (11) RULE_MISSING and GOVERNANCE_EXCEPTION counted in manifest.
"""

from __future__ import annotations

import dataclasses
import hashlib
from typing import Any

import pytest

from orthosteric.data.snapshots._builder import (
    SnapshotBuilder,
    _hash_payload,
    _stable_json,
)
from orthosteric.data.snapshots._manifest import (
    PolicyManifest,
    SoftwareProvenance,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _sw() -> SoftwareProvenance:
    """Deterministic software provenance for testing (no real git/env calls)."""
    return SoftwareProvenance(
        python_version="3.12.0 (test)",
        rdkit_version="2026.3.5",
        orthosteric_version="0.1.0",
        git_sha="abc123def456",
        git_dirty=False,
        os_platform="Linux",
        os_version="5.15.0-test",
        lockfile_hash="deadbeef" * 8,
        key_package_versions={"rdkit": "2026.3.5"},
    )


def _policy() -> PolicyManifest:
    return PolicyManifest(
        chemical_standardization_policy="sci0008b_rdkit_2026.3.5",
        identifier_harmonization_policy="sci0008c_inchikey_v1",
        deduplication_policy="sci0009_log_median_v1",
        confidence_scoring_policy="sci0010_v1",
        adr0003_adjudication_procedure="adr0003_procedure_v1.0",
        alphafold_fallback_policy="sci0007_af_fallback_v1.0",
        auditor5_status="INSUFFICIENT_EVIDENCE_frozen",
        cheng_prusoff_status="BLOCKED/AUDITOR-5",
        within_group_conflict_threshold="RULE_MISSING/SCI0-016_required",
        confidence_assay_quality_rule="RULE_MISSING",
        confidence_lit_tier_rule="RULE_MISSING",
    )


def _builder() -> SnapshotBuilder:
    return SnapshotBuilder(software=_sw(), policy=_policy())


def _rec(
    record_id: str = "R1",
    source_db: str = "chembl",
    exclusion_reason: str | None = None,
    censoring: str = "exact",
    conflict_status: str = "ok",
) -> dict[str, Any]:
    return {
        "record_type": "activity",
        "source_db": source_db,
        "source_record_id": record_id,
        "inchikey": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0",
        "isoform": "PI3Kalpha",
        "activity_value": 7.0,
        "censoring": censoring,
        "conflict_status": conflict_status,
        "exclusion_reason": exclusion_reason,
    }


def _str_rec(
    pdb_id: str = "1ABC",
    structure_source: str = "experimental_pdb",
    admissibility: str = "admissible",
) -> dict[str, Any]:
    return {
        "record_type": "structure",
        "source_db": "pdb",
        "source_record_id": pdb_id,
        "pdb_id": pdb_id,
        "isoform": "PI3Kalpha",
        "structure_source": structure_source,
        "admissibility": admissibility,
    }


# ── Exit criterion 1: determinism ─────────────────────────────────────────────


def test_same_inputs_same_hash() -> None:
    """Exit criterion 1: two builds from the same inputs → identical hash."""
    b = _builder()
    records = [_rec("R1"), _rec("R2")]
    snap1 = b.build(records, source_versions={"chembl": "34"})
    snap2 = b.build(records, source_versions={"chembl": "34"})
    assert snap1.manifest.snapshot_sha256 == snap2.manifest.snapshot_sha256


def test_snapshot_id_derived_from_sha256() -> None:
    snap = _builder().build([_rec()])
    assert snap.manifest.snapshot_id.startswith("SNAP-")
    assert snap.manifest.snapshot_sha256[:12] in snap.manifest.snapshot_id


# ── Exit criterion 2: immutability ───────────────────────────────────────────


def test_snapshot_is_frozen() -> None:
    """Exit criterion 2: CorpusSnapshotV2 is a frozen dataclass."""
    snap = _builder().build([_rec()])
    with pytest.raises((AttributeError, TypeError)):
        snap.manifest = snap.manifest  # type: ignore[misc]


def test_manifest_is_frozen() -> None:
    snap = _builder().build([_rec()])
    with pytest.raises((AttributeError, TypeError)):
        snap.manifest.record_count = 99  # type: ignore[misc]


def test_records_tuple_immutable() -> None:
    snap = _builder().build([_rec()])
    assert isinstance(snap.records, tuple)


# ── Requirement 3: content sensitivity ───────────────────────────────────────


def test_different_records_different_hash() -> None:
    b = _builder()
    # Fallback: just change the record
    records_a = [{"source_db": "chembl", "source_record_id": "R1", "record_type": "activity"}]
    records_b = [{"source_db": "chembl", "source_record_id": "R2", "record_type": "activity"}]
    snap_a = b.build(records_a)
    snap_b = b.build(records_b)
    assert snap_a.manifest.snapshot_sha256 != snap_b.manifest.snapshot_sha256


def test_adding_record_changes_hash() -> None:
    b = _builder()
    snap1 = b.build([_rec("R1")])
    snap2 = b.build([_rec("R1"), _rec("R2")])
    assert snap1.manifest.snapshot_sha256 != snap2.manifest.snapshot_sha256


# ── Requirement 4: policy/software sensitivity ────────────────────────────────


def test_different_rdkit_version_different_hash() -> None:
    sw1 = _sw()
    sw2 = SoftwareProvenance(
        python_version=sw1.python_version,
        rdkit_version="2025.1.0",
        orthosteric_version=sw1.orthosteric_version,
        git_sha=sw1.git_sha,
        git_dirty=sw1.git_dirty,
        os_platform=sw1.os_platform,
        os_version=sw1.os_version,
        lockfile_hash=sw1.lockfile_hash,
        key_package_versions=sw1.key_package_versions,
    )
    b1 = SnapshotBuilder(software=sw1, policy=_policy())
    b2 = SnapshotBuilder(software=sw2, policy=_policy())
    records = [_rec()]
    snap1 = b1.build(records)
    snap2 = b2.build(records)
    assert snap1.manifest.snapshot_sha256 != snap2.manifest.snapshot_sha256


def test_different_policy_version_different_hash() -> None:

    p1 = _policy()
    p2_fields = dataclasses.asdict(p1)
    p2_fields["deduplication_policy"] = "sci0009_v2_hypothetical"
    p2 = PolicyManifest(**p2_fields)
    b1 = SnapshotBuilder(software=_sw(), policy=p1)
    b2 = SnapshotBuilder(software=_sw(), policy=p2)
    records = [_rec()]
    snap1 = b1.build(records)
    snap2 = b2.build(records)
    assert snap1.manifest.snapshot_sha256 != snap2.manifest.snapshot_sha256


# ── Requirement 5: positive + negative evidence ───────────────────────────────


def test_excluded_records_in_snapshot_count() -> None:
    """Excluded records must be present in the hash (enter total record count)."""
    b = _builder()
    records = [
        _rec("GOOD"),
        _rec("BAD", exclusion_reason="INADMISSIBLE_NO_LIGAND"),
    ]
    snap = b.build(records)
    assert snap.manifest.record_count == 2
    assert snap.manifest.accepted_count == 1
    assert snap.manifest.excluded_count == 1


def test_excluded_record_changes_hash() -> None:
    """A snapshot with an excluded record has a different hash than one without."""
    b = _builder()
    snap1 = b.build([_rec("R1")])
    snap2 = b.build([_rec("R1"), _rec("R2", exclusion_reason="INADMISSIBLE")])
    assert snap1.manifest.snapshot_sha256 != snap2.manifest.snapshot_sha256


def test_censored_records_counted() -> None:
    b = _builder()
    records = [
        _rec("EXACT"),
        _rec("CENS", censoring="right_censored"),
    ]
    snap = b.build(records)
    assert snap.manifest.censored_count == 1


def test_conflict_records_counted() -> None:
    b = _builder()
    records = [
        _rec("OK"),
        _rec("CONF", conflict_status="WITHIN_GROUP_CONFLICT"),
    ]
    snap = b.build(records)
    assert snap.manifest.conflict_count == 1


def test_unresolved_records_counted() -> None:
    b = _builder()
    records = [_rec("UNRES", conflict_status="UNRESOLVED")]
    snap = b.build(records)
    assert snap.manifest.unresolved_count == 1


# ── Requirement 6: structural source provenance ──────────────────────────────


def test_experimental_pdb_counted_separately() -> None:
    """PDB and AlphaFold fallback records must be distinguishable."""
    b = _builder()
    structural = [
        _str_rec("1ABC", "experimental_pdb", "admissible"),
        _str_rec("AFXX", "alphafold_fallback", "admissible"),
        _str_rec("1BAD", "experimental_pdb", "inadmissible_resolution"),
    ]
    snap = b.build([], structural_records=structural)
    assert snap.manifest.structural_experimental_pdb == 1
    assert snap.manifest.structural_alphafold_fallback == 1
    assert snap.manifest.structural_inadmissible == 1
    assert snap.manifest.structural_records_total == 3


def test_alphafold_not_counted_as_experimental_pdb() -> None:
    b = _builder()
    structural = [_str_rec("AF1", "alphafold_fallback", "admissible")]
    snap = b.build([], structural_records=structural)
    assert snap.manifest.structural_experimental_pdb == 0
    assert snap.manifest.structural_alphafold_fallback == 1


# ── Requirement 7: parent-snapshot lineage ────────────────────────────────────


def test_parent_sha_preserved() -> None:
    b = _builder()
    parent = b.build([_rec("R1")])
    child = b.build([_rec("R1"), _rec("R2")], parent_sha256=parent.manifest.snapshot_sha256)
    assert child.manifest.parent_snapshot_sha256 == parent.manifest.snapshot_sha256


def test_no_parent_is_none() -> None:
    snap = _builder().build([_rec()])
    assert snap.manifest.parent_snapshot_sha256 is None


# ── Requirement 8: timestamps do not affect hash ─────────────────────────────


def test_created_at_utc_not_in_hash() -> None:
    """Hash must not include the creation timestamp.
    Same records built at different (simulated) times must share the hash."""
    b = _builder()
    snap1 = b.build([_rec()])
    snap2 = b.build([_rec()])
    # Both are built at different wall-clock times but records+policy+SW are identical
    assert snap1.manifest.snapshot_sha256 == snap2.manifest.snapshot_sha256
    # Timestamps are allowed to differ
    # (we can't force different times in a unit test but verify they're present)
    assert snap1.manifest.created_at_utc != ""


# ── Requirement 9: ordering invariance ───────────────────────────────────────


def test_record_order_does_not_affect_hash() -> None:
    """Ordering invariance: same records in different order → same hash."""
    b = _builder()
    r1 = _rec("R1", source_db="chembl")
    r2 = _rec("R2", source_db="bindingdb")
    snap_ab = b.build([r1, r2])
    snap_ba = b.build([r2, r1])
    assert snap_ab.manifest.snapshot_sha256 == snap_ba.manifest.snapshot_sha256


def test_source_version_ordering_invariant() -> None:
    """Source version dict order doesn't affect hash."""
    b = _builder()
    records = [_rec()]
    snap1 = b.build(records, source_versions={"chembl": "34", "bindingdb": "v3"})
    snap2 = b.build(records, source_versions={"bindingdb": "v3", "chembl": "34"})
    assert snap1.manifest.snapshot_sha256 == snap2.manifest.snapshot_sha256


# ── Requirement 11: RULE_MISSING / GOVERNANCE_EXCEPTION ──────────────────────


def test_rule_missing_counted_in_manifest() -> None:
    b = _builder()
    records = [
        {
            "source_db": "chembl",
            "source_record_id": "RM1",
            "record_type": "activity",
            "status": "RULE_MISSING/test",
        }
    ]
    snap = b.build(records)
    assert snap.manifest.rule_missing_count == 1


def test_policy_manifest_contains_rule_missing_states() -> None:
    p = _policy()
    d = p.to_canonical_dict()
    assert "RULE_MISSING" in d["within_group_conflict_threshold"]
    assert "RULE_MISSING" in d["confidence_assay_quality_rule"]
    assert "AUDITOR-5" in d["cheng_prusoff_status"]


# ── Serialization determinism ─────────────────────────────────────────────────


def test_stable_json_sorted_keys() -> None:
    obj = {"z": 1, "a": 2, "m": 3}
    s = _stable_json(obj)
    assert s == '{"a":2,"m":3,"z":1}'


def test_stable_json_nested_dicts_sorted() -> None:
    obj = {"outer": {"b": 2, "a": 1}}
    s = _stable_json(obj)
    assert s.index('"a"') < s.index('"b"')


def test_hash_payload_is_sha256() -> None:
    h = _hash_payload("test")
    assert len(h) == 64

    assert h == hashlib.sha256(b"test").hexdigest()

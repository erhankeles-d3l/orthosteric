"""Tests for corpus schema, snapshot immutability, and hash determinism."""

from __future__ import annotations

from orthosteric.data.corpus import (
    CorpusSnapshot,
    EvidenceRecord,
    Isoform,
    MeasurementType,
    ProvenanceTier,
)


def _sample_record(
    cid: str, iso: Isoform, study: str = "S1", excl: str | None = None
) -> EvidenceRecord:
    return EvidenceRecord(
        source_compound_id=cid,
        inchikey=f"INCHIKEY_{cid}",
        isoform=iso,
        assay_id=study,
        measurement_type=MeasurementType.IC50,
        value=100.0,
        units="nM",
        source_db="chembl",
        source_record_id=f"ACT_{cid}",
        provenance_tier=ProvenanceTier.T1 if excl is None else ProvenanceTier.T4,
        retrieval_timestamp="2026-08-02T00:00:00Z",
        exclusion_reason=excl,
    )


def test_snapshot_hash_is_deterministic() -> None:
    """Same records in different order → same hash."""
    recs = [_sample_record("C1", Isoform.ALPHA), _sample_record("C2", Isoform.BETA)]
    h1 = CorpusSnapshot.compute_hash(recs)
    recs_rev = list(reversed(recs))
    h2 = CorpusSnapshot.compute_hash(recs_rev)
    assert h1 == h2, "Hash must be order-independent"


def test_snapshot_create() -> None:
    recs = [
        _sample_record("C1", Isoform.ALPHA),
        _sample_record("C2", Isoform.BETA, excl="EXCLUDE_TEST"),
    ]
    snap = CorpusSnapshot.create(recs, git_sha="abc123")
    assert snap.manifest.accepted_count == 1
    assert snap.manifest.excluded_count == 1
    assert snap.manifest.record_count == 2
    assert len(snap.manifest.sha256) == 64  # SHA-256 hex


def test_snapshot_accepted_excluded_split() -> None:
    recs = [
        _sample_record("C1", Isoform.ALPHA),
        _sample_record("C2", Isoform.BETA, excl="EXCLUDE_TEST"),
    ]
    snap = CorpusSnapshot.create(recs)
    assert len(snap.accepted()) == 1
    assert snap.accepted()[0].source_compound_id == "C1"
    assert len(snap.excluded()) == 1


def test_snapshot_hash_changes_when_records_change() -> None:
    recs1 = [_sample_record("C1", Isoform.ALPHA)]
    recs2 = [_sample_record("C2", Isoform.ALPHA)]  # different compound
    assert CorpusSnapshot.compute_hash(recs1) != CorpusSnapshot.compute_hash(recs2)


def test_by_isoform() -> None:
    recs = [
        _sample_record("C1", Isoform.ALPHA),
        _sample_record("C2", Isoform.BETA),
        _sample_record("C3", Isoform.ALPHA),
    ]
    snap = CorpusSnapshot.create(recs)
    assert len(snap.by_isoform(Isoform.ALPHA)) == 2
    assert len(snap.by_isoform(Isoform.DELTA)) == 0

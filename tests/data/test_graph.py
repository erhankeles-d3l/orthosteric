"""Tests for graph statistics computation."""

from orthosteric.data.corpus import (
    CorpusSnapshot,
    EvidenceRecord,
    Isoform,
    MeasurementType,
    ProvenanceTier,
)
from orthosteric.data.graph import build_graph_stats


def _rec(cid: str, iso: Isoform, study: str = "S1") -> EvidenceRecord:
    return EvidenceRecord(
        source_compound_id=cid,
        isoform=iso,
        assay_id=study,
        measurement_type=MeasurementType.IC50,
        value=100.0,
        units="nM",
        source_db="chembl",
        source_record_id=f"A_{cid}",
        provenance_tier=ProvenanceTier.T1,
        retrieval_timestamp="2026-08-02T00:00:00Z",
    )


def test_empty_corpus_returns_zero_stats() -> None:
    snap = CorpusSnapshot.create([])
    stats = build_graph_stats(snap)
    assert stats.total_compounds == 0
    assert stats.largest_connected_component == 0


def test_single_compound_single_isoform() -> None:
    snap = CorpusSnapshot.create([_rec("C1", Isoform.ALPHA)])
    stats = build_graph_stats(snap)
    assert stats.total_compounds == 1
    assert stats.compounds_ge2_isoforms == 0
    assert stats.n_connected_components == 1
    assert stats.largest_connected_component == 1


def test_bridging_compound() -> None:
    """C1 measured in two studies → bridging if it has ≥2 isoforms."""
    recs = [
        _rec("C1", Isoform.ALPHA, "S1"),
        _rec("C1", Isoform.BETA, "S2"),  # different study
        _rec("C2", Isoform.ALPHA, "S1"),
    ]
    snap = CorpusSnapshot.create(recs)
    stats = build_graph_stats(snap)
    assert stats.bridging_compounds >= 1  # C1 bridges S1 and S2


def test_within_study_four_isoform() -> None:
    recs = [
        _rec("C1", Isoform.ALPHA, "S1"),
        _rec("C1", Isoform.BETA, "S1"),
        _rec("C1", Isoform.GAMMA, "S1"),
        _rec("C1", Isoform.DELTA, "S1"),
        _rec("C2", Isoform.ALPHA, "S2"),  # S2 only has one isoform
    ]
    snap = CorpusSnapshot.create(recs)
    stats = build_graph_stats(snap)
    assert stats.within_study_four_isoform >= 1  # C1 is in a four-isoform study

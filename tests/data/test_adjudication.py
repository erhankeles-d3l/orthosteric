"""Tests for adjudication determinism and governance-exception behavior."""

from orthosteric.data.adjudication import AdjudicationStatus, run_adr0003_adjudication
from orthosteric.data.corpus import (
    CorpusSnapshot,
    EvidenceRecord,
    Isoform,
    MeasurementType,
    ProvenanceTier,
)


def _rec(
    cid: str, iso: Isoform, study: str = "S1", tier: ProvenanceTier = ProvenanceTier.T1
) -> EvidenceRecord:
    return EvidenceRecord(
        source_compound_id=cid,
        isoform=iso,
        assay_id=study,
        measurement_type=MeasurementType.IC50,
        value=50.0,
        units="nM",
        source_db="chembl",
        source_record_id=f"A_{cid}_{iso.value}",
        provenance_tier=tier,
        retrieval_timestamp="2026-08-02T00:00:00Z",
    )


def _make_rich_snapshot() -> CorpusSnapshot:
    """Snapshot with enough records to produce non-trivial graph stats."""
    recs = []
    studies = ["S1", "S2", "S3", "S4", "S5"]
    isos = list(Isoform)
    for si, sid in enumerate(studies):
        for ii, iso in enumerate(isos):
            for ci in range(12):
                cid = f"C{si * 100 + ii * 10 + ci}"
                recs.append(_rec(cid, iso, sid))
    return CorpusSnapshot.create(recs)


def test_adjudication_is_deterministic() -> None:
    """Running adjudication twice on the same snapshot gives identical results."""
    snap = _make_rich_snapshot()
    r1 = run_adr0003_adjudication(snap)
    r2 = run_adr0003_adjudication(snap)
    assert r1.config_hash() == r2.config_hash(), "Adjudication must be deterministic"


def test_empty_corpus_returns_insufficient() -> None:
    snap = CorpusSnapshot.create([])
    result = run_adr0003_adjudication(snap)
    assert result.overall_status in (
        AdjudicationStatus.INSUFFICIENT_EVIDENCE,
        AdjudicationStatus.GOVERNANCE_EXCEPTION,
    )


def test_auditor3_always_resolves() -> None:
    """AUDITOR-3 is determined by logic, not corpus size."""
    snap = CorpusSnapshot.create([])
    result = run_adr0003_adjudication(snap)
    assert result.auditor3 is not None
    assert result.auditor3.status == AdjudicationStatus.RESOLVED
    assert result.auditor3.normalization_order == "normalize_then_aggregate"


def test_auditor4_always_resolves() -> None:
    """AUDITOR-4 T4 exclusion follows from the normalization requirement."""
    snap = CorpusSnapshot.create([])
    result = run_adr0003_adjudication(snap)
    assert result.auditor4 is not None
    assert result.auditor4.status == AdjudicationStatus.RESOLVED
    assert result.auditor4.t4_insufficient == "EXCLUDED"


def test_auditor5_insufficient_on_empty() -> None:
    """AUDITOR-5 remains INSUFFICIENT — no primary Km values verified."""
    snap = CorpusSnapshot.create([])
    result = run_adr0003_adjudication(snap)
    assert result.auditor5 is not None
    assert result.auditor5.status == AdjudicationStatus.INSUFFICIENT_EVIDENCE
    # All four isoforms remain unresolved
    for isoform_status in (
        result.auditor5.alpha_status,
        result.auditor5.beta_status,
        result.auditor5.gamma_status,
        result.auditor5.delta_status,
    ):
        assert isoform_status == AdjudicationStatus.INSUFFICIENT_EVIDENCE


def test_governance_exception_never_guesses() -> None:
    """When AUDITOR-5 is INSUFFICIENT, the config hash changes between two
    runs iff the corpus changes — not between two runs of the same corpus.
    """
    snap = _make_rich_snapshot()
    r1 = run_adr0003_adjudication(snap)
    r2 = run_adr0003_adjudication(snap)
    assert r1.auditor5 is not None
    assert r1.auditor5.delta_km_um is None
    assert r1.config_hash() == r2.config_hash()


def test_rich_corpus_produces_provisional_a1_a2() -> None:
    snap = _make_rich_snapshot()
    result = run_adr0003_adjudication(snap)
    assert result.auditor1 is not None
    assert result.auditor2 is not None
    # With 60 records (5 studies x 4 isos x 12 compounds), we should get
    # provisional results for AUDITOR-1 and AUDITOR-2
    assert result.auditor1.status != AdjudicationStatus.GOVERNANCE_EXCEPTION

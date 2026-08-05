"""SCI0-009 exit-criterion tests.

Exit criteria (docs/PROJECT_SPECIFICATION.md; docs/IMPLEMENTATION_BACKLOG.md
`SCI0-009`; Project Owner instructions, 2026-08-05):
  (1) Different stereoisomers are NEVER merged.
  (2) Same compound + different isoform -> distinct evidence preserved.
  (3) Same compound + different source/study -> distinct evidence preserved.
  (4) Literal duplicates (identical value+censoring in one identity group)
      are collapsed without loss.
  (5) Non-identical measurements in one identity group are NEVER silently
      aggregated: AUDITOR-3 (ADR-0003) is unresolved, so the group is marked
      RULE_MISSING/GOVERNANCE_DECISION_REQUIRED and all records retained.
  (6) A zero-tolerance logical contradiction between an exact value and a
      censoring bound is detected without any invented noise threshold.
  (7) Policy is recorded per group.
  (8) Censored records are retained, never dropped.
  (9) CompoundEvidenceMatrix preserves the compound x isoform structure.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from orthosteric.data.harmonization._deduplicator import (
    Deduplicator,
    EvidenceRecord,
    GroupConflictStatus,
)
from orthosteric.data.models import ActivityRecord, CensoringKind, DataTier, SourceDB
from orthosteric.data.provenance.enums import (
    LicenseType,
    MeasurementClass,
    MeasurementType,
    SourceConfidence,
    SourceType,
    Tier,
)
from orthosteric.data.provenance.models import (
    AssayMetadata,
    ExtractionMetadata,
    ProvenanceRecord,
    PublicationMetadata,
    SourceMetadata,
)

FIXED_TS = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)

IK_ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0"  # 27-char placeholder compound identity
IK_BETA = "BCDEFGHIJKLMNOPQRSTUVWXYZ01"
IK_L_ALA = "QNAYBMKLOCPYGJ-REOHCLBHSA-N"  # L-alanine InChIKey (real)
IK_D_ALA = "QNAYBMKLOCPYGJ-UHFFFAOYSA-N"  # D-alanine InChIKey (real)


def _prov(
    *,
    accession: str = "CHEMBL_ASSAY_1",
    isoform: str | None = "PI3Kalpha",
    assay_id: str | None = "A1",
    source_type: SourceType = SourceType.CHEMBL,
) -> ProvenanceRecord:
    return ProvenanceRecord(
        provenance_id=uuid4(),
        source=SourceMetadata(
            source_type=source_type,
            accession=accession,
            source_version="35",
            downloaded_utc=FIXED_TS,
            license=LicenseType.DATABASE_LICENSE,
            tdm_permission=None,
            tier=Tier.TIER_1,
        ),
        publication=PublicationMetadata(
            doi=None, pmid=None, pmcid=None, journal=None, publication_year=None
        ),
        assay=AssayMetadata(
            assay_id=assay_id,
            assay_description="radiometric kinase assay",
            organism="Homo sapiens",
            target="PI3K",
            isoform=isoform,
            construct=None,
            atp_concentration=None,
            measurement_type=MeasurementType.IC50,
            measurement_class=MeasurementClass.BIOCHEMICAL,
        ),
        extraction=ExtractionMetadata(
            curator_version="curation-1.0.0",
            pipeline_version="pipeline-1.0.0",
            extraction_tier=None,
            span_anchor=None,
            source_confidence=SourceConfidence.HIGH,
        ),
    )


def _rec(
    compound_id: str,
    isoform: str | None,
    value: float,
    *,
    accession: str = "CHEMBL_ASSAY_1",
    assay_id: str | None = "A1",
    censoring: CensoringKind = CensoringKind.EXACT,
) -> EvidenceRecord:
    activity = ActivityRecord(
        activity_id=uuid4(),
        provenance_id=UUID(int=0),
        data_tier=DataTier.TIER1,
        value=Decimal(str(value)),
        censoring=censoring,
        measurement_type=MeasurementType.IC50,
        measurement_class=MeasurementClass.BIOCHEMICAL,
        source_db=SourceDB.CHEMBL,
    )
    provenance = _prov(accession=accession, isoform=isoform, assay_id=assay_id)
    return EvidenceRecord(compound_id=compound_id, activity=activity, provenance=provenance)


# ── Exit criterion 1: stereoisomers never merged ──────────────────────────────


def test_stereoisomers_have_different_matrices() -> None:
    d = Deduplicator()
    r_l = _rec(IK_L_ALA, "PI3Kalpha", 7.0)
    r_d = _rec(IK_D_ALA, "PI3Kalpha", 6.5)
    matrices = d.deduplicate([r_l, r_d])
    assert len(matrices) == 2, "L- and D-alanine must be in separate matrices"
    compound_ids = {m.compound_id for m in matrices}
    assert compound_ids == {IK_L_ALA, IK_D_ALA}


def test_stereoisomers_distinct_flag_always_true() -> None:
    d = Deduplicator()
    matrices = d.deduplicate([_rec(IK_ALPHA, "PI3Kalpha", 7.0)])
    assert matrices[0].stereoisomers_distinct is True


# ── Exit criterion 2: same compound, different isoforms -> distinct ───────────


def test_same_compound_different_isoforms_preserved() -> None:
    d = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 8.0),
        _rec(IK_ALPHA, "PI3Kbeta", 5.5),
        _rec(IK_ALPHA, "PI3Kgamma", 4.0),
        _rec(IK_ALPHA, "PI3Kdelta", 6.0),
    ]
    matrices = d.deduplicate(records)
    assert len(matrices) == 1  # one compound
    m = matrices[0]
    assert len(m.isoforms_with_evidence) == 4
    assert m.has_multi_isoform_evidence()
    for iso in ("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"):
        isoform_groups = m.groups_for_isoform(iso)
        assert len(isoform_groups) == 1, f"Missing evidence group for {iso}"
        assert isoform_groups[0].conflict_status == GroupConflictStatus.OK


def test_isoform_values_not_pooled_together() -> None:
    """PI3Kalpha and PI3Kbeta evidence must land in separate groups, never combined."""
    d = Deduplicator()
    records = [_rec(IK_ALPHA, "PI3Kalpha", 8.0), _rec(IK_ALPHA, "PI3Kbeta", 5.5)]
    matrices = d.deduplicate(records)
    m = matrices[0]
    alpha_group = m.groups_for_isoform("PI3Kalpha")[0]
    beta_group = m.groups_for_isoform("PI3Kbeta")[0]
    assert len(alpha_group.records) == 1
    assert len(beta_group.records) == 1
    assert alpha_group.records[0].activity.value == Decimal("8.0")
    assert beta_group.records[0].activity.value == Decimal("5.5")


# ── Exit criterion 3: same compound, different source/study -> distinct ───────


def test_same_compound_different_sources_preserved() -> None:
    d = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 7.8, accession="CHEMBL_ASSAY_1"),
        _rec(IK_ALPHA, "PI3Kalpha", 7.6, accession="CHEMBL_ASSAY_2"),
        _rec(IK_ALPHA, "PI3Kalpha", 7.9, accession="CHEMBL_ASSAY_3"),
    ]
    matrices = d.deduplicate(records)
    m = matrices[0]
    alpha_groups = m.groups_for_isoform("PI3Kalpha")
    assert len(alpha_groups) == 3, "Each distinct source accession must be its own group"
    accessions = {g.source_key[1] for g in alpha_groups}
    assert accessions == {"CHEMBL_ASSAY_1", "CHEMBL_ASSAY_2", "CHEMBL_ASSAY_3"}


# ── Exit criterion 4: literal duplicates collapsed without loss ───────────────


def test_literal_duplicates_collapsed() -> None:
    """Same identity, same value, same censoring: this is the same observation."""
    d = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 7.0),
        _rec(IK_ALPHA, "PI3Kalpha", 7.0),
        _rec(IK_ALPHA, "PI3Kalpha", 7.0),
    ]
    matrices = d.deduplicate(records)
    g = matrices[0].groups_for_isoform("PI3Kalpha")[0]
    assert len(g.records) == 1
    assert g.n_literal_duplicates_collapsed == 2
    assert g.conflict_status == GroupConflictStatus.OK


# ── Exit criterion 5: non-identical values are NEVER silently aggregated ──────


def test_distinct_values_never_aggregated_marked_rule_missing() -> None:
    """Exit criterion 5: AUDITOR-3 is unresolved (ADR-0003 status: Proposed).

    Non-identical exact measurements in the same identity group must not be
    averaged, log-medianed, or otherwise combined. They are surfaced as
    RULE_MISSING and every record is retained.
    """
    d = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 7.0),
        _rec(IK_ALPHA, "PI3Kalpha", 7.4),
        _rec(IK_ALPHA, "PI3Kalpha", 7.2),
    ]
    matrices = d.deduplicate(records)
    g = matrices[0].groups_for_isoform("PI3Kalpha")[0]
    assert g.conflict_status == GroupConflictStatus.RULE_MISSING
    assert "RULE_MISSING" in g.governance_note
    assert "AUDITOR-3" in g.governance_note
    assert len(g.records) == 3, "no record may be dropped while unresolved"


def test_two_distinct_close_values_still_rule_missing() -> None:
    """Even a 'small' spread is not adjudicated here — there is no authorized
    noise floor (SCI0-016 not yet run) to distinguish noise from conflict."""
    d = Deduplicator()
    records = [_rec(IK_ALPHA, "PI3Kalpha", 7.0), _rec(IK_ALPHA, "PI3Kalpha", 7.1)]
    matrices = d.deduplicate(records)
    g = matrices[0].groups_for_isoform("PI3Kalpha")[0]
    assert g.conflict_status == GroupConflictStatus.RULE_MISSING


# ── Exit criterion 6: zero-tolerance logical contradiction ────────────────────


def test_censored_records_retained_and_contradiction_detected() -> None:
    """An exact value strictly above a right-censored bound is a contradiction
    by definition of right-censoring — no noise threshold required."""
    d = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 7.0, censoring=CensoringKind.EXACT),
        _rec(IK_ALPHA, "PI3Kalpha", 5.0, censoring=CensoringKind.RIGHT_CENSORED),
    ]
    matrices = d.deduplicate(records)
    g = matrices[0].groups_for_isoform("PI3Kalpha")[0]
    assert g.conflict_status == GroupConflictStatus.LOGICAL_CONTRADICTION
    assert len(g.records) == 2, "contradictory records are surfaced, not dropped"


def test_non_contradictory_mixed_censoring() -> None:
    """Exact value consistent with a right-censored bound: not a contradiction."""
    d = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 4.0, censoring=CensoringKind.EXACT),
        _rec(IK_ALPHA, "PI3Kalpha", 5.0, censoring=CensoringKind.RIGHT_CENSORED),
    ]
    matrices = d.deduplicate(records)
    g = matrices[0].groups_for_isoform("PI3Kalpha")[0]
    assert g.conflict_status == GroupConflictStatus.MIXED_CENSORED
    assert len(g.records) == 2


def test_all_censored_group() -> None:
    d = Deduplicator()
    records = [_rec(IK_ALPHA, "PI3Kalpha", 5.0, censoring=CensoringKind.RIGHT_CENSORED)]
    matrices = d.deduplicate(records)
    g = matrices[0].groups_for_isoform("PI3Kalpha")[0]
    assert g.conflict_status == GroupConflictStatus.CENSORED_ONLY
    assert len(g.records) == 1


# ── Exit criterion 7: policy recorded ─────────────────────────────────────────


def test_policy_recorded_on_every_group() -> None:
    d = Deduplicator()
    records = [_rec(IK_ALPHA, "PI3Kalpha", 7.0), _rec(IK_ALPHA, "PI3Kbeta", 5.5)]
    matrices = d.deduplicate(records)
    for group in matrices[0].groups:
        assert group.policy == Deduplicator.POLICY_ID
        assert group.policy != ""


def test_no_aggregation_field_invented() -> None:
    """This module must not expose a computed aggregate value anywhere —
    doing so would imply a resolved aggregation policy that does not exist."""
    d = Deduplicator()
    g = d.deduplicate([_rec(IK_ALPHA, "PI3Kalpha", 7.0)])[0].groups[0]
    assert not hasattr(g, "aggregated")
    assert not hasattr(g, "value")


# ── Exit criterion 9: compound x isoform matrix structure ────────────────────


def test_matrix_structure_for_four_isoforms() -> None:
    d = Deduplicator()
    isoforms = ["PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"]
    records = [_rec(IK_ALPHA, iso, 7.0 - i * 0.5) for i, iso in enumerate(isoforms)]
    matrices = d.deduplicate(records)
    assert len(matrices) == 1
    m = matrices[0]
    assert m.compound_id == IK_ALPHA
    assert m.has_multi_isoform_evidence()
    assert m.isoforms_with_evidence == set(isoforms)
    for iso in isoforms:
        assert len(m.groups_for_isoform(iso)) == 1


def test_empty_input_returns_empty() -> None:
    d = Deduplicator()
    assert d.deduplicate([]) == []


def test_unresolved_groups_helper() -> None:
    d = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 7.0),
        _rec(IK_ALPHA, "PI3Kalpha", 7.5),  # RULE_MISSING group
        _rec(IK_ALPHA, "PI3Kbeta", 5.0),  # OK group
    ]
    matrices = d.deduplicate(records)
    m = matrices[0]
    unresolved = m.unresolved_groups()
    assert len(unresolved) == 1
    assert unresolved[0].isoform == "PI3Kalpha"

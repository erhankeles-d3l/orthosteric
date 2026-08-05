"""SCI0-009 exit-criterion tests.

Exit criteria (docs/PROJECT_SPECIFICATION.md; docs/IMPLEMENTATION_BACKLOG.md
`SCI0-009`; GDR-001 duplicate-resolution-policy, 2026-08-05):
  (1) Different stereoisomers are NEVER merged.
  (2) Same compound + different isoform -> distinct evidence preserved.
  (3) Same compound + different source/study -> distinct evidence preserved.
  (3b) Same compound + different construct or organism -> distinct evidence
       preserved (GDR-001 identity-key correction).
  (4) Literal duplicates (identical value+censoring in one identity group)
      are collapsed without loss.
  (5) Non-identical exact measurements in a fully-specified identity group
      are combined by median (GDR-001), never silently discarding any
      contributing record.
  (6) A zero-tolerance logical contradiction between a value (single or
      median-resolved) and a censoring bound is detected without any
      invented noise threshold.
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
    construct: str | None = None,
    organism: str | None = "Homo sapiens",
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
            organism=organism,
            target="PI3K",
            isoform=isoform,
            construct=construct,
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
    construct: str | None = None,
    organism: str | None = "Homo sapiens",
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
    provenance = _prov(
        accession=accession,
        isoform=isoform,
        assay_id=assay_id,
        construct=construct,
        organism=organism,
    )
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


# ── Exit criterion 3b: different construct or organism -> distinct (GDR-001) ──


def test_different_construct_not_pooled() -> None:
    """A wild-type and a mutant construct sharing the same nominal assay_id
    must never land in the same identity group (GDR-001 correction)."""
    d = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 7.0, construct="p110alpha WT"),
        _rec(IK_ALPHA, "PI3Kalpha", 4.0, construct="p110alpha H1047R"),
    ]
    matrices = d.deduplicate(records)
    groups = matrices[0].groups_for_isoform("PI3Kalpha")
    assert len(groups) == 2, "WT and mutant constructs must be separate groups"
    for g in groups:
        assert g.conflict_status == GroupConflictStatus.OK
        assert len(g.records) == 1


def test_different_organism_not_pooled() -> None:
    """Human and murine measurements must never be combined by median."""
    d = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kdelta", 7.0, organism="Homo sapiens"),
        _rec(IK_ALPHA, "PI3Kdelta", 6.0, organism="Mus musculus"),
    ]
    matrices = d.deduplicate(records)
    groups = matrices[0].groups_for_isoform("PI3Kdelta")
    assert len(groups) == 2, "Human and murine records must be separate groups"


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


# ── Exit criterion 5: non-identical replicate values resolved by median ───────


def test_distinct_values_resolved_by_median() -> None:
    """GDR-001: non-identical exact measurements in a fully-specified identity
    group (same compound, isoform, construct, organism, measurement type,
    assay, and source) are combined by median. No record is dropped."""
    d = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 7.0),
        _rec(IK_ALPHA, "PI3Kalpha", 7.4),
        _rec(IK_ALPHA, "PI3Kalpha", 7.2),
    ]
    matrices = d.deduplicate(records)
    g = matrices[0].groups_for_isoform("PI3Kalpha")[0]
    assert g.conflict_status == GroupConflictStatus.RESOLVED_REPLICATE_MEDIAN
    assert g.resolved_value == Decimal("7.2")
    assert g.aggregation_method == "median"
    assert "GDR-001" in g.governance_note
    assert len(g.records) == 3, "no record may be dropped when resolving"


def test_median_of_two_values_is_average_of_middle_pair() -> None:
    """Even-count median: standard order-statistic behavior, exact Decimal math."""
    d = Deduplicator()
    records = [_rec(IK_ALPHA, "PI3Kalpha", 7.0), _rec(IK_ALPHA, "PI3Kalpha", 7.4)]
    matrices = d.deduplicate(records)
    g = matrices[0].groups_for_isoform("PI3Kalpha")[0]
    assert g.conflict_status == GroupConflictStatus.RESOLVED_REPLICATE_MEDIAN
    assert g.resolved_value == Decimal("7.2")


def test_median_does_not_resolve_cheng_prusoff() -> None:
    """AUDITOR-5 remains untouched: no Km-based conversion is applied anywhere
    in this module, regardless of how many replicates are combined."""
    d = Deduplicator()
    records = [_rec(IK_ALPHA, "PI3Kalpha", 7.0), _rec(IK_ALPHA, "PI3Kalpha", 7.4)]
    matrices = d.deduplicate(records)
    g = matrices[0].groups_for_isoform("PI3Kalpha")[0]
    # The resolved value is a plain median of the reported values, not a
    # Cheng-Prusoff-adjusted quantity.
    assert g.resolved_value == Decimal("7.2")
    assert "Cheng" not in g.conflict_note
    assert "Km" not in g.conflict_note


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


def test_multiple_exact_median_contradicts_censored_bound() -> None:
    """The median of several exact values, not just a single exact value, is
    checked against a censoring bound for logical contradiction."""
    d = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 7.0, censoring=CensoringKind.EXACT),
        _rec(IK_ALPHA, "PI3Kalpha", 7.4, censoring=CensoringKind.EXACT),
        # median of {7.0, 7.4} = 7.2, which exceeds this right-censored bound
        _rec(IK_ALPHA, "PI3Kalpha", 5.0, censoring=CensoringKind.RIGHT_CENSORED),
    ]
    matrices = d.deduplicate(records)
    g = matrices[0].groups_for_isoform("PI3Kalpha")[0]
    assert g.conflict_status == GroupConflictStatus.LOGICAL_CONTRADICTION
    assert len(g.records) == 3


def test_multiple_exact_median_consistent_with_censored_bound() -> None:
    """Median of several exact values that IS consistent with a censored
    bound resolves to RESOLVED_REPLICATE_MEDIAN, retaining the censored record."""
    d = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 7.0, censoring=CensoringKind.EXACT),
        _rec(IK_ALPHA, "PI3Kalpha", 7.4, censoring=CensoringKind.EXACT),
        # median = 7.2, right-censored bound of 8.0 is not contradicted
        _rec(IK_ALPHA, "PI3Kalpha", 8.0, censoring=CensoringKind.RIGHT_CENSORED),
    ]
    matrices = d.deduplicate(records)
    g = matrices[0].groups_for_isoform("PI3Kalpha")[0]
    assert g.conflict_status == GroupConflictStatus.RESOLVED_REPLICATE_MEDIAN
    assert g.resolved_value == Decimal("7.2")
    assert len(g.records) == 3


# ── Exit criterion 7: policy recorded ─────────────────────────────────────────


def test_policy_recorded_on_every_group() -> None:
    d = Deduplicator()
    records = [_rec(IK_ALPHA, "PI3Kalpha", 7.0), _rec(IK_ALPHA, "PI3Kbeta", 5.5)]
    matrices = d.deduplicate(records)
    for group in matrices[0].groups:
        assert group.policy == Deduplicator.POLICY_ID
        assert group.policy != ""


def test_resolved_value_absent_for_ok_groups() -> None:
    """A group with a single distinct observation carries no resolved_value —
    there was nothing to combine."""
    d = Deduplicator()
    g = d.deduplicate([_rec(IK_ALPHA, "PI3Kalpha", 7.0)])[0].groups[0]
    assert g.conflict_status == GroupConflictStatus.OK
    assert g.resolved_value is None
    assert g.aggregation_method == ""


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


def test_unresolved_groups_helper_empty_after_gdr001() -> None:
    """RULE_MISSING is no longer produced; the replicate case now resolves."""
    d = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 7.0),
        _rec(IK_ALPHA, "PI3Kalpha", 7.5),  # now RESOLVED_REPLICATE_MEDIAN
        _rec(IK_ALPHA, "PI3Kbeta", 5.0),  # OK group
    ]
    matrices = d.deduplicate(records)
    m = matrices[0]
    assert m.unresolved_groups() == []
    alpha_group = m.groups_for_isoform("PI3Kalpha")[0]
    assert alpha_group.conflict_status == GroupConflictStatus.RESOLVED_REPLICATE_MEDIAN

"""SCI0-010 exit-criterion tests.

Exit criteria (docs/specifications/SCI0-001-refinement-data-acquisition.md
`SCI0-010` — Confidence scoring; Project Owner instructions, 2026-08-05):
  (1) Score decomposition is inspectable per record (named components,
      each with an applicability flag and a human-readable basis).
  (2) Rerun reproduces identical scores (pure function of inputs; no
      corpus-level statistics, nothing learned).
  (3) No component is coerced to a numeric value when it does not apply;
      it is marked `applicable=False` instead.
  (4) `assay_quality` and `literature_extraction_tier`'s numeric conversion
      are RULE_MISSING/GOVERNANCE_DECISION_REQUIRED — exposed, not invented.
  (5) SCI0-009 conflict status is surfaced via `context`, never resolved
      or hidden by the confidence score.
  (6) Evidence characteristics (isoform, tier, censoring, source identity,
      standardization status, stereochemistry) are preserved in `context`.
  (7) Nothing is filtered or discarded — this module only annotates.
  (8) The additive score is an equal-weight sum with no invented weights.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from orthosteric.data.harmonization._chem_standardizer import (
    StandardizationStatus,
    StandardizedStructure,
)
from orthosteric.data.harmonization._confidence import (
    POLICY_VERSION,
    ConfidenceComponent,
    ConfidenceScorer,
    CurationConfidence,
)
from orthosteric.data.harmonization._deduplicator import (
    Deduplicator,
    EvidenceRecord,
    GroupConflictStatus,
)
from orthosteric.data.models import ActivityRecord, CensoringKind, DataTier, SourceDB
from orthosteric.data.provenance.enums import (
    ExtractionTier,
    LicenseType,
    LocatorType,
    MeasurementClass,
    MeasurementType,
    SourceConfidence,
    SourceType,
    Tier,
    Unit,
)
from orthosteric.data.provenance.models import (
    AssayMetadata,
    ExtractionMetadata,
    ProvenanceRecord,
    PublicationMetadata,
    Quantity,
    SourceMetadata,
    SpanAnchor,
)

FIXED_TS = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)
IK_ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0"


def _get(conf: CurationConfidence, name: str) -> ConfidenceComponent:
    """`component()` narrowed to non-None for typed test assertions."""
    c = conf.component(name)
    assert c is not None, f"missing component {name!r}"
    return c


def _prov(
    *,
    accession: str = "CHEMBL_ASSAY_1",
    isoform: str | None = "PI3Kalpha",
    assay_id: str | None = "A1",
    source_type: SourceType = SourceType.CHEMBL,
    construct: str | None = None,
    atp_concentration: Quantity | None = None,
    publication: PublicationMetadata | None = None,
    extraction_tier: ExtractionTier | None = None,
    span_anchor: SpanAnchor | None = None,
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
        publication=publication,
        assay=AssayMetadata(
            assay_id=assay_id,
            assay_description="radiometric kinase assay",
            organism="Homo sapiens",
            target="PI3K",
            isoform=isoform,
            construct=construct,
            atp_concentration=atp_concentration,
            measurement_type=MeasurementType.IC50,
            measurement_class=MeasurementClass.BIOCHEMICAL,
        ),
        extraction=ExtractionMetadata(
            curator_version="curation-1.0.0",
            pipeline_version="pipeline-1.0.0",
            extraction_tier=extraction_tier,
            span_anchor=span_anchor,
            source_confidence=SourceConfidence.HIGH,
        ),
    )


def _rec(
    compound_id: str,
    isoform: str | None,
    value: float,
    *,
    censoring: CensoringKind = CensoringKind.EXACT,
    provenance: ProvenanceRecord | None = None,
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
    return EvidenceRecord(
        compound_id=compound_id,
        activity=activity,
        provenance=provenance if provenance is not None else _prov(isoform=isoform),
    )


FULL_PUBLICATION = PublicationMetadata(
    doi="10.1000/example",
    pmid="12345678",
    pmcid=None,
    journal="J. Med. Chem.",
    publication_year=2013,
)
BARE_PUBLICATION = PublicationMetadata(
    doi=None, pmid=None, pmcid=None, journal=None, publication_year=None
)


# ── Exit criterion 1 & 3: inspectable decomposition, no coercion ──────────────


def test_score_has_all_named_components() -> None:
    scorer = ConfidenceScorer()
    conf = scorer.score(_rec(IK_ALPHA, "PI3Kalpha", 7.0))
    names = {c.name for c in conf.components}
    assert names == {
        "metadata_completeness",
        "bibliographic_identification",
        "span_verification",
        "literature_extraction_tier",
        "assay_quality",
        "duplicate_agreement",
        "measurement_consistency",
    }


def test_inapplicable_components_are_not_coerced_to_zero() -> None:
    """A record with no publication, no literature context, and no SCI0-009
    group must mark those components applicable=False, value=None — never 0.0."""
    scorer = ConfidenceScorer()
    conf = scorer.score(_rec(IK_ALPHA, "PI3Kalpha", 7.0))  # no publication attached
    for name in (
        "bibliographic_identification",
        "span_verification",
        "literature_extraction_tier",
        "duplicate_agreement",
        "measurement_consistency",
    ):
        c = conf.component(name)
        assert c is not None
        assert c.applicable is False
        assert c.value is None


def test_bibliographic_identification_scored_when_publication_present() -> None:
    scorer = ConfidenceScorer()
    prov = _prov(publication=FULL_PUBLICATION)
    conf = scorer.score(_rec(IK_ALPHA, "PI3Kalpha", 7.0, provenance=prov))
    c = _get(conf, "bibliographic_identification")
    assert c.applicable is True
    assert c.value == 1.0


def test_bibliographic_identification_zero_when_no_doi_or_pmid() -> None:
    scorer = ConfidenceScorer()
    prov = _prov(publication=BARE_PUBLICATION)
    conf = scorer.score(_rec(IK_ALPHA, "PI3Kalpha", 7.0, provenance=prov))
    c = _get(conf, "bibliographic_identification")
    assert c.applicable is True
    assert c.value == 0.0


def test_metadata_completeness_counts_populated_fields() -> None:
    scorer = ConfidenceScorer()
    prov = _prov(
        construct="p110alpha/p85alpha",
        atp_concentration=Quantity(value=Decimal("10"), unit=Unit.MICROMOLAR),
    )
    conf = scorer.score(_rec(IK_ALPHA, "PI3Kalpha", 7.0, provenance=prov))
    c = _get(conf, "metadata_completeness")
    assert c.applicable is True
    # assay_id, assay_description, organism, isoform, construct, atp_concentration all populated
    assert c.value == 1.0


def test_span_verification_scored_for_literature_records() -> None:
    scorer = ConfidenceScorer()
    verified = SpanAnchor(
        locator_type=LocatorType.SUPPLEMENTARY_TABLE,
        locator_id="Table S3",
        row_or_line="14",
        verified=True,
    )
    prov = _prov(source_type=SourceType.LITERATURE, span_anchor=verified)
    conf = scorer.score(_rec(IK_ALPHA, "PI3Kalpha", 7.0, provenance=prov))
    c = _get(conf, "span_verification")
    assert c.applicable is True
    assert c.value == 1.0


def test_span_verification_zero_when_unverified() -> None:
    scorer = ConfidenceScorer()
    unverified = SpanAnchor(
        locator_type=LocatorType.FREE_TEXT, locator_id="p.3", row_or_line=None, verified=False
    )
    prov = _prov(source_type=SourceType.LITERATURE, span_anchor=unverified)
    conf = scorer.score(_rec(IK_ALPHA, "PI3Kalpha", 7.0, provenance=prov))
    c = _get(conf, "span_verification")
    assert c.applicable is True
    assert c.value == 0.0


# ── Exit criterion 4: RULE_MISSING exposed, not invented ──────────────────────


def test_assay_quality_is_rule_missing() -> None:
    scorer = ConfidenceScorer()
    conf = scorer.score(_rec(IK_ALPHA, "PI3Kalpha", 7.0))
    c = _get(conf, "assay_quality")
    assert c.applicable is False
    assert c.value is None
    assert "RULE_MISSING" in c.governance_note
    assert "assay_quality" in conf.governance_gaps()


def test_extraction_tier_exposed_as_category_not_scored() -> None:
    scorer = ConfidenceScorer()
    anchor = SpanAnchor(
        locator_type=LocatorType.MANUSCRIPT_TABLE,
        locator_id="Table 2",
        row_or_line="3",
        verified=True,
    )
    prov = _prov(
        source_type=SourceType.LITERATURE,
        extraction_tier=ExtractionTier.MANUSCRIPT_TABLE,
        span_anchor=anchor,
    )
    conf = scorer.score(_rec(IK_ALPHA, "PI3Kalpha", 7.0, provenance=prov))
    c = _get(conf, "literature_extraction_tier")
    assert c.applicable is True
    assert c.value is None, "no authorized ordinal-to-numeric mapping exists"
    assert "manuscript_table" in c.basis
    assert "RULE_MISSING" in c.governance_note
    assert "literature_extraction_tier" in conf.governance_gaps()
    # The category itself must not silently vanish from the additive sum's inputs:
    numeric_names = {
        comp.name for comp in conf.components if comp.applicable and comp.value is not None
    }
    assert "literature_extraction_tier" not in numeric_names


# ── Exit criterion 5: SCI0-009 conflict surfaced, never resolved here ─────────


def test_duplicate_agreement_reflects_sci0009_conflict_status() -> None:
    scorer = ConfidenceScorer()
    dedup = Deduplicator()
    records = [_rec(IK_ALPHA, "PI3Kalpha", 7.0), _rec(IK_ALPHA, "PI3Kalpha", 7.5)]
    group = dedup.deduplicate(records)[0].groups[0]
    assert group.conflict_status == GroupConflictStatus.RULE_MISSING

    conf = scorer.score(records[0], group=group)
    dup = _get(conf, "duplicate_agreement")
    cons = _get(conf, "measurement_consistency")
    assert dup.applicable is True
    assert dup.value == 0.0  # disagreement surfaced, not hidden
    assert cons.applicable is True
    assert cons.value == 1.0  # RULE_MISSING is not a *logical* contradiction
    assert conf.context.conflict_status == "rule_missing"
    assert "RULE_MISSING" in conf.context.conflict_governance_note


def test_duplicate_agreement_positive_when_group_agrees() -> None:
    scorer = ConfidenceScorer()
    dedup = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 7.0),
        _rec(IK_ALPHA, "PI3Kalpha", 7.0),
    ]  # literal duplicates
    group = dedup.deduplicate(records)[0].groups[0]
    assert group.conflict_status == GroupConflictStatus.OK

    conf = scorer.score(records[0], group=group)
    dup = _get(conf, "duplicate_agreement")
    assert dup.applicable is True
    assert dup.value == 1.0


def test_measurement_consistency_zero_on_logical_contradiction() -> None:
    scorer = ConfidenceScorer()
    dedup = Deduplicator()
    records = [
        _rec(IK_ALPHA, "PI3Kalpha", 7.0, censoring=CensoringKind.EXACT),
        _rec(IK_ALPHA, "PI3Kalpha", 5.0, censoring=CensoringKind.RIGHT_CENSORED),
    ]
    group = dedup.deduplicate(records)[0].groups[0]
    assert group.conflict_status == GroupConflictStatus.LOGICAL_CONTRADICTION

    conf = scorer.score(records[0], group=group)
    assert _get(conf, "measurement_consistency").value == 0.0
    assert _get(conf, "duplicate_agreement").value == 0.0


def test_no_group_supplied_leaves_conflict_components_inapplicable() -> None:
    scorer = ConfidenceScorer()
    conf = scorer.score(_rec(IK_ALPHA, "PI3Kalpha", 7.0), group=None)
    assert _get(conf, "duplicate_agreement").applicable is False
    assert _get(conf, "measurement_consistency").applicable is False
    assert conf.context.conflict_status is None


# ── Exit criterion 6: evidence characteristics preserved in context ──────────


def test_context_preserves_evidence_characteristics() -> None:
    scorer = ConfidenceScorer()
    structure = StandardizedStructure(
        original_smiles="C[C@H](N)C(=O)O",
        canonical_smiles="C[C@H](N)C(=O)O",
        inchi="InChI=1S/...",
        inchikey="QNAYBMKLOCPYGJ-REOHCLBHSA-N",
        status=StandardizationStatus.OK,
        failure_reason=None,
        rdkit_version="2026.3.5",
        content_hash="deadbeef",
        stereochemistry_preserved=True,
        salt_stripped=False,
        steps_applied=("sanitize", "canonicalize"),
    )
    rec = _rec(IK_ALPHA, "PI3Kdelta", 7.0, censoring=CensoringKind.RIGHT_CENSORED)
    conf = scorer.score(rec, standardized_structure=structure, structural_admissibility="PDB")
    ctx = conf.context
    assert ctx.compound_id == IK_ALPHA
    assert ctx.isoform == "PI3Kdelta"
    assert ctx.censoring == str(CensoringKind.RIGHT_CENSORED)
    assert ctx.data_tier == str(Tier.TIER_1)
    assert ctx.source_type == str(SourceType.CHEMBL)
    assert ctx.chemical_standardization_status == "ok"
    assert ctx.stereochemistry_preserved is True
    assert ctx.structural_admissibility == "PDB"


# ── Exit criterion 2 & 8: determinism, reproducibility, equal-weight sum ──────


def test_scoring_is_deterministic() -> None:
    scorer = ConfidenceScorer()
    prov = _prov(publication=FULL_PUBLICATION)
    rec = _rec(IK_ALPHA, "PI3Kalpha", 7.0, provenance=prov)
    conf_a = scorer.score(rec)
    conf_b = scorer.score(rec)
    assert conf_a.additive_score == conf_b.additive_score
    assert conf_a.max_possible_score == conf_b.max_possible_score
    assert conf_a.components == conf_b.components


def test_additive_score_is_equal_weight_sum() -> None:
    scorer = ConfidenceScorer()
    prov = _prov(publication=FULL_PUBLICATION)
    rec = _rec(IK_ALPHA, "PI3Kalpha", 7.0, provenance=prov)
    conf = scorer.score(rec)
    numeric = [c.value for c in conf.components if c.applicable and c.value is not None]
    assert conf.additive_score == sum(numeric)
    assert conf.max_possible_score == float(len(numeric))


def test_policy_version_recorded() -> None:
    scorer = ConfidenceScorer()
    conf = scorer.score(_rec(IK_ALPHA, "PI3Kalpha", 7.0))
    assert conf.policy_version == POLICY_VERSION
    assert conf.policy_version != ""

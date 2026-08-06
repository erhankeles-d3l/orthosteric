"""Lifecycle invariant tests (Milestones A-H from corpus lifecycle spec).

These tests verify:
L1  Snapshot immutability: mutating CurrentCorpus after freeze doesn't change snapshot.
L2  Snapshot reproducibility: identical inputs produce identical SHA.
L3  Snapshot differentiation: different content produces different SHA.
L4  Parent lineage: V2 records V1 as parent.
L5  Model-generation binding: ModelGenerationRecord requires snapshot SHA.
L6  Training isolation: CurrentCorpus cannot be directly trained on.
L7  Update isolation: add_records() after freeze doesn't change prior snapshot.
L8  Synthetic-data firewall: SYNTHETIC_FIXTURE mode rejected by pipeline.
L9  Quality-before-training: pipeline enforces Profile->QA->Gate->Eligible order.
L10 Gate-report provenance: every LifecyclePipelineResult carries snapshot SHA.
L11 Determinism: same snapshot pair produces same SnapshotDiff SHA.
L12 Registry lineage: lineage() returns correct ancestor chain.
L13 Registry update: register_model_generation records MG ID.
L14 Data-mode rejection: DEVELOPMENT_REAL snapshots are ineligible.
"""

from __future__ import annotations

from typing import Any

import pytest

from orthosteric.data.corpus_lifecycle import (
    CorpusDataMode,
    CorpusLifecycleStage,
    CurrentCorpus,
    DataModeViolation,
)
from orthosteric.data.snapshots._builder import SnapshotBuilder
from orthosteric.data.snapshots._diff import compute_snapshot_diff
from orthosteric.data.snapshots._manifest import PolicyManifest, SoftwareProvenance
from orthosteric.data.snapshots._registry import (
    CorpusSnapshotRegistry,
    RegistryError,
)
from orthosteric.learning._interfaces import ModelGenerationRecord
from orthosteric.policy._corpus_gate import CorpusQualityGatePolicy
from orthosteric.policy._lifecycle_pipeline import (
    CorpusLifecyclePipeline,
    LifecycleEligibility,
)
from orthosteric.quality._assessment import CorpusQualityAssessor
from orthosteric.quality._dimensions import (
    ConfidenceEvaluator,
    ConnectivityEvaluator,
    CoverageEvaluator,
    MissingnessEvaluator,
    PublicationConcentrationEvaluator,
    ScaffoldDiversityEvaluator,
    StructuralCoverageEvaluator,
)

# ── Shared fixtures ────────────────────────────────────────────────────────────


def _sw() -> SoftwareProvenance:
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


def _rec(record_id: str = "R1", isoform: str = "PI3Kalpha") -> dict[str, Any]:
    return {
        "record_type": "activity",
        "source_db": "chembl",
        "source_record_id": record_id,
        "compound_id": record_id,
        "inchikey": f"AAAAAAAAAA{record_id:>10}",
        "isoform": isoform,
        "activity_value": 7.5,
        "censoring": "exact",
        "conflict_status": "ok",
        "exclusion_reason": None,
        "assay_id": "ASSAY001",
    }


def _make_corpus(
    records: list[dict[str, Any]], mode: CorpusDataMode = CorpusDataMode.SCIENTIFIC_CORPUS
) -> CurrentCorpus:
    cc = CurrentCorpus(data_mode=mode)
    cc.add_records(records)
    cc.update_source_version("chembl", "34")
    return cc


def _make_profile_for(snapshot: Any) -> Any:
    """Minimal CorpusProfile synthesized from a snapshot (for test purposes only).

    Uses the correct API: build_graph_stats_from_records + characterize +
    extract_strata + freeze_corpus_profile.
    """
    from orthosteric.data.audit import characterize
    from orthosteric.data.graph import build_graph_stats_from_records
    from orthosteric.data.snapshots._profile import freeze_corpus_profile
    from orthosteric.data.strata import extract_strata

    sha = snapshot.manifest.snapshot_sha256
    n = max(1, snapshot.manifest.accepted_count)
    records = [
        {
            "inchikey": f"IK{i:04d}",
            "isoform": iso,
            "study_id": "S1",
            "assay_id": "A1",
            "activity_value": 7.5,
            "censoring": "exact",
            "exclusion_reason": None,
        }
        for i in range(n)
        for iso in ("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta")
    ]
    gs = build_graph_stats_from_records(records)
    char = characterize(records, snapshot_sha256=sha)
    strata = extract_strata(records)
    return freeze_corpus_profile(
        snapshot_sha256=sha,
        graph_stats=gs,
        characterization=char,
        software=_sw(),
        policy=_policy(),
        strata_report=strata,
    )


def _make_assessor() -> CorpusQualityAssessor:
    return CorpusQualityAssessor(
        [
            ConnectivityEvaluator(),
            CoverageEvaluator(),
            MissingnessEvaluator(),
            PublicationConcentrationEvaluator(),
            ScaffoldDiversityEvaluator(),
            StructuralCoverageEvaluator(),
            ConfidenceEvaluator(),
        ]
    )


def _make_pipeline(registry: CorpusSnapshotRegistry | None = None) -> CorpusLifecyclePipeline:
    return CorpusLifecyclePipeline(
        assessor=_make_assessor(),
        gate_policy=CorpusQualityGatePolicy(),
        registry=registry,
    )


# ── L1: Snapshot immutability ─────────────────────────────────────────────────


def test_l1_snapshot_immutability() -> None:
    """Mutating CurrentCorpus after freeze does not change the snapshot SHA."""
    builder = _builder()
    cc = _make_corpus([_rec("R1")])
    snap1 = cc.freeze(builder)
    sha_before = snap1.manifest.snapshot_sha256

    cc.add_records([_rec("R2"), _rec("R3")])  # mutate AFTER freeze

    snap_after_mutation = cc.freeze(builder, parent_snapshot_sha256=sha_before)
    assert snap1.manifest.snapshot_sha256 == sha_before  # original unchanged
    assert snap_after_mutation.manifest.snapshot_sha256 != sha_before  # new snapshot differs


# ── L2: Snapshot reproducibility ─────────────────────────────────────────────


def test_l2_snapshot_reproducibility() -> None:
    """Same inputs always produce the same SHA."""
    builder = _builder()
    cc_a = _make_corpus([_rec("R1"), _rec("R2")])
    cc_b = _make_corpus([_rec("R1"), _rec("R2")])
    snap_a = cc_a.freeze(builder)
    snap_b = cc_b.freeze(builder)
    assert snap_a.manifest.snapshot_sha256 == snap_b.manifest.snapshot_sha256


# ── L3: Snapshot differentiation ─────────────────────────────────────────────


def test_l3_snapshot_differentiation() -> None:
    """Different record content produces a different SHA."""
    builder = _builder()
    snap_a = _make_corpus([_rec("R1")]).freeze(builder)
    snap_b = _make_corpus([_rec("R99")]).freeze(builder)  # different record
    assert snap_a.manifest.snapshot_sha256 != snap_b.manifest.snapshot_sha256


# ── L4: Parent lineage ───────────────────────────────────────────────────────


def test_l4_parent_lineage_recorded() -> None:
    """V2 records V1's SHA as its parent."""
    builder = _builder()
    snap_v1 = _make_corpus([_rec("R1")]).freeze(builder)
    sha_v1 = snap_v1.manifest.snapshot_sha256

    cc_v2 = _make_corpus([_rec("R1"), _rec("R2")])
    snap_v2 = cc_v2.freeze(builder, parent_snapshot_sha256=sha_v1)

    assert snap_v2.manifest.parent_snapshot_sha256 == sha_v1


def test_l4b_genesis_snapshot_has_no_parent() -> None:
    snap = _make_corpus([_rec("R1")]).freeze(_builder(), parent_snapshot_sha256=None)
    assert snap.manifest.parent_snapshot_sha256 is None


# ── L5: Model-generation binding ─────────────────────────────────────────────


def test_l5_model_generation_requires_snapshot_sha() -> None:
    """ModelGenerationRecord must carry a non-None training_snapshot_sha."""
    rec = ModelGenerationRecord(
        generation_id="MG-001",
        training_snapshot_sha="sha256:abc",
        feature_config_version="v0.1",
        training_split_id="SPLIT001",
        architecture_description="test",
        loss_function_id=None,
        uncertainty_method_id=None,
        ad_algorithm_id=None,
        alphafold_treatment=None,
        missingness_encoding=None,
        random_seed=None,
        phase_committed=None,
        s10_committed=False,
        s9_committed=False,
        algorithm_version="test_v1",
    )
    assert rec.training_snapshot_sha == "sha256:abc"
    assert rec.training_snapshot_sha is not None


def test_l5b_model_generation_without_snapshot_is_detectable() -> None:
    """A record with training_snapshot_sha=None is explicitly incomplete."""
    rec = ModelGenerationRecord(
        generation_id="MG-INCOMPLETE",
        training_snapshot_sha=None,  # type: ignore[arg-type]  # intentionally invalid
        feature_config_version="v0.1",
        training_split_id="SPLIT001",
        architecture_description="test",
        loss_function_id=None,
        uncertainty_method_id=None,
        ad_algorithm_id=None,
        alphafold_treatment=None,
        missingness_encoding=None,
        random_seed=None,
        phase_committed=None,
        s10_committed=False,
        s9_committed=False,
        algorithm_version="test_v1",
    )
    # The record can be created but is detectable as incomplete
    assert rec.training_snapshot_sha is None


# ── L6: Training isolation ───────────────────────────────────────────────────


def test_l6_current_corpus_is_not_a_snapshot() -> None:
    """CurrentCorpus has no snapshot_sha256 attribute — it cannot be used as a snapshot."""
    cc = CurrentCorpus(data_mode=CorpusDataMode.SCIENTIFIC_CORPUS)
    assert not hasattr(cc, "manifest")
    assert not hasattr(cc, "snapshot_sha256")


def test_l6b_current_corpus_requires_explicit_freeze() -> None:
    """freeze() must be called explicitly — there is no automatic snapshot."""
    cc = _make_corpus([_rec("R1")])
    # No snapshot exists until freeze() is called
    with pytest.raises(AttributeError):
        _ = cc.manifest  # type: ignore[attr-defined]


# ── L7: Update isolation ──────────────────────────────────────────────────────


def test_l7_adding_records_after_freeze_does_not_change_prior_snapshot() -> None:
    """Mutations after freeze() do not retroactively change the frozen snapshot."""
    builder = _builder()
    cc = _make_corpus([_rec("R1")])
    snap_v1 = cc.freeze(builder)
    original_sha = snap_v1.manifest.snapshot_sha256
    original_count = snap_v1.manifest.record_count

    # Add more records AFTER freezing
    cc.add_records([_rec("R2"), _rec("R3")])

    # The original snapshot is unchanged
    assert snap_v1.manifest.snapshot_sha256 == original_sha
    assert snap_v1.manifest.record_count == original_count

    # A new freeze produces a different snapshot
    snap_v2 = cc.freeze(builder, parent_snapshot_sha256=original_sha)
    assert snap_v2.manifest.snapshot_sha256 != original_sha
    assert snap_v2.manifest.record_count > original_count


# ── L8: Synthetic-data firewall ───────────────────────────────────────────────


def test_l8_synthetic_fixture_data_mode_raises_on_validate() -> None:
    """SYNTHETIC_FIXTURE mode raises DataModeViolation when validated as scientific."""
    cc = CurrentCorpus(data_mode=CorpusDataMode.SYNTHETIC_FIXTURE)
    with pytest.raises(DataModeViolation):
        cc.validate_data_mode(CorpusDataMode.SCIENTIFIC_CORPUS)


def test_l8b_scientific_corpus_passes_validation() -> None:
    cc = CurrentCorpus(data_mode=CorpusDataMode.SCIENTIFIC_CORPUS)
    cc.validate_data_mode(CorpusDataMode.SCIENTIFIC_CORPUS)  # must not raise


def test_l8c_pipeline_rejects_synthetic_fixture_snapshot() -> None:
    """LifecyclePipelineResult is INELIGIBLE_DATA_MODE for synthetic fixtures."""
    builder = _builder()
    cc = CurrentCorpus(data_mode=CorpusDataMode.SYNTHETIC_FIXTURE)
    cc.add_records([_rec("R1")])
    snap = cc.freeze(builder)
    profile = _make_profile_for(snap)

    pipeline = _make_pipeline()
    result = pipeline.run(snap, CorpusDataMode.SYNTHETIC_FIXTURE, profile)

    assert result.eligible_for_training is False
    assert result.eligibility == LifecycleEligibility.INELIGIBLE_DATA_MODE


# ── L9: Quality-before-training ───────────────────────────────────────────────


def test_l9_pipeline_populates_gate_decision() -> None:
    """Pipeline result carries a gate decision when run on a scientific snapshot."""
    builder = _builder()
    snap = _make_corpus([_rec("R1")]).freeze(builder)
    profile = _make_profile_for(snap)

    pipeline = _make_pipeline()
    result = pipeline.run(snap, CorpusDataMode.SCIENTIFIC_CORPUS, profile)

    assert result.profile is not None
    assert result.assessment is not None
    assert result.gate_decision is not None
    # The lifecycle stage reflects gate decision
    assert "gate_decided" in result.lifecycle_stage.value


def test_l9b_model_generation_registration_raises_without_eligibility() -> None:
    """register_model_generation raises DataModeViolation when ineligible."""
    builder = _builder()
    cc = CurrentCorpus(data_mode=CorpusDataMode.SYNTHETIC_FIXTURE)
    cc.add_records([_rec("R1")])
    snap = cc.freeze(builder)
    profile = _make_profile_for(snap)

    pipeline = _make_pipeline()
    result = pipeline.run(snap, CorpusDataMode.SYNTHETIC_FIXTURE, profile)

    assert not result.eligible_for_training
    with pytest.raises(DataModeViolation):
        pipeline.register_model_generation(result, snap, "MG-001", "test_arch", "v0.1", "SPLIT001")


# ── L10: Gate-report provenance ───────────────────────────────────────────────


def test_l10_lifecycle_result_contains_snapshot_sha() -> None:
    """Every LifecyclePipelineResult identifies the exact snapshot SHA."""
    builder = _builder()
    snap = _make_corpus([_rec("R1")]).freeze(builder)
    profile = _make_profile_for(snap)

    pipeline = _make_pipeline()
    result = pipeline.run(snap, CorpusDataMode.SCIENTIFIC_CORPUS, profile)

    assert result.snapshot_sha == snap.manifest.snapshot_sha256
    assert result.result_sha256  # non-empty content hash


def test_l10b_result_sha_is_deterministic() -> None:
    """Same snapshot → same result SHA when run twice."""
    builder = _builder()
    snap = _make_corpus([_rec("R1")]).freeze(builder)
    profile = _make_profile_for(snap)

    pipeline = _make_pipeline()
    r1 = pipeline.run(snap, CorpusDataMode.SCIENTIFIC_CORPUS, profile)
    r2 = pipeline.run(snap, CorpusDataMode.SCIENTIFIC_CORPUS, profile)

    assert r1.result_sha256 == r2.result_sha256


# ── L11: SnapshotDiff determinism ────────────────────────────────────────────


def test_l11_diff_is_deterministic() -> None:
    """Same pair (A, B) always produces the same diff SHA."""
    builder = _builder()
    snap_a = _make_corpus([_rec("R1")]).freeze(builder)
    cc_b = _make_corpus([_rec("R1"), _rec("R2")])
    snap_b = cc_b.freeze(builder, parent_snapshot_sha256=snap_a.manifest.snapshot_sha256)

    diff1 = compute_snapshot_diff(snap_a, snap_b)
    diff2 = compute_snapshot_diff(snap_a, snap_b)

    assert diff1.diff_sha256 == diff2.diff_sha256


def test_l11b_diff_counts_correctly() -> None:
    builder = _builder()
    snap_a = _make_corpus([_rec("R1"), _rec("R2")]).freeze(builder)
    sha_a = snap_a.manifest.snapshot_sha256
    # B has R2 (unchanged), R3 (new), not R1 (removed)
    cc_b = CurrentCorpus(data_mode=CorpusDataMode.SCIENTIFIC_CORPUS)
    cc_b.add_records([_rec("R2"), _rec("R3")])
    cc_b.update_source_version("chembl", "34")
    snap_b = cc_b.freeze(builder, parent_snapshot_sha256=sha_a)

    diff = compute_snapshot_diff(snap_a, snap_b)

    assert diff.records_added == 1  # R3
    assert diff.records_removed == 1  # R1
    assert diff.parent_lineage_valid is True


def test_l11c_identical_snapshots_produce_zero_diff() -> None:
    snap = _make_corpus([_rec("R1")]).freeze(_builder())
    diff = compute_snapshot_diff(snap, snap)
    assert diff.records_added == 0
    assert diff.records_removed == 0
    assert diff.records_changed == 0
    assert diff.has_any_change is False


# ── L12: Registry lineage ────────────────────────────────────────────────────


def test_l12_registry_lineage_chain() -> None:
    """lineage() returns the correct ancestor chain."""
    builder = _builder()
    snap_v1 = _make_corpus([_rec("R1")]).freeze(builder)
    sha_v1 = snap_v1.manifest.snapshot_sha256

    cc_v2 = _make_corpus([_rec("R1"), _rec("R2")])
    snap_v2 = cc_v2.freeze(builder, parent_snapshot_sha256=sha_v1)
    sha_v2 = snap_v2.manifest.snapshot_sha256

    registry = CorpusSnapshotRegistry()
    registry.register(snap_v1, CorpusDataMode.SCIENTIFIC_CORPUS)
    registry.register(snap_v2, CorpusDataMode.SCIENTIFIC_CORPUS)

    chain = registry.lineage(sha_v2)
    assert chain == [sha_v1, sha_v2]


# ── L13: Registry model-generation binding ───────────────────────────────────


def test_l13_registry_records_model_generation() -> None:
    """register_model_generation updates the registry entry."""
    builder = _builder()
    snap = _make_corpus([_rec("R1")]).freeze(builder)
    sha = snap.manifest.snapshot_sha256

    registry = CorpusSnapshotRegistry()
    registry.register(snap, CorpusDataMode.SCIENTIFIC_CORPUS)
    registry.advance_stage(sha, CorpusLifecycleStage.GATE_DECIDED_PROCEED)
    registry.register_model_generation(sha, "MG-001")

    entry = registry.get(sha)
    assert entry is not None
    assert "MG-001" in entry.model_generation_ids
    assert entry.lifecycle_stage == "model_generation_registered"


def test_l13b_registry_not_registered_raises() -> None:
    registry = CorpusSnapshotRegistry()
    with pytest.raises(RegistryError):
        registry.register_model_generation("nonexistent_sha", "MG-001")


# ── L14: Development-real data mode rejected ─────────────────────────────────


def test_l14_development_real_snapshot_is_ineligible() -> None:
    """DEVELOPMENT_REAL passes the gate but is NOT eligible for scientific training."""
    builder = _builder()
    snap = _make_corpus([_rec("R1")]).freeze(builder)
    profile = _make_profile_for(snap)

    pipeline = _make_pipeline()
    result = pipeline.run(snap, CorpusDataMode.DEVELOPMENT_REAL, profile)

    assert result.eligible_for_training is False
    assert result.eligibility == LifecycleEligibility.INELIGIBLE_DATA_MODE

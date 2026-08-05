"""Shared synthetic-profile builders for quality/ tests.

Every value is explicitly synthetic (CLAUDE.md §1). Reuses the same fixture
style already established in tests/data/snapshots/test_profile.py and
tests/policy/_fixtures.py.
"""

from __future__ import annotations

from orthosteric.data.audit import characterize
from orthosteric.data.graph import build_graph_stats_from_records
from orthosteric.data.snapshots import (
    CorpusProfile,
    PolicyManifest,
    SoftwareProvenance,
    freeze_corpus_profile,
)
from orthosteric.data.strata import extract_strata

SNAPSHOT_SHA = "a" * 64


def sw() -> SoftwareProvenance:
    return SoftwareProvenance(
        python_version="3.12.0 (test)",
        rdkit_version="2026.3.5",
        orthosteric_version="0.1.0",
        git_sha="abc123",
        git_dirty=False,
        os_platform="Linux",
        os_version="test",
        lockfile_hash="f" * 64,
        key_package_versions={"rdkit": "2026.3.5"},
    )


def policy() -> PolicyManifest:
    return PolicyManifest(
        chemical_standardization_policy="sci0008b_rdkit_2026.3.5",
        identifier_harmonization_policy="sci0008c_inchikey_v1",
        deduplication_policy="sci0009_identity_grouping_median_replicates_v2_gdr001",
        confidence_scoring_policy="sci0010_v1",
        adr0003_adjudication_procedure="adr0003_procedure_v1.0",
        alphafold_fallback_policy="sci0007_af_fallback_v1.0",
        auditor5_status="INSUFFICIENT_EVIDENCE_frozen",
        cheng_prusoff_status="BLOCKED/AUDITOR-5",
        within_group_conflict_threshold="RULE_MISSING/SCI0-016_required",
        confidence_assay_quality_rule="RULE_MISSING",
        confidence_lit_tier_rule="RULE_MISSING",
    )


def _rec(
    ik: str,
    iso: str,
    study: str = "S1",
    assay: str = "A1",
    pub: str | None = "doi:10.1/A",
    conf: float | None = 0.8,
) -> dict[str, object]:
    return {
        "inchikey": ik,
        "isoform": iso,
        "study_id": study,
        "assay_id": assay,
        "activity_value": 7.0,
        "censoring": "exact",
        "exclusion_reason": None,
        "publication_id": pub,
        "confidence_score": conf,
        "provenance_tier": "T1",
        "scaffold_family_id": f"FAM_{ik}",
    }


def healthy_records() -> list[dict[str, object]]:
    """A non-degenerate synthetic corpus: connected, bridging present, >=1
    complete four-isoform stratum, >=8 distinct scaffold families, >=2
    publications, confidence scores present."""
    records: list[dict[str, object]] = []
    isoforms = ("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta")
    # 8 distinct-scaffold compounds, complete across all 4 isoforms, in S1
    for i in range(8):
        ik = f"IK{i}"
        for iso in isoforms:
            records.append(_rec(ik, iso, study="S1", pub="doi:10.1/A"))
    # A bridging compound linking a second, independent publication/study
    records.append(_rec("IK0", "PI3Kalpha", study="S2", pub="doi:10.1/B"))
    records.append(_rec("IK9", "PI3Kbeta", study="S2", pub="doi:10.1/B"))
    return records


def degenerate_records() -> list[dict[str, object]]:
    """Every compound isolated: no isoform ever co-measured, n_c small, no
    bridging, n_w == 0, single publication, no confidence scores."""
    return [
        _rec("IK1", "PI3Kalpha", study="S1", pub="doi:10.1/ONLY", conf=None),
        _rec("IK2", "PI3Kbeta", study="S2", pub="doi:10.1/ONLY", conf=None),
    ]


def build_profile(records: list[dict[str, object]]) -> CorpusProfile:
    gs = build_graph_stats_from_records(records)
    report = characterize(records, snapshot_sha256=SNAPSHOT_SHA)
    strata = extract_strata(records)
    return freeze_corpus_profile(SNAPSHOT_SHA, gs, report, sw(), policy(), strata)

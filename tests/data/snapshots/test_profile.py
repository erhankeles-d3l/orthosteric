"""GDR-002 exit-criterion tests for the corpus profile.

Exit criteria (GDR-002):
  (1) N_c, N_b, N_w are computed deterministically from an already-frozen
      snapshot's characteristics, never re-derived from raw records here.
  (2) Two profiles from identical inputs yield an identical profile_sha256;
      the freeze timestamp does not affect it.
  (3) A change to the snapshot, software, policy, or algorithm version
      changes profile_sha256.
  (4) CorpusProfile is frozen (immutable).
  (5) The N_w compound-vs-strata ambiguity is recorded under two distinct
      names, never silently collapsed to one.
  (6) The scaffold-diversity-in-largest-component gap is recorded as None,
      never fabricated or silently substituted with the corpus-global count.
  (7) Software and policy provenance are embedded (reused from SCI0-011),
      not redefined.
"""

from __future__ import annotations

import dataclasses
import inspect
import json

import pytest

from orthosteric.data.audit import characterize
from orthosteric.data.graph import build_graph_stats_from_records
from orthosteric.data.snapshots import (
    CORPUS_PROFILE_SCHEMA_VERSION,
    PROFILE_ALGORITHM_VERSION,
    CorpusProfile,
    PolicyManifest,
    SoftwareProvenance,
    freeze_corpus_profile,
)
from orthosteric.data.strata import extract_strata

SNAPSHOT_SHA = "a" * 64


def _sw() -> SoftwareProvenance:
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


def _policy() -> PolicyManifest:
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


def _rec(ik: str, iso: str, study: str = "S1", assay: str = "A1") -> dict[str, object]:
    return {
        "inchikey": ik,
        "isoform": iso,
        "study_id": study,
        "assay_id": assay,
        "activity_value": 7.0,
        "censoring": "exact",
        "exclusion_reason": None,
    }


def _synthetic_records() -> list[dict[str, object]]:
    """A small four-isoform-complete synthetic corpus, entirely fabricated for
    testing (CLAUDE.md §1: no real data, no scientific claim implied)."""
    records = []
    for ik in ("IK1", "IK2"):
        for iso in ("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"):
            records.append(_rec(ik, iso, study="S1", assay="A1"))
    # A bridging compound linking a second study
    records.append(_rec("IK1", "PI3Kalpha", study="S2", assay="A1"))
    records.append(_rec("IK3", "PI3Kbeta", study="S2", assay="A1"))
    return records


def _profile(snapshot_sha: str = SNAPSHOT_SHA) -> CorpusProfile:
    records = _synthetic_records()
    gs = build_graph_stats_from_records(records)
    report = characterize(records, snapshot_sha256=snapshot_sha)
    strata = extract_strata(records)
    return freeze_corpus_profile(
        snapshot_sha256=snapshot_sha,
        graph_stats=gs,
        characterization=report,
        software=_sw(),
        policy=_policy(),
        strata_report=strata,
    )


# ── Exit criterion 1: computed from already-frozen characteristics ──────────


def test_engineering_parameters_match_graph_stats() -> None:
    records = _synthetic_records()
    gs = build_graph_stats_from_records(records)
    profile = _profile()
    ep = profile.engineering_parameters
    assert ep.n_c == gs.largest_connected_component
    assert ep.n_b == gs.bridging_compounds
    assert ep.n_w == gs.within_study_four_isoform
    assert ep.n_connected_components == gs.n_connected_components


def test_freeze_corpus_profile_signature_requires_precomputed_inputs() -> None:
    """No raw-record parameter exists on the function at all."""
    params = set(inspect.signature(freeze_corpus_profile).parameters)
    assert "records" not in params
    assert {"graph_stats", "characterization"}.issubset(params)


# ── Exit criterion 2 & 3: determinism and sensitivity ────────────────────────


def test_same_inputs_same_profile_hash() -> None:
    p1 = _profile()
    p2 = _profile()
    assert p1.profile_sha256 == p2.profile_sha256


def test_frozen_at_utc_excluded_from_hash() -> None:
    p1 = _profile()
    p2 = _profile()
    # frozen_at_utc may legitimately differ across calls (wall clock); the
    # hash must not, because it is excluded from the hashed payload.
    assert p1.profile_sha256 == p2.profile_sha256
    assert p1.frozen_at_utc != ""


def test_different_snapshot_sha_changes_profile_hash() -> None:
    p1 = _profile(snapshot_sha="a" * 64)
    p2 = _profile(snapshot_sha="b" * 64)
    assert p1.profile_sha256 != p2.profile_sha256


def test_different_software_changes_profile_hash() -> None:
    records = _synthetic_records()
    gs = build_graph_stats_from_records(records)
    report = characterize(records, snapshot_sha256=SNAPSHOT_SHA)
    strata = extract_strata(records)
    sw1 = _sw()
    sw2 = SoftwareProvenance(
        python_version=sw1.python_version,
        rdkit_version="2099.1.0",  # different toolchain version
        orthosteric_version=sw1.orthosteric_version,
        git_sha=sw1.git_sha,
        git_dirty=sw1.git_dirty,
        os_platform=sw1.os_platform,
        os_version=sw1.os_version,
        lockfile_hash=sw1.lockfile_hash,
        key_package_versions=sw1.key_package_versions,
    )
    p1 = freeze_corpus_profile(SNAPSHOT_SHA, gs, report, sw1, _policy(), strata)
    p2 = freeze_corpus_profile(SNAPSHOT_SHA, gs, report, sw2, _policy(), strata)
    assert p1.profile_sha256 != p2.profile_sha256


def test_different_policy_changes_profile_hash() -> None:
    records = _synthetic_records()
    gs = build_graph_stats_from_records(records)
    report = characterize(records, snapshot_sha256=SNAPSHOT_SHA)
    strata = extract_strata(records)
    p1_policy = _policy()
    p2_fields = dataclasses.asdict(p1_policy)
    p2_fields["deduplication_policy"] = "sci0009_hypothetical_v3"
    p2_policy = PolicyManifest(**p2_fields)
    p1 = freeze_corpus_profile(SNAPSHOT_SHA, gs, report, _sw(), p1_policy, strata)
    p2 = freeze_corpus_profile(SNAPSHOT_SHA, gs, report, _sw(), p2_policy, strata)
    assert p1.profile_sha256 != p2.profile_sha256


def test_algorithm_version_is_pinned() -> None:
    """A change to the computation method must be a deliberate, visible edit."""
    assert PROFILE_ALGORITHM_VERSION == "corpus_profile_algorithm_v1_gdr002"
    assert CORPUS_PROFILE_SCHEMA_VERSION == "corpus_profile_v1_gdr002"
    profile = _profile()
    assert profile.profile_algorithm_version == PROFILE_ALGORITHM_VERSION
    assert profile.schema_version == CORPUS_PROFILE_SCHEMA_VERSION


def test_different_corpus_changes_engineering_parameters_and_hash() -> None:
    """Changing the corpus creates a different profile, per GDR-002 freeze policy."""
    p1 = _profile()
    bigger_records = _synthetic_records() + [
        _rec("IK4", iso, study="S1", assay="A1")
        for iso in ("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta")
    ]
    gs2 = build_graph_stats_from_records(bigger_records)
    report2 = characterize(bigger_records, snapshot_sha256=SNAPSHOT_SHA)
    strata2 = extract_strata(bigger_records)
    p2 = freeze_corpus_profile(SNAPSHOT_SHA, gs2, report2, _sw(), _policy(), strata2)
    assert p1.engineering_parameters.n_c != p2.engineering_parameters.n_c
    assert p1.profile_sha256 != p2.profile_sha256


# ── Exit criterion 4: immutability ───────────────────────────────────────────


def test_corpus_profile_is_frozen() -> None:
    profile = _profile()
    with pytest.raises((AttributeError, TypeError)):
        profile.profile_sha256 = "tampered"  # type: ignore[misc]


def test_engineering_parameters_is_frozen() -> None:
    profile = _profile()
    with pytest.raises((AttributeError, TypeError)):
        profile.engineering_parameters.n_c = 999  # type: ignore[misc]


# ── Exit criterion 5: N_w compound-vs-strata ambiguity recorded distinctly ───


def test_n_w_and_n_complete_strata_are_distinct_fields() -> None:
    """GDR-002 §3: two units, two names, neither silently collapsed."""
    profile = _profile()
    ep = profile.engineering_parameters
    assert hasattr(ep, "n_w")
    assert hasattr(ep, "n_complete_strata")
    # In this synthetic corpus they happen to differ in general (compounds vs
    # panels are different units); the key guarantee is that both are present
    # and independently computed, not that they must differ numerically.
    records = _synthetic_records()
    strata = extract_strata(records)
    assert ep.n_complete_strata == strata.usable_strata


def test_n_complete_strata_defaults_to_zero_without_strata_report() -> None:
    """A profile can be frozen without a StratumReport; it is not required."""
    records = _synthetic_records()
    gs = build_graph_stats_from_records(records)
    report = characterize(records, snapshot_sha256=SNAPSHOT_SHA)
    profile = freeze_corpus_profile(SNAPSHOT_SHA, gs, report, _sw(), _policy(), strata_report=None)
    assert profile.engineering_parameters.n_complete_strata == 0


# ── Exit criterion 6: scaffold-diversity gap never fabricated ───────────────


def test_scaffold_families_in_largest_component_is_none_not_fabricated() -> None:
    profile = _profile()
    assert profile.engineering_parameters.scaffold_families_in_largest_component is None


def test_scaffold_gap_not_silently_substituted_with_corpus_global_count() -> None:
    """The corpus-global scaffold count exists on the characterization report
    but must never be copied into the component-restricted field."""
    profile = _profile()
    global_count = profile.characterization.scaffold_stats.n_ring_system_families
    component_restricted = profile.engineering_parameters.scaffold_families_in_largest_component
    assert component_restricted is None
    assert component_restricted != global_count  # None != int is always true, but explicit


# ── Exit criterion 7: provenance reused, not redefined ───────────────────────


def test_software_and_policy_are_embedded_verbatim() -> None:
    sw = _sw()
    policy = _policy()
    records = _synthetic_records()
    gs = build_graph_stats_from_records(records)
    report = characterize(records, snapshot_sha256=SNAPSHOT_SHA)
    profile = freeze_corpus_profile(SNAPSHOT_SHA, gs, report, sw, policy, None)
    assert profile.software is sw
    assert profile.policy is policy
    assert profile.software.rdkit_version == "2026.3.5"
    assert profile.policy.deduplication_policy == (
        "sci0009_identity_grouping_median_replicates_v2_gdr001"
    )


def test_to_dict_is_json_serializable() -> None:
    profile = _profile()
    assert json.loads(json.dumps(profile.to_dict()))["profile_sha256"] == profile.profile_sha256


def test_characterization_report_embedded_wholesale() -> None:
    """SCI0-014b's report -- dataset stats, connectivity, scaffold, publication
    concentration -- must all be present, per GDR-002's frozen-profile content
    requirement."""
    profile = _profile()
    c = profile.characterization
    assert c.isoform_stats
    assert c.scaffold_stats is not None
    assert c.connectivity is not None
    assert c.publication_stats is not None

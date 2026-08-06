"""Tests for GDR-004 phase commitment governance invariants.

Verifies that:
1. GDR-004 file exists and is non-empty.
2. ModelGenerationRecord correctly represents Core+Extension phase.
3. S9 and S10 remain conditionally gated (not automatically committed).
4. Extension-only items are correctly flagged.

These tests encode the frozen commitments from GDR-004 at the code level.
"""

from __future__ import annotations

import pathlib

from orthosteric.learning._interfaces import (
    BindingEvidence,
    DegeneracyTestStatus,
    JointUncertaintyMethod,
    ModelGenerationRecord,
)

_REPO_ROOT = pathlib.Path(__file__).parents[2]
_GDR_004 = (
    _REPO_ROOT
    / "docs"
    / "governance"
    / "decision-records"
    / "GDR-004-sci2-phase-commitment-core-plus-extension.md"
)


# ── G1-G5: GDR-004 file exists and is valid ──────────────────────────────────


def test_g1_gdr004_file_exists() -> None:
    """GDR-004 must exist -- it is the phase-commitment governance record."""
    assert _GDR_004.exists(), f"GDR-004 not found: {_GDR_004}"


def test_g2_gdr004_is_non_empty() -> None:
    content = _GDR_004.read_text()
    assert len(content) > 500, "GDR-004 is too short to be a valid governance record"


def test_g3_gdr004_states_phase_commitment() -> None:
    content = _GDR_004.read_text()
    assert "Core + Extension" in content or "Core+Extension" in content


def test_g4_gdr004_not_full_scope() -> None:
    content = _GDR_004.read_text()
    assert "NOT committed to Phase 3" in content or "NOT commit" in content


def test_g5_gdr004_selectivity_tiers_downstream() -> None:
    """Decision Policy tiers must be stated as downstream of model inference."""
    content = _GDR_004.read_text()
    # The tiers should appear alongside "NOT be training targets" or equivalent
    assert "training target" in content.lower() or "MUST NOT be training" in content


# ── G6-G10: ModelGenerationRecord reflects phase governance ──────────────────


def _core_extension_generation() -> ModelGenerationRecord:
    """Minimal generation record reflecting Core+Extension commitment."""
    return ModelGenerationRecord(
        generation_id="GEN_PLACEHOLDER",
        training_snapshot_sha="PENDING_SCI0011",
        feature_config_version="v0.1-rule_missing",
        training_split_id="PENDING_SPLIT",
        architecture_description="placeholder_pending_GDR-005_to_GDR-009",
        loss_function_id=None,  # BLOCKED: GDR-009 (loss form) not yet filed
        uncertainty_method_id=None,  # BLOCKED: GDR-007 not yet filed
        ad_algorithm_id=None,  # BLOCKED: GDR-005 not yet filed
        alphafold_treatment=None,  # BLOCKED: GDR-006 not yet filed
        missingness_encoding="ordinal_plus_unavailable_mask",  # ENGINEERING_CHOICE
        random_seed=None,
        phase_committed="Core+Extension",
        s10_committed=False,  # Phase 2 committed but S10 CONDITIONAL on GGR-002e
        s9_committed=False,  # Phase 2 committed but S9 CONDITIONAL on GGR-002d
        algorithm_version="sci2_interfaces_v1_sci2001",
    )


def test_g6_phase_committed_can_be_set() -> None:
    """Phase commitment can be recorded in the model generation record."""
    rec = _core_extension_generation()
    assert rec.phase_committed == "Core+Extension"


def test_g7_s10_remains_conditional_in_core_extension() -> None:
    """S10 is in Extension scope but conditional on GGR-002e prerequisites."""
    rec = _core_extension_generation()
    assert rec.s10_committed is False, (
        "S10 must remain False until mutation sites and protocol are sealed "
        "(GDR-004 §15 Extension item 15)"
    )


def test_g8_s9_remains_conditional_in_core_extension() -> None:
    """S9 is in Extension scope but conditional on S9 rule-set sealing."""
    rec = _core_extension_generation()
    assert rec.s9_committed is False, (
        "S9 must remain False until S9 reference rule set is sealed (GDR-004 §14 Extension item 14)"
    )


def test_g9_blocked_fields_are_none() -> None:
    """GDR-required fields must be None until their GDRs are filed."""
    rec = _core_extension_generation()
    # These are all GDR_REQUIRED per GDR-004 disposition table
    assert rec.loss_function_id is None, "GDR-009 (loss form) not yet filed"
    assert rec.uncertainty_method_id is None, "GDR-007 not yet filed"
    assert rec.ad_algorithm_id is None, "GDR-005 not yet filed"
    assert rec.alphafold_treatment is None, "GDR-006 not yet filed"


def test_g10_missingness_encoding_engineering_choice_can_be_set() -> None:
    """GGR-006 is an engineering choice; ordinal+mask may be set without a GDR."""
    rec = _core_extension_generation()
    assert rec.missingness_encoding == "ordinal_plus_unavailable_mask"


# ── G11-G13: DegeneracyTestStatus vocabulary for degeneracy battery ──────────


def test_g11_degeneracy_test_status_vocabulary() -> None:
    """DegeneracyTestStatus must have all required states."""
    vals = {s.value for s in DegeneracyTestStatus}
    assert "pass" in vals
    assert "fail" in vals
    assert "not_run" in vals
    assert "not_applicable" in vals  # used for Phase 3 tests in Core+Extension


def test_g12_binding_evidence_vocabulary_complete() -> None:
    """BindingEvidence vocabulary covers all three Constitution §2.2 states."""
    vals = {e.value for e in BindingEvidence}
    assert vals == {"productive", "non_productive", "indeterminate"}


def test_g13_joint_uncertainty_no_min_rule() -> None:
    """Constitution §2.4: conjunction product, NOT min-rule. No min_rule value."""
    vals = {m.value for m in JointUncertaintyMethod}
    assert "min_rule" not in vals

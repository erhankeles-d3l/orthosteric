"""Governance invariant tests for GDR-005 through GDR-009.

These tests verify that:
1. All five GDR documents exist with the expected algorithm identifiers.
2. Algorithm constants in _interfaces.py match the GDR decisions.
3. LOSS_N_OUTPUT_HEADS == 4 (frozen by Constitution §4.2(2)).
4. LOSS_EQUAL_WEIGHT == 1.0 (frozen by §4.2(2) symmetric-evidence).
5. ModelGenerationRecord can be constructed with all five governed fields set.
6. No model-implementation files exist (SCI2-002 not yet authorized).

These tests do NOT test model training, loss computation, or AD evaluation.
"""

from __future__ import annotations

import pathlib

import pytest

from orthosteric.learning import (
    AD_ALGORITHM_GDR,
    AD_ALGORITHM_ID,
    AD_COVERAGE_PERCENTILE,
    ALPHAFOLD_TREATMENT_GDR,
    ALPHAFOLD_TREATMENT_ID,
    CENSORED_LIKELIHOOD_GDR,
    CENSORED_LIKELIHOOD_ID,
    LOSS_EQUAL_WEIGHT,
    LOSS_FUNCTION_GDR,
    LOSS_FUNCTION_ID,
    LOSS_N_OUTPUT_HEADS,
    UNCERTAINTY_COVERAGE,
    UNCERTAINTY_METHOD_GDR,
    UNCERTAINTY_METHOD_ID,
    UNCERTAINTY_Z_95,
    VALIDATION_PROTOCOL_ID,
)
from orthosteric.learning._interfaces import ModelGenerationRecord

REPO = pathlib.Path(__file__).parent.parent.parent
DECISION_RECORDS_DIR = REPO / "docs" / "governance" / "decision-records"
LEARNING_SRC = REPO / "src" / "orthosteric" / "learning"


# ---- helpers -----------------------------------------------------------------


def _gdr_text(filename: str) -> str:
    path = DECISION_RECORDS_DIR / filename
    assert path.exists(), f"Missing: {path}"
    return path.read_text()


# ---- G1-G5: GDR documents exist and are Accepted ----------------------------


def test_g1_gdr005_exists_and_is_accepted() -> None:
    txt = _gdr_text("GDR-005-sci2-applicability-domain-algorithm.md")
    assert "Accepted" in txt


def test_g2_gdr006_exists_and_is_accepted() -> None:
    txt = _gdr_text("GDR-006-sci2-alphafold-model-treatment.md")
    assert "Accepted" in txt


def test_g3_gdr007_exists_and_is_accepted() -> None:
    txt = _gdr_text("GDR-007-sci2-uncertainty-representation.md")
    assert "Accepted" in txt


def test_g4_gdr008_exists_and_is_accepted() -> None:
    txt = _gdr_text("GDR-008-sci2-censored-likelihood-form.md")
    assert "Accepted" in txt


def test_g5_gdr009_exists_and_is_accepted() -> None:
    txt = _gdr_text("GDR-009-sci2-loss-function-and-validation-protocol.md")
    assert "Accepted" in txt


# ---- G6-G10: Algorithm identifiers match GDR decisions ----------------------


def test_g6_ad_algorithm_id_matches_gdr005() -> None:
    assert AD_ALGORITHM_ID == "leverage_knn_tanimoto_95pct_v1"
    assert AD_ALGORITHM_GDR == "GDR-005"
    txt = _gdr_text("GDR-005-sci2-applicability-domain-algorithm.md")
    assert AD_ALGORITHM_ID in txt


def test_g7_alphafold_treatment_matches_gdr006() -> None:
    assert ALPHAFOLD_TREATMENT_ID == "alphafold_include_source_indicator_v1"
    assert ALPHAFOLD_TREATMENT_GDR == "GDR-006"
    txt = _gdr_text("GDR-006-sci2-alphafold-model-treatment.md")
    assert ALPHAFOLD_TREATMENT_ID in txt


def test_g8_uncertainty_method_matches_gdr007() -> None:
    assert UNCERTAINTY_METHOD_ID == "heteroscedastic_gaussian_v1"
    assert UNCERTAINTY_METHOD_GDR == "GDR-007"
    assert pytest.approx(0.95) == UNCERTAINTY_COVERAGE
    assert pytest.approx(1.96) == UNCERTAINTY_Z_95
    txt = _gdr_text("GDR-007-sci2-uncertainty-representation.md")
    assert UNCERTAINTY_METHOD_ID in txt


def test_g9_censored_likelihood_matches_gdr008() -> None:
    assert CENSORED_LIKELIHOOD_ID == "tobit1_censored_normal_v1"
    assert CENSORED_LIKELIHOOD_GDR == "GDR-008"
    txt = _gdr_text("GDR-008-sci2-censored-likelihood-form.md")
    assert CENSORED_LIKELIHOOD_ID in txt


def test_g10_loss_function_matches_gdr009() -> None:
    assert LOSS_FUNCTION_ID == "tobit1_gaussian_nll_equal_weight_v1"
    assert LOSS_FUNCTION_GDR == "GDR-009"
    assert VALIDATION_PROTOCOL_ID == "scaffold_loso_cv_v1"
    txt = _gdr_text("GDR-009-sci2-loss-function-and-validation-protocol.md")
    assert LOSS_FUNCTION_ID in txt
    assert VALIDATION_PROTOCOL_ID in txt


# ---- G11-G13: Frozen constitution invariants --------------------------------


def test_g11_loss_heads_frozen_at_four() -> None:
    """Constitution §4.2(2): four heads = pAct_alpha + 3 Delta axes. FROZEN."""
    assert LOSS_N_OUTPUT_HEADS == 4, (
        "LOSS_N_OUTPUT_HEADS must be exactly 4 (Constitution §4.2(2)): "
        "pAct_alpha + Delta_alpha_beta + Delta_alpha_gamma + Delta_alpha_delta"
    )


def test_g12_equal_weight_frozen() -> None:
    """Constitution §4.2(2) symmetric evidence: all heads equal weight. FROZEN."""
    assert pytest.approx(1.0) == LOSS_EQUAL_WEIGHT, (
        "LOSS_EQUAL_WEIGHT must be 1.0 (Constitution §4.2(2) symmetric evidence)"
    )


def test_g13_ad_coverage_percentile() -> None:
    """GDR-005: 95th-percentile threshold."""
    assert pytest.approx(95.0) == AD_COVERAGE_PERCENTILE


# ---- G14-G15: ModelGenerationRecord accepts all five governed fields ---------


def test_g14_model_generation_record_with_five_governed_fields() -> None:
    rec = ModelGenerationRecord(
        generation_id="GEN_TEST_001",
        training_snapshot_sha="sha256:abc",
        feature_config_version="v0.1-test",
        training_split_id="SPLIT_TEST",
        architecture_description="test_placeholder",
        loss_function_id=LOSS_FUNCTION_ID,
        uncertainty_method_id=UNCERTAINTY_METHOD_ID,
        ad_algorithm_id=AD_ALGORITHM_ID,
        alphafold_treatment=ALPHAFOLD_TREATMENT_ID,
        missingness_encoding="ordinal_plus_mask_v1",
        random_seed=42,
        phase_committed="Core+Extension",
        s10_committed=False,
        s9_committed=False,
        algorithm_version="test_v1",
    )
    assert rec.loss_function_id == LOSS_FUNCTION_ID
    assert rec.uncertainty_method_id == UNCERTAINTY_METHOD_ID
    assert rec.ad_algorithm_id == AD_ALGORITHM_ID
    assert rec.alphafold_treatment == ALPHAFOLD_TREATMENT_ID
    assert rec.missingness_encoding == "ordinal_plus_mask_v1"


def test_g15_model_generation_record_none_fields_valid_pre_training() -> None:
    rec = ModelGenerationRecord(
        generation_id="GEN_PRE_TRAINING",
        training_snapshot_sha="sha256:def",
        feature_config_version="v0.1-test",
        training_split_id="SPLIT_TEST",
        architecture_description="not_yet_implemented",
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
    assert rec.generation_id == "GEN_PRE_TRAINING"
    assert rec.loss_function_id is None


# ---- G16: No SCI2-002 implementation files exist ----------------------------


def test_g16_no_model_implementation_files_exist() -> None:
    """SCI2-002 is not yet authorized. Only _interfaces.py and __init__.py allowed."""
    authorized_files = {"_interfaces.py", "__init__.py"}
    learning_files = {p.name for p in LEARNING_SRC.iterdir() if p.is_file()}
    unauthorized = learning_files - authorized_files
    assert not unauthorized, (
        f"Unauthorized learning/ files exist (SCI2-002 not authorized): {unauthorized}"
    )


# ---- G17-G19: Cross-GDR consistency ----------------------------------------


def test_g17_gdr007_gdr008_gaussian_consistency() -> None:
    """GDR-007 (Gaussian uncertainty) and GDR-008 (Tobit-1 censored normal)
    must reference the same underlying Normal distribution."""
    txt7 = _gdr_text("GDR-007-sci2-uncertainty-representation.md")
    txt8 = _gdr_text("GDR-008-sci2-censored-likelihood-form.md")
    assert "Gaussian" in txt7 or "Normal" in txt7
    assert "Normal" in txt8


def test_g18_gdr009_loss_references_gdr008() -> None:
    txt9 = _gdr_text("GDR-009-sci2-loss-function-and-validation-protocol.md")
    assert "GDR-008" in txt9


def test_g19_gdr009_mentions_symmetric_objective_section42() -> None:
    txt9 = _gdr_text("GDR-009-sci2-loss-function-and-validation-protocol.md")
    assert "4.2" in txt9

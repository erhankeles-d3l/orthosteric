"""SCI2-001 interface schema tests.

Verifies structural invariants of the SCI-2 input/output contract
without implementing the model. Tests encode frozen scientific
requirements from SCI2-001 §2--§4.

Exit criteria I1-I20.
"""

from __future__ import annotations

import pytest

from orthosteric.learning._interfaces import (
    INTERFACES_ALGORITHM_VERSION,
    ApplicabilityDomainResult,
    BindingEvidence,
    ComparativeInput,
    ComparativePrediction,
    IsoformEvidence,
    JointUncertaintyMethod,
    MissingnessFlag,
    ModelGenerationRecord,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _iso(isoform: str = "PI3Kalpha", available: bool = True) -> IsoformEvidence:
    return IsoformEvidence(
        isoform=isoform,
        structure_record_id="REC001" if available else None,
        features=None,
        is_alphafold=False,
        all_unavailable=not available,
        conformational_state="ligand_bound",
        algorithm_version="test_v1",
    )


def _ad(gen_id: str = "GEN001") -> ApplicabilityDomainResult:
    return ApplicabilityDomainResult(
        compound_id="CMP001",
        in_ad_alpha=True,
        in_ad_beta=True,
        in_ad_gamma=True,
        in_ad_delta=True,
        in_ad_lr_vs_beta=True,
        in_ad_lr_vs_gamma=True,
        in_ad_lr_vs_delta=True,
        ad_algorithm="RULE_MISSING",
        model_generation_id=gen_id,
        algorithm_version="test_v1",
    )


def _pred(
    alpha_bc: BindingEvidence = BindingEvidence.PRODUCTIVE,
    beta_bc: BindingEvidence = BindingEvidence.NON_PRODUCTIVE,
) -> ComparativePrediction:
    return ComparativePrediction(
        compound_id="CMP001",
        predicted_lr_vs_beta=2.0,
        predicted_lr_vs_gamma=1.5,
        predicted_lr_vs_delta=1.0,
        predicted_pac_alpha=8.0,
        uncertainty_lr_vs_beta=None,
        uncertainty_lr_vs_gamma=None,
        uncertainty_lr_vs_delta=None,
        uncertainty_pac_alpha=None,
        alpha_binding=alpha_bc,
        beta_binding=beta_bc,
        gamma_binding=BindingEvidence.NON_PRODUCTIVE,
        delta_binding=BindingEvidence.NON_PRODUCTIVE,
        applicability_domain=_ad(),
        joint_uncertainty_method=JointUncertaintyMethod.NOT_SPECIFIED,
        model_generation_id="GEN001",
        training_snapshot_sha="abc123",
        feature_config_version="v0.1-rule_missing",
        training_split_id="SPLIT001",
        alpha_structure_source="pdb:1E8X",
        beta_structure_source="pdb:3K3E",
        gamma_structure_source="pdb:1E9X",
        delta_structure_source="alphafold:P48736",
        algorithm_version="test_v1",
    )


# ── I1-I5: MissingnessFlag vocabulary (Constitution §4.2(5), §2.2) ───────────


def test_i1_missingness_flag_five_states() -> None:
    vals = {f.value for f in MissingnessFlag}
    assert vals == {"observed", "candidate", "absent", "unavailable", "not_applicable"}


def test_i2_unavailable_distinct_from_absent() -> None:
    """FROZEN: UNAVAILABLE != ABSENT."""
    # Mypy "non-overlapping" is exactly the point -- they ARE distinct
    assert MissingnessFlag.UNAVAILABLE.value == "unavailable"
    assert MissingnessFlag.ABSENT.value == "absent"
    assert MissingnessFlag.UNAVAILABLE.value != MissingnessFlag.ABSENT.value  # type: ignore[comparison-overlap]


def test_i3_not_applicable_distinct_from_absent() -> None:
    """FROZEN: NOT_APPLICABLE != ABSENT."""
    assert MissingnessFlag.NOT_APPLICABLE.value != MissingnessFlag.ABSENT.value  # type: ignore[comparison-overlap]


def test_i4_unavailable_not_applicable_have_distinct_values() -> None:
    """Both map to ordinal 0 in encoding but carry distinct string identities."""
    assert MissingnessFlag.UNAVAILABLE.value == "unavailable"
    assert MissingnessFlag.NOT_APPLICABLE.value == "not_applicable"
    assert MissingnessFlag.UNAVAILABLE.value != MissingnessFlag.ABSENT.value  # type: ignore[comparison-overlap]
    assert MissingnessFlag.NOT_APPLICABLE.value != MissingnessFlag.ABSENT.value  # type: ignore[comparison-overlap]


def test_i5_algorithm_version_pinned() -> None:
    assert INTERFACES_ALGORITHM_VERSION == "sci2_interfaces_v1_sci2001"


# ── I6-I9: IsoformEvidence ────────────────────────────────────────────────────


def test_i6_isoform_evidence_is_frozen() -> None:
    with pytest.raises((AttributeError, TypeError)):
        _iso().isoform = "tampered"  # type: ignore[misc]


def test_i7_unavailable_isoform_has_none_record() -> None:
    iso = _iso(available=False)
    assert iso.all_unavailable is True
    assert iso.structure_record_id is None
    assert iso.features is None


def test_i8_alphafold_flag_propagated() -> None:
    iso = IsoformEvidence(
        isoform="PI3Kdelta",
        structure_record_id="AF_P48736",
        features=None,
        is_alphafold=True,
        all_unavailable=False,
        conformational_state="unknown",
        algorithm_version="test_v1",
    )
    assert iso.is_alphafold is True


def test_i9_experimental_not_alphafold_by_default() -> None:
    assert _iso().is_alphafold is False


# ── I10-I13: ComparativeInput ─────────────────────────────────────────────────


def test_i10_comparative_input_requires_four_isoforms() -> None:
    """Constitution §4.1: all four isoforms jointly -- not independently."""
    ci = ComparativeInput(
        compound_id="CMP001",
        ligand_inchikey="TESTIK001",
        alpha=_iso("PI3Kalpha"),
        beta=_iso("PI3Kbeta"),
        gamma=_iso("PI3Kgamma"),
        delta=_iso("PI3Kdelta"),
        activity_target=None,
        training_snapshot_sha="sha:abc",
        feature_config_version="v0.1-rule_missing",
        split_id="SPLIT001",
        algorithm_version="test_v1",
    )
    assert ci.alpha.isoform == "PI3Kalpha"
    assert ci.beta.isoform == "PI3Kbeta"
    assert ci.gamma.isoform == "PI3Kgamma"
    assert ci.delta.isoform == "PI3Kdelta"


def test_i11_n_isoforms_available_counts_correctly() -> None:
    ci = ComparativeInput(
        compound_id="CMP001",
        ligand_inchikey=None,
        alpha=_iso(available=True),
        beta=_iso(available=False),
        gamma=_iso(available=True),
        delta=_iso(available=True),
        activity_target=None,
        training_snapshot_sha=None,
        feature_config_version="v0.1",
        split_id=None,
        algorithm_version="test_v1",
    )
    assert ci.n_isoforms_available == 3


def test_i12_any_alphafold_flag_propagates() -> None:
    af_iso = IsoformEvidence(
        isoform="PI3Kdelta",
        structure_record_id="AF_001",
        features=None,
        is_alphafold=True,
        all_unavailable=False,
        conformational_state="unknown",
        algorithm_version="test_v1",
    )
    ci = ComparativeInput(
        compound_id="CMP001",
        ligand_inchikey=None,
        alpha=_iso(),
        beta=_iso(),
        gamma=_iso(),
        delta=af_iso,
        activity_target=None,
        training_snapshot_sha=None,
        feature_config_version="v0.1",
        split_id=None,
        algorithm_version="test_v1",
    )
    assert ci.any_alphafold is True


def test_i13_comparative_input_is_frozen() -> None:
    ci = ComparativeInput(
        compound_id="CMP001",
        ligand_inchikey=None,
        alpha=_iso(),
        beta=_iso(),
        gamma=_iso(),
        delta=_iso(),
        activity_target=None,
        training_snapshot_sha=None,
        feature_config_version="v0.1",
        split_id=None,
        algorithm_version="test_v1",
    )
    with pytest.raises((AttributeError, TypeError)):
        ci.compound_id = "tampered"  # type: ignore[misc]


# ── I14-I18: ComparativePrediction ────────────────────────────────────────────


def test_i14_prediction_is_frozen() -> None:
    with pytest.raises((AttributeError, TypeError)):
        _pred().compound_id = "tampered"  # type: ignore[misc]


def test_i15_prediction_carries_direct_log_ratios() -> None:
    """Constitution §4.2(1): direct log-ratio predictions, not absolute potencies."""
    pred = _pred()
    assert pred.predicted_lr_vs_beta is not None
    assert pred.predicted_lr_vs_gamma is not None
    assert pred.predicted_lr_vs_delta is not None


def test_i16_indeterminate_propagated_and_identifiable() -> None:
    """Constitution §2.2: INDETERMINATE is a distinct classification."""
    pred = _pred(beta_bc=BindingEvidence.INDETERMINATE)
    assert pred.beta_binding == BindingEvidence.INDETERMINATE
    assert pred.any_isoform_indeterminate is True


def test_i17_alphafold_source_detectable_in_prediction() -> None:
    """AlphaFold source must be explicitly labeled in prediction provenance."""
    pred = _pred()
    assert pred.any_alphafold_source is True  # delta uses alphafold: in helper
    assert pred.delta_structure_source.startswith("alphafold:")


def test_i18_prediction_deterministic_hash() -> None:
    h1 = _pred().content_sha256()
    h2 = _pred().content_sha256()
    assert h1 == h2


# ── I19-I20: AD and phase governance ─────────────────────────────────────────


def test_i19_per_target_ad_separate_flags() -> None:
    """Constitution §4.2(4): per-target AD, not a single molecule flag."""
    ad = ApplicabilityDomainResult(
        compound_id="CMP001",
        in_ad_alpha=True,
        in_ad_beta=False,  # beta out of AD
        in_ad_gamma=True,
        in_ad_delta=True,
        in_ad_lr_vs_beta=False,
        in_ad_lr_vs_gamma=True,
        in_ad_lr_vs_delta=True,
        ad_algorithm="RULE_MISSING",
        model_generation_id="GEN001",
        algorithm_version="test_v1",
    )
    assert ad.in_ad_alpha is True
    assert ad.in_ad_beta is False
    assert ad.any_out_of_ad is True


def test_i20_model_generation_phase_fields_not_committed() -> None:
    """Phase 2 items must be explicitly marked not committed until governance resolves."""
    rec = ModelGenerationRecord(
        generation_id="GEN001",
        training_snapshot_sha="sha256:abc",
        feature_config_version="v0.1",
        training_split_id="SPLIT001",
        architecture_description="placeholder",
        loss_function_id=None,  # RULE_MISSING until GGR-003
        uncertainty_method_id=None,  # RULE_MISSING until GGR-007
        ad_algorithm_id=None,  # RULE_MISSING until GGR-004
        alphafold_treatment=None,  # RULE_MISSING until GGR-005
        missingness_encoding=None,  # RULE_MISSING until GGR-006 confirmed
        random_seed=None,
        phase_committed=None,  # NOT YET COMMITTED
        s10_committed=False,  # Phase 2 not committed
        s9_committed=False,  # Phase 2 not committed
        algorithm_version="test_v1",
    )
    assert rec.phase_committed is None
    assert rec.s10_committed is False
    assert rec.s9_committed is False
    assert rec.loss_function_id is None


# ── BindingEvidence vocabulary ────────────────────────────────────────────────


def test_binding_evidence_three_classes() -> None:
    vals = {e.value for e in BindingEvidence}
    assert vals == {"productive", "non_productive", "indeterminate"}


def test_indeterminate_not_non_productive() -> None:
    """FROZEN: INDETERMINATE != NON_PRODUCTIVE -- distinct contribution."""
    # These ARE non-overlapping -- that's the point
    assert BindingEvidence.INDETERMINATE.value != BindingEvidence.NON_PRODUCTIVE.value  # type: ignore[comparison-overlap]


def test_joint_uncertainty_not_min_rule_documented() -> None:
    """Constitution §2.4: conjunction product, not min. NOT_SPECIFIED != min rule."""
    # The min-rule is ABSENT from the vocabulary -- there is no "min_rule" value
    vals = {m.value for m in JointUncertaintyMethod}
    assert "min_rule" not in vals
    assert "independent_product" in vals
    assert "frechet_lower" in vals

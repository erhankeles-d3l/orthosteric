"""SCI1-007 and SCI1-008 tests: MD interface stubs and FeatureConfig.

Exit criteria M1-M12 (MD interface) and C1-C12 (FeatureConfig).
"""

from __future__ import annotations

import pytest

from orthosteric.features import (
    FEATURE_CONFIG_ALGORITHM_VERSION,
    MD_INTERFACE_ALGORITHM_VERSION,
    ConformationalStateLabel,
    FeatureConfig,
    InteractionPersistence,
    MDFeaturePlaceholder,
    MDStatus,
    WaterOccupancy,
    default_feature_config,
)
from orthosteric.features._contact_map import ContactMapConfig
from orthosteric.features._interaction_fingerprint import FingerprintConfig
from orthosteric.features._structural_graph import StructuralGraphConfig

# ══════════════════════════════════════════════════════════════════════════════
# MD interface tests (M1-M12)
# ══════════════════════════════════════════════════════════════════════════════


def test_m1_md_feature_placeholder_is_frozen() -> None:
    ph = MDFeaturePlaceholder.not_computed("REC001", "PI3Kalpha")
    with pytest.raises((AttributeError, TypeError)):
        ph.isoform = "tampered"  # type: ignore[misc]


def test_m2_algorithm_version_pinned() -> None:
    assert MD_INTERFACE_ALGORITHM_VERSION == "md_interface_v1_sci1007"


def test_m3_not_computed_status() -> None:
    ph = MDFeaturePlaceholder.not_computed("REC001", "PI3Kalpha")
    assert ph.ensemble_metadata.status == MDStatus.NOT_COMPUTED
    assert not ph.is_computed()


def test_m4_not_computed_fields_are_none() -> None:
    ph = MDFeaturePlaceholder.not_computed("REC001", "PI3Kalpha")
    assert ph.ensemble_metadata.n_replicates is None
    assert ph.ensemble_metadata.simulation_time_ns is None
    assert ph.ensemble_metadata.force_field is None
    assert ph.ensemble_metadata.converged is None


def test_m5_conformational_state_unknown_by_default() -> None:
    ph = MDFeaturePlaceholder.not_computed("REC001", "PI3Kalpha")
    assert ph.conformational_state == ConformationalStateLabel.UNKNOWN


def test_m6_phase_note_non_empty() -> None:
    ph = MDFeaturePlaceholder.not_computed("REC001", "PI3Kalpha")
    assert "PHASE_3_REQUIRED" in ph.phase_note


def test_m7_interaction_persistence_not_computed() -> None:
    ip = InteractionPersistence.not_computed(859, "A_859_ ", "hydrogen_bond")
    assert ip.status == MDStatus.NOT_COMPUTED
    assert ip.fraction_occupied is None
    assert ip.canonical_position == 859


def test_m8_water_occupancy_not_computed() -> None:
    wo = WaterOccupancy.not_computed("hinge_water_1")
    assert wo.status == MDStatus.NOT_COMPUTED
    assert wo.occupancy_fraction is None
    assert wo.water_site_label == "hinge_water_1"


def test_m9_md_status_vocabulary() -> None:
    vals = {s.value for s in MDStatus}
    assert "not_computed" in vals
    assert "computed" in vals
    assert "insufficient_sampling" in vals
    assert "inadmissible" in vals


def test_m10_conformational_state_vocabulary() -> None:
    vals = {s.value for s in ConformationalStateLabel}
    assert "specificity_open" in vals
    assert "ligand_bound" in vals
    assert "apo_closed" in vals


def test_m11_hash_deterministic() -> None:
    h1 = MDFeaturePlaceholder.not_computed("REC001", "PI3Kalpha").content_sha256()
    h2 = MDFeaturePlaceholder.not_computed("REC001", "PI3Kalpha").content_sha256()
    assert h1 == h2


def test_m12_different_isoform_different_hash() -> None:
    h1 = MDFeaturePlaceholder.not_computed("REC001", "PI3Kalpha").content_sha256()
    h2 = MDFeaturePlaceholder.not_computed("REC001", "PI3Kdelta").content_sha256()
    assert h1 != h2


# ══════════════════════════════════════════════════════════════════════════════
# FeatureConfig tests (C1-C12)
# ══════════════════════════════════════════════════════════════════════════════


def test_c1_feature_config_is_frozen() -> None:
    cfg = FeatureConfig()
    with pytest.raises((AttributeError, TypeError)):
        cfg.hbond_da_cutoff_angstrom = 3.5  # type: ignore[misc]


def test_c2_algorithm_version_pinned() -> None:
    assert FEATURE_CONFIG_ALGORITHM_VERSION == "feature_config_v1_sci1008"


def test_c3_default_all_thresholds_rule_missing() -> None:
    cfg = default_feature_config()
    assert cfg.all_thresholds_rule_missing()


def test_c4_partial_threshold_not_all_rule_missing() -> None:
    cfg = FeatureConfig(hbond_da_cutoff_angstrom=3.5)
    assert not cfg.all_thresholds_rule_missing()


def test_c5_fingerprint_config_derived_correctly() -> None:
    cfg = FeatureConfig(
        hbond_da_cutoff_angstrom=3.5,
        hydrophobic_cutoff_angstrom=4.0,
    )
    fp_cfg = cfg.fingerprint_config()
    assert isinstance(fp_cfg, FingerprintConfig)
    assert fp_cfg.hbond_da_cutoff_angstrom == 3.5
    assert fp_cfg.hydrophobic_cutoff_angstrom == 4.0
    assert fp_cfg.salt_bridge_cutoff_angstrom is None  # not set


def test_c6_contact_map_config_derived() -> None:
    cfg = FeatureConfig(contact_cutoff_angstrom=5.0)
    cm_cfg = cfg.contact_map_config()
    assert isinstance(cm_cfg, ContactMapConfig)
    assert cm_cfg.contact_cutoff_angstrom == 5.0


def test_c7_structural_graph_config_derived() -> None:
    cfg = FeatureConfig(spatial_edge_cutoff_angstrom=6.0)
    sg_cfg = cfg.structural_graph_config()
    assert isinstance(sg_cfg, StructuralGraphConfig)
    assert sg_cfg.spatial_cutoff_angstrom == 6.0


def test_c8_default_fingerprint_config_all_none() -> None:
    cfg = default_feature_config()
    fp_cfg = cfg.fingerprint_config()
    assert all(v is None for v in fp_cfg.to_canonical_dict().values())


def test_c9_version_is_in_canonical_dict() -> None:
    cfg = FeatureConfig(version="v1.0-sealed", governing_gdr="GDR-005")
    d = cfg.to_canonical_dict()
    assert d["version"] == "v1.0-sealed"
    assert d["governing_gdr"] == "GDR-005"


def test_c10_hash_deterministic() -> None:
    h1 = FeatureConfig().content_sha256()
    h2 = FeatureConfig().content_sha256()
    assert h1 == h2


def test_c11_different_threshold_different_hash() -> None:
    h1 = FeatureConfig(hbond_da_cutoff_angstrom=3.5).content_sha256()
    h2 = FeatureConfig(hbond_da_cutoff_angstrom=4.0).content_sha256()
    assert h1 != h2


def test_c12_governing_gdr_none_by_default() -> None:
    cfg = FeatureConfig()
    assert cfg.governing_gdr is None
    assert cfg.version == "v0.1-rule_missing"

"""Governed feature-layer configuration: FeatureConfig.

Authority: ADR-0010 [Architectural]; SCI1-008.
Constitution sections served: §4.2 (binding requirements on implementation),
  §4.6 (Path A adopted), §2.1 (correspondence-free input interface).

Consolidates all configuration parameters for the features/ layer into one
versioned, immutable dataclass. This is the single source of truth for any
threshold or algorithm choice in SCI1-004 through SCI1-007.

Every numeric threshold defaults to None (RULE_MISSING) unless a Governance
Decision Record has sealed its value. The `version` field identifies the
configuration vintage.

Relationship to component configs
-----------------------------------
FingerprintConfig, ContactMapConfig, StructuralGraphConfig in SCI1-004/005
remain valid standalone. FeatureConfig is a convenience wrapper that can
produce them deterministically from one sealed configuration. When a GDR
seals a threshold, it is set here; the component configs are derived from it.

What is and is not in this module
-----------------------------------
IN:  thresholds, algorithm choices, versioning.
NOT IN: scientific interpretations, selectivity criteria, production rules,
  policy decisions. Those belong to later layers.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from orthosteric.features._contact_map import ContactMapConfig
from orthosteric.features._interaction_fingerprint import FingerprintConfig
from orthosteric.features._structural_graph import StructuralGraphConfig

__all__ = [
    "FEATURE_CONFIG_ALGORITHM_VERSION",
    "FeatureConfig",
    "default_feature_config",
]

FEATURE_CONFIG_ALGORITHM_VERSION = "feature_config_v1_sci1008"


@dataclass(frozen=True, slots=True)
class FeatureConfig:
    """Versioned, immutable configuration for the entire features/ layer.

    Governance status: every threshold defaults to None (RULE_MISSING).
    A GDR must seal each threshold before it can be used to classify
    OBSERVED/ABSENT. Raw geometry is always preserved regardless.

    Attributes (interaction fingerprint thresholds -- SCI1-004)
    -----------------------------------------------------------
    hbond_da_cutoff_angstrom:       D...A distance for H-bond (RULE_MISSING).
    hbond_angle_min_degrees:        D-H...A angle minimum (RULE_MISSING).
    salt_bridge_cutoff_angstrom:    Salt-bridge distance (RULE_MISSING).
    pi_pi_centroid_cutoff_angstrom: pi-pi centroid (RULE_MISSING).
    cation_pi_cutoff_angstrom:      Cation-pi (RULE_MISSING).
    hydrophobic_cutoff_angstrom:    Hydrophobic contact (RULE_MISSING).
    halogen_distance_cutoff_angstrom: Halogen bond (RULE_MISSING).
    halogen_angle_min_degrees:      C-X...A angle (RULE_MISSING).
    metal_distance_cutoff_angstrom: Metal coordination (RULE_MISSING).
    water_arm_cutoff_angstrom:      Water-mediated arm (RULE_MISSING).

    Attributes (contact map thresholds -- SCI1-005)
    -----------------------------------------------
    contact_cutoff_angstrom:        Heavy-atom contact distance (RULE_MISSING).

    Attributes (structural graph thresholds -- SCI1-005)
    ----------------------------------------------------
    spatial_edge_cutoff_angstrom:   Graph spatial edge (RULE_MISSING).

    Attributes (versioning)
    -----------------------
    version:                        Human-readable version identifier.
    governing_gdr:                  GDR identifier that sealed this config,
                                    or None if still pre-governance.
    algorithm_version:              Pinned module version string.
    """

    # Interaction fingerprint
    hbond_da_cutoff_angstrom: float | None = None
    hbond_angle_min_degrees: float | None = None
    salt_bridge_cutoff_angstrom: float | None = None
    pi_pi_centroid_cutoff_angstrom: float | None = None
    pi_pi_plane_angle_max_degrees: float | None = None
    cation_pi_cutoff_angstrom: float | None = None
    hydrophobic_cutoff_angstrom: float | None = None
    halogen_distance_cutoff_angstrom: float | None = None
    halogen_angle_min_degrees: float | None = None
    metal_distance_cutoff_angstrom: float | None = None
    water_arm_cutoff_angstrom: float | None = None
    # Contact map
    contact_cutoff_angstrom: float | None = None
    # Structural graph
    spatial_edge_cutoff_angstrom: float | None = None
    # Versioning
    version: str = "v0.1-rule_missing"
    governing_gdr: str | None = None
    algorithm_version: str = FEATURE_CONFIG_ALGORITHM_VERSION

    def fingerprint_config(self) -> FingerprintConfig:
        """Derive a FingerprintConfig from this FeatureConfig."""
        return FingerprintConfig(
            hbond_da_cutoff_angstrom=self.hbond_da_cutoff_angstrom,
            hbond_angle_min_degrees=self.hbond_angle_min_degrees,
            salt_bridge_cutoff_angstrom=self.salt_bridge_cutoff_angstrom,
            pi_pi_centroid_cutoff_angstrom=self.pi_pi_centroid_cutoff_angstrom,
            pi_pi_plane_angle_max_degrees=self.pi_pi_plane_angle_max_degrees,
            cation_pi_cutoff_angstrom=self.cation_pi_cutoff_angstrom,
            hydrophobic_cutoff_angstrom=self.hydrophobic_cutoff_angstrom,
            halogen_distance_cutoff_angstrom=self.halogen_distance_cutoff_angstrom,
            halogen_angle_min_degrees=self.halogen_angle_min_degrees,
            metal_distance_cutoff_angstrom=self.metal_distance_cutoff_angstrom,
            water_arm_cutoff_angstrom=self.water_arm_cutoff_angstrom,
        )

    def contact_map_config(self) -> ContactMapConfig:
        """Derive a ContactMapConfig from this FeatureConfig."""
        return ContactMapConfig(contact_cutoff_angstrom=self.contact_cutoff_angstrom)

    def structural_graph_config(self) -> StructuralGraphConfig:
        """Derive a StructuralGraphConfig from this FeatureConfig."""
        return StructuralGraphConfig(spatial_cutoff_angstrom=self.spatial_edge_cutoff_angstrom)

    def all_thresholds_rule_missing(self) -> bool:
        """True iff every classification threshold is still None (RULE_MISSING)."""
        numeric_fields = [
            self.hbond_da_cutoff_angstrom,
            self.hbond_angle_min_degrees,
            self.salt_bridge_cutoff_angstrom,
            self.pi_pi_centroid_cutoff_angstrom,
            self.pi_pi_plane_angle_max_degrees,
            self.cation_pi_cutoff_angstrom,
            self.hydrophobic_cutoff_angstrom,
            self.halogen_distance_cutoff_angstrom,
            self.halogen_angle_min_degrees,
            self.metal_distance_cutoff_angstrom,
            self.water_arm_cutoff_angstrom,
            self.contact_cutoff_angstrom,
            self.spatial_edge_cutoff_angstrom,
        ]
        return all(f is None for f in numeric_fields)

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "algorithm_version": self.algorithm_version,
            "cation_pi_cutoff_angstrom": self.cation_pi_cutoff_angstrom,
            "contact_cutoff_angstrom": self.contact_cutoff_angstrom,
            "governing_gdr": self.governing_gdr,
            "hbond_angle_min_degrees": self.hbond_angle_min_degrees,
            "hbond_da_cutoff_angstrom": self.hbond_da_cutoff_angstrom,
            "hydrophobic_cutoff_angstrom": self.hydrophobic_cutoff_angstrom,
            "halogen_angle_min_degrees": self.halogen_angle_min_degrees,
            "halogen_distance_cutoff_angstrom": self.halogen_distance_cutoff_angstrom,
            "metal_distance_cutoff_angstrom": self.metal_distance_cutoff_angstrom,
            "pi_pi_centroid_cutoff_angstrom": self.pi_pi_centroid_cutoff_angstrom,
            "pi_pi_plane_angle_max_degrees": self.pi_pi_plane_angle_max_degrees,
            "salt_bridge_cutoff_angstrom": self.salt_bridge_cutoff_angstrom,
            "spatial_edge_cutoff_angstrom": self.spatial_edge_cutoff_angstrom,
            "version": self.version,
            "water_arm_cutoff_angstrom": self.water_arm_cutoff_angstrom,
        }

    def content_sha256(self) -> str:
        payload = json.dumps(
            self.to_canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def default_feature_config() -> FeatureConfig:
    """Return the default FeatureConfig with all thresholds RULE_MISSING."""
    return FeatureConfig()

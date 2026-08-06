"""Placeholder interfaces for MD-ready structural representations.

Authority: ADR-0010 [Architectural]; SCI1-007.
Constitution sections served: §3.2.2 (MD measurements for pocket dynamics),
  §4.2 (pocket conformational states as inputs).

Phase status: PHASE_3_REQUIRED. The interfaces are defined here so that
the features/ layer is fully typed and the learning layer can depend on
a stable API. No MD computation is performed. All instances produced by
this module carry status = MDStatus.NOT_COMPUTED until Phase 3.

Why define stubs now: Constitution §4.2 requires that "pocket conformational
states are inputs, not averaged away (C6, §2.1)." The learning layer (SCI-2)
must be designed to accept conformational state data; without a typed
interface, it cannot be written correctly even with placeholder values.

What Phase 3 will fill in: interaction-persistence fractions across an
MD ensemble, rotamer-state ensemble populations, water-occupancy maps,
trajectory-level pocket-volume distributions, and DCCM-derived dynamic
information.

Nothing in this module infers MD data from static structures.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

__all__ = [
    "MD_INTERFACE_ALGORITHM_VERSION",
    "ConformationalStateLabel",
    "EnsembleMetadata",
    "InteractionPersistence",
    "MDFeaturePlaceholder",
    "MDStatus",
    "WaterOccupancy",
]

MD_INTERFACE_ALGORITHM_VERSION = "md_interface_v1_sci1007"

_NOT_COMPUTED_NOTE = (
    "PHASE_3_REQUIRED: MD computation not performed. SCI1-007 defines the "
    "interface for Phase 3 population. This placeholder ensures the learning "
    "layer can depend on a stable typed API."
)


class MDStatus(StrEnum):
    """Availability status for MD-derived features.

    NOT_COMPUTED: Phase 3 not yet executed; interface defined but no data.
    COMPUTED:     MD ensemble sampled and features extracted.
    INSUFFICIENT_SAMPLING: MD run completed but did not converge (Constitution
        §3.2.3 timescale caveat); features are inconclusive.
    INADMISSIBLE: Structure or force-field issues prevent reliable sampling.
    """

    NOT_COMPUTED = "not_computed"
    COMPUTED = "computed"
    INSUFFICIENT_SAMPLING = "insufficient_sampling"
    INADMISSIBLE = "inadmissible"


class ConformationalStateLabel(StrEnum):
    """Discrete conformational state for the orthosteric pocket (Constitution §3.2.2).

    UNKNOWN:         State not assessed.
    APO_CLOSED:      Ligand-free, specificity pocket absent.
    LIGAND_BOUND:    ATP-competitive ligand bound.
    SPECIFICITY_OPEN: Induced specificity pocket (Trp780/Met772 cleft) open.
    INTERMEDIATE:    Between apo-closed and specificity-open.
    """

    UNKNOWN = "unknown"
    APO_CLOSED = "apo_closed"
    LIGAND_BOUND = "ligand_bound"
    SPECIFICITY_OPEN = "specificity_open"
    INTERMEDIATE = "intermediate"


@dataclass(frozen=True, slots=True)
class EnsembleMetadata:
    """Metadata for a molecular dynamics ensemble (placeholder).

    Phase 3 will populate these fields from actual MD runs. Until then,
    all numeric fields are None.

    Attributes:
        status:             MDStatus.NOT_COMPUTED until Phase 3.
        n_replicates:       Number of independent MD trajectories.
        simulation_time_ns: Wall-clock sampling time per replicate.
        force_field:        Force field identifier (e.g. "AMBER-ff14SB").
        water_model:        Explicit water model (e.g. "TIP3P").
        temperature_kelvin: Simulation temperature.
        converged:          Whether the ensemble is considered converged per
                            Constitution §3.2.3 statistical controls.
        phase_note:         Human-readable note about Phase 3 requirement.
    """

    status: MDStatus
    n_replicates: int | None
    simulation_time_ns: float | None
    force_field: str | None
    water_model: str | None
    temperature_kelvin: float | None
    converged: bool | None
    phase_note: str

    @classmethod
    def not_computed(cls) -> EnsembleMetadata:
        """Return a placeholder EnsembleMetadata for pre-Phase-3 use."""
        return cls(
            status=MDStatus.NOT_COMPUTED,
            n_replicates=None,
            simulation_time_ns=None,
            force_field=None,
            water_model=None,
            temperature_kelvin=None,
            converged=None,
            phase_note=_NOT_COMPUTED_NOTE,
        )

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "converged": self.converged,
            "force_field": self.force_field,
            "n_replicates": self.n_replicates,
            "phase_note": self.phase_note,
            "simulation_time_ns": self.simulation_time_ns,
            "status": self.status.value,
            "temperature_kelvin": self.temperature_kelvin,
            "water_model": self.water_model,
        }


@dataclass(frozen=True, slots=True)
class InteractionPersistence:
    """Persistence of a protein-ligand interaction across an MD ensemble.

    `fraction_occupied` = fraction of frames in which the interaction is
    observed (using a governed criterion applied to the trajectory).

    All numeric fields are None until Phase 3 (status = NOT_COMPUTED).
    """

    canonical_position: int | None
    protein_residue_id: str
    interaction_type: str
    status: MDStatus
    fraction_occupied: float | None  # [0, 1]; None if not computed
    mean_distance_angstrom: float | None
    std_distance_angstrom: float | None
    n_frames_sampled: int | None
    phase_note: str

    @classmethod
    def not_computed(
        cls,
        canonical_position: int | None,
        protein_residue_id: str,
        interaction_type: str,
    ) -> InteractionPersistence:
        return cls(
            canonical_position=canonical_position,
            protein_residue_id=protein_residue_id,
            interaction_type=interaction_type,
            status=MDStatus.NOT_COMPUTED,
            fraction_occupied=None,
            mean_distance_angstrom=None,
            std_distance_angstrom=None,
            n_frames_sampled=None,
            phase_note=_NOT_COMPUTED_NOTE,
        )


@dataclass(frozen=True, slots=True)
class WaterOccupancy:
    """Occupancy of an ordered water site in the ATP pocket across an MD ensemble.

    Constitution §2.1: "ordered ATP-site waters retained and flagged."
    MD provides the occupancy fraction; static structures provide presence/absence.
    All fields None until Phase 3.
    """

    water_site_label: str  # e.g. "hinge_water_1"
    status: MDStatus
    occupancy_fraction: float | None
    mean_residence_time_ns: float | None
    canonical_position_nearest_residue: int | None
    phase_note: str

    @classmethod
    def not_computed(cls, site_label: str) -> WaterOccupancy:
        return cls(
            water_site_label=site_label,
            status=MDStatus.NOT_COMPUTED,
            occupancy_fraction=None,
            mean_residence_time_ns=None,
            canonical_position_nearest_residue=None,
            phase_note=_NOT_COMPUTED_NOTE,
        )


@dataclass(frozen=True, slots=True)
class MDFeaturePlaceholder:
    """Container for all MD-derived features for one structure (placeholder).

    In Phase 3, this is populated by actual MD ensemble analysis.
    Until then, all contained objects carry MDStatus.NOT_COMPUTED.

    Attributes:
        structure_record_id:        Source structure.
        isoform:                    Target isoform.
        ensemble_metadata:          Simulation parameters.
        conformational_state:       Dominant pocket state.
        interaction_persistences:   Per-interaction persistence fractions.
        water_occupancies:          Per-site water occupancy fractions.
        algorithm_version:          Pinned version.
        phase_note:                 Always the NOT_COMPUTED note pre-Phase-3.
    """

    structure_record_id: str
    isoform: str
    ensemble_metadata: EnsembleMetadata
    conformational_state: ConformationalStateLabel
    interaction_persistences: tuple[InteractionPersistence, ...]
    water_occupancies: tuple[WaterOccupancy, ...]
    algorithm_version: str
    phase_note: str

    @classmethod
    def not_computed(cls, structure_record_id: str, isoform: str) -> MDFeaturePlaceholder:
        """Return a typed placeholder for pre-Phase-3 use."""
        return cls(
            structure_record_id=structure_record_id,
            isoform=isoform,
            ensemble_metadata=EnsembleMetadata.not_computed(),
            conformational_state=ConformationalStateLabel.UNKNOWN,
            interaction_persistences=(),
            water_occupancies=(),
            algorithm_version=MD_INTERFACE_ALGORITHM_VERSION,
            phase_note=_NOT_COMPUTED_NOTE,
        )

    def is_computed(self) -> bool:
        return self.ensemble_metadata.status == MDStatus.COMPUTED

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "algorithm_version": self.algorithm_version,
                "conformational_state": self.conformational_state.value,
                "ensemble_metadata": self.ensemble_metadata.to_canonical_dict(),
                "interaction_persistences": [
                    {
                        "canonical_position": ip.canonical_position,
                        "fraction_occupied": ip.fraction_occupied,
                        "interaction_type": ip.interaction_type,
                        "protein_residue_id": ip.protein_residue_id,
                        "status": ip.status.value,
                    }
                    for ip in self.interaction_persistences
                ],
                "isoform": self.isoform,
                "phase_note": self.phase_note,
                "structure_record_id": self.structure_record_id,
                "water_occupancies": [
                    {
                        "occupancy_fraction": w.occupancy_fraction,
                        "status": w.status.value,
                        "water_site_label": w.water_site_label,
                    }
                    for w in self.water_occupancies
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

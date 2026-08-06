"""DockingComplexRecord -- computational (docking-derived) compound x
isoform structural evidence, kept SEPARATE from StructuralEvidenceRecord's
experimental-evidence fields (per explicit instruction: "Do not overload
experimental fields with docking values").

Governance
----------
Docking-derived labels are COMPUTATIONAL, never experimental. Every
record's `evidence_class` is always `EvidenceClass.DOCKING_COMPLEX`
(never EXPERIMENTAL_COMPLEX) and `is_experimental` is always False.
A `docking_score` is a relative computational quantity, NOT a calibrated
pAct estimate -- no arithmetic anywhere in this module maps a docking
score to an activity unit. Any future score-to-pAct calibration is a
separate, explicitly validated decision this module does not make.

Provenance completeness
------------------------
Every record carries enough fields to reproduce the exact docking run:
compound identity, receptor identity + source tier (EXPERIMENTAL_RECEPTOR
vs ALPHAFOLD_RECEPTOR, never conflated), receptor/ligand preparation
software+version, docking engine+version+config, search-box definition,
seed, pose rank, score, and the parent activity snapshot the compound
identity was resolved against. Retrieval/run timestamp is provenance
only, never identity-defining (GDR-010 precedent).

Tiering (per this session's mandate §11)
-------------------------------------------
  D1 -- EXPERIMENTAL_RECEPTOR-based docking (highest computational tier)
  D2 -- ALPHAFOLD_RECEPTOR-based docking
The tier is derived from `receptor_source_class`, never invented
separately, so it cannot drift from the receptor's own evidence class.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from orthosteric.data.sources.structural._evidence_record import EvidenceClass

#: Docking pipeline policy identifier (versioned; bump on any protocol change).
DOCKING_POLICY_ID = "docking_pipeline_v1_vina1.2.7_meeko0.7.1"


class ReceptorSourceClass(StrEnum):
    """Which evidence class the receptor structure itself came from.
    Determines the D1/D2 computational-evidence tier -- never set
    independently of the receptor's own provenance.
    """

    EXPERIMENTAL_RECEPTOR = "experimental_receptor"  # -> Tier D1
    ALPHAFOLD_RECEPTOR = "alphafold_receptor"  # -> Tier D2


class DockingOutcome(StrEnum):
    """Explicit pipeline outcome -- never silently absent."""

    SUCCESS = "success"
    LIGAND_PREPARATION_FAILED = "ligand_preparation_failed"
    RECEPTOR_PREPARATION_FAILED = "receptor_preparation_failed"
    DOCKING_ENGINE_FAILED = "docking_engine_failed"
    NO_RECEPTOR_AVAILABLE = "no_receptor_available"


def docking_tier(receptor_source_class: ReceptorSourceClass) -> str:
    """D1 for experimental-receptor docking, D2 for AlphaFold-receptor
    docking -- derived, never set independently (see module docstring).
    """
    return "D1" if receptor_source_class is ReceptorSourceClass.EXPERIMENTAL_RECEPTOR else "D2"


@dataclass(frozen=True, slots=True)
class DockingBox:
    """Search-space definition, in Angstroms, receptor-frame coordinates.
    Derived from real structural evidence (e.g. a co-crystallized ligand's
    centroid) -- never an arbitrary/guessed box; the derivation method is
    recorded in `derivation_method` for audit.
    """

    center_x: float
    center_y: float
    center_z: float
    size_x: float
    size_y: float
    size_z: float
    derivation_method: str


@dataclass(frozen=True, slots=True)
class DockingComplexRecord:
    """One computational docking run's result for one (compound, isoform)
    pair. `evidence_class` is always DOCKING_COMPLEX; `is_experimental` is
    always False -- both fixed, never caller-settable, so a docking record
    can never be mistaken for or silently promoted to experimental evidence.
    """

    compound_id: str
    inchikey: str | None
    isoform: str
    outcome: DockingOutcome

    # Receptor provenance
    receptor_source_class: ReceptorSourceClass | None = None
    receptor_identifier: str = ""  # PDB ID (experimental) or AlphaFold model ID
    receptor_preparation_software: str = ""
    receptor_preparation_version: str = ""

    # Ligand provenance
    ligand_smiles: str | None = None
    ligand_preparation_software: str = ""
    ligand_preparation_version: str = ""

    # Docking configuration
    docking_engine: str = ""
    docking_engine_version: str = ""
    docking_box: DockingBox | None = None
    exhaustiveness: int | None = None
    num_modes: int | None = None
    seed: int | None = None

    # Result (only meaningful when outcome == SUCCESS)
    pose_rank: int | None = None  # 1 = best-scoring pose
    docking_score: float | None = None  # raw engine score; NOT a pAct estimate
    docking_score_units: str = "kcal/mol"

    # Provenance
    pipeline_version: str = DOCKING_POLICY_ID
    activity_snapshot_sha: str = ""
    retrieval_timestamp: str = ""  # provenance only, never identity-defining
    failure_reason: str = ""

    evidence_class: EvidenceClass = field(default=EvidenceClass.DOCKING_COMPLEX, init=False)
    is_experimental: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self.outcome is DockingOutcome.SUCCESS and self.docking_score is None:
            raise ValueError("A SUCCESS outcome must carry a docking_score.")
        if self.outcome is not DockingOutcome.SUCCESS and self.docking_score is not None:
            raise ValueError("A non-SUCCESS outcome must not carry a docking_score.")

    @property
    def tier(self) -> str | None:
        if self.receptor_source_class is None:
            return None
        return docking_tier(self.receptor_source_class)

    def content_sha256(self) -> str:
        payload = {
            "compound_id": self.compound_id,
            "isoform": self.isoform,
            "outcome": str(self.outcome),
            "receptor_identifier": self.receptor_identifier,
            "receptor_source_class": str(self.receptor_source_class)
            if self.receptor_source_class
            else None,
            "docking_engine": self.docking_engine,
            "docking_engine_version": self.docking_engine_version,
            "seed": self.seed,
            "pose_rank": self.pose_rank,
            "docking_score": self.docking_score,
            "pipeline_version": self.pipeline_version,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "compound_id": self.compound_id,
            "inchikey": self.inchikey,
            "isoform": self.isoform,
            "evidence_class": str(self.evidence_class),
            "is_experimental": self.is_experimental,
            "outcome": str(self.outcome),
            "receptor_source_class": str(self.receptor_source_class)
            if self.receptor_source_class
            else None,
            "tier": self.tier,
            "receptor_identifier": self.receptor_identifier,
            "receptor_preparation_software": self.receptor_preparation_software,
            "receptor_preparation_version": self.receptor_preparation_version,
            "ligand_smiles": self.ligand_smiles,
            "ligand_preparation_software": self.ligand_preparation_software,
            "ligand_preparation_version": self.ligand_preparation_version,
            "docking_engine": self.docking_engine,
            "docking_engine_version": self.docking_engine_version,
            "docking_box": {
                "center": [
                    self.docking_box.center_x,
                    self.docking_box.center_y,
                    self.docking_box.center_z,
                ],
                "size": [self.docking_box.size_x, self.docking_box.size_y, self.docking_box.size_z],
                "derivation_method": self.docking_box.derivation_method,
            }
            if self.docking_box
            else None,
            "exhaustiveness": self.exhaustiveness,
            "num_modes": self.num_modes,
            "seed": self.seed,
            "pose_rank": self.pose_rank,
            "docking_score": self.docking_score,
            "docking_score_units": self.docking_score_units,
            "pipeline_version": self.pipeline_version,
            "activity_snapshot_sha": self.activity_snapshot_sha,
            "retrieval_timestamp": self.retrieval_timestamp,
            "failure_reason": self.failure_reason,
            "content_sha256": self.content_sha256(),
        }

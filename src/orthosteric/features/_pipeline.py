"""Unified Path A feature pipeline for orthosteric ATP-site structures.

Authority: ADR-0010 [Architectural]; SCI1-009 (features/ scaffold complete),
  SCI1-010 (Path A representation), SCI1-011 (Path A verification).
Constitution sections served: §4.6 (Path A adopted), §4.2 (binding
  requirements on any implementation).

Path A compliance (Constitution §4.6)
--------------------------------------
"The representation shall be correspondence-free at the input interface:
geometric, field-based, or otherwise invariant to residue indexing,
accepting any ATP site -- including Tier 2 targets, second-family targets
and mutated Tier 1 structures -- without alignment to Class I positions."

This module is the Path A compliance layer. `compute_features()` accepts
any `bio_structure` with any `PocketResidueSet` and produces a complete
`FeaturePipelineResult`. No argument requires alignment to Tier 1 Class I
residue positions. The correspondence_table is OPTIONAL -- when absent,
all canonical_position fields are None, but all geometric computations
proceed normally.

Path A does NOT mean correspondence is irrelevant to the science. It means
the input interface is permissive; canonical-position annotation is applied
post-hoc from SCI1-003 when available. This is consistent with A.1: the
learning task requires correspondence (to be learned on Tier 1); the input
interface must accept structures outside Tier 1 for generalization tests.

What this module is NOT
------------------------
- A training pipeline. No labels, no optimization.
- A selectivity predictor. No IC50, no selectivity ratios.
- A structural biology tool. Uses governed definitions from pocket/ only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orthosteric.features._comparative_feature import (
    ComparativeFeatureSet,
    build_comparative_feature_set,
)
from orthosteric.features._contact_map import (
    PocketContactMap,
    compute_contact_map,
)
from orthosteric.features._feature_config import FeatureConfig, default_feature_config
from orthosteric.features._interaction_fingerprint import (
    InteractionFingerprint,
    build_comparative_fingerprint,
    compute_interaction_fingerprint,
)
from orthosteric.features._md_interface import MDFeaturePlaceholder
from orthosteric.features._pocket_descriptor import (
    PocketDescriptor,
    build_pocket_descriptor,
)
from orthosteric.features._structural_graph import (
    PocketGraph,
    compute_structural_graph,
)
from orthosteric.pocket._pocket_definition import PocketResidueSet
from orthosteric.pocket._pocket_geometry import PocketGeometry
from orthosteric.pocket._residue_mapping import ResidueCorrespondenceTable
from orthosteric.pocket._structure_record import LigandRecord, StructureRecord

__all__ = [
    "PIPELINE_ALGORITHM_VERSION",
    "FeaturePipelineResult",
    "compute_features",
    "is_path_a_compliant",
]

PIPELINE_ALGORITHM_VERSION = "feature_pipeline_v1_sci1010"

# Path A compliance assertions (Constitution §4.6)
_PATH_A_NOTE = (
    "Path A compliant: input interface is correspondence-free. "
    "Canonical positions are annotated post-hoc from SCI1-003 when a "
    "correspondence_table is supplied, but are not required for any "
    "geometric computation. The pipeline accepts Tier 1, Tier 2, "
    "second-family, and mutated structures without modification."
)


@dataclass(frozen=True, slots=True)
class FeaturePipelineResult:
    """Complete feature bundle for one protein-ligand structure (one isoform).

    All component features are computed from 3D coordinates without requiring
    alignment to Class I residue indices (Path A compliance). Canonical
    position annotation is post-hoc from SCI1-003 when available.

    Attributes:
        structure_record_id:    Source structure.
        isoform:                Target isoform (empty string for unseen targets).
        fingerprint:            SCI1-004 interaction fingerprint.
        contact_map:            SCI1-005 pocket contact maps.
        structural_graph:       SCI1-005 heterogeneous graph.
        descriptor:             SCI1-006 pocket-level scalar summary.
        md_placeholder:         SCI1-007 MD interface (NOT_COMPUTED pre-Phase-3).
        feature_config:         SCI1-008 config used for all components.
        correspondence_provided: True iff a correspondence_table was supplied.
        path_a_note:            Path A compliance statement.
        algorithm_version:      Pinned pipeline version.
    """

    structure_record_id: str
    isoform: str
    fingerprint: InteractionFingerprint
    contact_map: PocketContactMap
    structural_graph: PocketGraph
    descriptor: PocketDescriptor
    md_placeholder: MDFeaturePlaceholder
    feature_config: FeatureConfig
    correspondence_provided: bool
    path_a_note: str
    algorithm_version: str


def compute_features(
    bio_structure: Any,
    structure_record: StructureRecord,
    pocket_residue_set: PocketResidueSet,
    ligand_record: LigandRecord,
    isoform: str = "",
    correspondence_table: ResidueCorrespondenceTable | None = None,
    pocket_geometry: PocketGeometry | None = None,
    config: FeatureConfig | None = None,
) -> FeaturePipelineResult:
    """Compute the complete feature set for one structure.

    Path A: accepts any ATP site (Tier 1, Tier 2, mutated, second-family)
    without alignment to Class I residue indices. The correspondence_table
    is optional; when absent, all canonical_position fields are None.

    Parameters
    ----------
    bio_structure:      Parsed BioPython Structure.
    structure_record:   Source structure provenance.
    pocket_residue_set: Governed pocket (ligand-ensemble union per §2.1).
    ligand_record:      ATP-site ligand.
    isoform:            Isoform name. Empty string for unseen/Tier-2 targets.
    correspondence_table: SCI1-003 table for canonical annotation. Optional.
    pocket_geometry:    SCI1-002 geometry for volume in descriptor. Optional.
    config:             FeatureConfig. Uses default (all RULE_MISSING) if None.
    """
    if config is None:
        config = default_feature_config()
    rec_id = structure_record.record_id

    fp = compute_interaction_fingerprint(
        bio_structure=bio_structure,
        structure_record=structure_record,
        pocket_residue_set=pocket_residue_set,
        ligand_record=ligand_record,
        isoform=isoform,
        correspondence_table=correspondence_table,
        config=config.fingerprint_config(),
    )
    cm = compute_contact_map(
        bio_structure=bio_structure,
        structure_record=structure_record,
        pocket_residue_set=pocket_residue_set,
        ligand_record=ligand_record,
        isoform=isoform,
        correspondence_table=correspondence_table,
        config=config.contact_map_config(),
    )
    sg = compute_structural_graph(
        bio_structure=bio_structure,
        structure_record=structure_record,
        pocket_residue_set=pocket_residue_set,
        ligand_record=ligand_record,
        isoform=isoform,
        correspondence_table=correspondence_table,
        config=config.structural_graph_config(),
        interaction_fingerprint=fp,
    )
    desc = build_pocket_descriptor(
        structure_record=structure_record,
        pocket_residue_set=pocket_residue_set,
        isoform=isoform,
        correspondence_table=correspondence_table,
        interaction_fingerprint=fp,
        pocket_geometry=pocket_geometry,
    )
    md = MDFeaturePlaceholder.not_computed(rec_id, isoform)

    return FeaturePipelineResult(
        structure_record_id=rec_id,
        isoform=isoform,
        fingerprint=fp,
        contact_map=cm,
        structural_graph=sg,
        descriptor=desc,
        md_placeholder=md,
        feature_config=config,
        correspondence_provided=correspondence_table is not None,
        path_a_note=_PATH_A_NOTE,
        algorithm_version=PIPELINE_ALGORITHM_VERSION,
    )


def build_comparative_features(
    per_isoform_results: list[tuple[str, FeaturePipelineResult]],
    ligand_inchikey: str | None = None,
) -> ComparativeFeatureSet:
    """Build a comparative feature set from per-isoform pipeline results.

    Aligns interaction evidence by canonical position across all isoforms.
    Requires that correspondence tables were provided for at least some results.
    """
    fps = [(iso, result.fingerprint) for iso, result in per_isoform_results]
    comp_fp = build_comparative_fingerprint(fps, ligand_inchikey=ligand_inchikey)
    return build_comparative_feature_set(comp_fp)


def is_path_a_compliant(result: FeaturePipelineResult) -> bool:
    """Assert Path A compliance for a pipeline result.

    Returns True iff:
    1. The fingerprint algorithm version indicates SCI1-004 or later.
    2. The contact map algorithm version indicates SCI1-005 or later.
    3. The structural graph algorithm version indicates SCI1-005 or later.
    4. The pipeline was run with the SCI1-010 pipeline version.

    A result failing this check was produced by an incompatible pipeline.
    """
    return (
        result.algorithm_version == PIPELINE_ALGORITHM_VERSION
        and result.fingerprint.algorithm_version.startswith("interaction_fp_v1")
        and result.contact_map.algorithm_version.startswith("contact_map_v1")
        and result.structural_graph.algorithm_version.startswith("structural_graph_v1")
    )

"""Corpus profile — frozen, corpus-derived engineering parameters.

Authority: `GDR-002` (docs/governance/decision-records/
GDR-002-corpus-derived-engineering-parameters.md); extended by `ADR-0009`
(structural-coverage extension point, `StructuralCoverageStats`).

`N_c` (largest connected component), `N_b` (bridging-compound count), and
`N_w` (within-study four-isoform compound count) are corpus-derived
engineering parameters, not literature-derived scientific thresholds: they
are computed deterministically from an already-frozen `SCI0-011` snapshot,
never optimized during model development, never fitted to model performance,
and never estimated from the literature.

Workflow (GDR-002 §2)
----------------------
```
Raw evidence
      |
Corpus acquisition / harmonization        (SCI0-006..SCI0-012)
      |
Immutable snapshot (SHA-256)              (SCI0-011, data.snapshots._builder)
      |
Compute corpus characteristics            (SCI0-014 data.graph,
      |                                     SCI0-014b data.audit)
Freeze corpus profile                     (this module)
      |
Model development                         (SCI-1 onward)
```

`freeze_corpus_profile()` accepts only already-built `GraphStats` and
`CharacterizationReport` objects. There is no code path here that reads raw
records or a partially-built snapshot, so this module cannot be run against
partially curated data by construction (GDR-002 §5).

Two definitional issues are recorded rather than silently resolved (GDR-002
§3): the `N_w` compound-vs-strata ambiguity (both units are frozen, under
distinct names), and the scaffold-diversity-within-largest-component gap
(recorded as `None`, never substituted with the corpus-global count, which
would answer a different question).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

from orthosteric.data.audit import CharacterizationReport
from orthosteric.data.graph import GraphStats
from orthosteric.data.snapshots._manifest import PolicyManifest, SoftwareProvenance
from orthosteric.data.strata import StratumReport

__all__ = [
    "CORPUS_PROFILE_SCHEMA_VERSION",
    "PROFILE_ALGORITHM_VERSION",
    "CorpusProfile",
    "EngineeringParameters",
    "freeze_corpus_profile",
]

CORPUS_PROFILE_SCHEMA_VERSION = "corpus_profile_v3_adr0009"
PROFILE_ALGORITHM_VERSION = "corpus_profile_algorithm_v3_adr0009"
"""Version of *how* the profile is computed — distinct from the upstream
policy versions in `PolicyManifest`. Bump this if the connectivity or
aggregation method changes, even when no upstream policy does."""


def _canonical_default(obj: Any) -> Any:
    if hasattr(obj, "value"):  # StrEnum
        return obj.value
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def _stable_json(obj: Any) -> str:
    return json.dumps(
        obj, sort_keys=True, default=_canonical_default, separators=(",", ":"), ensure_ascii=True
    )


@dataclass(frozen=True, slots=True)
class EngineeringParameters:
    """`N_c`, `N_b`, `N_w`, and closely-related counts, per GDR-002.

    Attributes:
        n_c: Largest connected component of the compound x isoform evidence
            graph, in unique compounds (`GraphStats.largest_connected_
            component`). Corpus-derived; not a pre-sealed floor (GDR-002).
        n_b: Bridging-compound count (`GraphStats.bridging_compounds`):
            compounds appearing in >= 2 study panels with >= 2 isoforms
            measured in total. Corpus-derived; not a pre-sealed floor.
        n_w: Within-study four-isoform compound count as computed by
            `GraphStats.within_study_four_isoform` (`SCI0-014`). **Known
            semantic gap, discovered while implementing `ADR-0009`'s
            `CoverageEvaluator`:** this field counts compounds belonging to
            a study panel where all four isoforms are collectively
            represented *somewhere in the panel*, not compounds
            *individually* measured across all four isoforms. It can
            therefore be positive even when zero compounds actually satisfy
            the Constitution's own per-compound `N_w` definition (§2.3(4)'s
            `S1` requires one compound with all four `pAct` values). Kept
            for continuity with the already-merged `SCI0-014` field and
            because `GDR-002` named it explicitly; superseded for adequacy
            judgments by `n_complete_compounds` below, which is verified
            correct.
        n_complete_compounds: Compounds individually measured across all
            four Tier 1 isoforms within one qualifying stratum
            (`StratumReport.total_complete_compounds`, `SCI0-013`) — the
            quantity the Constitution's `N_w` actually specifies, verified
            correct against direct construction (see
            `tests/data/snapshots/test_profile.py`). `quality/`'s
            `CoverageEvaluator` uses this field, not `n_w`, for its
            degenerate check.
        n_complete_strata: Count of `(study, assay)` panels complete for all
            four Tier 1 isoforms (`StratumReport.usable_strata`) — the unit
            the Project Owner's GDR-002 instruction used for `N_w`. Recorded
            under a distinct name rather than silently treated as the same
            quantity as `n_w`; see GDR-002 §3.
        n_connected_components: Total connected components in the graph, for
            context (not itself one of `N_c`/`N_b`/`N_w`).
        scaffold_families_in_largest_component: Scaffold-family diversity
            restricted to the largest connected component specifically —
            the quantity R1's unchanged "< 8 scaffold families" disjunct
            requires. `None` because no existing module computes this
            component-restricted count; `SCI0-014b`'s `ScaffoldStats` is
            corpus-global and would answer a different question if
            substituted here (GDR-002 §3). Never fabricated.
    """

    n_c: int
    n_b: int
    n_w: int
    n_complete_compounds: int
    n_complete_strata: int
    n_connected_components: int
    scaffold_families_in_largest_component: int | None

    def to_canonical_dict(self) -> dict[str, int | None]:
        return {
            "n_b": self.n_b,
            "n_c": self.n_c,
            "n_complete_strata": self.n_complete_strata,
            "n_connected_components": self.n_connected_components,
            "n_w": self.n_w,
            "scaffold_families_in_largest_component": (self.scaffold_families_in_largest_component),
        }


@dataclass(frozen=True, slots=True)
class StructuralCoverageStats:
    """Reserved extension point for SCI0-007-derived structural coverage.

    Authority: `ADR-0009` §4. **No field here is computed by any code in this
    change set.** Every field defaults to `None`; the dataclass exists so a
    future `SCI0-018` computation has a documented target to populate, and so
    `quality/`'s `StructuralCoverageEvaluator` extension point can be
    demonstrated end-to-end (always returning `NOT_YET_AVAILABLE`) without
    inventing structural data.

    Attributes:
        experimental_pdb_coverage: Fraction or count of Tier 1 targets with an
            admissible experimental PDB structure (SCI0-007 §2.1). Reserved.
        alphafold_fallback_coverage: Fraction or count of Tier 1 targets
            relying on the governed AlphaFold fallback rather than an
            experimental structure (SCI0-007 amendment). Reserved.
        construct_diversity: Distinct construct descriptors observed across
            available structures. Reserved.
        conformational_state_diversity: Distinct conformational states
            represented (e.g. apo vs. ligand-bound, DFG-in/out where
            applicable). Reserved.
        ligand_bound_structural_coverage: Fraction or count of targets with at
            least one ligand-bound structure, as distinct from apo-only
            coverage (relevant to Constitution C6 / the induced specificity
            pocket). Reserved.
    """

    experimental_pdb_coverage: int | None = None
    alphafold_fallback_coverage: int | None = None
    construct_diversity: int | None = None
    conformational_state_diversity: int | None = None
    ligand_bound_structural_coverage: int | None = None

    def to_canonical_dict(self) -> dict[str, int | None]:
        return {
            "alphafold_fallback_coverage": self.alphafold_fallback_coverage,
            "conformational_state_diversity": self.conformational_state_diversity,
            "construct_diversity": self.construct_diversity,
            "experimental_pdb_coverage": self.experimental_pdb_coverage,
            "ligand_bound_structural_coverage": self.ligand_bound_structural_coverage,
        }


@dataclass(frozen=True, slots=True)
class CorpusProfile:
    """Immutable, content-hashed corpus profile attached to an SCI0-011 snapshot.

    Frozen dataclass — cannot be modified after creation, matching
    `CorpusSnapshotV2`'s immutability convention (`SCI0-011`).

    Attributes:
        schema_version: Corpus-profile schema version.
        profile_algorithm_version: See module-level `PROFILE_ALGORITHM_VERSION`.
        snapshot_sha256: The SCI0-011 snapshot this profile was computed from
            — a foreign-key reference, not an embedded mutation of the
            snapshot object.
        engineering_parameters: See `EngineeringParameters`.
        characterization: The full SCI0-014b `CharacterizationReport` for the
            same snapshot — dataset statistics, graph connectivity, scaffold
            statistics, and publication-concentration statistics, per
            GDR-002's frozen-profile content requirement.
        software: Toolchain provenance, reused from `SCI0-011`
            (`SoftwareProvenance`), not redefined.
        policy: Full policy-version bundle, reused from `SCI0-011`
            (`PolicyManifest`), not redefined.
        structural_coverage: Reserved SCI0-007 extension point (`ADR-0009` §4).
            `None` until `SCI0-018` exists; never fabricated.
        frozen_at_utc: When the profile was frozen. Provenance metadata only
            — excluded from `profile_sha256` (SCI0-011 precedent).
        profile_sha256: Content hash over every field above except
            `frozen_at_utc`. Two profiles computed from the same snapshot,
            software, policy, and algorithm version are byte-identical here.
    """

    schema_version: str
    profile_algorithm_version: str
    snapshot_sha256: str
    engineering_parameters: EngineeringParameters
    characterization: CharacterizationReport
    software: SoftwareProvenance
    policy: PolicyManifest
    structural_coverage: StructuralCoverageStats | None
    frozen_at_utc: str
    profile_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "engineering_parameters": self.engineering_parameters.to_canonical_dict(),
            "frozen_at_utc": self.frozen_at_utc,
            "policy": self.policy.to_canonical_dict(),
            "profile_algorithm_version": self.profile_algorithm_version,
            "profile_sha256": self.profile_sha256,
            "schema_version": self.schema_version,
            "snapshot_sha256": self.snapshot_sha256,
            "software": self.software.to_canonical_dict(),
            "structural_coverage": (
                self.structural_coverage.to_canonical_dict()
                if self.structural_coverage is not None
                else None
            ),
        }


def _characterization_canonical_dict(report: CharacterizationReport) -> dict[str, Any]:
    """Stable dict for a `CharacterizationReport`, for hashing and export.

    `CharacterizationReport` has no `to_dict()` of its own (SCI0-014b); this
    reads its dataclass fields directly rather than reopening that already-
    merged module to add one.
    """
    return {
        "accepted_records": report.accepted_records,
        "assay_format_counts": dict(sorted(report.assay_format_counts.items())),
        "censored_records": report.censored_records,
        "connectivity": {
            "bridging_compounds": report.connectivity.bridging_compounds,
            "compounds_all4_isoforms": report.connectivity.compounds_all4_isoforms,
            "largest_connected_component": report.connectivity.largest_connected_component,
            "n_connected_components": report.connectivity.n_connected_components,
            "n_four_isoform_clusters": report.connectivity.n_four_isoform_clusters,
            "n_study_clusters": report.connectivity.n_study_clusters,
            "total_compounds": report.connectivity.total_compounds,
            "within_study_four_isoform": report.connectivity.within_study_four_isoform,
        },
        "excluded_records": report.excluded_records,
        "isoform_stats": [
            {
                "isoform": s.isoform,
                "max_pactivity": s.max_pactivity,
                "median_pactivity": s.median_pactivity,
                "min_pactivity": s.min_pactivity,
                "n_censored": s.n_censored,
                "n_compounds": s.n_compounds,
                "n_exact": s.n_exact,
                "n_records": s.n_records,
                "quantity_types": dict(sorted(s.quantity_types.items())),
            }
            for s in sorted(report.isoform_stats, key=lambda x: x.isoform)
        ],
        "publication_stats": {
            "largest_publication_record_count": (
                report.publication_stats.largest_publication_record_count
            ),
            "median_records_per_publication": (
                report.publication_stats.median_records_per_publication
            ),
            "n_publications": report.publication_stats.n_publications,
            "n_records_with_pub": report.publication_stats.n_records_with_pub,
            "n_records_without_pub": report.publication_stats.n_records_without_pub,
        },
        "quantity_type_counts": dict(sorted(report.quantity_type_counts.items())),
        "scaffold_stats": {
            "largest_family_size": report.scaffold_stats.largest_family_size,
            "median_family_size": report.scaffold_stats.median_family_size,
            "n_acyclic_compounds": report.scaffold_stats.n_acyclic_compounds,
            "n_ring_system_families": report.scaffold_stats.n_ring_system_families,
            "n_scaffold_failed": report.scaffold_stats.n_scaffold_failed,
            "singleton_families": report.scaffold_stats.singleton_families,
        },
        "snapshot_sha256": report.snapshot_sha256,
        "temporal_counts": dict(sorted(report.temporal_counts.items())),
        "total_records": report.total_records,
    }


def freeze_corpus_profile(  # noqa: PLR0913, PLR0917
    snapshot_sha256: str,
    graph_stats: GraphStats,
    characterization: CharacterizationReport,
    software: SoftwareProvenance,
    policy: PolicyManifest,
    strata_report: StratumReport | None = None,
    structural_coverage: StructuralCoverageStats | None = None,
) -> CorpusProfile:
    """Freeze a corpus profile from already-computed corpus characteristics.

    Never reads raw records and never re-derives `graph_stats` or
    `characterization` — both must already exist, which by construction means
    they were computed from an already-frozen `SCI0-011` snapshot (GDR-002
    §5: "does not compute any parameter from partially curated data").

    Parameters
    ----------
    snapshot_sha256:
        The SCI0-011 snapshot's SHA-256. Not verified against `graph_stats`/
        `characterization` internally — the caller is responsible for
        passing characteristics actually computed from this snapshot; the
        `characterization.snapshot_sha256` field should already agree with
        this argument as a self-consistency check the caller can make.
    graph_stats:
        SCI0-014 `GraphStats` for the same snapshot.
    characterization:
        SCI0-014b `CharacterizationReport` for the same snapshot.
    software:
        Toolchain provenance (reused, not recomputed, from SCI0-011).
    policy:
        Policy-version bundle (reused, not recomputed, from SCI0-011).
    strata_report:
        SCI0-013 `StratumReport` for the same snapshot, if available. Supplies
        `n_complete_strata` (GDR-002 §3's strata-based `N_w` reading). `None`
        yields `n_complete_strata=0` with no error — a profile can be frozen
        without it, since it is not required to be the primary `n_w`.
    structural_coverage:
        Reserved SCI0-007 extension point (ADR-0009 §4). `None` by default;
        no code in this module computes it.

    Returns:
    -------
    CorpusProfile (frozen, immutable). Two calls with identical arguments
    (other than wall-clock time) produce an identical `profile_sha256`.
    """
    n_complete_strata = strata_report.usable_strata if strata_report is not None else 0
    n_complete_compounds = (
        strata_report.total_complete_compounds if strata_report is not None else 0
    )

    engineering_parameters = EngineeringParameters(
        n_c=graph_stats.largest_connected_component,
        n_b=graph_stats.bridging_compounds,
        n_w=graph_stats.within_study_four_isoform,
        n_complete_compounds=n_complete_compounds,
        n_complete_strata=n_complete_strata,
        n_connected_components=graph_stats.n_connected_components,
        scaffold_families_in_largest_component=None,
    )

    payload = _stable_json(
        {
            "characterization": _characterization_canonical_dict(characterization),
            "engineering_parameters": engineering_parameters.to_canonical_dict(),
            "policy": policy.to_canonical_dict(),
            "profile_algorithm_version": PROFILE_ALGORITHM_VERSION,
            "schema_version": CORPUS_PROFILE_SCHEMA_VERSION,
            "snapshot_sha256": snapshot_sha256,
            "software": software.to_canonical_dict(),
            "structural_coverage": (
                structural_coverage.to_canonical_dict() if structural_coverage is not None else None
            ),
        }
    )
    profile_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return CorpusProfile(
        schema_version=CORPUS_PROFILE_SCHEMA_VERSION,
        profile_algorithm_version=PROFILE_ALGORITHM_VERSION,
        snapshot_sha256=snapshot_sha256,
        engineering_parameters=engineering_parameters,
        characterization=characterization,
        software=software,
        policy=policy,
        structural_coverage=structural_coverage,
        frozen_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        profile_sha256=profile_sha256,
    )

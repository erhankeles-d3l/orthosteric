"""Compound × isoform measurement graph.

Objective: SCI0-014.
Specification: SCI0-001-refinement §SCI0-014.
  "Bipartite compound × isoform graph (graph.py): connected components,
   bridging compounds, study-cluster structure. This is the substrate the
   amended R1 is evaluated against."
Exit criteria:
  "largest component, bridging count and cluster structure computed and
   reproducible."

This module performs NO threshold selection and NO model training.
All statistics are descriptive and fully reproducible given the same input.

Graph definition
----------------
Nodes: compound InChIKeys (one node per unique compound).
Edges: a compound node is connected to an isoform node if the compound has
  at least one accepted, non-excluded activity record for that isoform.
  This is a bipartite compound × isoform graph in the graph-theoretic sense,
  but for connected-component purposes we project onto the compound layer:
  two compound nodes are in the same component if they co-appear in the same
  panel — i.e. they can be compared without cross-study confounding.

Panel definition (GDR-011, accepted, Option D)
-------------------------------------------------
A panel is `orthosteric.data.comparability.panel_key(record)` —
`(study_id, protocol)`, where `protocol` is the `(bao_format, assay_type)`
signature.  This REPLACES the previous `(study_id, assay_id)` definition,
which GDR-011 found structurally incapable of ever producing a
four-isoform panel on ChEMBL data (every ChEMBL assay covers exactly one
target).  Records lacking `bao_format`/`assay_type` fall back to
`(study_id, assay_id)` for backward compatibility with generic-algorithm
tests that predate GDR-011.

Connected components
--------------------
Two compounds are in the same component if they share a panel.
Implemented via union-find (path-compressed) for reproducibility and
O(n α(n)) complexity.

Bridging compounds
------------------
A compound is a bridging compound if it appears in ≥ 2 distinct panels AND
has measurements in ≥ 2 isoforms in at least one of those panels.  Bridging
compounds link study clusters and are the mechanism by which cross-study
comparison is possible.

Study-cluster structure
-----------------------
A study cluster is the set of compounds co-assayed in the same panel.  The
cluster structure records: number of clusters, size of the largest cluster,
median cluster size, and the number of clusters covering all four Tier 1
isoforms.

Primary interface
-----------------
build_graph_stats_from_records(records) — accepts serialized activity dicts,
  compatible with SCI0-011 snapshot architecture.  This is the SCI0-014 API.

Legacy interface (backwards compatibility)
------------------------------------------
build_graph_stats(snapshot) — accepts the legacy CorpusSnapshot/EvidenceRecord
  objects from corpus.py.  Retained to avoid breaking existing tests.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from orthosteric.data.comparability import resolve_panel_key

_TIER1_ISOFORMS: frozenset[str] = frozenset(
    {
        "PI3Kalpha",
        "PI3Kbeta",
        "PI3Kgamma",
        "PI3Kdelta",
    }
)


# ── Data types ────────────────────────────────────────────────────────────────


@dataclass
class StudyCluster:
    """Descriptive statistics for one within-study panel (GDR-011 Option D).

    `assay_id` retains its name for backward compatibility but, per
    GDR-011 (accepted), now holds the `(bao_format, assay_type)` protocol
    signature for records that carry those fields — not the raw ChEMBL
    assay identifier.  Records without those fields (generic-algorithm
    test fixtures predating GDR-011) still populate this with the literal
    assay_id, via `comparability.panel_key()`'s fallback.
    """

    study_id: str
    assay_id: str
    compound_count: int
    isoforms_covered: set[str]
    covers_all_tier1: bool


@dataclass
class GraphStats:
    """Descriptive graph statistics for the Stage 0 audit (R1, AUDITOR-2).

    All counts are over ACCEPTED records only (exclusion_reason is None).

    Attributes:
    ----------
    total_compounds:
        Unique compound InChIKeys with ≥ 1 accepted record.
    per_isoform_compounds:
        Compounds with ≥ 1 accepted record per isoform.
    compounds_ge2_isoforms:
        Compounds with accepted records for ≥ 2 isoforms.
    compounds_all4_isoforms:
        Compounds with accepted records for all 4 Tier 1 isoforms.
    n_connected_components:
        Number of connected components in the study-co-assay graph.
    largest_connected_component:
        N_c candidate — size of the largest component in compounds.
    bridging_compounds:
        N_b candidate — compounds appearing in ≥ 2 study panels with
        ≥ 2 isoforms in at least one panel.
    within_study_four_isoform:
        N_w candidate — unique compounds in studies covering all 4 isoforms.
    n_study_clusters:
        Number of distinct panels (GDR-011 Option D: study x protocol).
    largest_study_cluster:
        Compound count of the largest study cluster.
    median_study_cluster_size:
        Median compound count across all study clusters.
    n_four_isoform_clusters:
        Study clusters covering all 4 Tier 1 isoforms.
    scaffold_families:
        Unique scaffold_family_ids across accepted compounds.
    legacy_fallback_records:
        Count of accepted records whose panel key fell back to the
        rejected LEGACY_FALLBACK tier (GDR-011) — i.e. bao_format and
        assay_type were both absent.  Not scientific comparability
        evidence; reported for audit only.  Expected to be 0 on real
        ChEMBL data (bao_format/assay_type are 100% populated in Activity
        Snapshot A3).
    per_isoform_compounds:
        {isoform_name: compound_count}.
    study_clusters:
        Detailed list of StudyCluster objects.
    """

    total_compounds: int = 0
    per_isoform_compounds: dict[str, int] = field(default_factory=dict)
    compounds_ge2_isoforms: int = 0
    compounds_all4_isoforms: int = 0
    n_connected_components: int = 0
    largest_connected_component: int = 0
    bridging_compounds: int = 0
    within_study_four_isoform: int = 0
    n_study_clusters: int = 0
    largest_study_cluster: int = 0
    median_study_cluster_size: float = 0.0
    n_four_isoform_clusters: int = 0
    scaffold_families: int = 0
    legacy_fallback_records: int = 0
    study_clusters: list[StudyCluster] = field(default_factory=list)

    # Legacy aliases (keep backwards-compatible with existing tests)
    @property
    def n_studies(self) -> int:
        return self.n_study_clusters

    @property
    def compounds_per_study_median(self) -> float:
        return self.median_study_cluster_size

    @property
    def isoforms_per_study_median(self) -> float:
        if not self.study_clusters:
            return 0.0
        sizes = sorted(len(c.isoforms_covered) for c in self.study_clusters)
        return float(sizes[len(sizes) // 2])


@dataclass
class _RecordIndex:
    """Internal index built from accepted records — not part of the public API."""

    pass


def _index_records(
    accepted: list[dict[str, Any]],
) -> tuple[
    dict[str, set[str]],
    dict[str, set[tuple[str, str]]],
    dict[tuple[str, str], set[str]],
    dict[tuple[str, str], set[str]],
    set[str],
    int,
]:
    """Build index structures from accepted records."""
    compound_isoforms: dict[str, set[str]] = defaultdict(set)
    compound_panels: dict[str, set[tuple[str, str]]] = defaultdict(set)
    panel_compounds: dict[tuple[str, str], set[str]] = defaultdict(set)
    panel_isoforms: dict[tuple[str, str], set[str]] = defaultdict(set)
    scaffold_ids: set[str] = set()
    legacy_fallback_records = 0

    for rec in accepted:
        ik = str(rec["inchikey"])
        iso = str(rec["isoform"])
        # Panel definition: GDR-011 (accepted, Option D) — see module docstring.
        resolved = resolve_panel_key(rec)
        panel = resolved.key
        if not resolved.is_scientific_evidence:
            legacy_fallback_records += 1

        compound_isoforms[ik].add(iso)
        compound_panels[ik].add(panel)
        panel_compounds[panel].add(ik)
        panel_isoforms[panel].add(iso)

        fid = rec.get("scaffold_family_id")
        if fid and fid != "ACYCLIC":
            scaffold_ids.add(str(fid))

    return (
        compound_isoforms,
        compound_panels,
        panel_compounds,
        panel_isoforms,
        scaffold_ids,
        legacy_fallback_records,
    )


# ── Primary API (SCI0-014) ────────────────────────────────────────────────────


def build_graph_stats_from_records(
    records: list[dict[str, Any]],
    required_isoforms: frozenset[str] = _TIER1_ISOFORMS,
) -> GraphStats:
    """Compute graph statistics from serialized activity record dicts.

    Compatible with the SCI0-011 snapshot architecture and the
    harmonization layer (SCI0-008c, SCI0-009).

    Parameters
    ----------
    records:
        List of activity record dicts.  Each dict must contain at minimum:
        inchikey (str), isoform (str), study_id (str), assay_id (str).
        Records with exclusion_reason set are silently excluded.
        Records with missing inchikey or isoform are skipped.
    required_isoforms:
        The isoform set for completeness checks.  Defaults to all 4
        Tier 1 PI3K isoforms.

    Returns:
    -------
    GraphStats — fully reproducible given the same input set.
    """
    accepted = [
        r
        for r in records
        if r.get("exclusion_reason") is None and r.get("inchikey") and r.get("isoform")
    ]
    if not accepted:
        return GraphStats(
            per_isoform_compounds=dict.fromkeys(required_isoforms, 0),
        )

    return _compute_stats(accepted, required_isoforms)


def _compute_stats(
    accepted: list[dict[str, Any]],
    required_isoforms: frozenset[str],
) -> GraphStats:
    """Core computation — separated for testability."""
    (
        compound_isoforms,
        compound_panels,
        panel_compounds,
        panel_isoforms,
        scaffold_ids,
        legacy_fallback_records,
    ) = _index_records(accepted)

    all_compounds = list(compound_isoforms)
    n = len(all_compounds)
    c_idx = {c: i for i, c in enumerate(all_compounds)}

    # ── Union-find (path-compressed) ─────────────────────────────────────────
    parent = list(range(n))
    rank = [0] * n

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path halving
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px == py:
            return
        if rank[px] < rank[py]:
            px, py = py, px
        parent[py] = px
        if rank[px] == rank[py]:
            rank[px] += 1

    for panel_cset in panel_compounds.values():
        clist = list(panel_cset)
        for i in range(1, len(clist)):
            union(c_idx[clist[0]], c_idx[clist[i]])

    comp_sizes: dict[int, int] = defaultdict(int)
    for i in range(n):
        comp_sizes[find(i)] += 1

    lcc = max(comp_sizes.values()) if comp_sizes else 0
    n_components = len(comp_sizes)

    # ── Bridging compounds ────────────────────────────────────────────────────
    # A compound bridges study clusters if it appears in ≥ 2 distinct
    # panels (GDR-011 Option D).  It links those clusters, enabling
    # cross-study offset estimation even if each panel is single-isoform.
    # Additionally it must have ≥ 2 isoforms measured IN TOTAL across all panels
    # (so a compound seen twice in the same isoform across different studies is
    # not counted as a bridging compound for comparative purposes).
    bridging = sum(
        1
        for ik, panels in compound_panels.items()
        if len(panels) >= 2 and len(compound_isoforms[ik]) >= 2
    )

    # ── Within-study four-isoform (N_w) ──────────────────────────────────────
    four_iso_panels = {p for p, isos in panel_isoforms.items() if required_isoforms.issubset(isos)}
    nw_compounds: set[str] = set()
    for p in four_iso_panels:
        nw_compounds.update(panel_compounds[p])

    # ── Per-isoform counts ────────────────────────────────────────────────────
    per_iso: dict[str, int] = dict.fromkeys(required_isoforms, 0)
    for isos in compound_isoforms.values():
        for iso in isos:
            if iso in per_iso:
                per_iso[iso] += 1

    # ── Study cluster structure ───────────────────────────────────────────────
    clusters: list[StudyCluster] = []
    for (sid, aid), cset in panel_compounds.items():
        isos = panel_isoforms[(sid, aid)]
        clusters.append(
            StudyCluster(
                study_id=sid,
                assay_id=aid,
                compound_count=len(cset),
                isoforms_covered=isos,
                covers_all_tier1=required_isoforms.issubset(isos),
            )
        )

    cluster_sizes = sorted(c.compound_count for c in clusters)
    median_cs = float(statistics.median(cluster_sizes)) if cluster_sizes else 0.0
    largest_cs = max(cluster_sizes) if cluster_sizes else 0
    n_four_iso = sum(1 for c in clusters if c.covers_all_tier1)

    return GraphStats(
        total_compounds=n,
        per_isoform_compounds=per_iso,
        compounds_ge2_isoforms=sum(1 for v in compound_isoforms.values() if len(v) >= 2),
        compounds_all4_isoforms=sum(
            1 for v in compound_isoforms.values() if required_isoforms.issubset(v)
        ),
        n_connected_components=n_components,
        largest_connected_component=lcc,
        bridging_compounds=bridging,
        within_study_four_isoform=len(nw_compounds),
        n_study_clusters=len(clusters),
        largest_study_cluster=largest_cs,
        median_study_cluster_size=median_cs,
        n_four_isoform_clusters=n_four_iso,
        scaffold_families=len(scaffold_ids),
        legacy_fallback_records=legacy_fallback_records,
        study_clusters=clusters,
    )


# ── Legacy interface (backwards compatibility with corpus.py) ─────────────────


def build_graph_stats(snapshot: Any) -> GraphStats:
    """Build graph stats from a legacy CorpusSnapshot object.

    Backwards-compatible wrapper for existing tests and callers.
    New code should use build_graph_stats_from_records() instead.
    """
    accepted = snapshot.accepted()
    if not accepted:
        return GraphStats(
            per_isoform_compounds=dict.fromkeys(_TIER1_ISOFORMS, 0),
        )

    # Convert EvidenceRecord objects to the dict format expected by _compute_stats
    records = []
    for rec in accepted:
        # EvidenceRecord may have isoform as an Isoform enum or a string
        isoform_val = rec.isoform
        if hasattr(isoform_val, "value"):
            isoform_val = isoform_val.value
        records.append(
            {
                "inchikey": rec.inchikey or rec.source_compound_id,
                "isoform": str(isoform_val) if isoform_val else "",
                "study_id": rec.assay_id or "UNKNOWN_STUDY",
                "assay_id": rec.assay_id or "UNKNOWN_ASSAY",
                "exclusion_reason": rec.exclusion_reason,
                "scaffold_family_id": getattr(rec, "scaffold_family_id", None),
            }
        )

    return _compute_stats(
        [r for r in records if not r["exclusion_reason"] and r["inchikey"] and r["isoform"]],
        _TIER1_ISOFORMS,
    )

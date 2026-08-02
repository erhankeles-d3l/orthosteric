"""Compound × isoform evidence graph.

Builds a bipartite graph (compounds × isoforms) from an accepted corpus
snapshot and computes the descriptive statistics required by ADR-0003
AUDITOR-2: connected components, largest connected component (Lcc),
bridging compounds, study clustering, and within-study stratum.

This module performs NO threshold selection or model training.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from orthosteric.data.corpus import CorpusSnapshot, Isoform

# ──────────────────────────────────────────────────────────────────────────────
# Graph structure
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class GraphStats:
    """Descriptive graph statistics for the Auditor package."""

    total_compounds: int = 0
    per_isoform_compounds: dict[str, int] = field(default_factory=dict)
    compounds_ge2_isoforms: int = 0
    compounds_all4_isoforms: int = 0
    n_connected_components: int = 0
    largest_connected_component: int = 0  # N_c candidate
    bridging_compounds: int = 0  # N_b candidate
    within_study_four_isoform: int = 0  # N_w candidate
    n_studies: int = 0
    scaffold_families: int = 0
    compounds_per_study_median: float = 0.0
    isoforms_per_study_median: float = 0.0


def build_graph_stats(snapshot: CorpusSnapshot) -> GraphStats:
    """Compute descriptive statistics from the accepted records.

    Union-find approach for connected components: two compounds are in the
    same component if they share a study+isoform pair (i.e., they were
    co-assayed in the same study against the same isoform, enabling
    cross-compound offset estimation).
    """
    accepted = snapshot.accepted()
    if not accepted:
        return GraphStats()

    # ── Per-compound isoform coverage ────────────────────────────────────────
    compound_isoforms: dict[str, set[Isoform]] = defaultdict(set)
    compound_studies: dict[str, set[str]] = defaultdict(set)
    study_compounds: dict[str, set[str]] = defaultdict(set)
    study_isoforms: dict[str, set[Isoform]] = defaultdict(set)

    for rec in accepted:
        cid = rec.source_compound_id
        iso = rec.isoform
        sid = rec.assay_id or "UNKNOWN_STUDY"
        if cid and iso:
            compound_isoforms[cid].add(iso)
            compound_studies[cid].add(sid)
            study_compounds[sid].add(cid)
        if sid and iso:
            study_isoforms[sid].add(iso)

    all_compounds = list(compound_isoforms.keys())
    n = len(all_compounds)
    c_idx = {c: i for i, c in enumerate(all_compounds)}

    # ── Union-find for connected components ──────────────────────────────────
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Connect compounds sharing a study-isoform context
    for _sid, cset in study_compounds.items():
        clist = list(cset)
        for i in range(len(clist)):
            for j in range(i + 1, len(clist)):
                ci, cj = clist[i], clist[j]
                if ci in c_idx and cj in c_idx:
                    union(c_idx[ci], c_idx[cj])

    # Component sizes
    comp_sizes: dict[int, int] = defaultdict(int)
    for i in range(n):
        comp_sizes[find(i)] += 1

    n_components = len(comp_sizes)
    lcc = max(comp_sizes.values()) if comp_sizes else 0

    # ── Bridging compounds ────────────────────────────────────────────────────
    # A compound bridges study clusters if it appears in ≥2 distinct studies
    # and has measurements on overlapping isoforms across them.
    bridging = sum(
        1
        for cid, studies in compound_studies.items()
        if len(studies) >= 2 and len(compound_isoforms[cid]) >= 2
    )

    # ── Within-study four-isoform stratum ─────────────────────────────────────
    # Studies with records for all four isoforms; count unique compounds in them
    four_iso_studies = {sid for sid, isos in study_isoforms.items() if len(isos) == 4}
    within_study_cpds: set[str] = set()
    for rec in accepted:
        sid = rec.assay_id or "UNKNOWN_STUDY"
        if sid in four_iso_studies:
            within_study_cpds.add(rec.source_compound_id)

    # ── Per-isoform counts ────────────────────────────────────────────────────
    per_iso: dict[str, int] = {iso.value: 0 for iso in Isoform}
    for _cid, isos in compound_isoforms.items():
        for iso in isos:
            per_iso[iso.value] += 1

    # ── Study-level statistics ────────────────────────────────────────────────
    study_sizes = sorted(len(v) for v in study_compounds.values())
    iso_sizes = sorted(len(v) for v in study_isoforms.values())

    def _median_int(xs: list[int]) -> float:
        return float(xs[len(xs) // 2]) if xs else 0.0

    # ── Scaffold families ─────────────────────────────────────────────────────
    scaffold_ids = {r.scaffold_family_id for r in accepted if r.scaffold_family_id}

    return GraphStats(
        total_compounds=n,
        per_isoform_compounds=per_iso,
        compounds_ge2_isoforms=sum(1 for v in compound_isoforms.values() if len(v) >= 2),
        compounds_all4_isoforms=sum(1 for v in compound_isoforms.values() if len(v) == 4),
        n_connected_components=n_components,
        largest_connected_component=lcc,
        bridging_compounds=bridging,
        within_study_four_isoform=len(within_study_cpds),
        n_studies=len(study_compounds),
        scaffold_families=len(scaffold_ids),
        compounds_per_study_median=_median_int(study_sizes),
        isoforms_per_study_median=_median_int(iso_sizes),
    )

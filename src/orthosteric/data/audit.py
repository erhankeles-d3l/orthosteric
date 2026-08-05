"""Dataset characterization — descriptive analysis of a corpus snapshot.

Objective: SCI0-014b.
Specification: SCI0-001-refinement §SCI0-014b.
  "Describes the snapshot; never modifies it. Descriptive analysis only."
  Outputs: activity distributions per isoform and quantity type; assay-format
  distributions; publication distributions and per-publication concentration;
  scaffold distributions; confidence distributions (by contributing term);
  connectivity statistics; missingness heat maps; isoform overlap matrices;
  temporal trends.

Design invariants (binding)
---------------------------
1. This module NEVER modifies records, snapshots, or any upstream object.
2. All outputs are purely descriptive counts and distributions.
3. Outputs may NOT be used to inform split decisions, stratum selection,
   or threshold setting (Constitution §3.4 as amended; SCI0-028 owns sealing).
4. The characterization report is attached to the snapshot SHA-256 it was
   computed from — the snapshot identity is recorded in CharacterizationReport.
5. All statistics are reproducible: same snapshot → identical report.
"""

from __future__ import annotations

import contextlib
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

# ── Output types ────────────────────────────────────────────────────────────


@dataclass
class IsoformStats:
    """Activity statistics for one isoform."""

    isoform: str
    n_records: int
    n_compounds: int
    n_censored: int
    n_exact: int
    median_pactivity: float | None
    min_pactivity: float | None
    max_pactivity: float | None
    quantity_types: dict[str, int]  # {IC50, Ki, ...} → count


@dataclass
class ScaffoldStats:
    """Scaffold-family distribution."""

    n_ring_system_families: int
    n_acyclic_compounds: int
    n_scaffold_failed: int
    largest_family_size: int
    median_family_size: float
    singleton_families: int


@dataclass
class ConnectivityStats:
    """Graph connectivity summary (from SCI0-014)."""

    total_compounds: int
    n_connected_components: int
    largest_connected_component: int
    bridging_compounds: int
    within_study_four_isoform: int
    n_study_clusters: int
    n_four_isoform_clusters: int
    compounds_all4_isoforms: int


@dataclass
class ConfidenceStats:
    """Confidence distribution by tier."""

    tier_counts: dict[str, int]  # {T1, T2, T3, T4_EXCLUDED} → count
    mean_confidence: float | None
    median_confidence: float | None


@dataclass
class PublicationStats:
    """Per-publication concentration metrics."""

    n_publications: int
    n_records_with_pub: int
    n_records_without_pub: int
    largest_publication_record_count: int
    median_records_per_publication: float


@dataclass
class MissingnessMatrix:
    """Isoform overlap matrix — which isoform pairs co-appear in records.

    missing[iso_a][iso_b] = number of compounds with records for iso_a
    but NOT for iso_b (directional; not symmetric).
    overlap[iso_a][iso_b] = compounds measured in BOTH iso_a and iso_b.
    """

    overlap: dict[str, dict[str, int]]
    missing_directional: dict[str, dict[str, int]]
    isoforms: list[str]


@dataclass
class CharacterizationReport:
    """Complete dataset characterization for one corpus snapshot.

    Attributes:
    ----------
    snapshot_sha256:    SHA-256 of the snapshot this was computed from.
    total_records:      Total records (accepted + excluded).
    accepted_records:   Records with no exclusion_reason.
    excluded_records:   Records with an exclusion_reason.
    censored_records:   Right- or left-censored records.
    isoform_stats:      Per-isoform activity statistics.
    scaffold_stats:     Scaffold-family distribution.
    connectivity:       Graph connectivity (from SCI0-014).
    confidence_stats:   Confidence distribution.
    publication_stats:  Per-publication concentration.
    missingness:        Isoform overlap / missingness matrix.
    assay_format_counts:{assay_format → count}.
    quantity_type_counts:{quantity_type → count} across all records.
    temporal_counts:    {year → record_count} for records with retrieval dates.
    """

    snapshot_sha256: str
    total_records: int
    accepted_records: int
    excluded_records: int
    censored_records: int
    isoform_stats: list[IsoformStats]
    scaffold_stats: ScaffoldStats
    connectivity: ConnectivityStats
    confidence_stats: ConfidenceStats
    publication_stats: PublicationStats
    missingness: MissingnessMatrix
    assay_format_counts: dict[str, int]
    quantity_type_counts: dict[str, int]
    temporal_counts: dict[str, int]


# ── Builder ─────────────────────────────────────────────────────────────────


def characterize(
    records: list[dict[str, Any]],
    snapshot_sha256: str = "",
) -> CharacterizationReport:
    """Compute a full dataset characterization from serialized record dicts.

    NEVER modifies records.  Returns a CharacterizationReport with all
    descriptive statistics attached to snapshot_sha256.

    Parameters
    ----------
    records:
        All records from the snapshot (accepted AND excluded).
    snapshot_sha256:
        SHA-256 of the source snapshot (SCI0-011 identity).
    """
    total = len(records)
    accepted = [r for r in records if r.get("exclusion_reason") is None]
    excluded = [r for r in records if r.get("exclusion_reason") is not None]
    censored = [
        r for r in accepted if str(r.get("censoring", "")) in ("right_censored", "left_censored")
    ]

    isoform_stats = _build_isoform_stats(accepted)
    scaffold_stats = _build_scaffold_stats(accepted)
    connectivity = _build_connectivity(accepted)
    confidence_stats = _build_confidence_stats(accepted)
    pub_stats = _build_pub_stats(accepted)
    missingness = _build_missingness(accepted)
    assay_counts = _count_field(accepted, "assay_format")
    qty_counts = _count_field(accepted, "activity_type")
    temporal = _build_temporal(records)  # temporal over ALL records

    return CharacterizationReport(
        snapshot_sha256=snapshot_sha256,
        total_records=total,
        accepted_records=len(accepted),
        excluded_records=len(excluded),
        censored_records=len(censored),
        isoform_stats=isoform_stats,
        scaffold_stats=scaffold_stats,
        connectivity=connectivity,
        confidence_stats=confidence_stats,
        publication_stats=pub_stats,
        missingness=missingness,
        assay_format_counts=assay_counts,
        quantity_type_counts=qty_counts,
        temporal_counts=temporal,
    )


# ── Private helpers ─────────────────────────────────────────────────────────


def _build_isoform_stats(accepted: list[dict[str, Any]]) -> list[IsoformStats]:
    from orthosteric.data.graph import _TIER1_ISOFORMS  # noqa: PLC0415

    by_iso: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in accepted:
        iso = str(r.get("isoform", ""))
        if iso:
            by_iso[iso].append(r)

    stats = []
    all_isos = sorted(set(by_iso.keys()) | _TIER1_ISOFORMS)
    for iso in all_isos:
        recs = by_iso.get(iso, [])
        compounds = {str(r.get("inchikey", "")) for r in recs if r.get("inchikey")}
        exact = [r for r in recs if str(r.get("censoring", "exact")) == "exact"]
        censored = [
            r for r in recs if str(r.get("censoring", "")) in ("right_censored", "left_censored")
        ]
        values = [float(r["activity_value"]) for r in exact if r.get("activity_value") is not None]
        qty = _count_field(recs, "activity_type")
        stats.append(
            IsoformStats(
                isoform=iso,
                n_records=len(recs),
                n_compounds=len(compounds),
                n_censored=len(censored),
                n_exact=len(exact),
                median_pactivity=statistics.median(values) if values else None,
                min_pactivity=min(values) if values else None,
                max_pactivity=max(values) if values else None,
                quantity_types=qty,
            )
        )
    return stats


def _build_scaffold_stats(accepted: list[dict[str, Any]]) -> ScaffoldStats:
    ring_families: set[str] = set()
    acyclic = 0
    failed = 0
    family_sizes: Counter[str] = Counter()

    for r in accepted:
        fid = r.get("scaffold_family_id")
        status = str(r.get("scaffold_status", r.get("status", "")))
        if fid == "ACYCLIC" or status == "acyclic":
            acyclic += 1
        elif fid is None or "FAILED" in status.upper():
            failed += 1
        else:
            ring_families.add(str(fid))
            family_sizes[str(fid)] += 1

    sizes = list(family_sizes.values())
    return ScaffoldStats(
        n_ring_system_families=len(ring_families),
        n_acyclic_compounds=acyclic,
        n_scaffold_failed=failed,
        largest_family_size=max(sizes) if sizes else 0,
        median_family_size=float(statistics.median(sizes)) if sizes else 0.0,
        singleton_families=sum(1 for v in sizes if v == 1),
    )


def _build_connectivity(accepted: list[dict[str, Any]]) -> ConnectivityStats:
    from orthosteric.data.graph import build_graph_stats_from_records  # noqa: PLC0415

    gs = build_graph_stats_from_records(accepted)
    return ConnectivityStats(
        total_compounds=gs.total_compounds,
        n_connected_components=gs.n_connected_components,
        largest_connected_component=gs.largest_connected_component,
        bridging_compounds=gs.bridging_compounds,
        within_study_four_isoform=gs.within_study_four_isoform,
        n_study_clusters=gs.n_study_clusters,
        n_four_isoform_clusters=gs.n_four_isoform_clusters,
        compounds_all4_isoforms=gs.compounds_all4_isoforms,
    )


def _build_confidence_stats(accepted: list[dict[str, Any]]) -> ConfidenceStats:
    tiers: Counter[str] = Counter()
    scores: list[float] = []
    for r in accepted:
        tier = str(r.get("provenance_tier", r.get("curation_tier", "")))
        if tier:
            tiers[tier] += 1
        score = r.get("confidence_score")
        if score is not None:
            with contextlib.suppress(ValueError, TypeError):
                scores.append(float(score))
    return ConfidenceStats(
        tier_counts=dict(tiers),
        mean_confidence=statistics.mean(scores) if scores else None,
        median_confidence=statistics.median(scores) if scores else None,
    )


def _build_pub_stats(accepted: list[dict[str, Any]]) -> PublicationStats:
    with_pub = [r for r in accepted if r.get("publication_id") or r.get("publication_doi")]
    without_pub = [
        r for r in accepted if not r.get("publication_id") and not r.get("publication_doi")
    ]
    pub_ids: Counter[str] = Counter()
    for r in with_pub:
        pid = str(r.get("publication_id") or r.get("publication_doi") or "")
        if pid:
            pub_ids[pid] += 1
    sizes = list(pub_ids.values())
    return PublicationStats(
        n_publications=len(pub_ids),
        n_records_with_pub=len(with_pub),
        n_records_without_pub=len(without_pub),
        largest_publication_record_count=max(sizes) if sizes else 0,
        median_records_per_publication=float(statistics.median(sizes)) if sizes else 0.0,
    )


def _build_missingness(accepted: list[dict[str, Any]]) -> MissingnessMatrix:
    from orthosteric.data.graph import _TIER1_ISOFORMS  # noqa: PLC0415

    isoforms = sorted(_TIER1_ISOFORMS)
    compound_isos: dict[str, set[str]] = defaultdict(set)
    for r in accepted:
        ik = str(r.get("inchikey", ""))
        iso = str(r.get("isoform", ""))
        if ik and iso:
            compound_isos[ik].add(iso)

    overlap: dict[str, dict[str, int]] = {i: dict.fromkeys(isoforms, 0) for i in isoforms}
    missing: dict[str, dict[str, int]] = {i: dict.fromkeys(isoforms, 0) for i in isoforms}

    for isos in compound_isos.values():
        for i in isoforms:
            for j in isoforms:
                if i in isos and j in isos:
                    overlap[i][j] += 1
                elif i in isos and j not in isos:
                    missing[i][j] += 1

    return MissingnessMatrix(
        overlap=overlap,
        missing_directional=missing,
        isoforms=isoforms,
    )


def _count_field(records: list[dict[str, Any]], field_name: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for r in records:
        val = r.get(field_name)
        if val is not None:
            counts[str(val)] += 1
    return dict(counts)


def _build_temporal(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for r in records:
        ts = str(r.get("retrieval_timestamp", "") or r.get("created_at", ""))
        if len(ts) >= 4 and ts[:4].isdigit():
            counts[ts[:4]] += 1
    return dict(sorted(counts.items()))

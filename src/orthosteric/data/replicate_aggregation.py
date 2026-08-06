"""Deterministic, provenance-preserving replicate aggregation.

Objective: GDR-013 (GGR-002b noise-floor structure), prerequisite for
GDR-012 (GGR-002a evidence classification).

Replaces the last-write-wins collapse previously present in the
analysis-layer GGR-002a pair-generation code (`ggr_reassessment_a4.py`),
which took whichever record Python iterated last for a
(panel, compound, isoform) cell with >=2 pchembl_value-bearing records.
That was reproducible given a fixed input file, but not a principled
aggregate, and not invariant to a re-ordering of upstream records
(473 of 852 such cells in Activity Snapshot A4 have >0.3 pAct spread
between candidate values -- see analysis/ggr002_decision_package_audit.py).

Policy (GDR-013)
-----------------
Within one (panel, compound, isoform) cell:
  - Exact (pchembl_value-bearing) observations are combined by MEDIAN,
    computed over a value list sorted before aggregation so the result and
    every derived provenance list is independent of input record order.
    This mirrors the GDR-001 precedent (`_deduplicator.py`,
    `RESOLVED_REPLICATE_MEDIAN`) at the coarser panel-level identity used by
    GDR-011's comparability unit, rather than the finer
    compound x isoform x construct x organism x assay x source identity
    `_deduplicator.py` operates on.
  - Censored observations (right/left) are NEVER folded into the exact
    median and NEVER silently discarded: their source_record_ids and
    censoring kinds are retained on the AggregatedCell for audit, but
    `value` reflects exact evidence only. A cell with only censored
    contributors has `value is None` -- explicitly excluded from any
    exact-value MMP evidence (GDR-012) until a censoring-aware method is
    governed, never treated as "missing" or "inactive".
  - Every contributing ChEMBL `assay_id` is retained, which lets a
    downstream consumer (noise_floor.py) distinguish a TRUE_REPLICATE cell
    (all contributors share one assay_id -- a genuine repeat measurement)
    from a CROSS_ASSAY cell (contributors span >1 assay_id under one
    GDR-011 C1 protocol signature -- cross-assay agreement, a different and
    generally larger source of variance; see GDR-013).

This module does not decide what a "valid MMP" or a "noise floor multiplier"
is -- see mmp_candidates.py and noise_floor.py respectively.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from orthosteric.data.comparability import resolve_panel_key

#: GDR-013 aggregation policy identifier.
POLICY_ID = "gdr013_replicate_median_aggregation_v1"


class ReplicateType(StrEnum):
    """Whether a cell's exact contributors represent a true repeat
    measurement or cross-assay agreement (GDR-013).
    """

    SINGLE = "single"  # exactly one exact contributor; not a replicate at all
    TRUE_REPLICATE = "true_replicate"  # >=2 exact contributors, one assay_id
    CROSS_ASSAY = "cross_assay"  # >=2 exact contributors, >1 assay_id
    NONE = "none"  # zero exact contributors (censored-only or empty cell)


def _pact(record: dict[str, Any]) -> float | None:
    v = record.get("pchembl_value")
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class AggregatedCell:
    """Deterministic aggregate of all records sharing one
    (panel, compound, isoform) cell.

    Attributes:
    ----------
    panel_key:          (study_id, protocol) per `comparability.panel_key`.
    inchikey:           Compound identity.
    isoform:            PI3K isoform.
    value:              Median of exact (pchembl_value) observations, or
                        None if the cell has zero exact observations
                        (censored-only or empty). NEVER a censored value.
    exact_values:       All contributing exact values, sorted ascending --
                        retained (not just the median) so noise_floor.py can
                        compute within-cell spread/variance directly.
    n_exact:            len(exact_values).
    spread:             max(exact_values) - min(exact_values), or None if
                        n_exact < 2.
    replicate_type:     SINGLE / TRUE_REPLICATE / CROSS_ASSAY / NONE.
    source_record_ids:  source_record_id of every EXACT contributor, sorted.
    censored_source_record_ids: source_record_id of every CENSORED
                        contributor, sorted. Retained for audit even though
                        excluded from `value` (GDR-012: censored preserved
                        explicitly, never silently discarded).
    censoring_kinds:    Distinct censoring values among censored
                        contributors (e.g. ("left",), ("right",),
                        ("left", "right")).
    unclassified_source_record_ids: source_record_id of every contributor
                        that is neither an exact pchembl_value nor a
                        right/left-censored record -- e.g. `censoring ==
                        "exact"` with pchembl_value absent (a ChEMBL
                        data-quality gap, ~0.7% of A4 accepted records;
                        empirically observed in
                        analysis/ggr002_decision_package_audit.py section
                        2). Retained explicitly rather than silently
                        dropped; NOT folded into either `value` or
                        `censored_source_record_ids`.
    assay_ids:          Distinct ChEMBL assay_id values among ALL
                        contributors (exact + censored + unclassified),
                        sorted.
    policy:             POLICY_ID.
    """

    panel_key: tuple[str, str]
    inchikey: str
    isoform: str
    value: float | None
    exact_values: tuple[float, ...]
    n_exact: int
    spread: float | None
    replicate_type: ReplicateType
    source_record_ids: tuple[str, ...]
    censored_source_record_ids: tuple[str, ...]
    censoring_kinds: tuple[str, ...]
    unclassified_source_record_ids: tuple[str, ...]
    assay_ids: tuple[str, ...]
    policy: str = field(default=POLICY_ID)


def aggregate_cell(
    records: list[dict[str, Any]],
    panel_key: tuple[str, str],
    inchikey: str,
    isoform: str,
) -> AggregatedCell:
    """Deterministically aggregate all records for one (panel, compound,
    isoform) cell. Caller supplies records already filtered to that cell.

    Order-independent: sorting happens inside this function, so calling it
    with the same record set in any order produces an identical result.
    """
    exact = sorted(
        ((r, v) for r in records if (v := _pact(r)) is not None),
        key=lambda rv: (rv[1], str(rv[0].get("source_record_id", ""))),
    )
    censored = [
        r for r in records if _pact(r) is None and r.get("censoring") not in (None, "exact")
    ]
    unclassified = [
        r for r in records if _pact(r) is None and r.get("censoring") in (None, "exact")
    ]

    exact_values = tuple(v for _, v in exact)
    n_exact = len(exact_values)
    value = statistics.median(exact_values) if exact_values else None
    spread = (max(exact_values) - min(exact_values)) if n_exact >= 2 else None

    exact_assay_ids = {str(r.get("assay_id")) for r, _ in exact if r.get("assay_id") is not None}
    if n_exact == 0:
        replicate_type = ReplicateType.NONE
    elif n_exact == 1:
        replicate_type = ReplicateType.SINGLE
    elif len(exact_assay_ids) <= 1:
        replicate_type = ReplicateType.TRUE_REPLICATE
    else:
        replicate_type = ReplicateType.CROSS_ASSAY

    all_assay_ids = sorted(
        {str(r.get("assay_id")) for r in records if r.get("assay_id") is not None}
    )
    source_record_ids = sorted(str(r.get("source_record_id", "")) for r, _ in exact)
    censored_source_record_ids = sorted(str(r.get("source_record_id", "")) for r in censored)
    censoring_kinds = tuple(sorted({str(r.get("censoring")) for r in censored}))
    unclassified_source_record_ids = sorted(
        str(r.get("source_record_id", "")) for r in unclassified
    )

    return AggregatedCell(
        panel_key=panel_key,
        inchikey=inchikey,
        isoform=isoform,
        value=value,
        exact_values=exact_values,
        n_exact=n_exact,
        spread=spread,
        replicate_type=replicate_type,
        source_record_ids=tuple(source_record_ids),
        censored_source_record_ids=tuple(censored_source_record_ids),
        censoring_kinds=censoring_kinds,
        unclassified_source_record_ids=tuple(unclassified_source_record_ids),
        assay_ids=tuple(all_assay_ids),
        policy=POLICY_ID,
    )


def aggregate_records_by_cell(
    records: list[dict[str, Any]],
) -> dict[tuple[tuple[str, str], str, str], AggregatedCell]:
    """Group accepted records into (panel, compound, isoform) cells and
    aggregate each deterministically.

    Only C1_PRIMARY panels (GDR-011, Option D) contribute --
    LEGACY_FALLBACK records are excluded here, at the point of entry, the
    same way `mmp_candidates.py` and `noise_floor.py` require.
    """
    raw_cells: dict[tuple[tuple[str, str], str, str], list[dict[str, Any]]] = {}
    for r in records:
        if r.get("exclusion_reason") is not None:
            continue
        resolved = resolve_panel_key(r)
        if not resolved.is_scientific_evidence:
            continue
        ik = r.get("inchikey")
        iso = r.get("isoform")
        if not ik or not iso:
            continue
        raw_cells.setdefault((resolved.key, ik, iso), []).append(r)

    return {
        cell_key: aggregate_cell(cell_records, cell_key[0], cell_key[1], cell_key[2])
        for cell_key, cell_records in raw_cells.items()
    }

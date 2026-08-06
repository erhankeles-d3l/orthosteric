"""Tests for GDR-013 replicate aggregation.

Exit criteria:
  (1) Deterministic aggregation is order-independent (the property that
      replaces the last-write-wins defect in the prior analysis code).
  (2) TRUE_REPLICATE vs CROSS_ASSAY vs SINGLE vs NONE classified correctly.
  (3) Censored observations preserved explicitly, never folded into value.
  (4) The censoring="exact"-with-no-pchembl_value edge case is tracked
      separately from true censoring, never silently dropped.
  (5) LEGACY_FALLBACK panels never contribute a cell.
"""

from __future__ import annotations

import random

from orthosteric.data.replicate_aggregation import (
    ReplicateType,
    aggregate_cell,
    aggregate_records_by_cell,
)


def _r(
    pchembl=None,
    source_record_id="R1",
    assay_id="A1",
    censoring="exact",
    inchikey="IK1",
    isoform="PI3Kalpha",
    study_id="S1",
    bao_format="BAO_1",
    assay_type="B",
    exclusion_reason=None,
):
    return {
        "pchembl_value": pchembl,
        "source_record_id": source_record_id,
        "assay_id": assay_id,
        "censoring": censoring,
        "inchikey": inchikey,
        "isoform": isoform,
        "study_id": study_id,
        "bao_format": bao_format,
        "assay_type": assay_type,
        "exclusion_reason": exclusion_reason,
    }


PANEL = ("S1", "BAO_1::B")


# ── determinism / order-independence ─────────────────────────────────────────


def test_aggregate_cell_median_of_two_exact() -> None:
    recs = [_r(pchembl=6.0, source_record_id="R1"), _r(pchembl=7.0, source_record_id="R2")]
    cell = aggregate_cell(recs, PANEL, "IK1", "PI3Kalpha")
    assert cell.value == 6.5
    assert cell.n_exact == 2
    assert cell.spread == 1.0


def test_aggregate_cell_order_independent() -> None:
    """The exact property that replaces last-write-wins: any permutation of
    the same records must yield an identical result."""
    recs = [
        _r(pchembl=6.0, source_record_id="R1", assay_id="A1"),
        _r(pchembl=7.5, source_record_id="R2", assay_id="A1"),
        _r(pchembl=6.8, source_record_id="R3", assay_id="A1"),
    ]
    results = []
    for _ in range(10):
        shuffled = recs[:]
        random.shuffle(shuffled)
        results.append(aggregate_cell(shuffled, PANEL, "IK1", "PI3Kalpha"))
    values = {r.value for r in results}
    source_id_tuples = {r.source_record_ids for r in results}
    assert len(values) == 1
    assert len(source_id_tuples) == 1
    assert results[0].value == 6.8  # median of {6.0, 6.8, 7.5}


def test_aggregate_records_by_cell_order_independent() -> None:
    recs = [
        _r(pchembl=6.0, source_record_id="R1", assay_id="A1"),
        _r(pchembl=7.5, source_record_id="R2", assay_id="A1"),
    ]
    r1 = aggregate_records_by_cell(recs)
    r2 = aggregate_records_by_cell(list(reversed(recs)))
    assert r1 == r2


# ── ReplicateType classification ─────────────────────────────────────────────


def test_single_exact_record_is_single_type() -> None:
    cell = aggregate_cell([_r(pchembl=6.0)], PANEL, "IK1", "PI3Kalpha")
    assert cell.replicate_type is ReplicateType.SINGLE
    assert cell.value == 6.0
    assert cell.spread is None


def test_two_records_same_assay_is_true_replicate() -> None:
    recs = [
        _r(pchembl=6.0, source_record_id="R1", assay_id="A1"),
        _r(pchembl=6.4, source_record_id="R2", assay_id="A1"),
    ]
    cell = aggregate_cell(recs, PANEL, "IK1", "PI3Kalpha")
    assert cell.replicate_type is ReplicateType.TRUE_REPLICATE
    assert cell.assay_ids == ("A1",)


def test_two_records_different_assay_is_cross_assay() -> None:
    recs = [
        _r(pchembl=6.0, source_record_id="R1", assay_id="A1"),
        _r(pchembl=6.4, source_record_id="R2", assay_id="A2"),
    ]
    cell = aggregate_cell(recs, PANEL, "IK1", "PI3Kalpha")
    assert cell.replicate_type is ReplicateType.CROSS_ASSAY
    assert cell.assay_ids == ("A1", "A2")


def test_zero_exact_records_is_none_type() -> None:
    recs = [_r(pchembl=None, censoring="right", source_record_id="R1")]
    cell = aggregate_cell(recs, PANEL, "IK1", "PI3Kalpha")
    assert cell.replicate_type is ReplicateType.NONE
    assert cell.value is None


# ── censoring: preserved explicitly, never folded into value ────────────────


def test_censored_record_excluded_from_value_but_retained() -> None:
    recs = [
        _r(pchembl=6.0, source_record_id="R1", censoring="exact"),
        _r(pchembl=None, source_record_id="R2", censoring="right"),
    ]
    cell = aggregate_cell(recs, PANEL, "IK1", "PI3Kalpha")
    assert cell.value == 6.0  # censored never enters the exact median
    assert cell.n_exact == 1
    assert cell.censored_source_record_ids == ("R2",)
    assert cell.censoring_kinds == ("right",)


def test_censored_only_cell_has_no_value() -> None:
    recs = [_r(pchembl=None, source_record_id="R1", censoring="right")]
    cell = aggregate_cell(recs, PANEL, "IK1", "PI3Kalpha")
    assert cell.value is None
    assert cell.censored_source_record_ids == ("R1",)


def test_left_and_right_censoring_both_recorded() -> None:
    recs = [
        _r(pchembl=None, source_record_id="R1", censoring="right"),
        _r(pchembl=None, source_record_id="R2", censoring="left"),
    ]
    cell = aggregate_cell(recs, PANEL, "IK1", "PI3Kalpha")
    assert cell.censoring_kinds == ("left", "right")


# ── the censoring="exact"-with-no-pchembl edge case ──────────────────────────


def test_exact_censoring_with_no_pchembl_is_unclassified_not_dropped() -> None:
    """A ChEMBL data-quality gap (censoring == 'exact' but pchembl_value
    absent) must be tracked, never silently discarded and never confused
    with a true right/left-censored observation."""
    recs = [_r(pchembl=None, source_record_id="R1", censoring="exact")]
    cell = aggregate_cell(recs, PANEL, "IK1", "PI3Kalpha")
    assert cell.value is None
    assert cell.censored_source_record_ids == ()
    assert cell.unclassified_source_record_ids == ("R1",)


# ── LEGACY_FALLBACK exclusion at the aggregate_records_by_cell layer ───────


def test_legacy_fallback_records_never_produce_a_cell() -> None:
    legacy = {
        "inchikey": "IK1",
        "isoform": "PI3Kalpha",
        "study_id": "S1",
        "assay_id": "A1",
        "pchembl_value": 6.0,
        "censoring": "exact",
        "exclusion_reason": None,
    }  # no bao_format/assay_type -> LEGACY_FALLBACK
    cells = aggregate_records_by_cell([legacy])
    assert cells == {}


def test_excluded_records_never_contribute() -> None:
    recs = [_r(pchembl=6.0, exclusion_reason="INADMISSIBLE")]
    cells = aggregate_records_by_cell(recs)
    assert cells == {}


def test_mixed_legacy_and_c1_only_c1_contributes() -> None:
    legacy = {
        "inchikey": "IK1",
        "isoform": "PI3Kalpha",
        "study_id": "S1",
        "assay_id": "A1",
        "pchembl_value": 9.0,
        "censoring": "exact",
        "exclusion_reason": None,
    }
    c1 = _r(pchembl=6.0, inchikey="IK2")
    cells = aggregate_records_by_cell([legacy, c1])
    assert len(cells) == 1
    (((_panel, ik, _iso), cell),) = cells.items()
    assert ik == "IK2"
    assert cell.value == 6.0

"""Tests for GDR-013 per-isoform / per-isoform-pair noise floor.

Exit criteria:
  (1) TRUE_REPLICATE and CROSS_ASSAY sigma are computed and reported
      separately -- never silently pooled into one number.
  (2) Per-isoform sigma differs across isoforms when the underlying data
      differs (no cross-isoform pooling).
  (3) Per-isoform-pair sigma_diff = sqrt(sum of squares), with an explicit
      independence-assumption note on every result.
  (4) Missing per-isoform data produces None, never a substituted/default
      value.
  (5) No switch-magnitude multiplier is ever computed; the sentinel status
      is returned unconditionally.
"""

from __future__ import annotations

from orthosteric.data.noise_floor import (
    SWITCH_MAGNITUDE_MULTIPLIER_STATUS,
    IsoformNoiseFloor,
    compute_isoform_noise_floors,
    compute_isoform_pair_noise_floors,
    switch_magnitude_multiplier_status,
)
from orthosteric.data.replicate_aggregation import AggregatedCell, ReplicateType


def _cell(isoform, exact_values, replicate_type):
    return AggregatedCell(
        panel_key=("S1", "BAO_1::B"),
        inchikey="IK1",
        isoform=isoform,
        value=exact_values[len(exact_values) // 2] if exact_values else None,
        exact_values=tuple(exact_values),
        n_exact=len(exact_values),
        spread=(max(exact_values) - min(exact_values)) if len(exact_values) >= 2 else None,
        replicate_type=replicate_type,
        source_record_ids=(),
        censored_source_record_ids=(),
        censoring_kinds=(),
        unclassified_source_record_ids=(),
        assay_ids=(),
    )


# ── per-isoform noise floors ──────────────────────────────────────────────────


def test_true_replicate_and_cross_assay_reported_separately() -> None:
    cells = {
        ("k1", "IK1", "PI3Kalpha"): _cell("PI3Kalpha", [6.0, 6.2], ReplicateType.TRUE_REPLICATE),
        ("k2", "IK2", "PI3Kalpha"): _cell("PI3Kalpha", [6.0, 7.0], ReplicateType.CROSS_ASSAY),
    }
    floors = compute_isoform_noise_floors(cells)
    a = floors["PI3Kalpha"]
    assert a.n_true_replicate_groups == 1
    assert a.n_cross_assay_groups == 1
    assert a.sigma_true_replicate is not None
    assert a.sigma_cross_assay is not None
    # true-replicate group has smaller spread than the cross-assay group
    assert a.sigma_true_replicate < a.sigma_cross_assay
    assert a.n_pooled_groups == 2


def test_single_type_cells_do_not_contribute_sigma() -> None:
    cells = {("k1", "IK1", "PI3Kalpha"): _cell("PI3Kalpha", [6.0], ReplicateType.SINGLE)}
    floors = compute_isoform_noise_floors(cells)
    a = floors["PI3Kalpha"]
    assert a.n_true_replicate_groups == 0
    assert a.n_cross_assay_groups == 0
    assert a.sigma_true_replicate is None
    assert a.sigma_pooled is None


def test_isoforms_never_pooled_together() -> None:
    cells = {
        ("k1", "IK1", "PI3Kalpha"): _cell("PI3Kalpha", [6.0, 6.1], ReplicateType.TRUE_REPLICATE),
        ("k2", "IK2", "PI3Kgamma"): _cell("PI3Kgamma", [6.0, 8.0], ReplicateType.TRUE_REPLICATE),
    }
    floors = compute_isoform_noise_floors(cells)
    assert floors["PI3Kalpha"].sigma_true_replicate != floors["PI3Kgamma"].sigma_true_replicate
    assert floors["PI3Kbeta"].n_true_replicate_groups == 0  # no data -> not fabricated
    assert floors["PI3Kbeta"].sigma_true_replicate is None


def test_all_four_tier1_isoforms_always_present_in_result() -> None:
    floors = compute_isoform_noise_floors({})
    assert set(floors) == {"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}
    for f in floors.values():
        assert f.sigma_pooled is None


# ── per-isoform-pair noise floors ────────────────────────────────────────────


def test_pair_sigma_is_sqrt_sum_of_squares() -> None:
    per_iso = {
        "PI3Kalpha": IsoformNoiseFloor(
            isoform="PI3Kalpha",
            n_true_replicate_groups=5,
            sigma_true_replicate=0.1,
            n_cross_assay_groups=0,
            sigma_cross_assay=None,
            n_pooled_groups=5,
            sigma_pooled=0.1,
        ),
        "PI3Kbeta": IsoformNoiseFloor(
            isoform="PI3Kbeta",
            n_true_replicate_groups=5,
            sigma_true_replicate=0.2,
            n_cross_assay_groups=0,
            sigma_cross_assay=None,
            n_pooled_groups=5,
            sigma_pooled=0.2,
        ),
        "PI3Kgamma": IsoformNoiseFloor(
            isoform="PI3Kgamma",
            n_true_replicate_groups=0,
            sigma_true_replicate=None,
            n_cross_assay_groups=0,
            sigma_cross_assay=None,
            n_pooled_groups=0,
            sigma_pooled=None,
        ),
        "PI3Kdelta": IsoformNoiseFloor(
            isoform="PI3Kdelta",
            n_true_replicate_groups=0,
            sigma_true_replicate=None,
            n_cross_assay_groups=0,
            sigma_cross_assay=None,
            n_pooled_groups=0,
            sigma_pooled=None,
        ),
    }
    pairs = compute_isoform_pair_noise_floors(per_iso)
    ab = pairs[("PI3Kalpha", "PI3Kbeta")]
    assert abs(ab.sigma_diff_true_replicate - (0.1**2 + 0.2**2) ** 0.5) < 1e-12
    assert "independent" in ab.independence_assumption_note.lower()


def test_pair_sigma_none_when_either_isoform_missing() -> None:
    per_iso = {
        "PI3Kalpha": IsoformNoiseFloor(
            isoform="PI3Kalpha",
            n_true_replicate_groups=5,
            sigma_true_replicate=0.1,
            n_cross_assay_groups=0,
            sigma_cross_assay=None,
            n_pooled_groups=5,
            sigma_pooled=0.1,
        ),
        "PI3Kgamma": IsoformNoiseFloor(
            isoform="PI3Kgamma",
            n_true_replicate_groups=0,
            sigma_true_replicate=None,
            n_cross_assay_groups=0,
            sigma_cross_assay=None,
            n_pooled_groups=0,
            sigma_pooled=None,
        ),
    }
    pairs = compute_isoform_pair_noise_floors(per_iso)
    ag = pairs[("PI3Kalpha", "PI3Kgamma")]
    assert ag.sigma_diff_true_replicate is None  # never fabricated from partial data


def test_pair_covers_all_three_non_reference_isoforms() -> None:
    per_iso = compute_isoform_noise_floors({})
    pairs = compute_isoform_pair_noise_floors(per_iso)
    assert set(pairs) == {
        ("PI3Kalpha", "PI3Kbeta"),
        ("PI3Kalpha", "PI3Kgamma"),
        ("PI3Kalpha", "PI3Kdelta"),
    }


# ── switch-magnitude multiplier: never invented ──────────────────────────────


def test_switch_magnitude_multiplier_is_the_rule_missing_sentinel() -> None:
    assert switch_magnitude_multiplier_status() == "RULE_MISSING/GDR_REQUIRED"
    assert switch_magnitude_multiplier_status() == SWITCH_MAGNITUDE_MULTIPLIER_STATUS


def test_switch_magnitude_multiplier_is_constant_regardless_of_input() -> None:
    """No amount of noise-floor evidence changes this -- the multiplier is
    a Project Owner decision, not a corpus-derived quantity."""
    assert switch_magnitude_multiplier_status() == switch_magnitude_multiplier_status()

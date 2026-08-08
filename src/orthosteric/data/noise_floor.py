"""Per-isoform and per-isoform-pair noise-floor representation.

Objective: GDR-013 (GGR-002b).

Replaces a single pooled global sigma (0.260 pAct units across all 852 C1
replicate cells) with a structure that keeps three things separate, because
the A4 evidence shows pooling them is not defensible:

  1. Per-isoform sigma varies ~3x (PI3Kalpha median 0.140 vs PI3Kgamma
     median 0.431 -- analysis/ggr002_decision_package_audit.py section 5).
     A single global sigma systematically over-penalizes the precise
     isoforms and under-penalizes the noisy ones.
  2. TRUE_REPLICATE cells (single ChEMBL assay_id, a genuine repeat
     measurement) and CROSS_ASSAY cells (multiple assay_ids merged under
     one GDR-011 protocol signature) have materially different sigma
     (single-assay median 0.212 vs multi-assay median 0.343 in the pooled
     C1 population) -- these are different noise sources and are reported
     separately, never silently averaged together.
  3. The quantity a comparative selectivity model actually needs is the
     uncertainty of a DIFFERENCE (pAct_alpha - pAct_X), not of a single
     isoform's measurement. This module combines per-isoform sigma into a
     per-isoform-PAIR sigma via sqrt(sigma_a^2 + sigma_b^2) -- an explicit,
     stated INDEPENDENCE ASSUMPTION, not an empirically measured covariance
     (A4 has no paired-difference replicate structure to measure it
     directly). This assumption is documented on every result, not hidden.

What this module does NOT do
-----------------------------
It does not choose a switch-magnitude multiplier. `k * sigma_diff` is the
quantity a switch-detection rule would need, but the RIGHT k depends on the
statistical power/false-positive tradeoff the project wants, which is a
Project Owner decision this module surfaces (via
`switch_magnitude_multiplier_status()`) rather than makes.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from orthosteric.data.replicate_aggregation import AggregatedCell, ReplicateType

#: GDR-013 noise-floor policy identifier.
POLICY_ID = "gdr013_per_isoform_pair_noise_floor_v1"

#: Explicit, documented sentinel: no switch-magnitude multiplier is chosen
#: by this codebase. Mirrors the existing RULE_MISSING convention
#: (`PolicyManifest.within_group_conflict_threshold`, etc.).
SWITCH_MAGNITUDE_MULTIPLIER_STATUS = "RULE_MISSING/GDR_REQUIRED"

_TIER1_ISOFORMS = ("PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta")


def switch_magnitude_multiplier_status() -> str:
    """Explicit remaining Project Owner decision (GDR-012). Not invented here."""
    return SWITCH_MAGNITUDE_MULTIPLIER_STATUS


@dataclass(frozen=True, slots=True)
class IsoformNoiseFloor:
    """Replicate-derived noise statistics for one isoform, split by
    replicate type (GDR-013). No single value here is "the" noise floor --
    all three are reported.

    Attributes:
    ----------
    isoform:                    e.g. "PI3Kalpha".
    n_true_replicate_groups:    Cells with >=2 exact obs, single assay_id.
    sigma_true_replicate:       Median stdev across those cells, or None.
    n_cross_assay_groups:       Cells with >=2 exact obs, multiple assay_ids.
    sigma_cross_assay:          Median stdev across those cells, or None.
    n_pooled_groups:            n_true_replicate_groups + n_cross_assay_groups.
    sigma_pooled:                Median stdev pooling both -- REFERENCE ONLY,
                                 not the recommended estimator (GDR-013 finds
                                 the two populations are not homogeneous).
    """

    isoform: str
    n_true_replicate_groups: int
    sigma_true_replicate: float | None
    n_cross_assay_groups: int
    sigma_cross_assay: float | None
    n_pooled_groups: int
    sigma_pooled: float | None
    policy: str = field(default=POLICY_ID)


def compute_isoform_noise_floors(
    cells: Mapping[Any, AggregatedCell],
) -> dict[str, IsoformNoiseFloor]:
    """Per-isoform noise floors, split by ReplicateType, from aggregated cells.

    Only cells with `n_exact >= 2` contribute (a cell needs >=2 exact
    observations to have a within-cell stdev at all; SINGLE and NONE cells
    are silently skipped here -- they contribute to compound completeness
    elsewhere, not to noise estimation).
    """
    by_iso_true: dict[str, list[float]] = {iso: [] for iso in _TIER1_ISOFORMS}
    by_iso_cross: dict[str, list[float]] = {iso: [] for iso in _TIER1_ISOFORMS}

    for cell in cells.values():
        if cell.n_exact < 2:
            continue
        sigma = statistics.stdev(cell.exact_values)
        if cell.replicate_type is ReplicateType.TRUE_REPLICATE:
            by_iso_true.setdefault(cell.isoform, []).append(sigma)
        elif cell.replicate_type is ReplicateType.CROSS_ASSAY:
            by_iso_cross.setdefault(cell.isoform, []).append(sigma)

    result: dict[str, IsoformNoiseFloor] = {}
    for iso in _TIER1_ISOFORMS:
        true_sds = by_iso_true.get(iso, [])
        cross_sds = by_iso_cross.get(iso, [])
        pooled = true_sds + cross_sds
        result[iso] = IsoformNoiseFloor(
            isoform=iso,
            n_true_replicate_groups=len(true_sds),
            sigma_true_replicate=statistics.median(true_sds) if true_sds else None,
            n_cross_assay_groups=len(cross_sds),
            sigma_cross_assay=statistics.median(cross_sds) if cross_sds else None,
            n_pooled_groups=len(pooled),
            sigma_pooled=statistics.median(pooled) if pooled else None,
        )
    return result


@dataclass(frozen=True, slots=True)
class IsoformPairNoiseFloor:
    """Combined uncertainty for a pAct_alpha - pAct_X selectivity difference.

    `sigma_diff_* = sqrt(sigma_a_*^2 + sigma_b_*^2)`, computed independently
    per replicate-type basis (true-replicate, cross-assay, pooled-reference).
    None wherever either contributing isoform's sigma is unavailable for
    that basis -- never silently substituted or defaulted.

    `independence_assumption_note` documents that this combination assumes
    the two isoforms' measurement errors are independent; A4 contains no
    paired-difference replicate structure to test that assumption directly.
    """

    isoform_a: str
    isoform_b: str
    sigma_diff_true_replicate: float | None
    sigma_diff_cross_assay: float | None
    sigma_diff_pooled: float | None
    independence_assumption_note: str = (
        "sigma_diff = sqrt(sigma_a^2 + sigma_b^2) assumes independent "
        "measurement error between isoform_a and isoform_b. Not empirically "
        "validated against A4 (no paired-difference replicate structure "
        "exists in the corpus to measure covariance directly). GDR-013."
    )
    policy: str = field(default=POLICY_ID)


def compute_isoform_pair_noise_floors(
    per_isoform: dict[str, IsoformNoiseFloor],
    reference_isoform: str = "PI3Kalpha",
) -> dict[tuple[str, str], IsoformPairNoiseFloor]:
    """Combine per-isoform noise floors into per-pair sigma_diff, for every
    (reference_isoform, X) pair matching the project's S1 selectivity vector
    (pAct_alpha, pAct_alpha-beta, pAct_alpha-gamma, pAct_alpha-delta).
    """

    def combine(a: float | None, b: float | None) -> float | None:
        if a is None or b is None:
            return None
        return math.sqrt(a**2 + b**2)

    ref = per_isoform.get(reference_isoform)
    result: dict[tuple[str, str], IsoformPairNoiseFloor] = {}
    for iso in _TIER1_ISOFORMS:
        if iso == reference_isoform:
            continue
        other = per_isoform.get(iso)
        result[(reference_isoform, iso)] = IsoformPairNoiseFloor(
            isoform_a=reference_isoform,
            isoform_b=iso,
            sigma_diff_true_replicate=combine(
                ref.sigma_true_replicate if ref else None,
                other.sigma_true_replicate if other else None,
            ),
            sigma_diff_cross_assay=combine(
                ref.sigma_cross_assay if ref else None,
                other.sigma_cross_assay if other else None,
            ),
            sigma_diff_pooled=combine(
                ref.sigma_pooled if ref else None,
                other.sigma_pooled if other else None,
            ),
        )
    return result

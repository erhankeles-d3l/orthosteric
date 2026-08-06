"""Exploratory Bemis-Murcko scaffold-pair candidates for isoform-selectivity
sign changes.

Objective: GDR-012 (GGR-002a evidence classification).

Governance status (binding)
-----------------------------
Every pair this module emits carries `evidence_class =
ScaffoldPairEvidenceClass.EXPLORATORY_BEMIS_MURCKO`. This is NOT matched
molecular pair (MMP) evidence and MUST NOT be reported, cited, or consumed
downstream as "MMP evidence" or a "confirmed switch". Two compounds sharing
a Bemis-Murcko scaffold family (SCI0-012) may differ at several positions
simultaneously -- the scaffold family identity guarantees only that their
ring/linker system matches, not that they are related by a single chemical
transformation. A true MMP definition (single-point transformation) is not
implemented anywhere in this repository; `ScaffoldPairEvidenceClass` reserves
`MMP_CONFIRMED` for a future module that would implement one, and no code
path here produces it.

What changed from the prior analysis-layer implementation
-----------------------------------------------------------
`analysis/ggr_reassessment_a4.py`'s original GGR-002a pair generation built
its per-cell value via a plain dict overwrite (`d[key] = value`), which
took whichever record Python iterated last for any (panel, compound,
isoform) cell with >=2 pchembl_value-bearing records -- reproducible given
a fixed input file, but not a principled aggregate, and not invariant to
upstream record reordering (473 of 852 such cells in A4 have >0.3 pAct
spread between candidates). This module uses
`replicate_aggregation.aggregate_records_by_cell()` instead: every cell
value is a deterministic median, with full provenance
(source_record_ids, assay_ids, replicate_type) retained on
`ScaffoldPairCandidate` via its two `AggregatedCell` references.

Censoring (GDR-012, binding)
------------------------------
A compound is eligible for exact-value candidate-pair generation in one
panel only if EVERY required isoform's `AggregatedCell.value` is not None
-- i.e. has at least one EXACT (pchembl_value) observation. A compound with
a censored-only cell for a required isoform is excluded from candidate
generation, but the exclusion is counted and the censored evidence remains
visible on request (via `n_compounds_excluded_censored_required_isoform`
and the underlying `AggregatedCell.censored_source_record_ids`) -- censored
observations are never silently discarded, and never treated as either an
exact value or a missing measurement.

Magnitude (GDR-012, binding)
-------------------------------
This module reports the raw |delta_a - delta_b| magnitude and, for
reference, the ratio of that magnitude to the best-available per-isoform-
pair sigma_diff from `noise_floor.py` -- WITHOUT asserting a pass/fail
threshold. `noise_floor.switch_magnitude_multiplier_status()` remains
RULE_MISSING/GDR_REQUIRED; no multiplier is chosen here.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, cast

from orthosteric.data.noise_floor import (
    IsoformPairNoiseFloor,
    compute_isoform_noise_floors,
    compute_isoform_pair_noise_floors,
)
from orthosteric.data.replicate_aggregation import AggregatedCell, aggregate_records_by_cell

#: GDR-012 evidence-generation policy identifier.
POLICY_ID = "gdr012_exploratory_scaffold_pairs_v1"

_TIER1_ISOFORMS = frozenset({"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"})
_NON_REFERENCE_ISOFORMS = ("PI3Kbeta", "PI3Kgamma", "PI3Kdelta")
_REFERENCE_ISOFORM = "PI3Kalpha"


class ScaffoldPairEvidenceClass(StrEnum):
    """Evidentiary status of a scaffold-pair candidate (GDR-012)."""

    #: Bemis-Murcko scaffold-family identity only. NOT an MMP. The only
    #: value any code path in this module currently produces.
    EXPLORATORY_BEMIS_MURCKO = "exploratory_bemis_murcko"

    #: Reserved for a future single-point-transformation MMP module.
    #: No code here produces this.
    MMP_CONFIRMED = "mmp_confirmed"


@dataclass(frozen=True, slots=True)
class ScaffoldPairCandidate:
    """One exploratory scaffold-pair sign-flip observation.

    `magnitude` is |delta_a - delta_b| in pAct units. `sigma_diff_reference`
    is the best-available per-isoform-pair combined sigma from
    `noise_floor.py` (true-replicate, else cross-assay, else pooled --
    documented fallback, never invented). `magnitude_over_sigma` is their
    ratio, reported for descriptive/sensitivity use only -- it is NOT a
    pass/fail signal; no threshold is applied to it anywhere in this module.
    """

    panel_key: tuple[str, str]
    isoform_x: str  # the non-reference isoform in this alpha-vs-X comparison
    inchikey_a: str
    inchikey_b: str
    delta_a: float  # pAct_alpha - pAct_X for compound a
    delta_b: float  # pAct_alpha - pAct_X for compound b
    sign_flip: bool
    magnitude: float
    sigma_diff_reference: float | None
    sigma_diff_basis: str  # "true_replicate" / "cross_assay" / "pooled" / "unavailable"
    magnitude_over_sigma: float | None
    evidence_class: ScaffoldPairEvidenceClass = field(
        default=ScaffoldPairEvidenceClass.EXPLORATORY_BEMIS_MURCKO
    )
    policy: str = field(default=POLICY_ID)


@dataclass(frozen=True, slots=True)
class ScaffoldPairReport:
    """Summary of exploratory scaffold-pair candidate generation on one corpus."""

    candidates: tuple[ScaffoldPairCandidate, ...]
    n_pairs_examined: int
    n_sign_flip_candidates: int
    n_studies_involved: int
    n_compounds_excluded_censored_required_isoform: int
    isoform_pair_noise_floors: dict[tuple[str, str], IsoformPairNoiseFloor]
    evidence_class_note: str = (
        "Every candidate carries evidence_class=EXPLORATORY_BEMIS_MURCKO. "
        "This is NOT matched molecular pair (MMP) evidence -- see module "
        "docstring. GDR-012."
    )


def _resolve_sigma_reference(
    isoform_x: str,
    pair_floors: dict[tuple[str, str], IsoformPairNoiseFloor],
) -> tuple[float | None, str]:
    floor = pair_floors.get((_REFERENCE_ISOFORM, isoform_x))
    if floor is None:
        return None, "unavailable"
    if floor.sigma_diff_true_replicate is not None:
        return floor.sigma_diff_true_replicate, "true_replicate"
    if floor.sigma_diff_cross_assay is not None:
        return floor.sigma_diff_cross_assay, "cross_assay"
    if floor.sigma_diff_pooled is not None:
        return floor.sigma_diff_pooled, "pooled"
    return None, "unavailable"


def generate_exploratory_scaffold_pairs(
    records: list[dict[str, Any]],
) -> ScaffoldPairReport:
    """Generate exploratory (NOT MMP) scaffold-pair sign-flip candidates.

    Uses `replicate_aggregation.aggregate_records_by_cell()` for
    deterministic, provenance-preserving per-cell values (GDR-013),
    replacing the prior last-write-wins collapse.
    """
    accepted = [r for r in records if not r.get("exclusion_reason")]
    cells = aggregate_records_by_cell(accepted)

    per_isoform = compute_isoform_noise_floors(cells)
    pair_floors = compute_isoform_pair_noise_floors(per_isoform)

    # Index: panel -> compound -> isoform -> AggregatedCell
    panel_cmpd_iso: dict[tuple[str, str], dict[str, dict[str, AggregatedCell]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for (panel, ik, iso), cell in cells.items():
        panel_cmpd_iso[panel][ik][iso] = cell

    # Scaffold family lookup (any accepted record carrying it; deterministic
    # via sorted source_record_id tie-break to avoid order dependence).
    scaffold_of: dict[str, str] = {}
    for r in sorted(accepted, key=lambda r: str(r.get("source_record_id", ""))):
        ik_lookup = r.get("inchikey")
        fam = r.get("scaffold_family_id")
        if ik_lookup and fam and ik_lookup not in scaffold_of:
            scaffold_of[ik_lookup] = str(fam)

    n_excluded_censored = 0
    candidates: list[ScaffoldPairCandidate] = []
    studies_involved: set[str] = set()

    for panel, cmpd_map in panel_cmpd_iso.items():
        complete_iks: list[str] = []
        for ik, iso_map in cmpd_map.items():
            if not _TIER1_ISOFORMS.issubset(iso_map):
                continue  # not measured in all 4 isoforms in this panel at all
            if all(iso_map[iso].value is not None for iso in _TIER1_ISOFORMS):
                complete_iks.append(ik)
            elif any(
                iso_map[iso].value is None
                and (
                    iso_map[iso].censored_source_record_ids
                    or iso_map[iso].unclassified_source_record_ids
                )
                for iso in _TIER1_ISOFORMS
            ):
                # Measured in all 4 isoforms, but >=1 required cell has no
                # exact value -- only censored and/or unclassified
                # (e.g. censoring="exact" with no pchembl_value) evidence.
                # Excluded from exact-value candidate generation, counted,
                # never discarded (GDR-012).
                n_excluded_censored += 1

        by_scaffold: dict[str, list[str]] = defaultdict(list)
        for ik in complete_iks:
            fam = scaffold_of.get(ik)
            if fam:
                by_scaffold[fam].append(ik)

        for members in by_scaffold.values():
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    ik_a, ik_b = sorted((members[i], members[j]))
                    a_cells = cmpd_map[ik_a]
                    b_cells = cmpd_map[ik_b]
                    studies_involved.add(panel[0])
                    a_ref = a_cells[_REFERENCE_ISOFORM].value
                    b_ref = b_cells[_REFERENCE_ISOFORM].value
                    # Guaranteed not None: ik_a/ik_b only reached complete_iks
                    # after all four isoform cells were confirmed value-bearing.
                    a_ref = cast(float, a_ref)
                    b_ref = cast(float, b_ref)
                    for iso_x in _NON_REFERENCE_ISOFORMS:
                        a_x = cast(float, a_cells[iso_x].value)
                        b_x = cast(float, b_cells[iso_x].value)
                        da = a_ref - a_x
                        db = b_ref - b_x
                        flip = (da * db) < 0
                        magnitude = abs(da - db)
                        sigma_ref, basis = _resolve_sigma_reference(iso_x, pair_floors)
                        ratio = (magnitude / sigma_ref) if sigma_ref else None
                        candidates.append(
                            ScaffoldPairCandidate(
                                panel_key=panel,
                                isoform_x=iso_x,
                                inchikey_a=ik_a,
                                inchikey_b=ik_b,
                                delta_a=da,
                                delta_b=db,
                                sign_flip=flip,
                                magnitude=magnitude,
                                sigma_diff_reference=sigma_ref,
                                sigma_diff_basis=basis,
                                magnitude_over_sigma=ratio,
                            )
                        )

    n_flips = sum(1 for c in candidates if c.sign_flip)
    return ScaffoldPairReport(
        candidates=tuple(candidates),
        n_pairs_examined=len({(c.panel_key, c.inchikey_a, c.inchikey_b) for c in candidates}),
        n_sign_flip_candidates=n_flips,
        n_studies_involved=len(studies_involved),
        n_compounds_excluded_censored_required_isoform=n_excluded_censored,
        isoform_pair_noise_floors=pair_floors,
    )

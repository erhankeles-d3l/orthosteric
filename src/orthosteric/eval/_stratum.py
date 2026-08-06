"""Within-study evaluation stratum loader.

Authority: SCI1-017b. Constitution §2.3(1).

Constitution §2.3(1) mandate:
  "Selectivity computed ONLY from within-study, within-assay panels.
  Cross-study ratios excluded from primary targets."

The within-study stratum consists of records where all four isoforms
(alpha, beta, gamma, delta) were measured in the same study under the
same assay conditions. Only this stratum is admissible for the primary
selectivity evaluation (S2, S4).

Cross-study records may be used as auxiliary low-reliability evidence
but NEVER as the primary target, and NEVER pooled with within-study.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

__all__ = [
    "STRATUM_ALGORITHM_VERSION",
    "ActivityRecord",
    "StratumResult",
    "load_within_study_stratum",
]

STRATUM_ALGORITHM_VERSION = "stratum_v1_sci1017b"

_TIER1_ISOFORMS = frozenset({"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"})


@dataclass(frozen=True, slots=True)
class ActivityRecord:
    """One activity measurement for one compound at one isoform.

    Attributes:
        compound_id:     Compound identifier (e.g. scaffold family + serial).
        isoform:         Target isoform.
        pac_value:       pActivity (pIC50 or equivalent); None if right-censored.
        is_censored:     True if value is an upper bound (> threshold only).
        study_id:        Study/paper identifier (Constitution §2.3: within-study).
        assay_atp_mm:    Assay ATP concentration in mM. Required per §2.3.
        smiles:          SMILES for the compound. None if not available.
    """

    compound_id: str
    isoform: str
    pac_value: float | None
    is_censored: bool
    study_id: str
    assay_atp_mm: float | None
    smiles: str | None


@dataclass(frozen=True, slots=True)
class StratumResult:
    """Within-study and cross-study stratum classification.

    Attributes:
        within_study_ids:  Compound IDs where all 4 isoforms measured in
                           the same study. These are the primary targets.
        cross_study_ids:   Compound IDs present in multiple studies with
                           inconsistent assay conditions. Auxiliary only.
        excluded_ids:      Compound IDs with ATP concentration missing
                           (§2.3 compliance: excluded from all strata).
        n_within_study:    Count of within-study compounds.
        n_cross_study:     Count of cross-study compounds.
        n_excluded:        Count of excluded compounds.
        algorithm_version: Pinned version.
    """

    within_study_ids: tuple[str, ...]
    cross_study_ids: tuple[str, ...]
    excluded_ids: tuple[str, ...]
    n_within_study: int
    n_cross_study: int
    n_excluded: int
    algorithm_version: str


def load_within_study_stratum(
    records: list[ActivityRecord],
) -> StratumResult:
    """Classify records into within-study and cross-study strata.

    A compound qualifies for the within-study stratum if:
    1. All four Tier 1 isoforms are measured for it.
    2. All four measurements come from the same study_id.
    3. All four measurements have assay_atp_mm recorded (§2.3 compliance).

    Returns `StratumResult` with clearly separated strata.
    """
    compound_isoforms: dict[str, dict[str, list[ActivityRecord]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for r in records:
        compound_isoforms[r.compound_id][r.isoform].append(r)

    within_study: list[str] = []
    cross_study: list[str] = []
    excluded: list[str] = []

    for cid, iso_map in sorted(compound_isoforms.items()):
        # Must have all four isoforms
        if not _TIER1_ISOFORMS.issubset(iso_map.keys()):
            cross_study.append(cid)
            continue
        # Collect one record per isoform (prefer non-censored, then first)
        recs = []
        for iso in sorted(_TIER1_ISOFORMS):
            candidates = iso_map[iso]
            non_censored = [r for r in candidates if not r.is_censored]
            recs.append((non_censored or candidates)[0])
        # Check ATP concentration present for all
        if any(r.assay_atp_mm is None for r in recs):
            excluded.append(cid)
            continue
        # Check all from same study
        study_ids = {r.study_id for r in recs}
        if len(study_ids) == 1:
            within_study.append(cid)
        else:
            cross_study.append(cid)

    return StratumResult(
        within_study_ids=tuple(sorted(within_study)),
        cross_study_ids=tuple(sorted(cross_study)),
        excluded_ids=tuple(sorted(excluded)),
        n_within_study=len(within_study),
        n_cross_study=len(cross_study),
        n_excluded=len(excluded),
        algorithm_version=STRATUM_ALGORITHM_VERSION,
    )

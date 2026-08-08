"""Within-study / within-assay stratum extraction.

Objective: SCI0-013.
Specification: SCI0-001-refinement §SCI0-012/SCI0-013.
  "Per compound, per isoform: individual measurements, explicit missingness,
   multiple measurements retained, publication links. No imputation.
   Plus within-study/within-assay stratum extraction (strata.py) —
   the evaluation ground truth under §2.3(1) as amended."
Exit criterion:
  "missing ≠ inactive anywhere in the schema; the within-study stratum is
   separable and its size reported."

What is the within-study stratum? (GDR-011, accepted, Option D)
-------------------------------------------------------------------
A within-study stratum is `orthosteric.data.comparability.panel_key(record)`
— `(study_id, protocol)`, where `protocol` is the `(bao_format, assay_type)`
signature.  This REPLACES the previous `(study_id, assay_id)` definition:
GDR-011 found every ChEMBL assay covers exactly one isoform, so
`(study_id, assay_id)` can never produce a four-isoform stratum — the
defect was structural, not a matter of corpus size.

Records lacking `bao_format`/`assay_type` fall back to `(study_id,
assay_id)`, tagged LEGACY_FALLBACK by `comparability.resolve_panel_key()`.
Each `WithinStudyStratum` records its `panel_tier`; any GGR-002a/GGR-002b
analysis MUST filter to `PanelKeyTier.C1_PRIMARY` strata before drawing a
scientific conclusion — a LEGACY_FALLBACK stratum is not comparability
evidence.

Explicit missingness
--------------------
A compound that was not measured in a particular isoform/study combination is
MISSING, not inactive.  Missing is never imputed to a low-activity value.
The StratumEntry.activity_value is None when the compound was not tested in
that cell; the StratumEntry.is_missing flag distinguishes missing from
genuinely zero activity.

No imputation
-------------
No value is estimated, interpolated, or filled.  The presence of None in a
stratum cell means exactly: this compound was not measured here.

Stratum size
------------
The stratum size is the number of compounds with complete measurements across
all required isoforms within the same panel.  Incomplete strata (missing at
least one isoform) are reported separately.  Stratum size is reported per
(study_id, protocol, isoforms_covered).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from orthosteric.data.comparability import PanelKeyTier, resolve_panel_key


@dataclass
class StratumEntry:
    """One cell in the within-study evaluation matrix.

    Attributes:
    ----------
    inchikey:       Compound identity (SCI0-008c).
    isoform:        PI3K isoform measured.
    study_id:       Study/publication identifier.
    assay_id:       Assay identifier within the study.
    activity_value: Log activity (e.g. pIC50), or None if NOT MEASURED.
    censoring:      'exact' / 'right_censored' / 'left_censored' / None.
    is_missing:     True when the compound was not tested in this cell.
                    missing ≠ inactive: do not interpret None as inactive.
    source_records: Source record IDs contributing to this cell.
    publication_id: DOI, PMID, or other publication link.
    """

    inchikey: str
    isoform: str
    study_id: str
    assay_id: str
    activity_value: float | None  # None means NOT MEASURED
    censoring: str | None
    is_missing: bool
    source_records: list[str]
    publication_id: str | None = None


@dataclass
class WithinStudyStratum:
    """All measurements for a single (study_id, assay_id) panel.

    A stratum is the set of records that can be used together to compute
    selectivity ratios without cross-study confounding.

    Attributes:
    ----------
    study_id:           Study identifier.
    assay_id:           Assay identifier.
    isoforms_covered:   Set of isoforms with at least one measurement.
    entries:            All StratumEntry records for this stratum.
    complete_compounds: InChIKeys with measurements in ALL four Tier 1 isoforms.
    incomplete_compounds: InChIKeys missing at least one isoform.
    stratum_size:       Number of complete compounds (the evaluation unit).
    panel_tier:         PanelKeyTier.C1_PRIMARY or LEGACY_FALLBACK
                        (GDR-011).  Only C1_PRIMARY strata are scientific
                        comparability evidence.
    """

    study_id: str
    assay_id: str
    isoforms_covered: set[str]
    entries: list[StratumEntry]
    complete_compounds: list[str]
    incomplete_compounds: list[str]
    stratum_size: int
    panel_tier: PanelKeyTier = PanelKeyTier.LEGACY_FALLBACK

    def is_usable_for_selectivity(self, required_isoforms: set[str]) -> bool:
        """True when the stratum contains at least one complete compound.

        Completeness-only signal (SCI0-013 exit criterion); does NOT gate
        on `panel_tier`.  Any GGR-002a/GGR-002b/SCI-2-eligibility analysis
        MUST additionally check `panel_tier is PanelKeyTier.C1_PRIMARY`
        before treating this stratum as scientific comparability evidence
        (GDR-011) — a complete LEGACY_FALLBACK stratum is still complete,
        it is simply not built on the approved comparability unit.
        """
        return self.stratum_size > 0 and required_isoforms.issubset(self.isoforms_covered)


_TIER1_ISOFORMS: frozenset[str] = frozenset(
    {
        "PI3Kalpha",
        "PI3Kbeta",
        "PI3Kgamma",
        "PI3Kdelta",
    }
)


@dataclass
class StratumReport:
    """Summary report of all within-study strata in a corpus.

    Used to satisfy the SCI0-013 exit criterion: stratum size reported.
    """

    total_strata: int
    usable_strata: int  # complete for all four Tier 1 isoforms
    total_complete_compounds: int
    total_incomplete_compounds: int
    strata: list[WithinStudyStratum]
    strata_by_key: dict[tuple[str, str], WithinStudyStratum] = field(default_factory=dict)

    def stratum_sizes(self) -> dict[tuple[str, str], int]:
        """Map of panel key → stratum size."""
        return {(s.study_id, s.assay_id): s.stratum_size for s in self.strata}

    def c1_primary_strata(self) -> list[WithinStudyStratum]:
        """Strata built on the GDR-011 Option D comparability unit — the
        only strata usable as scientific evidence for GGR-002a, GGR-002b,
        or SCI-2 eligibility.  Excludes every LEGACY_FALLBACK stratum.
        """
        return [s for s in self.strata if s.panel_tier is PanelKeyTier.C1_PRIMARY]


def extract_strata(
    records: list[dict[str, Any]],
    required_isoforms: frozenset[str] = _TIER1_ISOFORMS,
) -> StratumReport:
    """Extract within-study strata from a list of serialized evidence records.

    Parameters
    ----------
    records:
        List of evidence record dicts with at minimum: inchikey, isoform,
        study_id, assay_id, activity_value, censoring, exclusion_reason,
        source_record_id, publication_id (optional).  bao_format and
        assay_type (GDR-011) should be present for real ChEMBL data; their
        absence degrades the stratum to LEGACY_FALLBACK (see module
        docstring and `orthosteric.data.comparability`).
    required_isoforms:
        The set of isoforms that a compound must be measured in for the
        stratum entry to be complete.  Defaults to all four Tier 1 isoforms.

    Returns:
    -------
    StratumReport with all strata and the stratum size report.  Each
    stratum carries a `panel_tier`; use `StratumReport.c1_primary_strata()`
    before drawing any scientific conclusion.

    Rules
    -----
    * Only accepted records (exclusion_reason is None) contribute.
    * Missing ≠ inactive: compounds not tested in a cell have is_missing=True.
    * No imputation: activity_value is None for missing cells.
    * All measurements within a (inchikey, isoform, panel) cell are
      retained — multiple measurements are not collapsed here.
    * Grouping uses `comparability.resolve_panel_key()` (GDR-011, Option D),
      not a raw `(study_id, assay_id)` pair.
    """
    # Group by panel key (GDR-011, accepted, Option D).
    by_stratum: dict[tuple[str, str], list[dict[str, Any]]] = {}
    stratum_tier: dict[tuple[str, str], PanelKeyTier] = {}
    for rec in records:
        if rec.get("exclusion_reason") is not None:
            continue  # excluded records do not contribute
        resolved = resolve_panel_key(rec)
        key = resolved.key
        by_stratum.setdefault(key, []).append(rec)
        # Conservative: any LEGACY_FALLBACK contributor downgrades the whole
        # stratum.  Ambiguity must never upgrade a stratum to C1_PRIMARY.
        prior = stratum_tier.get(key, PanelKeyTier.C1_PRIMARY)
        if resolved.tier is PanelKeyTier.LEGACY_FALLBACK or prior is PanelKeyTier.LEGACY_FALLBACK:
            stratum_tier[key] = PanelKeyTier.LEGACY_FALLBACK
        else:
            stratum_tier[key] = PanelKeyTier.C1_PRIMARY

    strata: list[WithinStudyStratum] = []

    for (study_id, assay_id), group_records in by_stratum.items():
        # Index by (inchikey, isoform) → list of records
        cell_map: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for rec in group_records:
            ik = str(rec.get("inchikey", ""))
            iso = str(rec.get("isoform", ""))
            if ik and iso:
                cell_map.setdefault((ik, iso), []).append(rec)

        # All inchikeys and isoforms in this stratum
        all_inchikeys = {k for k, _ in cell_map}
        covered_isoforms = {iso for _, iso in cell_map}

        # Build StratumEntry for every (inchikey × isoform) pair present
        entries: list[StratumEntry] = []
        for (ik, iso), cell_recs in cell_map.items():
            # Use first record's value (multiple retained in source_records)
            val = cell_recs[0].get("activity_value")
            if isinstance(val, str):
                try:
                    val = float(val)
                except ValueError:
                    val = None
            censoring = cell_recs[0].get("censoring")
            pub = cell_recs[0].get("publication_id")
            entries.append(
                StratumEntry(
                    inchikey=ik,
                    isoform=iso,
                    study_id=study_id,
                    assay_id=assay_id,
                    activity_value=val,
                    censoring=censoring,
                    is_missing=False,
                    source_records=[str(r.get("source_record_id", "")) for r in cell_recs],
                    publication_id=pub,
                )
            )

        # Completeness: a compound is complete if it has all required isoforms
        complete = sorted(
            [
                ik
                for ik in all_inchikeys
                if required_isoforms.issubset({iso for (_ik, iso) in cell_map if _ik == ik})
            ]
        )
        incomplete = sorted(all_inchikeys - set(complete))

        strata.append(
            WithinStudyStratum(
                study_id=study_id,
                assay_id=assay_id,
                isoforms_covered=covered_isoforms,
                entries=entries,
                complete_compounds=complete,
                incomplete_compounds=incomplete,
                stratum_size=len(complete),
                panel_tier=stratum_tier[(study_id, assay_id)],
            )
        )

    usable = sum(1 for s in strata if s.is_usable_for_selectivity(set(required_isoforms)))
    total_complete = sum(s.stratum_size for s in strata)
    total_incomplete = sum(len(s.incomplete_compounds) for s in strata)

    strata_by_key = {(s.study_id, s.assay_id): s for s in strata}

    return StratumReport(
        total_strata=len(strata),
        usable_strata=usable,
        total_complete_compounds=total_complete,
        total_incomplete_compounds=total_incomplete,
        strata=strata,
        strata_by_key=strata_by_key,
    )

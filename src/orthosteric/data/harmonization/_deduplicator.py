"""Duplicate and conflict resolution for the biological evidence layer.

Objective: SCI0-009.
Specification: docs/PROJECT_SPECIFICATION.md §1 ("Duplicate and conflict
  resolution", `data/harmonization`, `SCI0-009`); docs/IMPLEMENTATION_BACKLOG.md
  `SCI0-009` ("different stereoisomers never merged; policy recorded").
Prerequisite: SCI0-008b (canonical structure / InChIKey identity, via
  `HarmonizedCompound`), SCI0-008c (cross-source identifier harmonization).

Governance status of the aggregation question (read before editing)
-----------------------------------------------------------------------------
AUDITOR-3 (duplicate-resolution policy) is RESOLVED by
`docs/governance/decision-records/GDR-001-duplicate-resolution-policy.md`
(2026-08-05), under Project Owner authorization to resolve scientific
methodology questions via comprehensive literature review where a single,
well-supported choice exists.

Resolution, narrowly scoped: within a fully-specified evidence-identity group
— same compound, isoform, construct, organism, measurement type, measurement
class, assay, and source — two or more non-identical exact values are
combined by taking their median. This is a decision about combining literal
replicate measurements sharing source and assay; it does NOT authorize
combining values across different studies, sources, or accessions (that
remains governed by Constitution §2.3(1) as amended and `SCI0-013`'s
within-study stratum architecture, both unaffected). It does NOT resolve
Cheng-Prusoff normalization or the ATP Km source question (AUDITOR-5 remains
`INSUFFICIENT_EVIDENCE`, unchanged — no Cheng-Prusoff conversion is applied
anywhere in this module).

See GDR-001 for full rationale, cited literature, alternatives considered,
confidence level, and explicit assumptions. A prior draft of this module
computed no aggregate and marked every multi-value group `RULE_MISSING`;
that was correct given the state of governance at the time it was written
and is superseded in effect (not retroactively rewritten) by GDR-001.

What SCI0-009 does
-----------------------------------------------------------------
1. Group records by deterministic identity (compound x isoform x construct
   x organism x measurement type x measurement class x assay x source) built
   entirely from fields the schema already carries (`HarmonizedCompound.
   internal_id`, `AssayMetadata.isoform/construct/organism/assay_id`,
   `ActivityRecord.measurement_type/class`, `ProvenanceRecord.source.
   source_type/accession`). `construct` and `organism` were added to the key
   by GDR-001 as a prerequisite correctness fix: the original key omitted
   them, creating a latent risk of blending a wild-type and a mutant
   construct (or two species) that happened to share a nominal `assay_id`.
2. Collapse **literal** duplicates: two records in the same identity group
   that report the identical value under identical censoring are the same
   observation (e.g. the same record ingested twice by two connectors).
3. Detect a **zero-tolerance logical contradiction**: an exact value (or the
   resolved median of several) that is inconsistent with a censoring bound
   *by the definition of that bound*. This requires no noise-floor
   threshold — it follows from what right/left-censoring means.
4. Where a group contains >=2 non-identical exact values, per GDR-001,
   resolve them to their median and record `GroupConflictStatus.
   RESOLVED_REPLICATE_MEDIAN`. All contributing records are retained
   unchanged in `EvidenceGroup.records`; only a resolved point estimate is
   added, never removed.

Stereoisomers
-------------
Different stereoisomers have distinct InChIKeys (SCI0-008b guarantee) and
therefore distinct `HarmonizedCompound.internal_id` values. Because grouping
here starts from `internal_id`, stereoisomers land in different
`CompoundEvidenceMatrix` instances automatically; no code here merges them.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from orthosteric.data.models import ActivityRecord, CensoringKind
from orthosteric.data.provenance.models import ProvenanceRecord

__all__ = [
    "CompoundEvidenceMatrix",
    "Deduplicator",
    "EvidenceGroup",
    "EvidenceRecord",
    "GroupConflictStatus",
]


class GroupConflictStatus(StrEnum):
    """Resolution status of one evidence-identity group.

    `RESOLVED_REPLICATE_MEDIAN` is produced under GDR-001 when >=2 distinct
    exact values are combined by median. `RULE_MISSING` is retained in the
    enum for forward compatibility with a future case this module does not
    currently produce; it is not emitted by any code path today.
    """

    OK = "ok"  # exactly one distinct observation (after literal-duplicate collapse)
    CENSORED_ONLY = "censored_only"  # only censored records, none contradictory
    MIXED_CENSORED = "mixed_censored"  # exact + censored, not contradictory
    RESOLVED_REPLICATE_MEDIAN = "resolved_replicate_median"  # GDR-001
    LOGICAL_CONTRADICTION = "logical_contradiction"  # censoring bound violated by definition
    RULE_MISSING = "rule_missing"  # reserved; not currently produced (see GDR-001)
    INSUFFICIENT = "insufficient"  # zero usable records


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """One (`ActivityRecord`, `ProvenanceRecord`) pair joined to compound identity.

    This is the unit `Deduplicator` operates on. `compound_id` must come from
    a `HarmonizedCompound.internal_id` (SCI0-008b/c) — never a raw source ID —
    so that stereoisomers and cross-source aliases are already resolved before
    this module runs.
    """

    compound_id: str
    activity: ActivityRecord
    provenance: ProvenanceRecord

    @property
    def isoform(self) -> str | None:
        return self.provenance.assay.isoform

    @property
    def construct(self) -> str | None:
        return self.provenance.assay.construct

    @property
    def organism(self) -> str | None:
        return self.provenance.assay.organism

    @property
    def assay_id(self) -> str | None:
        return self.provenance.assay.assay_id

    @property
    def source_key(self) -> tuple[str, str]:
        """Deterministic study/source proxy: (source_type, accession).

        No `study_id` field exists in the provenance schema; `accession` is
        the source's own record-native identifier (`SourceMetadata.accession`),
        which is the closest available deterministic proxy without inventing
        a new concept.
        """
        return (str(self.provenance.source.source_type), self.provenance.source.accession)

    @property
    def identity_key(
        self,
    ) -> tuple[str, str | None, str | None, str | None, str, str, str | None, tuple[str, str]]:
        """The deterministic evidence-identity key for grouping.

        (compound_id, isoform, construct, organism, measurement_type,
        measurement_class, assay_id, (source_type, accession)) — every
        component is read directly off the schema; none is inferred or
        thresholded. `construct` and `organism` added by GDR-001.
        """
        return (
            self.compound_id,
            self.isoform,
            self.construct,
            self.organism,
            str(self.activity.measurement_type),
            str(self.activity.measurement_class),
            self.assay_id,
            self.source_key,
        )

    @property
    def _dedup_fingerprint(self) -> tuple[Any, ...]:
        """Fields that must match exactly for two records to be literal duplicates."""
        return (
            self.identity_key,
            self.activity.value,
            self.activity.censoring,
        )


@dataclass(frozen=True, slots=True)
class EvidenceGroup:
    """All evidence for a single deterministic identity key.

    Attributes:
        compound_id:      HarmonizedCompound.internal_id (InChIKey).
        isoform:           PI3K isoform as reported in AssayMetadata.
        construct:         Construct as reported (GDR-001 identity component).
        organism:          Source organism as reported (GDR-001 identity component).
        measurement_type:  IC50 / Ki / Kd / EC50.
        measurement_class: biochemical / cellular.
        assay_id:          Source-native assay identifier.
        source_key:        (source_type, accession) study/source proxy.
        records:           All contributing `EvidenceRecord`s (duplicates collapsed).
        n_literal_duplicates_collapsed: Count of bit-identical records folded together.
        conflict_status:   See `GroupConflictStatus`.
        conflict_note:     Human-readable explanation.
        policy:            Identifier for the deterministic policy applied here.
        resolved_value:    Median of exact values when conflict_status ==
                            RESOLVED_REPLICATE_MEDIAN; None otherwise (GDR-001).
        aggregation_method: "median" when resolved_value is set; "" otherwise.
        governance_note:   Present (non-empty) whenever a scientific decision is
                            still required to go further.
    """

    compound_id: str
    isoform: str | None
    construct: str | None
    organism: str | None
    measurement_type: str
    measurement_class: str
    assay_id: str | None
    source_key: tuple[str, str]
    records: list[EvidenceRecord]
    n_literal_duplicates_collapsed: int
    conflict_status: GroupConflictStatus
    conflict_note: str
    policy: str
    resolved_value: Decimal | None = None
    aggregation_method: str = ""
    governance_note: str = ""

    @property
    def identity_key(
        self,
    ) -> tuple[str, str | None, str | None, str | None, str, str, str | None, tuple[str, str]]:
        return (
            self.compound_id,
            self.isoform,
            self.construct,
            self.organism,
            self.measurement_type,
            self.measurement_class,
            self.assay_id,
            self.source_key,
        )


@dataclass
class CompoundEvidenceMatrix:
    """Structured evidence matrix for one compound across all isoforms and sources.

    Structure:
        compound identity (InChIKey / internal_id)
          -> isoform
                -> (construct, organism, measurement type, measurement class,
                    assay, source) cell

    Nothing is collapsed across isoforms, constructs, organisms, or sources;
    this only organizes evidence that already exists so downstream Phase C
    consumers can compare the same compound across isoforms without
    accidentally pooling them.

    Attributes:
        compound_id:             Compound identity (InChIKey / internal_id).
        groups:                  All evidence groups for this compound.
        isoforms_with_evidence:  Set of isoforms with >=1 group.
        stereoisomers_distinct:  Always True — guaranteed by grouping on
                                  `HarmonizedCompound.internal_id`, which is
                                  stereochemistry-preserving (SCI0-008b).
    """

    compound_id: str
    groups: list[EvidenceGroup]
    isoforms_with_evidence: set[str]
    stereoisomers_distinct: bool = True

    def groups_for_isoform(self, isoform: str) -> list[EvidenceGroup]:
        return [g for g in self.groups if g.isoform == isoform]

    def has_multi_isoform_evidence(self) -> bool:
        """True if this compound has evidence for >=2 isoforms.

        Required for comparative selectivity in Phase C — computing it here
        (without comparing values) does not require a scientific decision.
        """
        return len(self.isoforms_with_evidence) >= 2

    def unresolved_groups(self) -> list[EvidenceGroup]:
        """Groups that still require a governance decision before further use.

        As of GDR-001 this is limited to `LOGICAL_CONTRADICTION` and
        `RULE_MISSING` (the latter currently unreachable); replicate-median
        resolution is no longer an unresolved state.
        """
        return [g for g in self.groups if g.conflict_status in (GroupConflictStatus.RULE_MISSING,)]


class Deduplicator:
    """Resolves duplicates and surfaces conflicts within evidence groups.

    Does NOT collapse across isoforms, constructs, organisms, assays, or
    sources. Same InChIKey + different isoform, construct, organism, assay,
    or source is always preserved as distinct evidence. Within a fully
    identical group, non-identical exact values are combined by median
    (GDR-001).
    """

    POLICY_ID = "sci0009_identity_grouping_median_replicates_v2_gdr001"

    GOVERNANCE_NOTE_RESOLVED = (
        "RESOLVED/GDR-001 (2026-08-05): median of >=2 distinct exact values "
        "in this fully-specified identity group (compound x isoform x "
        "construct x organism x measurement_type x measurement_class x "
        "assay x source). See docs/governance/decision-records/"
        "GDR-001-duplicate-resolution-policy.md for rationale, cited "
        "literature, and explicit scope limits. This does not resolve "
        "AUDITOR-5 (ATP Km / Cheng-Prusoff) or any cross-study combination, "
        "both unaffected."
    )

    def deduplicate(self, records: list[EvidenceRecord]) -> list[CompoundEvidenceMatrix]:
        """Group records by deterministic identity and build evidence matrices.

        Parameters
        ----------
        records:
            Flat list of `EvidenceRecord`, each already carrying a
            `HarmonizedCompound.internal_id` as `compound_id`.

        Returns:
        -------
        One `CompoundEvidenceMatrix` per distinct `compound_id`; each matrix
        holds one `EvidenceGroup` per deterministic identity cell.
        """
        groups_map: dict[tuple[Any, ...], list[EvidenceRecord]] = {}
        for rec in records:
            groups_map.setdefault(rec.identity_key, []).append(rec)

        evidence_groups = [
            self._resolve_group(key, group_records) for key, group_records in groups_map.items()
        ]

        by_compound: dict[str, list[EvidenceGroup]] = {}
        for eg in evidence_groups:
            by_compound.setdefault(eg.compound_id, []).append(eg)

        return [
            CompoundEvidenceMatrix(
                compound_id=compound_id,
                groups=egs,
                isoforms_with_evidence={eg.isoform for eg in egs if eg.isoform is not None},
                stereoisomers_distinct=True,
            )
            for compound_id, egs in by_compound.items()
        ]

    def _resolve_group(
        self,
        key: tuple[Any, ...],
        records: list[EvidenceRecord],
    ) -> EvidenceGroup:
        (
            compound_id,
            isoform,
            construct,
            organism,
            measurement_type,
            measurement_class,
            assay_id,
            source_key,
        ) = key

        if not records:
            return EvidenceGroup(
                compound_id=compound_id,
                isoform=isoform,
                construct=construct,
                organism=organism,
                measurement_type=measurement_type,
                measurement_class=measurement_class,
                assay_id=assay_id,
                source_key=source_key,
                records=[],
                n_literal_duplicates_collapsed=0,
                conflict_status=GroupConflictStatus.INSUFFICIENT,
                conflict_note="No records in group",
                policy=self.POLICY_ID,
            )

        deduped_records, n_collapsed = _collapse_literal_duplicates(records)

        exact = [r for r in deduped_records if r.activity.censoring == CensoringKind.EXACT]
        censored = [r for r in deduped_records if r.activity.censoring != CensoringKind.EXACT]

        (
            conflict_status,
            conflict_note,
            governance_note,
            resolved_value,
            aggregation_method,
        ) = self._assess(exact, censored)

        return EvidenceGroup(
            compound_id=compound_id,
            isoform=isoform,
            construct=construct,
            organism=organism,
            measurement_type=measurement_type,
            measurement_class=measurement_class,
            assay_id=assay_id,
            source_key=source_key,
            records=deduped_records,
            n_literal_duplicates_collapsed=n_collapsed,
            conflict_status=conflict_status,
            conflict_note=conflict_note,
            policy=self.POLICY_ID,
            resolved_value=resolved_value,
            aggregation_method=aggregation_method,
            governance_note=governance_note,
        )

    def _assess(
        self,
        exact: list[EvidenceRecord],
        censored: list[EvidenceRecord],
    ) -> tuple[GroupConflictStatus, str, str, Decimal | None, str]:
        if not exact and not censored:
            return GroupConflictStatus.INSUFFICIENT, "No records", "", None, ""
        if not exact:
            return GroupConflictStatus.CENSORED_ONLY, "All records are censored", "", None, ""
        if censored:
            return self._assess_mixed(exact, censored)
        return self._assess_exact_only(exact)

    def _assess_mixed(
        self,
        exact: list[EvidenceRecord],
        censored: list[EvidenceRecord],
    ) -> tuple[GroupConflictStatus, str, str, Decimal | None, str]:
        distinct_values = {r.activity.value for r in exact}
        point_value = (
            _median_decimal(distinct_values)
            if len(distinct_values) > 1
            else next(iter(distinct_values))
        )

        contradiction = _censored_contradicts_value(point_value, censored)
        if contradiction:
            return (
                GroupConflictStatus.LOGICAL_CONTRADICTION,
                f"Censored record contradicts exact value(s) by definition: {contradiction}",
                "",
                None,
                "",
            )
        if len(distinct_values) > 1:
            return (
                GroupConflictStatus.RESOLVED_REPLICATE_MEDIAN,
                f"{len(distinct_values)} distinct exact values combined by median "
                "(GDR-001); non-contradictory censored records also present and retained",
                self.GOVERNANCE_NOTE_RESOLVED,
                point_value,
                "median",
            )
        return (
            GroupConflictStatus.MIXED_CENSORED,
            "Exact and censored records present, not contradictory",
            "",
            None,
            "",
        )

    def _assess_exact_only(
        self,
        exact: list[EvidenceRecord],
    ) -> tuple[GroupConflictStatus, str, str, Decimal | None, str]:
        distinct_exact_values = {r.activity.value for r in exact}
        if len(distinct_exact_values) > 1:
            median_value = _median_decimal(distinct_exact_values)
            return (
                GroupConflictStatus.RESOLVED_REPLICATE_MEDIAN,
                f"{len(distinct_exact_values)} distinct exact values in one identity "
                "group combined by median (GDR-001)",
                self.GOVERNANCE_NOTE_RESOLVED,
                median_value,
                "median",
            )
        return GroupConflictStatus.OK, "Single distinct observation", "", None, ""


# ── helpers ───────────────────────────────────────────────────────────────────


def _median_decimal(values: set[Decimal]) -> Decimal:
    """Median of a set of Decimal values (order-statistic; exact arithmetic)."""
    return statistics.median(sorted(values))


def _collapse_literal_duplicates(
    records: list[EvidenceRecord],
) -> tuple[list[EvidenceRecord], int]:
    """Fold bit-identical records into one; return (kept_records, n_collapsed).

    Two records are literal duplicates only if they agree on the full
    fingerprint (identity key + value + censoring). Collapsing loses no
    information because nothing distinguishes the collapsed copies.
    """
    seen: dict[tuple[Any, ...], EvidenceRecord] = {}
    n_collapsed = 0
    for rec in records:
        fp = rec._dedup_fingerprint
        if fp in seen:
            n_collapsed += 1
            continue
        seen[fp] = rec
    return list(seen.values()), n_collapsed


def _censored_contradicts_value(
    value: Decimal,
    censored: list[EvidenceRecord],
) -> str | None:
    """Zero-tolerance check: does a censoring bound rule out this value?

    No noise-floor threshold is used — a contradiction is asserted only when
    the value is strictly on the wrong side of the bound implied by the
    censoring's own definition:
      * right-censored (no activity detected below the tested concentration,
        i.e. pActivity is bounded ABOVE by the reported threshold) is
        contradicted by a value strictly greater than that bound;
      * left-censored (activity saturates at the lowest tested concentration,
        i.e. pActivity is bounded BELOW) is contradicted by a value strictly
        less than that bound.

    `value` may be a single exact reading or a GDR-001 resolved median; the
    check is identical either way.
    """
    for cen_rec in censored:
        bound = cen_rec.activity.value
        if cen_rec.activity.censoring == CensoringKind.RIGHT_CENSORED and value > bound:
            return f"value {value} > right-censored bound {bound}"
        if cen_rec.activity.censoring == CensoringKind.LEFT_CENSORED and value < bound:
            return f"value {value} < left-censored bound {bound}"
    return None

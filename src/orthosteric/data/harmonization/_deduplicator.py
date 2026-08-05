"""Duplicate and conflict resolution for the biological evidence layer.

Objective: SCI0-009.
Specification: docs/PROJECT_SPECIFICATION.md §1 ("Duplicate and conflict
  resolution", `data/harmonization`, `SCI0-009`); docs/IMPLEMENTATION_BACKLOG.md
  `SCI0-009` ("different stereoisomers never merged; policy recorded").
Prerequisite: SCI0-008b (canonical structure / InChIKey identity, via
  `HarmonizedCompound`), SCI0-008c (cross-source identifier harmonization).

Governance status of the aggregation question (must be read before editing)
-----------------------------------------------------------------------------
`docs/reports/audit_reports/ADR-0003_AUDITOR_3_DUPLICATE_EVIDENCE.md` proposes
log-median aggregation, stratified by isoform x construct x species, as a
*candidate* policy. Its own status line reads:

    "Status: Evidence prepared | CANDIDATE POLICY — requires Auditor approval"
    "Independent Auditor decision still required: YES."

`ADR-0003` itself remains `Proposed`, not `Accepted` (`ADR-0003_INDEPENDENT_
AUDITOR_BRIEF.md`: "No default or candidate policy text exists anywhere ...
the referenced content is the open item itself, not a resolution").
`docs/IMPLEMENTATION_BACKLOG.md` additionally seals the numeric duplicate-
resolution policy under `SCI0-028`, sequenced *before* `SCI0-015` — it has not
run.

Consequently this module MUST NOT compute a single aggregated value across
non-identical measurements (no log-median, no mean, no confidence-weighted
combination). Doing so would be inventing a scientific resolution rule
(CLAUDE.md §1) under a rule that is explicitly `RULE_MISSING /
GOVERNANCE_DECISION_REQUIRED` pending Independent Scientific Auditor sign-off
on AUDITOR-3 (and, transitively, the AUDITOR-5 Cheng-Prusoff ordering
constraint, and the SCI0-016 noise floor for judging "conflicting" vs.
"replicate"). A prior draft of this module implemented log-median aggregation
under a mislabeled "(RESOLVED)" comment; that draft is superseded by this one
and must not be resurrected without an actual Auditor sign-off changing
ADR-0003's Status line.

What SCI0-009 is authorized to do without a scientific decision
-----------------------------------------------------------------
1. Group records by deterministic identity (compound x isoform x measurement
   type x measurement class x assay x source) built entirely from fields the
   schema already carries (`HarmonizedCompound.internal_id`,
   `AssayMetadata.isoform/assay_id`, `ActivityRecord.measurement_type/class`,
   `ProvenanceRecord.source.source_type/accession`). This is identity
   bookkeeping, not a scientific judgement, and follows directly from
   Constitution requirements that isoform, assay class, and study/source
   provenance are never pooled.
2. Collapse **literal** duplicates: two records in the same identity group
   that report the identical value under identical censoring are the same
   observation (e.g. the same record ingested twice by two connectors).
   Collapsing these loses no information because the collapsed records are
   bit-identical on every measured field.
3. Detect a **zero-tolerance logical contradiction**: an exact value that is
   inconsistent with a censoring bound *by the definition of that bound*
   (e.g. an exact pActivity above what a right-censored "no activity below
   this bound" record permits). This requires no noise-floor threshold — it
   follows from what right/left-censoring means.
4. Where a group contains >=2 non-identical exact values, that is a genuine
   scientific aggregation question that AUDITOR-3 has not resolved. This
   module fails closed: it emits the group with status
   `GroupConflictStatus.RULE_MISSING`, keeps every record, computes no
   aggregate, and cites the exact ADR/backlog items blocking resolution.

Stereoisomers
-------------
Different stereoisomers have distinct InChIKeys (SCI0-008b guarantee) and
therefore distinct `HarmonizedCompound.internal_id` values. Because grouping
here starts from `internal_id`, stereoisomers land in different
`CompoundEvidenceMatrix` instances automatically; no code here merges them.
"""

from __future__ import annotations

from dataclasses import dataclass
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

    Only `OK` (a single observation, or exact duplicates of it) and
    `CENSORED_ONLY` describe groups this module can fully characterize
    without a scientific decision. `RULE_MISSING` and `LOGICAL_CONTRADICTION`
    are surfaced, not silently resolved.
    """

    OK = "ok"  # exactly one distinct observation (after literal-duplicate collapse)
    CENSORED_ONLY = "censored_only"  # only censored records, none contradictory
    MIXED_CENSORED = "mixed_censored"  # exact + censored, not contradictory
    LOGICAL_CONTRADICTION = "logical_contradiction"  # censoring bound violated by definition
    RULE_MISSING = "rule_missing"  # >=2 distinct exact values; AUDITOR-3 unresolved
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
    ) -> tuple[str, str | None, str, str, str | None, tuple[str, str]]:
        """The deterministic evidence-identity key for grouping.

        (compound_id, isoform, measurement_type, measurement_class, assay_id,
        (source_type, accession)) — every component is read directly off the
        schema; none is inferred or thresholded.
        """
        return (
            self.compound_id,
            self.isoform,
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
        measurement_type:  IC50 / Ki / Kd / EC50.
        measurement_class: biochemical / cellular.
        assay_id:          Source-native assay identifier.
        source_key:        (source_type, accession) study/source proxy.
        records:           All contributing `EvidenceRecord`s (duplicates collapsed).
        n_literal_duplicates_collapsed: Count of bit-identical records folded together.
        conflict_status:   See `GroupConflictStatus`.
        conflict_note:     Human-readable explanation.
        policy:            Identifier for the deterministic policy applied here.
        governance_note:   Present (non-empty) whenever a scientific decision is
                            still required to go further (RULE_MISSING cases).
    """

    compound_id: str
    isoform: str | None
    measurement_type: str
    measurement_class: str
    assay_id: str | None
    source_key: tuple[str, str]
    records: list[EvidenceRecord]
    n_literal_duplicates_collapsed: int
    conflict_status: GroupConflictStatus
    conflict_note: str
    policy: str
    governance_note: str = ""

    @property
    def identity_key(
        self,
    ) -> tuple[str, str | None, str, str, str | None, tuple[str, str]]:
        return (
            self.compound_id,
            self.isoform,
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
                -> (measurement type, measurement class, assay, source) cell

    Nothing is collapsed across isoforms or sources; this only organizes
    evidence that already exists so downstream Phase C consumers can compare
    the same compound across isoforms without accidentally pooling them.

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
        """Groups that require a governance decision before further use."""
        return [g for g in self.groups if g.conflict_status == GroupConflictStatus.RULE_MISSING]


class Deduplicator:
    """Resolves *literal* duplicates and surfaces conflicts within evidence groups.

    Does NOT collapse across isoforms, assays, or sources. Does NOT aggregate
    non-identical measurements into a single value (AUDITOR-3 unresolved —
    see module docstring). Same InChIKey + different isoform, assay, or
    source is always preserved as distinct evidence.
    """

    POLICY_ID = "sci0009_identity_grouping_no_aggregation_v1"

    GOVERNANCE_NOTE_RULE_MISSING = (
        "RULE_MISSING/GOVERNANCE_DECISION_REQUIRED: group contains >=2 distinct "
        "exact values. Aggregation policy is AUDITOR-3 (ADR-0003), status "
        "CANDIDATE POLICY — not yet Auditor-approved; the noise-vs-conflict "
        "floor is SCI0-016; the sealed numeric policy is SCI0-028. No "
        "aggregate value may be computed until these resolve. All "
        "contributing records are retained; this operation (aggregation) "
        "alone is stopped."
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
        compound_id, isoform, measurement_type, measurement_class, assay_id, source_key = key

        if not records:
            return EvidenceGroup(
                compound_id=compound_id,
                isoform=isoform,
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

        conflict_status, conflict_note, governance_note = self._assess(exact, censored)

        return EvidenceGroup(
            compound_id=compound_id,
            isoform=isoform,
            measurement_type=measurement_type,
            measurement_class=measurement_class,
            assay_id=assay_id,
            source_key=source_key,
            records=deduped_records,
            n_literal_duplicates_collapsed=n_collapsed,
            conflict_status=conflict_status,
            conflict_note=conflict_note,
            policy=self.POLICY_ID,
            governance_note=governance_note,
        )

    def _assess(
        self,
        exact: list[EvidenceRecord],
        censored: list[EvidenceRecord],
    ) -> tuple[GroupConflictStatus, str, str]:
        if not exact and not censored:
            return GroupConflictStatus.INSUFFICIENT, "No records", ""
        if not exact:
            return GroupConflictStatus.CENSORED_ONLY, "All records are censored", ""
        if censored:
            return self._assess_mixed(exact, censored)
        return self._assess_exact_only(exact)

    def _assess_mixed(
        self,
        exact: list[EvidenceRecord],
        censored: list[EvidenceRecord],
    ) -> tuple[GroupConflictStatus, str, str]:
        contradiction = _censored_contradicts_exact(exact, censored)
        if contradiction:
            return (
                GroupConflictStatus.LOGICAL_CONTRADICTION,
                f"Censored record contradicts exact value by definition: {contradiction}",
                "",
            )
        if len({r.activity.value for r in exact}) > 1:
            return (
                GroupConflictStatus.RULE_MISSING,
                "Multiple distinct exact values coexist with non-contradictory "
                "censored records; aggregation policy unresolved.",
                self.GOVERNANCE_NOTE_RULE_MISSING,
            )
        return (
            GroupConflictStatus.MIXED_CENSORED,
            "Exact and censored records present, not contradictory",
            "",
        )

    def _assess_exact_only(
        self,
        exact: list[EvidenceRecord],
    ) -> tuple[GroupConflictStatus, str, str]:
        distinct_exact_values = {r.activity.value for r in exact}
        if len(distinct_exact_values) > 1:
            return (
                GroupConflictStatus.RULE_MISSING,
                f"{len(distinct_exact_values)} distinct exact values in one identity "
                "group; aggregation policy unresolved.",
                self.GOVERNANCE_NOTE_RULE_MISSING,
            )
        return GroupConflictStatus.OK, "Single distinct observation", ""


# ── helpers ───────────────────────────────────────────────────────────────────


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


def _censored_contradicts_exact(
    exact: list[EvidenceRecord],
    censored: list[EvidenceRecord],
) -> str | None:
    """Zero-tolerance check: does a censoring bound rule out an exact value?

    No noise-floor threshold is used — a contradiction is asserted only when
    the exact value is strictly on the wrong side of the bound implied by the
    censoring's own definition:
      * right-censored (no activity detected below the tested concentration,
        i.e. pActivity is bounded ABOVE by the reported threshold) is
        contradicted by an exact pActivity strictly greater than that bound;
      * left-censored (activity saturates at the lowest tested concentration,
        i.e. pActivity is bounded BELOW) is contradicted by an exact
        pActivity strictly less than that bound.
    """
    for exact_rec in exact:
        exact_value = exact_rec.activity.value
        for cen_rec in censored:
            bound = cen_rec.activity.value
            if cen_rec.activity.censoring == CensoringKind.RIGHT_CENSORED and exact_value > bound:
                return f"exact value {exact_value} > right-censored bound {bound}"
            if cen_rec.activity.censoring == CensoringKind.LEFT_CENSORED and exact_value < bound:
                return f"exact value {exact_value} < left-censored bound {bound}"
    return None

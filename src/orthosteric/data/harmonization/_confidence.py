"""Curation-confidence assignment for the biological evidence layer.

Objective: SCI0-010.
Specification: docs/specifications/SCI0-001-refinement-data-acquisition.md
  §"SCI0-010 — Confidence scoring":

    "Interpretable, additive and inspectable score over: assay quality
     (including BAO format and interference susceptibility), publication
     quality, duplicate agreement, measurement consistency, metadata
     completeness, and literature extraction tier where applicable.
     Deterministic; its version enters the snapshot hash, since changing it
     changes the corpus."
    "No learned confidence model at SCI-0 ... Exit: score decomposition is
     inspectable per record; rerun reproduces identical scores."

Prerequisite: SCI0-003/004 (`ActivityRecord`/`ProvenanceRecord`), SCI0-006/006b
(source adapters, literature span verification), SCI0-008b (chemical
standardization), SCI0-008c (identifier harmonization), SCI0-009 (duplicate
and conflict resolution — `EvidenceGroup`).

What "additive" means here, precisely
--------------------------------------
No document anywhere in this repository specifies *relative weights* between
the named components (e.g. how much "publication quality" should count
against "metadata completeness"). Inventing such weights would be exactly
the kind of scientific-parameter fabrication CLAUDE.md §1 forbids, and is
the same failure mode as ADR-0003 AUDITOR-3's unresolved aggregation policy
(see `_deduplicator.py`). This module therefore computes each component as
an independent, deterministic value in ``[0.0, 1.0]`` (or ``None`` where the
component does not apply to a given record) and combines them by **equal-
weight summation** — the only combination that requires no comparative
judgement between components. The resulting `additive_score` /
`max_possible_score` pair is a transparent count of "how many quality
signals fired," not a calibrated probability, and is not intended as a
sole admissibility criterion. Per governance:

    "Prefer explicit confidence components and an inspectable final
     confidence state/score so downstream operations can determine
     admissibility through their own governed rules."

Downstream code that needs an admissibility rule must inspect
`CurationConfidence.components` (or `context`) directly and apply its own
governed threshold — this module defines no such threshold, and using its
score as a hidden mechanism to resolve SCI0-009 conflicts is out of scope
(SCI0-009's `RULE_MISSING` groups are surfaced here via `context`, never
silently resolved).

Two named components cannot be scored at all today, and are exposed as
explicit governance gaps rather than invented:

* **assay_quality** (BAO format + interference susceptibility) requires
  fields that do not exist yet on `AssayMetadata` — the assay-ontology
  mapping is part of SCI0-008 and has not run. Exposed as
  ``applicable=False`` with a `RULE_MISSING` governance note.
* **literature_extraction_tier** is an ordinal category
  (`ExtractionTier`, "ordered by descending reliability") with no
  authorized ordinal-to-numeric mapping. Exposed as a categorical fact
  (excluded from the additive sum), not converted into a number.

Everything this module can score is scored; everything it cannot is named
and explained, never silently dropped or guessed (CLAUDE.md §1, §2).

No exclusion, no learned model
-------------------------------
This module never discards, filters, or reorders records: it only attaches
an inspectable `CurationConfidence` alongside the evidence it describes.
It contains no statistical fitting, no parameters learned from the corpus,
and no dependency on corpus contents beyond the single record (and,
optionally, its SCI0-009 `EvidenceGroup`) being scored — satisfying SI3 and
the specification's "no learned confidence model" requirement.
"""

from __future__ import annotations

from dataclasses import dataclass

from orthosteric.data.harmonization._chem_standardizer import StandardizedStructure
from orthosteric.data.harmonization._deduplicator import (
    EvidenceGroup,
    EvidenceRecord,
    GroupConflictStatus,
)
from orthosteric.data.provenance.enums import ExtractionTier

__all__ = [
    "POLICY_VERSION",
    "ConfidenceComponent",
    "ConfidenceScorer",
    "CurationConfidence",
    "EvidenceContext",
]

POLICY_VERSION = "sci0010_equal_weight_additive_v1"
"""Confidence-policy version. Per spec this must enter the snapshot hash
(SCI0-011) since changing this module's rules changes the corpus."""


@dataclass(frozen=True, slots=True)
class ConfidenceComponent:
    """One independently inspectable contribution to curation confidence.

    Attributes:
        name:            Stable identifier, matches the specification's
                          named components (or a documented sub-split of one).
        applicable:       False when this record/group has no basis for the
                          component (e.g. no publication, no literature span,
                          no duplicate group supplied). Never coerced to 0.
        value:            ``[0.0, 1.0]`` when applicable and numerically
                          composable; ``None`` when not applicable, or when
                          the value exists only as a category (see
                          `governance_note`).
        basis:            Human-readable, deterministic derivation — the
                          "why" a reviewer can check by hand.
        governance_note:  Non-empty only when a governed rule is genuinely
                          absent (`RULE_MISSING/GOVERNANCE_DECISION_REQUIRED`)
                          rather than merely inapplicable to this record.
    """

    name: str
    applicable: bool
    value: float | None
    basis: str
    governance_note: str = ""


@dataclass(frozen=True, slots=True)
class EvidenceContext:
    """Pass-through evidence characteristics, preserved but never scored.

    These are exposed for inspection because erasing them would hide
    exactly the distinctions the project depends on (isoform identity,
    censoring state, conflict status, and so on) — but assigning them a
    confidence weight would require a scientific judgement this module is
    not authorized to make.
    """

    compound_id: str
    isoform: str | None
    source_type: str
    source_accession: str
    data_tier: str
    censoring: str
    measurement_type: str
    measurement_class: str
    assay_id: str | None
    conflict_status: str | None  # SCI0-009 GroupConflictStatus, if a group was supplied
    conflict_governance_note: str  # non-empty when the group is RULE_MISSING
    chemical_standardization_status: str | None = None  # SCI0-008b, if supplied
    stereochemistry_preserved: bool | None = None  # SCI0-008b, if supplied
    structural_admissibility: str | None = None  # SCI0-007, if supplied (free text)


@dataclass(frozen=True, slots=True)
class CurationConfidence:
    """SCI0-010 output for one evidence record: score decomposition + context.

    `additive_score` / `max_possible_score` are an equal-weight sum over
    applicable numeric components (see module docstring for why no other
    weighting is used). They are informative, not an admissibility gate.
    """

    activity_id: str
    context: EvidenceContext
    components: tuple[ConfidenceComponent, ...]
    additive_score: float
    max_possible_score: float
    policy_version: str = POLICY_VERSION

    def component(self, name: str) -> ConfidenceComponent | None:
        return next((c for c in self.components if c.name == name), None)

    def unavailable_components(self) -> tuple[str, ...]:
        """Names of components that could not be assessed for this record."""
        return tuple(c.name for c in self.components if not c.applicable)

    def governance_gaps(self) -> tuple[str, ...]:
        """Component names carrying a RULE_MISSING/GOVERNANCE_DECISION_REQUIRED note."""
        return tuple(c.name for c in self.components if c.governance_note)


class ConfidenceScorer:
    """Computes SCI0-010 curation confidence: deterministic, additive, inspectable.

    Every method here is a pure function of its inputs — no corpus-level
    statistics, no fitted parameters, nothing resembling a learned model.
    """

    POLICY_VERSION = POLICY_VERSION

    # Fixed, alphabetically-irrelevant checklist of nullable AssayMetadata
    # fields whose *presence* is mechanically countable. Equal-weight
    # completeness count — no claim that these fields matter equally to
    # scientific validity, only that none is more countable than another.
    _ASSAY_METADATA_FIELDS: tuple[str, ...] = (
        "assay_id",
        "assay_description",
        "organism",
        "isoform",
        "construct",
        "atp_concentration",
    )

    def score(
        self,
        record: EvidenceRecord,
        group: EvidenceGroup | None = None,
        *,
        standardized_structure: StandardizedStructure | None = None,
        structural_admissibility: str | None = None,
    ) -> CurationConfidence:
        """Score one evidence record.

        Parameters
        ----------
        record:
            The evidence record to score (`ActivityRecord` + `ProvenanceRecord`
            joined to compound identity, per SCI0-009's `EvidenceRecord`).
        group:
            The SCI0-009 `EvidenceGroup` this record belongs to, if available.
            Enables `duplicate_agreement` and `measurement_consistency`;
            without it those components are `applicable=False`.
        standardized_structure:
            SCI0-008b output for this compound, if available. Exposed in
            `context`, never scored (stereochemistry/standardization
            correctness is a structural-identity guarantee, not a curation-
            confidence input).
        structural_admissibility:
            Free-text structural-evidence admissibility note (SCI0-007,
            e.g. "PDB" / "AlphaFold fallback" / an `INADMISSIBLE_*` status),
            if available. Exposed in `context`, never scored.
        """
        components = (
            self._metadata_completeness(record),
            self._bibliographic_identification(record),
            self._span_verification(record),
            self._extraction_tier(record),
            self._assay_quality(),
            self._duplicate_agreement(group),
            self._measurement_consistency(group),
        )
        numeric_values = [c.value for c in components if c.applicable and c.value is not None]

        return CurationConfidence(
            activity_id=str(record.activity.activity_id),
            context=self._build_context(
                record, group, standardized_structure, structural_admissibility
            ),
            components=components,
            additive_score=sum(numeric_values),
            max_possible_score=float(len(numeric_values)),
        )

    # ── components ───────────────────────────────────────────────────────

    def _metadata_completeness(self, record: EvidenceRecord) -> ConfidenceComponent:
        assay = record.provenance.assay
        populated = sum(1 for f in self._ASSAY_METADATA_FIELDS if getattr(assay, f) is not None)
        total = len(self._ASSAY_METADATA_FIELDS)
        return ConfidenceComponent(
            name="metadata_completeness",
            applicable=True,
            value=populated / total,
            basis=f"{populated}/{total} assay metadata fields populated: "
            f"{', '.join(f for f in self._ASSAY_METADATA_FIELDS if getattr(assay, f) is not None)}",
        )

    def _bibliographic_identification(self, record: EvidenceRecord) -> ConfidenceComponent:
        pub = record.provenance.publication
        if pub is None:
            return ConfidenceComponent(
                name="bibliographic_identification",
                applicable=False,
                value=None,
                basis="No PublicationMetadata attached to this record",
            )
        has_id = pub.doi is not None or pub.pmid is not None
        return ConfidenceComponent(
            name="bibliographic_identification",
            applicable=True,
            value=1.0 if has_id else 0.0,
            basis=f"doi={pub.doi!r}, pmid={pub.pmid!r}",
        )

    def _span_verification(self, record: EvidenceRecord) -> ConfidenceComponent:
        anchor = record.provenance.extraction.span_anchor
        if anchor is None:
            return ConfidenceComponent(
                name="span_verification",
                applicable=False,
                value=None,
                basis="No literature span anchor (non-literature source, or SCI0-006b not run)",
            )
        return ConfidenceComponent(
            name="span_verification",
            applicable=True,
            value=1.0 if anchor.verified else 0.0,
            basis=f"span_anchor.verified={anchor.verified} "
            f"(locator_type={anchor.locator_type.value}, locator_id={anchor.locator_id!r})",
        )

    def _extraction_tier(self, record: EvidenceRecord) -> ConfidenceComponent:
        tier: ExtractionTier | None = record.provenance.extraction.extraction_tier
        if tier is None:
            return ConfidenceComponent(
                name="literature_extraction_tier",
                applicable=False,
                value=None,
                basis="Not applicable (non-literature source)",
            )
        return ConfidenceComponent(
            name="literature_extraction_tier",
            applicable=True,
            value=None,
            basis=f"extraction_tier={tier.value} (ordinal: SUPPLEMENTARY_TABLE > "
            "MANUSCRIPT_TABLE > ASSAY_SECTION > FREE_TEXT, descending reliability)",
            governance_note=(
                "RULE_MISSING/GOVERNANCE_DECISION_REQUIRED: no authorized "
                "ordinal-to-numeric mapping exists for extraction tier; the "
                "category is exposed for downstream use, not converted to a score."
            ),
        )

    def _assay_quality(self) -> ConfidenceComponent:
        return ConfidenceComponent(
            name="assay_quality",
            applicable=False,
            value=None,
            basis=(
                "BAO assay-format and interference-susceptibility fields are "
                "not present on AssayMetadata: the SCI0-008 assay-ontology "
                "normalization this component depends on has not run."
            ),
            governance_note=(
                "RULE_MISSING/GOVERNANCE_DECISION_REQUIRED: prerequisite "
                "SCI0-008 assay-ontology mapping is not implemented."
            ),
        )

    def _duplicate_agreement(self, group: EvidenceGroup | None) -> ConfidenceComponent:
        if group is None:
            return ConfidenceComponent(
                name="duplicate_agreement",
                applicable=False,
                value=None,
                basis="No SCI0-009 evidence group supplied",
            )
        total_observations = len(group.records) + group.n_literal_duplicates_collapsed
        if total_observations <= 1:
            return ConfidenceComponent(
                name="duplicate_agreement",
                applicable=False,
                value=None,
                basis="Single observation in group; no replication to assess agreement",
            )
        # RESOLVED_REPLICATE_MEDIAN (GDR-001) still reflects >=2 distinct
        # exact values in the group -- the aggregation policy is now resolved,
        # but the underlying disagreement signal is unchanged and must still
        # be surfaced here, not hidden by the fact that a median now exists.
        disagrees = group.conflict_status in (
            GroupConflictStatus.RULE_MISSING,
            GroupConflictStatus.RESOLVED_REPLICATE_MEDIAN,
            GroupConflictStatus.LOGICAL_CONTRADICTION,
        )
        return ConfidenceComponent(
            name="duplicate_agreement",
            applicable=True,
            value=0.0 if disagrees else 1.0,
            basis=f"{total_observations} observations in identity group; "
            f"conflict_status={group.conflict_status.value}",
        )

    def _measurement_consistency(self, group: EvidenceGroup | None) -> ConfidenceComponent:
        if group is None:
            return ConfidenceComponent(
                name="measurement_consistency",
                applicable=False,
                value=None,
                basis="No SCI0-009 evidence group supplied",
            )
        contradiction = group.conflict_status == GroupConflictStatus.LOGICAL_CONTRADICTION
        return ConfidenceComponent(
            name="measurement_consistency",
            applicable=True,
            value=0.0 if contradiction else 1.0,
            basis=f"conflict_status={group.conflict_status.value}",
        )

    # ── context (unscored, preserved) ───────────────────────────────────

    def _build_context(
        self,
        record: EvidenceRecord,
        group: EvidenceGroup | None,
        standardized_structure: StandardizedStructure | None,
        structural_admissibility: str | None,
    ) -> EvidenceContext:
        return EvidenceContext(
            compound_id=record.compound_id,
            isoform=record.isoform,
            source_type=str(record.provenance.source.source_type),
            source_accession=record.provenance.source.accession,
            data_tier=str(record.provenance.source.tier),
            censoring=str(record.activity.censoring),
            measurement_type=str(record.activity.measurement_type),
            measurement_class=str(record.activity.measurement_class),
            assay_id=record.assay_id,
            conflict_status=group.conflict_status.value if group is not None else None,
            conflict_governance_note=group.governance_note if group is not None else "",
            chemical_standardization_status=(
                standardized_structure.status.value if standardized_structure is not None else None
            ),
            stereochemistry_preserved=(
                standardized_structure.stereochemistry_preserved
                if standardized_structure is not None
                else None
            ),
            structural_admissibility=structural_admissibility,
        )

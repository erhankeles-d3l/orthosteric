"""Quality dimension evaluators and the interpretation vocabulary.

Authority: `ADR-0009` (architecture); `GDR-003` (which rules each evaluator
may use, and why none is an invented threshold).

Every evaluator's `evaluate()` takes only a `CorpusProfile` — never a record
list, never a raw snapshot — matching `ADR-0009` §2's design contract
("`CorpusProfile` must remain descriptive only... `quality/` never accesses
raw records directly").

`DimensionStatus` is closed and its members are defined precisely in
`GDR-003` §3. A new status value, or a new dimension using `WARNING` /
`GOVERNED_THRESHOLD_*`, requires a Governance Decision Record stating which
of the two permitted rule kinds justifies it (structural/definitional fact,
or an already-governed magnitude cited by reference) — see `GDR-003` §2 for
the standard every existing evaluator below is held to.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from orthosteric.data.snapshots import CorpusProfile

__all__ = [
    "GOVERNED_SCAFFOLD_FAMILY_FLOOR",
    "ConfidenceEvaluator",
    "ConnectivityEvaluator",
    "CoverageEvaluator",
    "DimensionAssessment",
    "DimensionStatus",
    "MissingnessEvaluator",
    "PublicationConcentrationEvaluator",
    "QualityDimensionEvaluator",
    "ScaffoldDiversityEvaluator",
    "StructuralCoverageEvaluator",
]

GOVERNED_SCAFFOLD_FAMILY_FLOOR = 8
"""R1's unchanged fourth disjunct ('< 8 scaffold families'), fixed at the
Constitution's original authorship (v4.6) — not invented here (GDR-003 §2,
"Scaffold diversity"). Cited by reference, never re-derived."""


class DimensionStatus(StrEnum):
    """Closed interpretation vocabulary.

    See `GDR-003` §3 for the binding definition of each value and which
    rule kind may produce it.
    """

    STRUCTURALLY_DEGENERATE = "structurally_degenerate"
    GOVERNED_THRESHOLD_MET = "governed_threshold_met"
    GOVERNED_THRESHOLD_NOT_MET = "governed_threshold_not_met"
    INSUFFICIENT_DATA = "insufficient_data"
    WARNING = "warning"
    NON_DEGENERATE_UNQUANTIFIED = "non_degenerate_unquantified"
    NOT_YET_AVAILABLE = "not_yet_available"


@dataclass(frozen=True, slots=True)
class DimensionAssessment:
    """One dimension's interpretation of a `CorpusProfile`.

    Attributes:
        dimension: Stable dimension name, e.g. ``"connectivity"``.
        status: See `DimensionStatus`.
        rationale: Human-readable explanation, always naming which rule
            (structural fact or governed magnitude) produced the status.
            Never empty ("no information may be hidden").
        supporting_metrics: The raw values the rationale refers to, so a
            reader can verify the rule without re-deriving it from the
            profile.
        provenance: Which `CorpusProfile` field(s) this evaluator read.
    """

    dimension: str
    status: DimensionStatus
    rationale: str
    supporting_metrics: Mapping[str, Any]
    provenance: str

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "provenance": self.provenance,
            "rationale": self.rationale,
            "status": self.status.value,
            "supporting_metrics": dict(sorted(self.supporting_metrics.items())),
        }


class QualityDimensionEvaluator(ABC):
    """Interface every quality dimension implements.

    Adding a dimension (structural diversity, MD-state diversity,
    pocket-state diversity, mutation coverage, assay diversity, experimental
    modality diversity — all named as future extensions in `ADR-0009`) means
    adding a class and registering an instance with `CorpusQualityAssessor`;
    no existing evaluator changes (`ADR-0009` §3, reusing the `ADR-0008`
    `Policy` extensibility pattern).
    """

    @property
    @abstractmethod
    def dimension_name(self) -> str:
        """Stable identifier, recorded in `DimensionAssessment.dimension`."""

    @abstractmethod
    def evaluate(self, profile: CorpusProfile) -> DimensionAssessment:
        """Interpret `profile`.

        Must not raise on well-formed input, must not read anything other
        than `profile`.
        """


class ConnectivityEvaluator(QualityDimensionEvaluator):
    """Graph connectivity: N_c, N_b, and total-isolation checks.

    Rules (GDR-003 §2, "Connectivity") — all structural/definitional facts,
    no invented magnitude:
      STRUCTURALLY_DEGENERATE if n_c == 0, or every compound is its own
        isolated component, or (>1 component exists and n_b == 0).
      NON_DEGENERATE_UNQUANTIFIED otherwise.
    """

    @property
    def dimension_name(self) -> str:
        return "connectivity"

    def evaluate(self, profile: CorpusProfile) -> DimensionAssessment:
        ep = profile.engineering_parameters
        total = profile.characterization.connectivity.total_compounds
        metrics = {
            "n_b": ep.n_b,
            "n_c": ep.n_c,
            "n_connected_components": ep.n_connected_components,
            "total_compounds": total,
        }

        if ep.n_c == 0:
            return DimensionAssessment(
                dimension=self.dimension_name,
                status=DimensionStatus.STRUCTURALLY_DEGENERATE,
                rationale="n_c == 0: the evidence graph has no compounds in "
                "any component. Structural fact, not a magnitude threshold.",
                supporting_metrics=metrics,
                provenance="CorpusProfile.engineering_parameters",
            )
        if total > 0 and ep.n_connected_components == total:
            return DimensionAssessment(
                dimension=self.dimension_name,
                status=DimensionStatus.STRUCTURALLY_DEGENERATE,
                rationale="n_connected_components == total_compounds: every "
                "compound is its own isolated component; zero co-assay "
                "relationships exist anywhere. Structural fact.",
                supporting_metrics=metrics,
                provenance="CorpusProfile.engineering_parameters",
            )
        if ep.n_connected_components > 1 and ep.n_b == 0:
            return DimensionAssessment(
                dimension=self.dimension_name,
                status=DimensionStatus.STRUCTURALLY_DEGENERATE,
                rationale="More than one connected component exists and "
                "n_b == 0: nothing bridges any pair of components, so no "
                "cross-study comparison is possible anywhere. Structural "
                "fact about graph topology, not a magnitude.",
                supporting_metrics=metrics,
                provenance="CorpusProfile.engineering_parameters",
            )
        return DimensionAssessment(
            dimension=self.dimension_name,
            status=DimensionStatus.NON_DEGENERATE_UNQUANTIFIED,
            rationale="No structural degeneracy detected. Whether n_c/n_b "
            "is 'enough' is the judgment GDR-002 routed to the SCI0-031 "
            "gate; not assessed here.",
            supporting_metrics=metrics,
            provenance="CorpusProfile.engineering_parameters",
        )


class CoverageEvaluator(QualityDimensionEvaluator):
    """Per-isoform compound coverage and four-isoform-stratum availability.

    Rules (GDR-003 §2, "Coverage") — structural facts only:
      STRUCTURALLY_DEGENERATE if any Tier 1 isoform has zero compounds, or
        n_complete_compounds == 0.
      NON_DEGENERATE_UNQUANTIFIED otherwise.

    Uses `n_complete_compounds`, not `n_w`. `n_w` (`GraphStats.
    within_study_four_isoform`) was discovered, while implementing this
    evaluator, to count compounds in a panel where all four isoforms are
    collectively represented somewhere in the panel — not compounds
    individually measured across all four, which is what the Constitution's
    N_w actually specifies and what a degenerate-coverage check needs.
    `n_complete_compounds` (`StratumReport.total_complete_compounds`) is
    verified correct against direct construction (see
    `tests/data/snapshots/test_profile.py`).
    """

    @property
    def dimension_name(self) -> str:
        return "coverage"

    def evaluate(self, profile: CorpusProfile) -> DimensionAssessment:
        per_iso = {s.isoform: s.n_compounds for s in profile.characterization.isoform_stats}
        n_complete = profile.engineering_parameters.n_complete_compounds
        metrics: dict[str, Any] = {
            "n_complete_compounds": n_complete,
            "per_isoform_compounds": per_iso,
        }

        zero_isoforms = sorted(iso for iso, n in per_iso.items() if n == 0)
        if zero_isoforms:
            return DimensionAssessment(
                dimension=self.dimension_name,
                status=DimensionStatus.STRUCTURALLY_DEGENERATE,
                rationale=f"Zero measured compounds for {zero_isoforms}. "
                "Constitution §2.3(4)'s S1 vector requires evidence for all "
                "four isoforms to exist at all. Structural fact.",
                supporting_metrics=metrics,
                provenance="CorpusProfile.characterization.isoform_stats",
            )
        if n_complete == 0:
            return DimensionAssessment(
                dimension=self.dimension_name,
                status=DimensionStatus.STRUCTURALLY_DEGENERATE,
                rationale="n_complete_compounds == 0: no compound has been "
                "measured across all four isoforms within one qualifying "
                "stratum. S1, S2, S4a, S4b are undefined without at least "
                "one. Structural fact, not a chosen minimum.",
                supporting_metrics=metrics,
                provenance="CorpusProfile.engineering_parameters",
            )
        return DimensionAssessment(
            dimension=self.dimension_name,
            status=DimensionStatus.NON_DEGENERATE_UNQUANTIFIED,
            rationale="Every Tier 1 isoform has >=1 measured compound and "
            "n_complete_compounds > 0. Magnitude adequacy not governed; not "
            "assessed here.",
            supporting_metrics=metrics,
            provenance="CorpusProfile.characterization.isoform_stats, "
            "CorpusProfile.engineering_parameters",
        )


class ScaffoldDiversityEvaluator(QualityDimensionEvaluator):
    """R1's fourth disjunct: >= 8 scaffold families.

    The one dimension using an already-governed magnitude (GDR-003 §2,
    "Scaffold diversity") rather than a structural fact. Checked against the
    corpus-global count, not the component-restricted count R1 actually
    specifies (GDR-002's known gap: `scaffold_families_in_largest_component`
    is always `None`); the rationale states this caveat explicitly whenever
    the corpus-global count meets the floor, since a global count meeting it
    does not guarantee the true, narrower criterion does.
    """

    @property
    def dimension_name(self) -> str:
        return "scaffold_diversity"

    def evaluate(self, profile: CorpusProfile) -> DimensionAssessment:
        global_count = profile.characterization.scaffold_stats.n_ring_system_families
        restricted = profile.engineering_parameters.scaffold_families_in_largest_component
        metrics = {
            "governed_floor": GOVERNED_SCAFFOLD_FAMILY_FLOOR,
            "n_ring_system_families_corpus_global": global_count,
            "scaffold_families_in_largest_component": restricted,
        }

        if global_count < GOVERNED_SCAFFOLD_FAMILY_FLOOR:
            return DimensionAssessment(
                dimension=self.dimension_name,
                status=DimensionStatus.GOVERNED_THRESHOLD_NOT_MET,
                rationale=f"Corpus-global scaffold family count "
                f"({global_count}) is below R1's governed floor of "
                f"{GOVERNED_SCAFFOLD_FAMILY_FLOOR} (Constitution v4.6, "
                "original authorship, cited not invented). The global "
                "count is an upper bound on the true component-restricted "
                "count, so failing globally means the true criterion also "
                "fails.",
                supporting_metrics=metrics,
                provenance="CorpusProfile.characterization.scaffold_stats, "
                "CorpusProfile.engineering_parameters",
            )
        return DimensionAssessment(
            dimension=self.dimension_name,
            status=DimensionStatus.GOVERNED_THRESHOLD_MET,
            rationale=f"Corpus-global scaffold family count ({global_count}) "
            f"meets R1's governed floor of {GOVERNED_SCAFFOLD_FAMILY_FLOOR}. "
            "CAVEAT: this checks the corpus-global count, not the "
            "component-restricted count R1 actually specifies "
            "(GDR-002's known gap). A global pass does NOT guarantee the "
            "true, narrower criterion is met.",
            supporting_metrics=metrics,
            provenance="CorpusProfile.characterization.scaffold_stats, "
            "CorpusProfile.engineering_parameters",
        )


class PublicationConcentrationEvaluator(QualityDimensionEvaluator):
    """Independent-source availability.

    Rules (GDR-003 §2, "Publication concentration") — structural facts only:
      INSUFFICIENT_DATA if n_publications == 0.
      WARNING if n_publications == 1 (independent replication is
        definitionally impossible with fewer than two sources).
      NON_DEGENERATE_UNQUANTIFIED otherwise.
    """

    @property
    def dimension_name(self) -> str:
        return "publication_concentration"

    def evaluate(self, profile: CorpusProfile) -> DimensionAssessment:
        pub = profile.characterization.publication_stats
        metrics = {
            "largest_publication_record_count": pub.largest_publication_record_count,
            "n_publications": pub.n_publications,
            "n_records_with_pub": pub.n_records_with_pub,
        }

        if pub.n_publications == 0:
            return DimensionAssessment(
                dimension=self.dimension_name,
                status=DimensionStatus.INSUFFICIENT_DATA,
                rationale="No publication-linked evidence exists.",
                supporting_metrics=metrics,
                provenance="CorpusProfile.characterization.publication_stats",
            )
        if pub.n_publications == 1:
            return DimensionAssessment(
                dimension=self.dimension_name,
                status=DimensionStatus.WARNING,
                rationale="Exactly one publication contributes all "
                "publication-linked evidence. Independent replication is "
                "definitionally impossible with fewer than two independent "
                "sources (Constitution §2.4's inter-lab reproducibility "
                "framing). Structural fact, not a chosen percentage.",
                supporting_metrics=metrics,
                provenance="CorpusProfile.characterization.publication_stats",
            )
        return DimensionAssessment(
            dimension=self.dimension_name,
            status=DimensionStatus.NON_DEGENERATE_UNQUANTIFIED,
            rationale=">=2 independent publications exist; independent "
            "replication is at least possible. Distribution across them is "
            "reported, not scored.",
            supporting_metrics=metrics,
            provenance="CorpusProfile.characterization.publication_stats",
        )


class ConfidenceEvaluator(QualityDimensionEvaluator):
    """Curation-confidence availability and distribution.

    Rules (GDR-003 §2, "Confidence") — structural fact only:
      INSUFFICIENT_DATA if mean_confidence is None.
      NON_DEGENERATE_UNQUANTIFIED otherwise; full distribution reported.
    """

    @property
    def dimension_name(self) -> str:
        return "confidence"

    def evaluate(self, profile: CorpusProfile) -> DimensionAssessment:
        conf = profile.characterization.confidence_stats
        metrics = {
            "mean_confidence": conf.mean_confidence,
            "median_confidence": conf.median_confidence,
            "tier_counts": dict(conf.tier_counts),
        }
        if conf.mean_confidence is None:
            return DimensionAssessment(
                dimension=self.dimension_name,
                status=DimensionStatus.INSUFFICIENT_DATA,
                rationale="No confidence scores attached to any record.",
                supporting_metrics=metrics,
                provenance="CorpusProfile.characterization.confidence_stats",
            )
        return DimensionAssessment(
            dimension=self.dimension_name,
            status=DimensionStatus.NON_DEGENERATE_UNQUANTIFIED,
            rationale="Confidence distribution reported in full; no cutoff is applied to it.",
            supporting_metrics=metrics,
            provenance="CorpusProfile.characterization.confidence_stats",
        )


class MissingnessEvaluator(QualityDimensionEvaluator):
    """Isoform-pair co-measurement, reported independently of connectivity.

    Rule (GDR-003 §2, "Missingness") — structural fact, same underlying
    condition as one Connectivity rule, reported from a different field so
    "no information may be hidden" holds even where the signal is redundant.
    """

    @property
    def dimension_name(self) -> str:
        return "missingness"

    def evaluate(self, profile: CorpusProfile) -> DimensionAssessment:
        overlap = profile.characterization.missingness.overlap
        # Off-diagonal entries only: overlap[i][i] is self-overlap (a
        # compound's isoform measured against itself), not a co-measured
        # PAIR, and must not count toward "no pair is ever co-measured."
        off_diagonal_zero = (
            all(v == 0 for i, row in overlap.items() for j, v in row.items() if i != j)
            if overlap
            else True
        )
        metrics: dict[str, Any] = {"overlap": overlap}

        if off_diagonal_zero:
            return DimensionAssessment(
                dimension=self.dimension_name,
                status=DimensionStatus.STRUCTURALLY_DEGENERATE,
                rationale="No two DISTINCT Tier 1 isoforms are ever "
                "co-measured for any compound (diagonal self-overlap "
                "excluded from this check). Same underlying condition as a "
                "Connectivity degenerate case, reported here so no "
                "information is hidden.",
                supporting_metrics=metrics,
                provenance="CorpusProfile.characterization.missingness",
            )
        return DimensionAssessment(
            dimension=self.dimension_name,
            status=DimensionStatus.NON_DEGENERATE_UNQUANTIFIED,
            rationale="At least one isoform pair is co-measured for at least one compound.",
            supporting_metrics=metrics,
            provenance="CorpusProfile.characterization.missingness",
        )


class StructuralCoverageEvaluator(QualityDimensionEvaluator):
    """Extension point for SCI0-007-derived structural coverage.

    Always returns `NOT_YET_AVAILABLE` (ADR-0009 §4): `CorpusProfile.
    structural_coverage` is `None` until SCI0-018 exists. This evaluator
    demonstrates the extension mechanism end-to-end without inventing
    structural data — no PDB or AlphaFold record is read anywhere in this
    class.
    """

    @property
    def dimension_name(self) -> str:
        return "structural_coverage"

    def evaluate(self, profile: CorpusProfile) -> DimensionAssessment:
        sc = profile.structural_coverage
        return DimensionAssessment(
            dimension=self.dimension_name,
            status=DimensionStatus.NOT_YET_AVAILABLE,
            rationale="No structural-coverage data source exists yet "
            "(SCI0-018 has not run). Once available, this evaluator will "
            "assess experimental PDB coverage, AlphaFold-fallback coverage, "
            "construct diversity, conformational-state diversity, and "
            "ligand-bound structural coverage (ADR-0009 §4).",
            supporting_metrics={"structural_coverage_present": sc is not None},
            provenance="CorpusProfile.structural_coverage",
        )

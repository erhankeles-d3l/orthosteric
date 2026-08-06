"""Productive / Non-Productive / Indeterminate binding classification.

Authority: SCI1-016. Constitution §2.2.

Constitution §2.2 mandate:
  "Positive criteria for all three classes. Non-Productive defined as
  the negation of Productive was forbidden. Indeterminate is NOT weak
  evidence of sparing and contributes zero to selectivity claims. A
  model unable to output Indeterminate per target is non-compliant."

Classification vocabulary (Constitution §2.2):
  PRODUCTIVE:      Pose reproduced (RMSD <= 2.0 A, >= 3 of 5 runs);
                   required hinge and affinity-pocket contacts present;
                   no heavy-atom clash < 2.2 A; ligand RMSD <= 3.0 A
                   across 3 x 100 ns MD replicates.
  NON_PRODUCTIVE:  Positive evidence of failure: reproducible steric clash,
                   reproducible loss of required contact, or ligand egress
                   in >= 2 of 3 MD replicates.
  INDETERMINATE:   Neither criterion set satisfied, OR replicates disagree.
                   NOT weak evidence of sparing. Contributes ZERO to
                   selectivity claims.

Scientific rule classification
  RULE_AVAILABLE:  The three-class vocabulary (PRODUCTIVE / NON_PRODUCTIVE /
    INDETERMINATE) and the requirement that all three have positive criteria.
    This is stated explicitly in Constitution §2.2.
  RULE_AVAILABLE:  Indeterminate criterion: neither set satisfied, or
    replicates disagree.
  RULE_MISSING:    The specific RMSD, clash, and contact thresholds in the
    PRODUCTIVE criterion. Constitution §2.2 states them (2.0 A, 2.2 A,
    3.0 A, 3 of 5 runs, etc.) but they are provisional and labelled
    as such. This module implements the classification LOGIC; the
    thresholds are configurable via ProductiveBindingConfig.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "PRODUCTIVE_BINDING_ALGORITHM_VERSION",
    "BindingClassification",
    "ProductiveBindingConfig",
    "ProductiveBindingRecord",
]

PRODUCTIVE_BINDING_ALGORITHM_VERSION = "productive_binding_v1_sci1016"

# Constitution §2.2 nominal thresholds (provisional; labelled PROVISIONAL
# in the Constitution -- not sealed). Exposed here as config defaults so
# downstream can override them without code changes.
_CONSTITUTION_DOCKING_RMSD_A = 2.0  # docking pose RMSD cutoff
_CONSTITUTION_MIN_DOCKING_RUNS = 3  # of 5 independent runs
_CONSTITUTION_CLASH_CUTOFF_A = 2.2  # heavy-atom clash distance
_CONSTITUTION_MD_RMSD_A = 3.0  # MD ligand RMSD cutoff
_CONSTITUTION_MD_REPLICATES = 3  # number of MD replicates


class BindingClassification(StrEnum):
    """Three-class binding vocabulary (Constitution §2.2).

    Indeterminate must never be treated as weak non-productive evidence.
    """

    PRODUCTIVE = "productive"
    NON_PRODUCTIVE = "non_productive"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class ProductiveBindingConfig:
    """Thresholds for productive binding classification (Constitution §2.2).

    All defaults match the Constitution §2.2 provisional criteria.
    Override to explore sensitivity; never alter without a Decision Record.

    Attributes:
        docking_rmsd_cutoff_angstrom:   Docking pose RMSD cutoff.
        min_docking_runs_converged:     Minimum of 5 runs that must reproduce.
        total_docking_runs:             Total independent docking runs.
        clash_distance_cutoff_angstrom: Heavy-atom clash distance.
        md_ligand_rmsd_cutoff_angstrom: MD ligand RMSD cutoff over replicates.
        md_egress_min_replicates:       Min replicates showing egress = non-prod.
        total_md_replicates:            Total MD replicates.
    """

    docking_rmsd_cutoff_angstrom: float = _CONSTITUTION_DOCKING_RMSD_A
    min_docking_runs_converged: int = _CONSTITUTION_MIN_DOCKING_RUNS
    total_docking_runs: int = 5
    clash_distance_cutoff_angstrom: float = _CONSTITUTION_CLASH_CUTOFF_A
    md_ligand_rmsd_cutoff_angstrom: float = _CONSTITUTION_MD_RMSD_A
    md_egress_min_replicates: int = 2
    total_md_replicates: int = _CONSTITUTION_MD_REPLICATES


@dataclass(frozen=True, slots=True)
class ProductiveBindingRecord:
    """Binding classification for one compound at one isoform.

    Attributes:
        compound_id:            Compound identifier.
        isoform:                Target isoform.
        classification:         PRODUCTIVE / NON_PRODUCTIVE / INDETERMINATE.
        n_docking_converged:    How many of the docking runs reproduced.
        has_required_contacts:  Whether required hinge and affinity-pocket
                                contacts are present. None if not assessed.
        has_heavy_clash:        Whether a non-allowable steric clash was found.
        n_md_egress:            Number of MD replicates showing ligand egress.
        productive_evidence:    Tuple of positive evidence items for PRODUCTIVE.
        nonproductive_evidence: Tuple of positive evidence items for NON_PRODUCTIVE.
        indeterminate_reason:   Non-empty if INDETERMINATE.
        config:                 Config used for classification.
        algorithm_version:      Pinned version.
    """

    compound_id: str
    isoform: str
    classification: BindingClassification
    n_docking_converged: int | None
    has_required_contacts: bool | None
    has_heavy_clash: bool | None
    n_md_egress: int | None
    productive_evidence: tuple[str, ...]
    nonproductive_evidence: tuple[str, ...]
    indeterminate_reason: str
    config: ProductiveBindingConfig
    algorithm_version: str

    @property
    def contributes_to_selectivity(self) -> bool:
        """Productive records only. Indeterminate contributes ZERO (§2.2)."""
        return self.classification == BindingClassification.PRODUCTIVE

    @property
    def is_indeterminate(self) -> bool:
        return self.classification == BindingClassification.INDETERMINATE


def classify_productive_binding(
    compound_id: str,
    isoform: str,
    n_docking_converged: int | None = None,
    has_required_contacts: bool | None = None,
    has_heavy_clash: bool | None = None,
    n_md_egress: int | None = None,
    config: ProductiveBindingConfig | None = None,
) -> ProductiveBindingRecord:
    """Apply Constitution §2.2 positive-criterion classification.

    Classification logic:
      PRODUCTIVE if ALL of: n_docking_converged >= min_runs, contacts present,
        no heavy clash, n_md_egress < md_egress_threshold.
      NON_PRODUCTIVE if ANY of: heavy_clash observed, contacts lost,
        n_md_egress >= threshold. Requires positive evidence.
      INDETERMINATE otherwise (data insufficient, replicates disagree).
    """
    if config is None:
        config = ProductiveBindingConfig()

    productive_ev: list[str] = []
    nonproductive_ev: list[str] = []
    indet_reason = ""

    # Productive criteria
    docking_ok = (
        n_docking_converged is not None and n_docking_converged >= config.min_docking_runs_converged
    )
    contacts_ok = has_required_contacts is True
    no_clash = has_heavy_clash is False
    md_ok = n_md_egress is not None and n_md_egress < config.md_egress_min_replicates

    if docking_ok:
        productive_ev.append(
            f"docking: {n_docking_converged}/{config.total_docking_runs} runs converged"
        )
    if contacts_ok:
        productive_ev.append("required contacts present")
    if no_clash:
        productive_ev.append("no heavy-atom clash")
    if md_ok:
        productive_ev.append(
            f"MD: {n_md_egress}/{config.total_md_replicates} replicates with egress"
        )

    # Non-productive criteria (positive evidence required)
    if has_heavy_clash is True:
        nonproductive_ev.append("reproducible heavy-atom clash")
    if has_required_contacts is False:
        nonproductive_ev.append("required contacts absent")
    if n_md_egress is not None and n_md_egress >= config.md_egress_min_replicates:
        nonproductive_ev.append(
            f"MD egress in {n_md_egress}/{config.total_md_replicates} replicates"
        )

    # Classification decision
    all_productive = docking_ok and contacts_ok and no_clash and md_ok
    any_nonproductive = bool(nonproductive_ev)

    if all_productive and not any_nonproductive:
        classification = BindingClassification.PRODUCTIVE
    elif any_nonproductive:
        classification = BindingClassification.NON_PRODUCTIVE
    else:
        classification = BindingClassification.INDETERMINATE
        missing = []
        if n_docking_converged is None:
            missing.append("docking data unavailable")
        elif not docking_ok:
            missing.append(
                f"insufficient docking convergence ({n_docking_converged}/"
                f"{config.total_docking_runs})"
            )
        if has_required_contacts is None:
            missing.append("contact assessment unavailable")
        if has_heavy_clash is None:
            missing.append("clash assessment unavailable")
        if n_md_egress is None:
            missing.append("MD data unavailable")
        indet_reason = "; ".join(missing) if missing else "replicates disagree"

    return ProductiveBindingRecord(
        compound_id=compound_id,
        isoform=isoform,
        classification=classification,
        n_docking_converged=n_docking_converged,
        has_required_contacts=has_required_contacts,
        has_heavy_clash=has_heavy_clash,
        n_md_egress=n_md_egress,
        productive_evidence=tuple(productive_ev),
        nonproductive_evidence=tuple(nonproductive_ev),
        indeterminate_reason=indet_reason,
        config=config,
        algorithm_version=PRODUCTIVE_BINDING_ALGORITHM_VERSION,
    )

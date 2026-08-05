"""Configuration for the Decision Policy Layer.

Authority: ADR-0008 [Architectural].

Everything here is **configuration, not an implementation constant**. The
selectivity tier bands in particular are project prioritization criteria, not
scientific truths about PI3K: a different project may replace them without
touching source code, and changing them never requires rebuilding the curated
evidence corpus (ADR-0008).

One value is different in kind and is treated differently
--------------------------------------------------------
`potency_floor_p_activity` defaults to `Decimal("7.0")` because Constitution
§2.3(6) states: selectivity is undefined below `pAct_alpha >= 7.0`. That is a
governed rule, not a project preference. It is exposed as configuration so the
layer stays reusable, but any value other than the Constitution's raises a
recorded governance deviation (:meth:`PolicyConfig.governance_deviations`),
which propagates into the decision record rather than passing silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = [
    "BELOW_LOWEST_TIER",
    "CONSTITUTION_POTENCY_FLOOR",
    "DEFAULT_SELECTIVITY_TIERS",
    "PolicyConfig",
    "SelectivityTier",
    "SelectivityTierTable",
]

CONSTITUTION_POTENCY_FLOOR = Decimal("7.0")
"""Constitution §2.3(6): selectivity is undefined below ``pAct_alpha >= 7.0``."""

BELOW_LOWEST_TIER = "BELOW_LOWEST_TIER"
"""Classification for a computed selectivity that reaches no configured tier.

Distinct from an `UNDEFINED_*` status: the selectivity *was* validly computed,
it simply falls below the lowest configured band.
"""


@dataclass(frozen=True, slots=True)
class SelectivityTier:
    """One selectivity prioritization band.

    Attributes:
        name: Band label, e.g. ``TIER_C``.
        min_fold: Inclusive minimum fold-selectivity for the band. A compound
            with ``Smin == min_fold`` is in the band.
    """

    name: str
    min_fold: Decimal

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("SelectivityTier.name must be non-empty")
        if self.min_fold <= 0:
            raise ValueError(f"SelectivityTier.min_fold must be positive; got {self.min_fold}")


@dataclass(frozen=True, slots=True)
class SelectivityTierTable:
    """An ordered set of selectivity bands.

    Bands must be supplied in strictly ascending `min_fold` order; the table
    validates this rather than sorting silently, so a misordered configuration
    is a loud error instead of a quietly reinterpreted one.
    """

    tiers: tuple[SelectivityTier, ...]

    def __post_init__(self) -> None:
        if not self.tiers:
            raise ValueError("SelectivityTierTable requires at least one tier")
        folds = [t.min_fold for t in self.tiers]
        if folds != sorted(folds) or len(set(folds)) != len(folds):
            raise ValueError(
                "SelectivityTierTable.tiers must be in strictly ascending "
                f"min_fold order; got {folds}"
            )
        names = [t.name for t in self.tiers]
        if len(set(names)) != len(names):
            raise ValueError(f"SelectivityTierTable tier names must be unique; got {names}")

    def classify(self, fold_selectivity: Decimal) -> str:
        """Return the highest band whose `min_fold` is met.

        Returns :data:`BELOW_LOWEST_TIER` when no band is reached.
        """
        result = BELOW_LOWEST_TIER
        for tier in self.tiers:
            if fold_selectivity >= tier.min_fold:
                result = tier.name
            else:
                break
        return result

    def to_canonical_dict(self) -> dict[str, str]:
        return {t.name: format(t.min_fold, "f") for t in self.tiers}


DEFAULT_SELECTIVITY_TIERS = SelectivityTierTable(
    tiers=(
        SelectivityTier(name="TIER_A", min_fold=Decimal("10")),
        SelectivityTier(name="TIER_B", min_fold=Decimal("30")),
        SelectivityTier(name="TIER_C", min_fold=Decimal("100")),
        SelectivityTier(name="TIER_D", min_fold=Decimal("300")),
        SelectivityTier(name="TIER_E", min_fold=Decimal("1000")),
    )
)
"""Default prioritization bands: 10x / 30x / 100x / 300x / 1000x.

Project objectives, not scientific claims. No sealed status; not listed in
`sealed/MANIFEST.md` (ADR-0008).
"""


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    """Versioned configuration shared by the policies in one engine.

    Attributes:
        config_version: Identifier recorded in decision provenance. Change it
            whenever any field below changes, so decisions remain traceable to
            the configuration that produced them.
        reference_isoform: The isoform selectivity is measured *against*
            (the numerator's reference). ``PI3Kalpha`` for this project.
        off_target_isoforms: Isoforms that must be spared for a selectivity
            claim. ``Smin`` is the minimum fold-selectivity across these.
        selectivity_tiers: Prioritization bands.
        potency_floor_p_activity: See module docstring; Constitution §2.3(6).
        min_confidence: Minimum per-target confidence for `ConfidencePolicy`
            to classify ``PASS``.
        label_noise_floor_log_units: Label-noise floor in log units for
            `UncertaintyPolicy`. ``None`` means no floor has been supplied, in
            which case that policy abstains rather than assuming one. The
            project's own floor is an output of `SCI0-016`, which has not run;
            Constitution §2.4 notes assay uncertainty is "typically >= 0.3 log
            units" but that is a general observation, not this project's sealed
            floor, and is deliberately not defaulted here.
    """

    config_version: str
    reference_isoform: str
    off_target_isoforms: tuple[str, ...]
    selectivity_tiers: SelectivityTierTable = DEFAULT_SELECTIVITY_TIERS
    potency_floor_p_activity: Decimal = CONSTITUTION_POTENCY_FLOOR
    min_confidence: float = 0.5
    label_noise_floor_log_units: float | None = None

    def __post_init__(self) -> None:
        if not self.config_version:
            raise ValueError("PolicyConfig.config_version must be non-empty")
        if not self.reference_isoform:
            raise ValueError("PolicyConfig.reference_isoform must be non-empty")
        if not self.off_target_isoforms:
            raise ValueError("PolicyConfig.off_target_isoforms must be non-empty")
        if self.reference_isoform in self.off_target_isoforms:
            raise ValueError(
                "reference_isoform must not also appear in off_target_isoforms; "
                f"got {self.reference_isoform!r}"
            )
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError(f"min_confidence must be in [0, 1]; got {self.min_confidence}")

    def governance_deviations(self) -> tuple[str, ...]:
        """Deviations from governed values, recorded in every decision.

        Presently one check: the Constitution §2.3(6) potency floor.
        """
        flags: list[str] = []
        if self.potency_floor_p_activity != CONSTITUTION_POTENCY_FLOOR:
            flags.append(
                "GOVERNANCE_DEVIATION: potency_floor_p_activity="
                f"{format(self.potency_floor_p_activity, 'f')} differs from the "
                f"Constitution §2.3(6) floor of "
                f"{format(CONSTITUTION_POTENCY_FLOOR, 'f')}"
            )
        return tuple(flags)

    def to_canonical_dict(self) -> dict[str, object]:
        """Stable, sorted representation for the decision content hash."""
        return {
            "config_version": self.config_version,
            "label_noise_floor_log_units": self.label_noise_floor_log_units,
            "min_confidence": self.min_confidence,
            "off_target_isoforms": sorted(self.off_target_isoforms),
            "potency_floor_p_activity": format(self.potency_floor_p_activity, "f"),
            "reference_isoform": self.reference_isoform,
            "selectivity_tiers": self.selectivity_tiers.to_canonical_dict(),
        }

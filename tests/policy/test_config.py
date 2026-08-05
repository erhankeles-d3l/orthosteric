"""PolicyConfig and SelectivityTierTable validation and versioning."""

from __future__ import annotations

from decimal import Decimal

import pytest

from orthosteric.policy import (
    BELOW_LOWEST_TIER,
    CONSTITUTION_POTENCY_FLOOR,
    DEFAULT_SELECTIVITY_TIERS,
    SelectivityTier,
    SelectivityTierTable,
)
from tests.policy._fixtures import BETA, GAMMA, config


def test_default_tiers_match_documented_bands() -> None:
    assert DEFAULT_SELECTIVITY_TIERS.to_canonical_dict() == {
        "TIER_A": "10",
        "TIER_B": "30",
        "TIER_C": "100",
        "TIER_D": "300",
        "TIER_E": "1000",
    }


def test_default_potency_floor_is_the_constitution_value() -> None:
    assert Decimal("7.0") == CONSTITUTION_POTENCY_FLOOR
    assert config().potency_floor_p_activity == CONSTITUTION_POTENCY_FLOOR


def test_no_governance_deviation_by_default() -> None:
    assert config().governance_deviations() == ()


def test_overriding_potency_floor_records_a_governance_deviation() -> None:
    """The floor is a governed value (§2.3(6)); departing from it is recorded."""
    flags = config(potency_floor_p_activity=Decimal("6.0")).governance_deviations()
    assert len(flags) == 1
    assert "GOVERNANCE_DEVIATION" in flags[0]
    assert "2.3(6)" in flags[0]


def test_tier_table_rejects_descending_order() -> None:
    with pytest.raises(ValueError, match="ascending"):
        SelectivityTierTable(
            tiers=(
                SelectivityTier(name="HI", min_fold=Decimal("100")),
                SelectivityTier(name="LO", min_fold=Decimal("10")),
            )
        )


def test_tier_table_rejects_duplicate_folds() -> None:
    with pytest.raises(ValueError, match="ascending"):
        SelectivityTierTable(
            tiers=(
                SelectivityTier(name="A", min_fold=Decimal("10")),
                SelectivityTier(name="B", min_fold=Decimal("10")),
            )
        )


def test_tier_table_rejects_duplicate_names() -> None:
    with pytest.raises(ValueError, match="unique"):
        SelectivityTierTable(
            tiers=(
                SelectivityTier(name="SAME", min_fold=Decimal("10")),
                SelectivityTier(name="SAME", min_fold=Decimal("20")),
            )
        )


def test_tier_table_rejects_empty() -> None:
    with pytest.raises(ValueError, match="at least one tier"):
        SelectivityTierTable(tiers=())


def test_tier_rejects_non_positive_fold() -> None:
    with pytest.raises(ValueError, match="positive"):
        SelectivityTier(name="BAD", min_fold=Decimal("0"))


def test_single_tier_table_classifies() -> None:
    table = SelectivityTierTable(tiers=(SelectivityTier(name="ONLY", min_fold=Decimal("50")),))
    assert table.classify(Decimal("60")) == "ONLY"
    assert table.classify(Decimal("40")) == BELOW_LOWEST_TIER


def test_config_rejects_reference_isoform_in_off_targets() -> None:
    with pytest.raises(ValueError, match="must not also appear"):
        config(reference_isoform=BETA, off_target_isoforms=(BETA, GAMMA))


def test_config_rejects_empty_off_targets() -> None:
    with pytest.raises(ValueError, match="off_target_isoforms"):
        config(off_target_isoforms=())


def test_config_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        config(min_confidence=1.5)


def test_config_rejects_empty_version() -> None:
    with pytest.raises(ValueError, match="config_version"):
        config(config_version="")


def test_canonical_dict_is_sorted_and_stable() -> None:
    d = config().to_canonical_dict()
    assert list(d.keys()) == sorted(d.keys())
    assert d["potency_floor_p_activity"] == "7.0"

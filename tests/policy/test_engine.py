"""PolicyEngine: provenance, determinism, extensibility, separation."""

from __future__ import annotations

import dataclasses
import json

import pytest

from orthosteric.data.snapshots import SoftwareProvenance
from orthosteric.policy import (
    DECISION_SCHEMA_VERSION,
    ConfidencePolicy,
    Policy,
    PolicyConfig,
    PolicyEngine,
    PolicyOutcome,
    PolicyStatus,
    PotencyPolicy,
    PredictionInput,
    SelectivityPolicy,
    UncertaintyPolicy,
)
from tests.policy._fixtures import (
    ALPHA,
    SYNTHETIC_SNAPSHOT_SHA,
    config,
    iso,
    prediction,
    worked_example,
)


def _software() -> SoftwareProvenance:
    """Fixed software provenance so decision hashes are stable across machines."""
    return SoftwareProvenance(
        python_version="3.12.0 (test)",
        rdkit_version="2026.3.5",
        orthosteric_version="0.1.0",
        git_sha="abc123",
        git_dirty=False,
        os_platform="Linux",
        os_version="test",
        lockfile_hash="f" * 64,
        key_package_versions={"rdkit": "2026.3.5"},
    )


def _engine(cfg: PolicyConfig | None = None) -> PolicyEngine:
    c = cfg if cfg is not None else config()
    return PolicyEngine(
        policies=[
            SelectivityPolicy(c),
            PotencyPolicy(c),
            ConfidencePolicy(c),
            UncertaintyPolicy(c),
        ],
        config=c,
        software=_software(),
    )


# ── provenance completeness ───────────────────────────────────────────────────


def test_provenance_records_every_required_field() -> None:
    record = _engine().decide(worked_example())
    p = record.provenance
    assert p.schema_version == DECISION_SCHEMA_VERSION
    assert p.prediction_id == "PRED-1"
    assert p.model_version == "gen-1"
    assert p.evidence_snapshot_sha256 == SYNTHETIC_SNAPSHOT_SHA
    assert p.policy_config_version == "test-config-1"
    assert p.threshold_configuration["selectivity_tiers"]["TIER_C"] == "100"
    assert p.decision_timestamp_utc.endswith("Z")
    assert len(p.decision_content_sha256) == 64
    assert p.software.rdkit_version == "2026.3.5"


def test_provenance_records_all_participating_policies() -> None:
    record = _engine().decide(worked_example())
    ids = {pid for pid, _ in record.provenance.policies}
    assert ids == {
        "selectivity_tier",
        "potency_floor",
        "joint_confidence",
        "uncertainty_floor",
    }
    assert all(ver for _, ver in record.provenance.policies)


def test_threshold_configuration_is_embedded_not_referenced() -> None:
    """A decision stays interpretable even if the config file later changes."""
    record = _engine().decide(worked_example())
    cfg = record.provenance.threshold_configuration
    assert cfg["potency_floor_p_activity"] == "7.0"
    assert cfg["reference_isoform"] == ALPHA


def test_decision_is_reproducible_from_snapshot_sha() -> None:
    record = _engine().decide(worked_example())
    assert record.provenance.evidence_snapshot_sha256 == SYNTHETIC_SNAPSHOT_SHA


# ── determinism ───────────────────────────────────────────────────────────────


def test_same_inputs_yield_same_content_hash() -> None:
    engine = _engine()
    pred = worked_example()
    assert (
        engine.decide(pred).provenance.decision_content_sha256
        == engine.decide(pred).provenance.decision_content_sha256
    )


def test_timestamp_excluded_from_content_hash() -> None:
    """SCI0-011 precedent: a timestamp must not make identical artefacts differ."""
    engine = _engine()
    pred = worked_example()
    a = engine.decide(pred).provenance
    b = engine.decide(pred).provenance
    assert a.decision_content_sha256 == b.decision_content_sha256
    assert "decision_timestamp_utc" not in a.decision_content_sha256


def test_config_change_changes_content_hash() -> None:
    pred = worked_example()
    h1 = _engine(config()).decide(pred).provenance.decision_content_sha256
    h2 = (
        _engine(config(config_version="other", min_confidence=0.9))
        .decide(pred)
        .provenance.decision_content_sha256
    )
    assert h1 != h2


def test_prediction_change_changes_content_hash() -> None:
    engine = _engine()
    h1 = engine.decide(worked_example()).provenance.decision_content_sha256
    other = prediction(
        iso(ALPHA, "9.301"),
        iso("PI3Kbeta", "7.500"),
        iso("PI3Kgamma", "6.770"),
        iso("PI3Kdelta", "6.921"),
    )
    h2 = engine.decide(other).provenance.decision_content_sha256
    assert h1 != h2


def test_batch_preserves_order_and_matches_individual_decisions() -> None:
    engine = _engine()
    p1 = worked_example()
    p2 = prediction(iso(ALPHA, "6.0"), prediction_id="PRED-2")
    records = engine.decide_batch([p1, p2])
    assert [r.provenance.prediction_id for r in records] == ["PRED-1", "PRED-2"]
    assert (
        records[0].provenance.decision_content_sha256
        == engine.decide(p1).provenance.decision_content_sha256
    )


# ── immutability / separation ────────────────────────────────────────────────


def test_decision_record_is_frozen() -> None:
    record = _engine().decide(worked_example())
    with pytest.raises((AttributeError, TypeError)):
        record.criterion_eligible = True  # type: ignore[misc]


def test_prediction_input_is_frozen() -> None:
    pred = worked_example()
    with pytest.raises((AttributeError, TypeError)):
        pred.model_version = "tampered"  # type: ignore[misc]


def test_engine_does_not_mutate_the_prediction() -> None:
    pred = worked_example()
    before = dataclasses.asdict(pred)
    _engine().decide(pred)
    assert dataclasses.asdict(pred) == before


def test_no_decision_is_criterion_eligible() -> None:
    record = _engine().decide(worked_example())
    assert record.criterion_eligible is False
    assert all(o.criterion_eligible is False for o in record.outcomes)


# ── flag aggregation ─────────────────────────────────────────────────────────


def test_engine_aggregates_governance_flags_deduplicated_and_sorted() -> None:
    record = _engine().decide(worked_example())
    assert list(record.governance_flags) == sorted(set(record.governance_flags))
    # UncertaintyPolicy abstains with no floor configured -> its flag surfaces
    assert any("SCI0-016" in f for f in record.governance_flags)


def test_outcome_lookup_by_policy_id() -> None:
    record = _engine().decide(worked_example())
    assert record.outcome_for("selectivity_tier") is not None
    assert record.outcome_for("selectivity_tier").classification == "TIER_C"  # type: ignore[union-attr]
    assert record.outcome_for("no_such_policy") is None


def test_to_dict_is_json_serializable() -> None:
    record = _engine().decide(worked_example())
    assert json.loads(json.dumps(record.to_dict()))["criterion_eligible"] is False


# ── extensibility ─────────────────────────────────────────────────────────────


class _CustomDevelopabilityPolicy(Policy):
    """A new policy added without modifying any existing module (ADR-0008)."""

    @property
    def policy_id(self) -> str:
        return "developability_demo"

    @property
    def policy_version(self) -> str:
        return "0.1.0"

    def evaluate(self, prediction: PredictionInput) -> PolicyOutcome:  # noqa: ARG002
        # `prediction` is unused: the Policy interface requires the parameter,
        # and this demonstration policy classifies unconditionally.
        return PolicyOutcome(
            policy_id=self.policy_id,
            policy_version=self.policy_version,
            status=PolicyStatus.CLASSIFIED,
            classification="PASS",
            rationale="Synthetic demonstration policy.",
        )


def test_new_policy_requires_no_change_to_existing_code() -> None:
    cfg = config()
    engine = PolicyEngine(
        policies=[SelectivityPolicy(cfg), _CustomDevelopabilityPolicy()],
        config=cfg,
        software=_software(),
    )
    record = engine.decide(worked_example())
    assert record.outcome_for("developability_demo") is not None
    assert ("developability_demo", "0.1.0") in record.provenance.policies


def test_added_policy_is_still_not_criterion_eligible() -> None:
    """The firewall is a property of the outcome type, not of specific policies."""
    cfg = config()
    engine = PolicyEngine(
        policies=[_CustomDevelopabilityPolicy()], config=cfg, software=_software()
    )
    assert engine.decide(worked_example()).criterion_eligible is False


def test_engine_rejects_duplicate_policy_ids() -> None:
    cfg = config()
    with pytest.raises(ValueError, match="Duplicate policy_id"):
        PolicyEngine(
            policies=[_CustomDevelopabilityPolicy(), _CustomDevelopabilityPolicy()],
            config=cfg,
            software=_software(),
        )


def test_engine_rejects_empty_policy_set() -> None:
    with pytest.raises(ValueError, match="at least one policy"):
        PolicyEngine(policies=[], config=config(), software=_software())


# ── backward compatibility ───────────────────────────────────────────────────


def test_default_config_reproduces_documented_default_behaviour() -> None:
    """Guards the documented defaults against silent drift."""
    cfg = config()
    assert cfg.potency_floor_p_activity.compare_total(__import__("decimal").Decimal("7.0")) == 0
    assert cfg.selectivity_tiers.to_canonical_dict()["TIER_A"] == "10"
    assert cfg.label_noise_floor_log_units is None  # abstains by default


def test_schema_version_is_pinned() -> None:
    """A schema change must be a deliberate, visible edit."""
    assert DECISION_SCHEMA_VERSION == "policy_decision_v1"

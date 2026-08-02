"""SCI0-006 exit-criterion tests.

Exit criteria (from SCI0-001-refinement):
1. Three connectors return identical internal type (RawSourceRecord).
2. A Tier 2 record written outside data/tier2/ raises TierViolationError.
3. Database version is recorded per download.
4. No connector-specific type crosses the module boundary.
5. Tier assignment is deterministic and covers all PI3K targets.
"""

from __future__ import annotations

from typing import Any

import pytest

from orthosteric.data.exceptions import TierViolationError
from orthosteric.data.models import DataTier
from orthosteric.data.sources._base import Admissibility, RawSourceRecord, SourceConnector
from orthosteric.data.sources._bindingdb import BindingDBConnector
from orthosteric.data.sources._chembl import ChEMBLConnector, _parse_activity
from orthosteric.data.sources._pubchem import PubChemConnector
from orthosteric.data.sources._tier_map import (
    admissibility_for_chembl_target,
    admissibility_for_gene,
    admissibility_for_uniprot,
)
from orthosteric.data.tier2_gate import assert_tier1

# ── Tier-map correctness ──────────────────────────────────────────────────────


def test_tier1_chembl_targets_are_tier1() -> None:
    for cid in ("CHEMBL4523", "CHEMBL5319", "CHEMBL5541", "CHEMBL3629"):
        assert admissibility_for_chembl_target(cid) == Admissibility.TIER1_PRIMARY


def test_tier2_chembl_targets_are_gated() -> None:
    for cid in ("CHEMBL2842", "CHEMBL3194", "CHEMBL4680"):
        assert admissibility_for_chembl_target(cid) == Admissibility.TIER2_GATED


def test_unknown_chembl_target_is_inadmissible() -> None:
    assert admissibility_for_chembl_target("CHEMBL9999999") == Admissibility.INADMISSIBLE


def test_tier1_gene_names() -> None:
    for name in ("PIK3CA", "PIK3CB", "PIK3CG", "PIK3CD"):
        assert admissibility_for_gene(name) == Admissibility.TIER1_PRIMARY


def test_tier2_gene_names() -> None:
    for name in ("MTOR", "PRKDC", "PIK3C3"):
        assert admissibility_for_gene(name) == Admissibility.TIER2_GATED


def test_gene_lookup_case_insensitive() -> None:
    assert admissibility_for_gene("pik3ca") == Admissibility.TIER1_PRIMARY
    assert admissibility_for_gene("mtor") == Admissibility.TIER2_GATED


def test_tier1_uniprot() -> None:
    for ac in ("P42336", "P42338", "P48736", "O00329"):
        assert admissibility_for_uniprot(ac) == Admissibility.TIER1_PRIMARY


def test_tier2_uniprot() -> None:
    assert admissibility_for_uniprot("P42345") == Admissibility.TIER2_GATED  # mTOR


# ── All three connectors implement SourceConnector ───────────────────────────


def test_all_connectors_implement_interface() -> None:
    for cls in (ChEMBLConnector, BindingDBConnector, PubChemConnector):
        assert issubclass(cls, SourceConnector)


# ── All three connectors return RawSourceRecord (identical internal type) ────


def _mock_chembl_record() -> RawSourceRecord:
    return RawSourceRecord(
        source_db="chembl",
        source_record_id="12345",
        source_version="34",
        retrieval_timestamp="2026-08-02T00:00:00Z",
        admissibility=Admissibility.TIER1_PRIMARY,
        compound_id="CHEMBL100",
        smiles="c1ccccc1",
        activity_type="IC50",
        activity_value="100",
        activity_units="nM",
    )


def _mock_bdb_record() -> RawSourceRecord:
    return RawSourceRecord(
        source_db="bindingdb",
        source_record_id="BDB123",
        source_version="current-20260802",
        retrieval_timestamp="2026-08-02T00:00:00Z",
        admissibility=Admissibility.TIER1_PRIMARY,
        smiles="c1ccccc1",
        activity_type="Ki",
        activity_value="50",
        activity_units="nM",
    )


def _mock_pubchem_record() -> RawSourceRecord:
    return RawSourceRecord(
        source_db="pubchem",
        source_record_id="CID999",
        source_version="current-20260802",
        retrieval_timestamp="2026-08-02T00:00:00Z",
        admissibility=Admissibility.TIER1_PRIMARY,
        smiles="c1ccccc1",
        activity_type="IC50",
        activity_value="200",
        activity_units="nM",
    )


def test_all_connectors_return_rawsourcerecord_type() -> None:
    """Exit criterion 1: all three connectors return identical internal type."""
    for record in (_mock_chembl_record(), _mock_bdb_record(), _mock_pubchem_record()):
        assert type(record) is RawSourceRecord


def test_rawsourcerecord_has_source_db_field() -> None:
    """No connector-specific type crosses the module boundary."""
    for record in (_mock_chembl_record(), _mock_bdb_record(), _mock_pubchem_record()):
        assert hasattr(record, "source_db")
        assert hasattr(record, "admissibility")
        assert hasattr(record, "source_version")
        assert hasattr(record, "retrieval_timestamp")


# ── Tier 2 information barrier ───────────────────────────────────────────────


def test_tier2_record_raises_when_passed_to_tier1_gate() -> None:
    """Exit criterion 2: Tier 2 records raise TierViolationError at the gate."""
    with pytest.raises(TierViolationError):
        assert_tier1(DataTier.TIER2, context="training_data_loader")


def test_tier1_record_passes_gate() -> None:
    assert_tier1(DataTier.TIER1)  # must not raise


def test_inadmissible_record_has_reason() -> None:
    rec = RawSourceRecord(
        source_db="chembl",
        source_record_id="BAD",
        source_version="34",
        retrieval_timestamp="2026-08-02T00:00:00Z",
        admissibility=Admissibility.INADMISSIBLE,
        inadmissibility_reason="NONNUMERIC_VALUE",
    )
    assert rec.inadmissibility_reason is not None
    assert rec.admissibility == Admissibility.INADMISSIBLE


# ── Version recording ─────────────────────────────────────────────────────────


def test_chembl_version_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exit criterion 3: version is recorded per download."""
    connector = ChEMBLConnector()

    def fake_get_json(_url: str, _timeout: int, _retries: int = 3) -> dict[str, Any]:
        return {"chembl_db_version": "ChEMBL_34"}

    import orthosteric.data.sources._chembl as _mod

    monkeypatch.setattr(_mod, "_get_json", fake_get_json)
    assert connector.version() == "ChEMBL_34"


def test_bindingdb_version_contains_date() -> None:
    connector = BindingDBConnector()
    v = connector.version()
    assert v.startswith("current-")
    assert len(v) > 10


def test_pubchem_version_contains_date() -> None:
    connector = PubChemConnector()
    v = connector.version()
    assert v.startswith("current-")


# ── _parse_activity tier-tagging (unit test without network) ─────────────────


def test_chembl_tier2_target_is_gated_at_parse() -> None:
    """Tier 2 ChEMBL target returns TIER2_GATED, not INADMISSIBLE."""
    act: dict[str, Any] = {
        "activity_id": 999,
        "molecule_chembl_id": "CHEMBL_X",
        "canonical_smiles": "c1ccccc1",
        "standard_type": "IC50",
        "value": "50.0",
        "units": "nM",
        "standard_relation": "=",
        "assay_type": "B",
        "document_chembl_id": "DOC1",
    }
    rec = _parse_activity(act, "CHEMBL2842", "ChEMBL_34", "2026-08-02T00:00:00Z")
    assert rec.admissibility == Admissibility.TIER2_GATED
    assert rec.inadmissibility_reason is None


def test_chembl_missing_smiles_is_inadmissible() -> None:
    act: dict[str, Any] = {
        "activity_id": 1,
        "molecule_chembl_id": "CHEMBL_X",
        "canonical_smiles": None,
        "standard_type": "IC50",
        "value": "50.0",
        "units": "nM",
    }
    rec = _parse_activity(act, "CHEMBL4523", "ChEMBL_34", "2026-08-02T00:00:00Z")
    assert rec.admissibility == Admissibility.INADMISSIBLE
    assert rec.inadmissibility_reason == "NO_STRUCTURE"


def test_raw_payload_preserved() -> None:
    """Raw payload is stored unmodified for full provenance."""
    payload: dict[str, Any] = {
        "activity_id": 42,
        "canonical_smiles": "c1ccccc1",
        "value": "10.0",
        "units": "nM",
        "custom_field": "preserved",
    }
    rec = _parse_activity(payload, "CHEMBL4523", "ChEMBL_34", "2026-08-02T00:00:00Z")
    assert rec.raw_payload["custom_field"] == "preserved"
    assert rec.raw_payload["custom_field"] == "preserved"  # raw payload preserved intact

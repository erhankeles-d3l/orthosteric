"""QC checks for the docking pilot output (data/structural_evidence/
docking_pilot_A4.json). Structural, not statistical -- verifies the
pipeline's OWN invariants, not scientific conclusions about docking
quality (which the pilot's small size cannot support).

Exit criteria:
  (1) Every record has evidence_class DOCKING_COMPLEX and
      is_experimental=False.
  (2) Every SUCCESS record carries complete provenance (engine, version,
      seed, box, receptor identifier).
  (3) No record with outcome != SUCCESS carries a docking_score.
  (4) PI3Kbeta records are all NO_RECEPTOR_AVAILABLE -- never silently
      dropped, never given a fabricated score.
  (5) Score distribution has no pathological concentration (all-identical
      scores would indicate a broken box/receptor) and no absurd outliers
      (Vina scores for drug-like ligands are essentially always in
      roughly -3 to -14 kcal/mol; anything outside signals a setup bug,
      not a real result).
"""

from __future__ import annotations

import json
from pathlib import Path

RECORDS_PATH = Path("data/structural_evidence/docking_pilot_A4.json")


def _records() -> list[dict]:
    return json.loads(RECORDS_PATH.read_text())


def test_pilot_file_exists_and_nonempty() -> None:
    assert RECORDS_PATH.exists()
    recs = _records()
    assert len(recs) > 0


def test_every_record_is_docking_complex_never_experimental() -> None:
    for r in _records():
        assert r["evidence_class"] == "docking_complex"
        assert r["is_experimental"] is False


def test_success_records_have_complete_provenance() -> None:
    for r in _records():
        if r["outcome"] != "success":
            continue
        assert r["docking_engine"] == "AutoDock Vina"
        assert r["docking_engine_version"]
        assert r["seed"] is not None
        assert r["docking_box"] is not None
        assert r["docking_box"]["derivation_method"]
        assert r["receptor_identifier"]
        assert r["docking_score"] is not None


def test_non_success_records_never_carry_a_score() -> None:
    for r in _records():
        if r["outcome"] != "success":
            assert r["docking_score"] is None


def test_beta_never_silently_dropped() -> None:
    recs = _records()
    beta_recs = [r for r in recs if r["isoform"] == "PI3Kbeta"]
    assert len(beta_recs) > 0
    assert all(r["outcome"] == "no_receptor_available" for r in beta_recs)
    assert all(r["docking_score"] is None for r in beta_recs)
    assert all(r["failure_reason"] for r in beta_recs)


def test_score_distribution_not_pathological() -> None:
    scores = [r["docking_score"] for r in _records() if r["outcome"] == "success"]
    assert len(scores) >= 5
    assert len(set(scores)) > 1  # not all identical (would indicate a broken box)
    assert all(-14.0 <= s <= -3.0 for s in scores)  # plausible Vina range for drug-like ligands


def test_receptor_source_tier_derived_correctly() -> None:
    for r in _records():
        if r["outcome"] != "success":
            continue
        assert r["receptor_source_class"] == "experimental_receptor"
        assert r["tier"] == "D1"

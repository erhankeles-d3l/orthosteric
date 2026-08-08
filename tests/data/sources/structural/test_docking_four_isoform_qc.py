"""QC checks for the four-isoform cross-docking pilot
(data/structural_evidence/docking_pilot_four_isoform_A4.json and its
comparative companion file).

Exit criteria:
  (1) All four isoforms are represented for every compound (the central
      requirement: same compound x alpha/beta/gamma/delta).
  (2) PI3Kbeta records use ALPHAFOLD_RECEPTOR (never EXPERIMENTAL_RECEPTOR,
      never silently promoted); alpha/gamma/delta use EXPERIMENTAL_RECEPTOR.
  (3) Tier is correctly derived (D1 for experimental, D2 for AlphaFold).
  (4) Given one compound_id, the four-isoform record set can be
      reconstructed and shows differential (not identical) scores across
      isoforms.
  (5) The comparative delta-dock file is internally consistent with the
      raw per-isoform scores.
  (6) No score is fabricated for a compound/isoform pair that has no
      corresponding SUCCESS record.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

RECORDS_PATH = Path("data/structural_evidence/docking_pilot_four_isoform_A4.json")
COMPARATIVE_PATH = Path("data/structural_evidence/docking_pilot_four_isoform_comparative_A4.json")

_ISOFORMS = {"PI3Kalpha", "PI3Kbeta", "PI3Kgamma", "PI3Kdelta"}


def _records() -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads(RECORDS_PATH.read_text())
    return data


def _comparative() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(COMPARATIVE_PATH.read_text())
    return data


def _by_compound() -> dict[str, dict[str, dict[str, Any]]]:
    out: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for r in _records():
        out[r["compound_id"]][r["isoform"]] = r
    return out


def test_files_exist() -> None:
    assert RECORDS_PATH.exists()
    assert COMPARATIVE_PATH.exists()


def test_every_compound_has_all_four_isoforms_attempted() -> None:
    by_cmpd = _by_compound()
    assert len(by_cmpd) > 0
    for cid, iso_map in by_cmpd.items():
        assert set(iso_map) == _ISOFORMS, f"{cid} missing isoforms: {_ISOFORMS - set(iso_map)}"


def test_beta_always_alphafold_others_always_experimental() -> None:
    for r in _records():
        if r["outcome"] != "success":
            continue
        if r["isoform"] == "PI3Kbeta":
            assert r["receptor_source_class"] == "alphafold_receptor"
            assert r["tier"] == "D2"
        else:
            assert r["receptor_source_class"] == "experimental_receptor"
            assert r["tier"] == "D1"


def test_reconstruct_four_isoform_profile_for_one_compound() -> None:
    """The pipeline's central capability: given one compound_id, recover
    a complete, differential (not identical) four-isoform profile."""
    by_cmpd = _by_compound()
    cid = next(iter(by_cmpd))
    profile = {iso: rec["docking_score"] for iso, rec in by_cmpd[cid].items()}
    assert set(profile) == _ISOFORMS
    assert all(v is not None for v in profile.values())
    assert len(set(profile.values())) > 1  # differential, not identical


def test_comparative_deltas_consistent_with_raw_scores() -> None:
    by_cmpd = _by_compound()
    comp = _comparative()
    for cid, entry in comp.items():
        raw = by_cmpd[cid]
        alpha = raw["PI3Kalpha"]["docking_score"]
        for iso, delta_key in (
            ("PI3Kbeta", "alpha_vs_beta"),
            ("PI3Kgamma", "alpha_vs_gamma"),
            ("PI3Kdelta", "alpha_vs_delta"),
        ):
            expected = raw[iso]["docking_score"] - alpha
            assert abs(entry["delta_dock"][delta_key] - expected) < 1e-9


def test_no_fabricated_score_for_non_success_pairs() -> None:
    for r in _records():
        if r["outcome"] != "success":
            assert r["docking_score"] is None


def test_all_pilot_compounds_classified() -> None:
    comp = _comparative()
    for _cid, entry in comp.items():
        assert entry["classification"] != "unresolved"


def test_receptor_provenance_traceable() -> None:
    for r in _records():
        if r["outcome"] != "success":
            continue
        assert r["receptor_identifier"]
        assert r["docking_box"]["derivation_method"]
        if r["isoform"] == "PI3Kbeta":
            assert (
                "P42338" in r["receptor_identifier"]
                or "uniprot" in r["docking_box"]["derivation_method"]
            )

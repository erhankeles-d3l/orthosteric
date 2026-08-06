"""Tests for SCI1 SelectivityTarget construction from Activity Snapshot records.

Exit criteria:
  (1) Only compounds with a complete (all 4 isoform) C1_PRIMARY panel
      produce a target.
  (2) Multi-panel compounds aggregate per-panel differences by median,
      never mixing isoform values across panels.
  (3) LEGACY_FALLBACK records never contribute.
  (4) Compounds without canonical_smiles are excluded (cannot fit
      ligand-based baselines).
  (5) Output is deterministic and sorted by compound_id.
"""

from __future__ import annotations

from orthosteric.eval._target_construction import (
    build_selectivity_targets,
    compounds_for_split,
)


def _r(
    ik,
    iso,
    pchembl,
    smiles="CCO",
    study_id="S1",
    bao_format="BAO_1",
    assay_type="B",
    source_record_id=None,
    assay_id="A1",
):
    return {
        "inchikey": ik,
        "isoform": iso,
        "pchembl_value": pchembl,
        "canonical_smiles": smiles,
        "source_record_id": source_record_id or f"{ik}_{iso}_{study_id}",
        "assay_id": assay_id,
        "censoring": "exact",
        "study_id": study_id,
        "bao_format": bao_format,
        "assay_type": assay_type,
        "exclusion_reason": None,
    }


def _complete(ik, a, b, g, d, **kw):
    return [
        _r(ik, "PI3Kalpha", a, **kw),
        _r(ik, "PI3Kbeta", b, **kw),
        _r(ik, "PI3Kgamma", g, **kw),
        _r(ik, "PI3Kdelta", d, **kw),
    ]


def test_complete_compound_produces_one_target() -> None:
    recs = _complete("IKA", 8.0, 5.0, 6.0, 6.0)
    targets = build_selectivity_targets(recs)
    assert len(targets) == 1
    t = targets[0]
    assert t.compound_id == "IKA"
    assert t.pac_alpha == 8.0
    assert t.lr_vs_beta == 3.0
    assert t.lr_vs_gamma == 2.0
    assert t.lr_vs_delta == 2.0
    assert t.within_study is True


def test_incomplete_compound_excluded() -> None:
    recs = [_r("IKA", "PI3Kalpha", 8.0), _r("IKA", "PI3Kbeta", 5.0)]  # missing gamma/delta
    targets = build_selectivity_targets(recs)
    assert targets == []


def test_multi_panel_compound_aggregates_by_median_within_panel_diffs() -> None:
    """Two panels, each internally complete; the emitted target must be
    the median of the two WITHIN-panel differences, never a cross-panel mix."""
    recs = _complete("IKA", 8.0, 5.0, 6.0, 6.0, study_id="S1") + _complete(
        "IKA", 7.0, 5.0, 6.0, 6.0, study_id="S2"
    )
    targets = build_selectivity_targets(recs)
    assert len(targets) == 1
    t = targets[0]
    # panel S1: alpha-beta = 3.0 ; panel S2: alpha-beta = 2.0 ; median = 2.5
    assert t.lr_vs_beta == 2.5
    assert t.pac_alpha == 7.5  # median of 8.0 and 7.0


def test_legacy_fallback_records_excluded() -> None:
    legacy = [
        {
            "inchikey": "IKA",
            "isoform": iso,
            "pchembl_value": v,
            "canonical_smiles": "CCO",
            "study_id": "S1",
            "assay_id": "A1",
            "censoring": "exact",
            "exclusion_reason": None,
            "source_record_id": f"IKA_{iso}",
        }
        for iso, v in [
            ("PI3Kalpha", 8.0),
            ("PI3Kbeta", 5.0),
            ("PI3Kgamma", 6.0),
            ("PI3Kdelta", 6.0),
        ]
    ]  # no bao_format/assay_type -> LEGACY_FALLBACK
    targets = build_selectivity_targets(legacy)
    assert targets == []


def test_compound_without_smiles_excluded() -> None:
    recs = _complete("IKA", 8.0, 5.0, 6.0, 6.0, smiles=None)
    targets = build_selectivity_targets(recs)
    assert targets == []


def test_deterministic_sorted_output() -> None:
    recs = _complete("IKB", 8.0, 5.0, 6.0, 6.0) + _complete("IKA", 7.0, 5.0, 6.0, 6.0)
    targets = build_selectivity_targets(recs)
    assert [t.compound_id for t in targets] == ["IKA", "IKB"]


def test_compounds_for_split_extracts_id_smiles_pairs() -> None:
    recs = _complete("IKA", 8.0, 5.0, 6.0, 6.0, smiles="c1ccccc1")
    targets = build_selectivity_targets(recs)
    pairs = compounds_for_split(targets)
    assert pairs == [("IKA", "c1ccccc1")]

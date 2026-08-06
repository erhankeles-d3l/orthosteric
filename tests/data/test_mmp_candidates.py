"""Tests for GDR-012 exploratory scaffold-pair candidate generation.

Exit criteria:
  (1) Every candidate carries evidence_class=EXPLORATORY_BEMIS_MURCKO --
      MMP_CONFIRMED is never produced by any code path here.
  (2) Sign-flip detection is correct.
  (3) Candidate generation is deterministic under record-order shuffling
      (via the GDR-013 aggregation it now uses).
  (4) A compound with a censored-only required-isoform cell is excluded
      from candidate generation, and the exclusion is counted, never
      silently dropped.
  (5) magnitude_over_sigma is reported descriptively; no pass/fail
      threshold is ever applied.
"""

from __future__ import annotations

import random

from orthosteric.data.mmp_candidates import (
    ScaffoldPairEvidenceClass,
    generate_exploratory_scaffold_pairs,
)


def _r(
    inchikey,
    isoform,
    pchembl,
    scaffold_family_id="FAM1",
    source_record_id=None,
    assay_id="A1",
    censoring="exact",
    study_id="S1",
    bao_format="BAO_1",
    assay_type="B",
):
    return {
        "inchikey": inchikey,
        "isoform": isoform,
        "pchembl_value": pchembl,
        "scaffold_family_id": scaffold_family_id,
        "source_record_id": source_record_id or f"{inchikey}_{isoform}",
        "assay_id": assay_id,
        "censoring": censoring,
        "study_id": study_id,
        "bao_format": bao_format,
        "assay_type": assay_type,
        "exclusion_reason": None,
    }


def _complete_compound(ik, alpha, beta, gamma, delta, scaffold="FAM1"):
    return [
        _r(ik, "PI3Kalpha", alpha, scaffold_family_id=scaffold),
        _r(ik, "PI3Kbeta", beta, scaffold_family_id=scaffold),
        _r(ik, "PI3Kgamma", gamma, scaffold_family_id=scaffold),
        _r(ik, "PI3Kdelta", delta, scaffold_family_id=scaffold),
    ]


# ── evidence classification ──────────────────────────────────────────────────


def test_every_candidate_is_exploratory_bemis_murcko() -> None:
    recs = _complete_compound("IKA", 8.0, 5.0, 5.0, 5.0) + _complete_compound(
        "IKB", 5.0, 8.0, 5.0, 5.0
    )
    report = generate_exploratory_scaffold_pairs(recs)
    assert report.candidates  # sanity: something was generated
    for c in report.candidates:
        assert c.evidence_class is ScaffoldPairEvidenceClass.EXPLORATORY_BEMIS_MURCKO
        assert c.evidence_class is not ScaffoldPairEvidenceClass.MMP_CONFIRMED
    assert "NOT matched molecular pair" in report.evidence_class_note


# ── sign-flip detection ───────────────────────────────────────────────────────


def test_sign_flip_detected_between_alpha_selective_and_beta_selective() -> None:
    # IKA is alpha-selective vs beta (delta = +3); IKB is beta-selective (delta = -3)
    recs = _complete_compound("IKA", 8.0, 5.0, 6.0, 6.0) + _complete_compound(
        "IKB", 5.0, 8.0, 6.0, 6.0
    )
    report = generate_exploratory_scaffold_pairs(recs)
    beta_candidates = [c for c in report.candidates if c.isoform_x == "PI3Kbeta"]
    assert len(beta_candidates) == 1
    assert beta_candidates[0].sign_flip is True
    assert report.n_sign_flip_candidates >= 1


def test_no_flip_when_both_compounds_alpha_selective() -> None:
    recs = _complete_compound("IKA", 8.0, 5.0, 6.0, 6.0) + _complete_compound(
        "IKB", 7.5, 5.5, 6.0, 6.0
    )
    report = generate_exploratory_scaffold_pairs(recs)
    beta_candidates = [c for c in report.candidates if c.isoform_x == "PI3Kbeta"]
    assert beta_candidates[0].sign_flip is False


def test_different_scaffold_families_never_paired() -> None:
    recs = _complete_compound("IKA", 8.0, 5.0, 5.0, 5.0, scaffold="FAM1") + _complete_compound(
        "IKB", 5.0, 8.0, 5.0, 5.0, scaffold="FAM2"
    )
    report = generate_exploratory_scaffold_pairs(recs)
    assert report.candidates == ()
    assert report.n_pairs_examined == 0


# ── determinism under record shuffling (GDR-013 dependency) ─────────────────


def test_deterministic_under_record_order_shuffle() -> None:
    recs = _complete_compound("IKA", 8.0, 5.0, 5.0, 5.0) + _complete_compound(
        "IKB", 5.0, 8.0, 5.0, 5.0
    )
    reports = []
    for _ in range(10):
        shuffled = recs[:]
        random.shuffle(shuffled)
        reports.append(generate_exploratory_scaffold_pairs(shuffled))
    magnitudes = {tuple(sorted(c.magnitude for c in r.candidates)) for r in reports}
    flips = {r.n_sign_flip_candidates for r in reports}
    assert len(magnitudes) == 1
    assert len(flips) == 1


def test_multi_record_cell_uses_median_not_last_writer() -> None:
    """The exact regression this module was built to fix: a cell with
    multiple pchembl values must use the deterministic median (GDR-013),
    not whichever record appears last."""
    recs = (
        _complete_compound("IKA", 8.0, 5.0, 5.0, 5.0)
        + [_r("IKA", "PI3Kalpha", 6.0, source_record_id="IKA_alpha_2")]  # 2nd alpha obs
        + _complete_compound("IKB", 5.0, 8.0, 5.0, 5.0)
    )
    report = generate_exploratory_scaffold_pairs(recs)
    # median of {8.0, 6.0} = 7.0, regardless of which was "last"
    beta_candidates = [c for c in report.candidates if c.isoform_x == "PI3Kbeta"]
    assert beta_candidates[0].delta_a == 7.0 - 5.0


# ── censoring: excluded from exact-value candidates, never silently dropped ─


def test_censored_required_isoform_excludes_compound_but_is_counted() -> None:
    recs = [
        _r("IKA", "PI3Kalpha", 8.0),
        _r("IKA", "PI3Kbeta", None, censoring="right"),  # censored, no exact value
        _r("IKA", "PI3Kgamma", 5.0),
        _r("IKA", "PI3Kdelta", 5.0),
    ] + _complete_compound("IKB", 5.0, 8.0, 5.0, 5.0)
    report = generate_exploratory_scaffold_pairs(recs)
    assert report.n_compounds_excluded_censored_required_isoform == 1
    # IKA never appears as a candidate member (only IKB is complete)
    for c in report.candidates:
        assert "IKA" not in (c.inchikey_a, c.inchikey_b)


def test_fully_measured_but_no_scaffold_partner_is_not_censoring_excluded() -> None:
    recs = _complete_compound("IKA", 8.0, 5.0, 5.0, 5.0)
    report = generate_exploratory_scaffold_pairs(recs)
    assert report.n_compounds_excluded_censored_required_isoform == 0
    assert report.candidates == ()


# ── magnitude reporting: descriptive only, no threshold applied ─────────────


def test_magnitude_over_sigma_reported_without_threshold_decision() -> None:
    recs = _complete_compound("IKA", 8.0, 5.0, 5.0, 5.0) + _complete_compound(
        "IKB", 5.0, 8.0, 5.0, 5.0
    )
    report = generate_exploratory_scaffold_pairs(recs)
    for c in report.candidates:
        # No sigma data available in this tiny synthetic corpus -> None,
        # never fabricated; and there is no boolean "passes_threshold" field
        # anywhere on the dataclass (verified structurally).
        assert not hasattr(c, "passes_threshold")
        assert not hasattr(c, "is_confirmed_switch")
        assert c.sigma_diff_basis in ("true_replicate", "cross_assay", "pooled", "unavailable")

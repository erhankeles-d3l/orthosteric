"""Tests for GDR-011 (accepted) Issue 2 — ATP-status extraction.

Exit criteria:
  (1) A single unambiguous numeric ATP concentration -> KNOWN.
  (2) Two or more distinct numeric candidates -> AMBIGUOUS, with NO
      first-match resolution (concentration_um stays None).
  (3) No numeric concentration (including radiolabel and Km references)
      -> UNKNOWN.
  (4) Two UNKNOWN results are never asserted equal by this module — it
      returns concentration_um=None for both, and callers must not treat
      that as a match (tested at the comparability layer, not here).
  (5) Extraction is deterministic and reproducible.
"""

from __future__ import annotations

from orthosteric.data.harmonization._atp_extraction import (
    ATP_EXTRACTION_RULE_VERSION,
    AtpStatus,
    extract_atp_status,
)

# ── KNOWN ─────────────────────────────────────────────────────────────────────


def test_known_single_um_value() -> None:
    r = extract_atp_status("Inhibition of PI3Kalpha in presence of 25 uM ATP")
    assert r.status == AtpStatus.KNOWN
    assert r.concentration_um == 25.0
    assert r.candidate_values_um == (25.0,)


def test_known_greek_mu() -> None:
    r = extract_atp_status("PI3K assay with 10 \u03bcM ATP added")
    assert r.status == AtpStatus.KNOWN
    assert r.concentration_um == 10.0


def test_known_millimolar_converted_to_um() -> None:
    r = extract_atp_status("Reaction initiated with 1 mM ATP")
    assert r.status == AtpStatus.KNOWN
    assert r.concentration_um == 1000.0


def test_known_nanomolar_converted_to_um() -> None:
    r = extract_atp_status("Assay run at 500 nM ATP")
    assert r.status == AtpStatus.KNOWN
    assert r.concentration_um == 0.5


def test_known_atp_n_pattern() -> None:
    r = extract_atp_status("Kinase reaction with ATP at 60 uM")
    assert r.status == AtpStatus.KNOWN
    assert r.concentration_um == 60.0


def test_known_repeated_same_value_not_ambiguous() -> None:
    """The SAME concentration stated twice is not ambiguity."""
    r = extract_atp_status("10 uM ATP was used; ATP 10 uM final concentration")
    assert r.status == AtpStatus.KNOWN
    assert r.concentration_um == 10.0


# ── AMBIGUOUS — no first-match resolution ────────────────────────────────────


def test_ambiguous_two_distinct_values_real_corpus_example() -> None:
    """Real A3 corpus example (GDR-011 evidence, failure mode 4): the
    reaction mixture states one ATP concentration for substrate context and
    a different one elsewhere in the same description."""
    desc = (
        "Scintillation Proximity Assay: the kinase reaction was conducted "
        "in a 384-well plate. The final reaction mixture consisted of "
        "20 uM PIP2, 20 uM ATP, 0.2 uCi [gamma-33P]ATP, diluted from a "
        "400 uM ATP stock solution."
    )
    r = extract_atp_status(desc)
    assert r.status == AtpStatus.AMBIGUOUS
    assert r.concentration_um is None  # GDR-011: never resolved by first match
    assert set(r.candidate_values_um) == {20.0, 400.0}


def test_ambiguous_um_and_mm_together() -> None:
    r = extract_atp_status("Assay at 10 uM ATP, control run at 1 mM ATP")
    assert r.status == AtpStatus.AMBIGUOUS
    assert r.concentration_um is None
    assert set(r.candidate_values_um) == {10.0, 1000.0}


def test_ambiguous_candidates_order_independent() -> None:
    """Swapping which value appears first must not change the outcome —
    this is the concrete guard against a first-match rule."""
    r_a = extract_atp_status("20 uM ATP ... 400 uM ATP")
    r_b = extract_atp_status("400 uM ATP ... 20 uM ATP")
    assert r_a.status == r_b.status == AtpStatus.AMBIGUOUS
    assert r_a.concentration_um is None
    assert r_b.concentration_um is None
    assert set(r_a.candidate_values_um) == set(r_b.candidate_values_um) == {20.0, 400.0}


# ── UNKNOWN ───────────────────────────────────────────────────────────────────


def test_unknown_no_atp_mention() -> None:
    r = extract_atp_status("Inhibition of PI3Kgamma by fluorescence polarization")
    assert r.status == AtpStatus.UNKNOWN
    assert r.concentration_um is None
    assert r.mentions_atp is False


def test_unknown_radiolabel_reference_no_concentration() -> None:
    """Real A3 corpus example: ATP appears only as a radiolabelled
    substrate, not as a stated condition (failure mode 2, 10,284 records)."""
    desc = (
        "Inhibition of recombinant PI3K p110delta using "
        "L-alpha-phosphatidylinositol as substrate and [gamma-33P]ATP "
        "after 60 mins by thin layer chromatography"
    )
    r = extract_atp_status(desc)
    assert r.status == AtpStatus.UNKNOWN
    assert r.concentration_um is None
    assert r.mentions_atp is True


def test_unknown_km_referenced() -> None:
    """Real A3 corpus example: ATP stated only relative to Km, no number
    (failure mode 1, 60 records)."""
    desc = (
        "Inhibition of PI3Kalpha using PIP2:3PS peptide as substrate "
        "preincubated for 15 mins followed by ATP addition at Km"
    )
    r = extract_atp_status(desc)
    assert r.status == AtpStatus.UNKNOWN
    assert r.concentration_um is None
    assert r.mentions_atp is True


def test_unknown_empty_description() -> None:
    r = extract_atp_status("")
    assert r.status == AtpStatus.UNKNOWN
    assert r.mentions_atp is False


def test_unknown_none_description() -> None:
    r = extract_atp_status(None)
    assert r.status == AtpStatus.UNKNOWN


# ── UNKNOWN != ABSENT / UNKNOWN != UNKNOWN (documentation-level guard) ───────


def test_two_unknowns_are_not_the_same_object_or_value() -> None:
    """GDR-011 (accepted): two UNKNOWN results must never be treated as a
    match by a caller.  This module makes that easy to respect: both have
    concentration_um=None, which is not a usable equality key, and neither
    result claims a shared identity."""
    r1 = extract_atp_status("Fluorescence assay, no ATP mentioned")
    r2 = extract_atp_status("Radioligand binding assay, no ATP mentioned")
    assert r1.status == r2.status == AtpStatus.UNKNOWN
    assert r1.concentration_um is None
    assert r2.concentration_um is None
    # Two None concentrations must not be usable as a comparability match key.
    assert (r1.concentration_um == r2.concentration_um) is True  # None == None in Python
    # -> which is exactly why callers must key comparability on `status`,
    #    never on `concentration_um` alone; see _comparability.py.


# ── Reproducibility ───────────────────────────────────────────────────────────


def test_extraction_deterministic() -> None:
    desc = "Inhibition of PI3Kbeta in presence of 2 uM ATP"
    r1 = extract_atp_status(desc)
    r2 = extract_atp_status(desc)
    assert r1 == r2


def test_rule_version_recorded() -> None:
    r = extract_atp_status("10 uM ATP")
    assert r.rule_version == ATP_EXTRACTION_RULE_VERSION

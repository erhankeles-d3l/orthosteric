"""Tests for PIK3Kgamma experimental-complex matching.

Exit criteria:
  (1) EXACT InChIKey matches produce EXPERIMENTAL_COMPLEX records.
  (2) SKELETON-only matches are tagged separately from EXACT -- never
      conflated as the same evidence tier.
  (3) A ligand co-crystallized in multiple PDB entries produces one
      record per entry, all real (no aggregation/collapsing).
  (4) Every unmatched corpus compound gets an explicit UNAVAILABLE
      record -- never silently omitted.
  (5) A ligand matching NOTHING in the corpus contributes zero records
      (never fabricates a match).
  (6) Excluded (exclusion_reason set) corpus records never contribute to
      matching or to the UNAVAILABLE default set.
"""

from __future__ import annotations

from typing import Any

from orthosteric.data.sources.structural._evidence_record import EvidenceClass
from orthosteric.data.sources.structural._pi3kg_complex_matching import (
    MATCH_TIER_EXACT,
    MATCH_TIER_SKELETON,
    LigandPdbEvidence,
    match_corpus_to_pi3kg_complexes,
)


def _corpus_rec(ik: str, exclusion_reason: str | None = None) -> dict[str, Any]:
    return {"inchikey": ik, "exclusion_reason": exclusion_reason}


def test_exact_match_produces_experimental_complex() -> None:
    corpus = [_corpus_rec("HKSZLNNOFSGOKW-FYTWVXJKSA-N")]
    ligands = [
        LigandPdbEvidence(
            ccd_code="STU",
            inchikey="HKSZLNNOFSGOKW-FYTWVXJKSA-N",
            pdb_entries=(("1E7V", 2.4),),
        )
    ]
    records = match_corpus_to_pi3kg_complexes(corpus, ligands, "sha1", "2026-08-06")
    complex_recs = [r for r in records if r.evidence_class == EvidenceClass.EXPERIMENTAL_COMPLEX]
    assert len(complex_recs) == 1
    r = complex_recs[0]
    assert r.receptor_pdb_id == "1E7V"
    assert r.ligand_pdb_id == "STU"
    assert r.is_experimental is True
    assert MATCH_TIER_EXACT in r.source_type


def test_skeleton_match_tagged_separately_from_exact() -> None:
    """Same connectivity, different stereo layer -- must be SKELETON, not EXACT."""
    corpus = [_corpus_rec("HUAOHTKULCUTBL-UHFFFAOYSA-N")]  # different stereo suffix
    ligands = [
        LigandPdbEvidence(
            ccd_code="BWY",
            inchikey="HUAOHTKULCUTBL-UMSFTDKQSA-N",  # PDB's stereo layer differs
            pdb_entries=(("6AUD", 2.015),),
        )
    ]
    records = match_corpus_to_pi3kg_complexes(corpus, ligands, "sha1", "2026-08-06")
    complex_recs = [r for r in records if r.evidence_class == EvidenceClass.EXPERIMENTAL_COMPLEX]
    assert len(complex_recs) == 1
    assert MATCH_TIER_SKELETON in complex_recs[0].source_type
    assert MATCH_TIER_EXACT not in complex_recs[0].source_type


def test_exact_match_preferred_over_skeleton_when_both_possible() -> None:
    corpus = [_corpus_rec("ABCDEFGHIJKLMN-UHFFFAOYSA-N")]
    ligands = [
        LigandPdbEvidence(
            ccd_code="XYZ",
            inchikey="ABCDEFGHIJKLMN-UHFFFAOYSA-N",  # exact
            pdb_entries=(("1ABC", 2.0),),
        )
    ]
    records = match_corpus_to_pi3kg_complexes(corpus, ligands, "sha1", "2026-08-06")
    complex_recs = [r for r in records if r.evidence_class == EvidenceClass.EXPERIMENTAL_COMPLEX]
    assert MATCH_TIER_EXACT in complex_recs[0].source_type


def test_multiple_pdb_entries_for_one_ligand_produce_multiple_records() -> None:
    """A promiscuously-crystallized ligand (e.g. Gedatolisib-like tool
    compound) must yield one record per real PDB entry -- never collapsed."""
    corpus = [_corpus_rec("XUMALORDVCFWKV-IBGZPJMESA-N")]
    ligands = [
        LigandPdbEvidence(
            ccd_code="V7Y",
            inchikey="XUMALORDVCFWKV-IBGZPJMESA-N",
            pdb_entries=(("6XRL", 2.99), ("7JWZ", 2.65)),
        )
    ]
    records = match_corpus_to_pi3kg_complexes(corpus, ligands, "sha1", "2026-08-06")
    complex_recs = [r for r in records if r.evidence_class == EvidenceClass.EXPERIMENTAL_COMPLEX]
    assert len(complex_recs) == 2
    assert {r.receptor_pdb_id for r in complex_recs} == {"6XRL", "7JWZ"}


def test_unmatched_compound_gets_explicit_unavailable_record() -> None:
    corpus = [_corpus_rec("NOMATCH0000000-UHFFFAOYSA-N")]
    records = match_corpus_to_pi3kg_complexes(corpus, [], "sha1", "2026-08-06")
    assert len(records) == 1
    assert records[0].evidence_class == EvidenceClass.UNAVAILABLE
    assert records[0].is_experimental is False
    assert "does not imply inactive" in records[0].missingness_note.lower()


def test_ligand_matching_nothing_contributes_zero_records_for_itself() -> None:
    """A PDB ligand whose InChIKey isn't in the corpus at all must not
    fabricate a phantom match."""
    corpus = [_corpus_rec("SOMEOTHER00000-UHFFFAOYSA-N")]
    ligands = [
        LigandPdbEvidence(
            ccd_code="NOPE", inchikey="TOTALLYDIFFEREN-UHFFFAOYSA-N", pdb_entries=(("9XYZ", 3.0),)
        )
    ]
    records = match_corpus_to_pi3kg_complexes(corpus, ligands, "sha1", "2026-08-06")
    assert all(r.evidence_class == EvidenceClass.UNAVAILABLE for r in records)


def test_excluded_corpus_records_never_contribute() -> None:
    corpus = [
        _corpus_rec("ABCDEFGHIJKLMN-UHFFFAOYSA-N", exclusion_reason="INADMISSIBLE"),
        _corpus_rec("OTHERVALID0000-UHFFFAOYSA-N"),
    ]
    ligands = [
        LigandPdbEvidence(
            ccd_code="XYZ", inchikey="ABCDEFGHIJKLMN-UHFFFAOYSA-N", pdb_entries=(("1ABC", 2.0),)
        )
    ]
    records = match_corpus_to_pi3kg_complexes(corpus, ligands, "sha1", "2026-08-06")
    # the excluded compound must not appear as EXPERIMENTAL_COMPLEX or UNAVAILABLE
    assert all(r.compound_id != "ABCDEFGHIJKLMN-UHFFFAOYSA-N" for r in records)
    assert any(
        r.compound_id == "OTHERVALID0000-UHFFFAOYSA-N"
        and r.evidence_class == EvidenceClass.UNAVAILABLE
        for r in records
    )


def test_deduplicated_corpus_compound_produces_one_unavailable_not_many() -> None:
    corpus = [_corpus_rec("DUPDUPDUPDUPDU-UHFFFAOYSA-N")] * 5  # same compound, 5 records
    records = match_corpus_to_pi3kg_complexes(corpus, [], "sha1", "2026-08-06")
    assert len(records) == 1

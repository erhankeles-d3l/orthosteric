"""Tests for sequence-based residue correspondence
(pocket._sequence_correspondence).

Exit criteria:
  (1) Identical sequences produce a 1:1 correspondence (every reference
      residue maps to the same-numbered target residue).
  (2) A single-residue insertion in the target correctly shifts downstream
      correspondence rather than misaligning everything after it.
  (3) A deletion in the target correctly leaves the corresponding
      reference residue with target_resnum=None (gap), never a fabricated
      guess.
  (4) Alignment is deterministic (same inputs -> identical output).
  (5) The correspondence table's lookup() is correct in both directions
      of presence/absence.
  (6) Every record is tagged with the provisional-method policy string,
      never silently presented as the governed SCI1-003 structural
      correspondence.
"""

from __future__ import annotations

from orthosteric.pocket._sequence_correspondence import (
    CORRESPONDENCE_POLICY_ID,
    CorrespondenceTable,
    align_sequences,
)


def _seq(one_letter: str, start: int = 1) -> list[tuple[int, str, str]]:
    return [(start + i, "A", c) for i, c in enumerate(one_letter)]


def test_identical_sequences_give_1to1_correspondence() -> None:
    ref = _seq("MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ")
    tgt = _seq("MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ")
    records = align_sequences(ref, tgt, "PI3Kalpha", "PI3Kbeta")
    assert all(r.target_resnum == r.reference_resnum for r in records)
    assert all(r.method == CORRESPONDENCE_POLICY_ID for r in records)


def test_single_insertion_shifts_downstream_correspondence() -> None:
    ref = _seq("MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ")
    # insert an extra residue after position 10 in the target
    tgt_str = "MKTAYIAKQR" + "W" + "QISFVKSHFSRQLEERLGLIEVQ"
    tgt = _seq(tgt_str)
    records = align_sequences(ref, tgt, "PI3Kalpha", "PI3Kbeta")
    by_ref = {r.reference_resnum: r.target_resnum for r in records}
    # residues before the insertion point are unaffected
    assert by_ref[1] == 1
    assert by_ref[10] == 10
    # residues after the insertion point are shifted by +1 in the target
    assert by_ref[11] == 12
    assert by_ref[20] == 21


def test_deletion_produces_gap_for_corresponding_reference_residue() -> None:
    ref_str = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ"
    ref = _seq(ref_str)
    # delete residue at reference position 11 ('Q') from the target
    tgt_str = ref_str[:10] + ref_str[11:]
    tgt = _seq(tgt_str)
    records = align_sequences(ref, tgt, "PI3Kalpha", "PI3Kbeta")
    by_ref = {r.reference_resnum: r.target_resnum for r in records}
    # exactly one reference residue must map to a gap (None) -- the deleted one
    assert sum(1 for v in by_ref.values() if v is None) == 1


def test_alignment_is_deterministic() -> None:
    ref = _seq("MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ")
    tgt = _seq("MKTAYIAKKRQISFVKSHFSRQLEERAGLIEVQ")  # a couple of substitutions
    r1 = align_sequences(ref, tgt, "PI3Kalpha", "PI3Kbeta")
    r2 = align_sequences(ref, tgt, "PI3Kalpha", "PI3Kbeta")
    assert [rec.to_dict() for rec in r1] == [rec.to_dict() for rec in r2]


def test_correspondence_table_lookup_present_and_absent() -> None:
    ref = _seq("MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ")
    tgt = _seq("MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ")
    records = align_sequences(ref, tgt, "PI3Kalpha", "PI3Kbeta")
    table = CorrespondenceTable(
        reference_isoform="PI3Kalpha", by_target_isoform={"PI3Kbeta": records}
    )
    assert table.lookup("PI3Kbeta", 5) == 5
    assert table.lookup("PI3Kgamma", 5) is None  # isoform not in table
    assert table.lookup("PI3Kbeta", 9999) is None  # residue not in table


def test_table_content_sha256_deterministic() -> None:
    ref = _seq("MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ")
    tgt = _seq("MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ")
    records = align_sequences(ref, tgt, "PI3Kalpha", "PI3Kbeta")
    t1 = CorrespondenceTable(reference_isoform="PI3Kalpha", by_target_isoform={"PI3Kbeta": records})
    t2 = CorrespondenceTable(reference_isoform="PI3Kalpha", by_target_isoform={"PI3Kbeta": records})
    assert t1.content_sha256() == t2.content_sha256()

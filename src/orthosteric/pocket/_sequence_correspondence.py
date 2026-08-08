"""Bounded, sequence-based cross-isoform residue correspondence.

For the interaction-motif fingerprints workstream.

IMPORTANT scope distinction (read before using this module)
-----------------------------------------------------------------------
`orthosteric.pocket._residue_mapping` (SCI1-003) documents that the
Constitution-governed cross-isoform correspondence requires
STRUCTURE-BASED alignment ("structure-based alignment, not sequence-only"
-- Constitution SS2.1), with the three named anchor positions
(alpha-859, Trp780, Met772) "explicitly recorded and manually verified."
That governed method is NOT implemented here, and this module does NOT
claim to satisfy it.

This module implements a SEPARATE, explicitly bounded, SEQUENCE-based
correspondence -- a real, deterministic, testable pairwise sequence
alignment (Biopython PairwiseAligner, BLOSUM62, global alignment) --
adopted per this session's explicit instruction: "If SCI1-003 remains
incomplete, implement the minimum deterministic correspondence layer
necessary for this workstream... Do not stop merely because SCI1-003 is
labeled a prior gap." It is a bounded ENGINEERING CHOICE for THIS
workstream's cross-isoform interaction comparison, not a fulfillment of
SCI1-003, and every correspondence record produced here is tagged
`method="sequence_alignment_v1_provisional"` so it can never be silently
mistaken for the governed structural correspondence if that is sealed
later.

Algorithm (documented, deterministic, not tuned on any experimental label)
-----------------------------------------------------------------------------
Biopython Bio.Align.PairwiseAligner, global alignment mode, BLOSUM62
substitution matrix, open_gap_score=-10, extend_gap_score=-0.5 (standard
BLOSUM62 defaults widely used for global protein alignment; not chosen to
optimize any downstream metric). PI3Kalpha's sequence (from the 8EXL
receptor) is the reference; beta/gamma/delta are each aligned to it
independently. A residue in a non-reference isoform corresponds to the
alpha residue occupying the same alignment column, when neither side is
a gap.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

CORRESPONDENCE_POLICY_ID = "sequence_alignment_v1_provisional"

_THREE_TO_ONE = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}


def extract_sequence_from_pdb(
    pdb_path: Path, chain_id: str | None = None
) -> list[tuple[int, str, str]]:
    """Extract the (residue_number, chain_id, one_letter_code) sequence.

    Uses the first protein chain (or `chain_id` if given) from a PDB
    file, CA atoms only. Real structural data, never fabricated -- any
    non-standard residue is simply skipped (not guessed).
    """
    seen: dict[tuple[str, int], str] = {}
    order: list[tuple[str, int]] = []
    for line in pdb_path.read_text().splitlines():
        if not line.startswith("ATOM"):
            continue
        atom_name = line[12:16].strip()
        if atom_name != "CA":
            continue
        this_chain = line[21].strip() or "A"
        if chain_id is not None and this_chain != chain_id:
            continue
        resname = line[17:20].strip()
        if resname not in _THREE_TO_ONE:
            continue
        resnum = int(line[22:26])
        key = (this_chain, resnum)
        if key not in seen:
            seen[key] = _THREE_TO_ONE[resname]
            order.append(key)
    return [(resnum, chain, seen[(chain, resnum)]) for chain, resnum in order]


@dataclass(frozen=True, slots=True)
class CorrespondenceRecord:
    """One residue-level correspondence assignment, sequence-alignment-derived."""

    reference_isoform: str
    reference_resnum: int
    target_isoform: str
    target_resnum: int | None  # None if this reference position aligns to a gap
    method: str = CORRESPONDENCE_POLICY_ID

    def to_dict(self) -> dict[str, object]:
        return {
            "reference_isoform": self.reference_isoform,
            "reference_resnum": self.reference_resnum,
            "target_isoform": self.target_isoform,
            "target_resnum": self.target_resnum,
            "method": self.method,
        }


def align_sequences(
    reference_seq: list[tuple[int, str, str]],
    target_seq: list[tuple[int, str, str]],
    reference_isoform: str,
    target_isoform: str,
) -> list[CorrespondenceRecord]:
    """Global pairwise alignment (BLOSUM62).

    Returns one CorrespondenceRecord per reference residue.
    """
    from Bio.Align import PairwiseAligner, substitution_matrices  # noqa: PLC0415

    aligner = PairwiseAligner()
    aligner.substitution_matrix = substitution_matrices.load("BLOSUM62")
    aligner.open_gap_score = -10
    aligner.extend_gap_score = -0.5
    aligner.mode = "global"

    ref_str = "".join(r[2] for r in reference_seq)
    tgt_str = "".join(r[2] for r in target_seq)
    alignment = aligner.align(ref_str, tgt_str)[
        0
    ]  # best-scoring alignment; deterministic given fixed inputs

    ref_aligned, tgt_aligned = alignment[0], alignment[1]
    records: list[CorrespondenceRecord] = []
    ref_i, tgt_i = 0, 0
    for ref_char, tgt_char in zip(ref_aligned, tgt_aligned, strict=True):
        ref_resnum = reference_seq[ref_i][0] if ref_char != "-" else None
        tgt_resnum = target_seq[tgt_i][0] if tgt_char != "-" else None
        if ref_resnum is not None:
            records.append(
                CorrespondenceRecord(
                    reference_isoform=reference_isoform,
                    reference_resnum=ref_resnum,
                    target_isoform=target_isoform,
                    target_resnum=tgt_resnum,
                )
            )
        if ref_char != "-":
            ref_i += 1
        if tgt_char != "-":
            tgt_i += 1
    return records


@dataclass(frozen=True, slots=True)
class CorrespondenceTable:
    """All reference->target correspondences for the four-isoform panel.

    Keyed by target isoform.
    """

    reference_isoform: str
    by_target_isoform: dict[str, list[CorrespondenceRecord]]

    def lookup(self, target_isoform: str, reference_resnum: int) -> int | None:
        for rec in self.by_target_isoform.get(target_isoform, []):
            if rec.reference_resnum == reference_resnum:
                return rec.target_resnum
        return None

    def content_sha256(self) -> str:
        payload = {
            iso: [r.to_dict() for r in recs] for iso, recs in sorted(self.by_target_isoform.items())
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "reference_isoform": self.reference_isoform,
            "policy": CORRESPONDENCE_POLICY_ID,
            "by_target_isoform": {
                iso: [r.to_dict() for r in recs] for iso, recs in self.by_target_isoform.items()
            },
            "content_sha256": self.content_sha256(),
        }


def build_correspondence_table(
    receptor_pdb_paths: dict[str, Path], reference_isoform: str = "PI3Kalpha"
) -> CorrespondenceTable:
    """Build the full four-isoform sequence-correspondence table.

    `receptor_pdb_paths` maps isoform name -> PDB path (the exact same
    four-receptor panel already governed for this workstream:
    8EXL/AF-P42338/6AUD/6PYR).
    """
    sequences = {iso: extract_sequence_from_pdb(path) for iso, path in receptor_pdb_paths.items()}
    ref_seq = sequences[reference_isoform]
    by_target: dict[str, list[CorrespondenceRecord]] = {}
    for iso, seq in sequences.items():
        if iso == reference_isoform:
            continue
        by_target[iso] = align_sequences(ref_seq, seq, reference_isoform, iso)
    return CorrespondenceTable(reference_isoform=reference_isoform, by_target_isoform=by_target)

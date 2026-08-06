"""Match Activity Snapshot corpus compounds to real experimental PIK3Kgamma
PDB co-crystal structures via InChIKey.

Objective: Stage D (docs/governance/STAGE_D_STRUCTURAL_EVIDENCE_STATE.md),
first completed compound-level cross-reference. All ligand identities and
PDB IDs below are REAL, fetched from the RCSB PDB REST API
(analysis/fetch_pik3cg_pdb_evidence.py); nothing here is fabricated,
imputed, or inferred.

Matching policy
-----------------
Two match tiers, both retained explicitly (never conflated):
  - EXACT: ligand InChIKey (full, including stereo layer) equals a corpus
    compound's InChIKey exactly.
  - SKELETON: only the connectivity layer (first 14 characters of the
    InChIKey) matches; the stereo/tautomer layer differs or is absent from
    the PDB ligand's recorded stereochemistry. Reported as a SEPARATE,
    weaker tier -- a skeleton match is NOT the same evidence as an exact
    match and downstream consumers must not merge them silently.

Every corpus compound NOT found in either tier defaults to
`StructuralEvidenceRecord.unavailable()` (Level 6) -- the vast majority
of the corpus, and honestly so: this module discovers real PDB coverage
for PIK3Kgamma only, and only for compounds sharing an identity with one
of 102 distinct co-crystallized ligands across 107 PIK3Kgamma PDB entries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orthosteric.data.sources.structural._evidence_record import (
    EvidenceClass,
    PoseStatus,
    StructuralEvidenceRecord,
)

POLICY_ID = "stage_d_pi3kg_experimental_complex_matching_v1"

#: StrEnum-like literal values for match tier, kept as plain strings to
#: avoid a fourth tiny enum module; documented here as the source of truth.
MATCH_TIER_EXACT = "exact_inchikey"
MATCH_TIER_SKELETON = "skeleton_inchikey"


@dataclass(frozen=True, slots=True)
class LigandPdbEvidence:
    """One real, fetched PIK3Kgamma-ligand-complex fact.

    Attributes:
        ccd_code:    PDB Chemical Component Dictionary code (e.g. "STU").
        inchikey:    InChIKey computed by RCSB for this ligand.
        pdb_entries: (pdb_id, resolution_angstrom) pairs where this ligand
                     was co-crystallized with PIK3Kgamma.
    """

    ccd_code: str
    inchikey: str
    pdb_entries: tuple[tuple[str, float | None], ...]


def match_corpus_to_pi3kg_complexes(
    corpus_records: list[dict[str, Any]],
    ligand_evidence: list[LigandPdbEvidence],
    activity_snapshot_sha: str,
    retrieval_date: str,
) -> list[StructuralEvidenceRecord]:
    """Produce one StructuralEvidenceRecord per unique corpus compound.

    Matched compounds (EXACT or SKELETON tier) get EXPERIMENTAL_COMPLEX
    records, one per matching PDB entry (a compound co-crystallized in
    multiple structures gets multiple records, all real). Every other
    compound in the corpus gets an explicit UNAVAILABLE record -- never
    silently omitted.
    """
    corpus_iks = {
        r["inchikey"] for r in corpus_records if r.get("inchikey") and not r.get("exclusion_reason")
    }
    skeleton_index: dict[str, str] = {ik[:14]: ik for ik in corpus_iks}

    records: list[StructuralEvidenceRecord] = []
    matched_corpus_iks: set[str] = set()

    for lig in ligand_evidence:
        matched_ik: str | None = None
        tier = None
        if lig.inchikey in corpus_iks:
            matched_ik, tier = lig.inchikey, MATCH_TIER_EXACT
        elif lig.inchikey[:14] in skeleton_index:
            matched_ik, tier = skeleton_index[lig.inchikey[:14]], MATCH_TIER_SKELETON

        if matched_ik is None:
            continue
        matched_corpus_iks.add(matched_ik)
        for pdb_id, resolution in lig.pdb_entries:
            records.append(
                StructuralEvidenceRecord(
                    compound_id=matched_ik,
                    inchikey=matched_ik,
                    isoform="PI3Kgamma",
                    evidence_class=EvidenceClass.EXPERIMENTAL_COMPLEX,
                    receptor_pdb_id=pdb_id,
                    ligand_pdb_id=lig.ccd_code,
                    is_experimental=True,
                    is_alphafold=False,
                    is_docked=False,
                    pose_status=PoseStatus.OBSERVED,
                    source_type=f"rcsb_pdb_{tier}",
                    source_identifier=f"ccd={lig.ccd_code};resolution={resolution}",
                    retrieval_date=retrieval_date,
                    activity_snapshot_sha=activity_snapshot_sha,
                )
            )

    for ik in sorted(corpus_iks - matched_corpus_iks):
        records.append(
            StructuralEvidenceRecord.unavailable(
                compound_id=ik,
                inchikey=ik,
                isoform="PI3Kgamma",
                activity_snapshot_sha=activity_snapshot_sha,
                source_type="rcsb_pdb_no_match",
                retrieval_date=retrieval_date,
                reason=(
                    "no co-crystallized ligand among 102 distinct PIK3Kgamma "
                    "PDB ligands (107 entries) shares this compound's InChIKey"
                ),
            )
        )

    return records

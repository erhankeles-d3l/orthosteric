"""Pocket-level scalar descriptors for orthosteric ATP sites.

Authority: ADR-0010 [Architectural]; SCI1-006 (part 1 of 2).
Constitution sections served: §2.1, §4.2, §4.6.

Produces a compact, structured summary of an orthosteric pocket from its
residue composition, interaction evidence, and correspondence coverage.
Suitable for per-isoform feature tables and for the comparative layer.

Scientific rule classification
  RULE_AVAILABLE:  Standard residue polarity and charge classification at pH
    7.4. Asp/Glu anionic, Arg/Lys cationic, His treated as neutral (its pKa
    is near 6; at pH 7.4 predominantly neutral), Ser/Thr/Asn/Gln/Tyr polar
    neutral. These are standard biochemistry, not project-specific choices.
  RULE_AVAILABLE:  Hydrophobic residue set from Constitution §0.3 and
    SCI1-004 (_HYDROPHOBIC_RESIDUES). Using the same set avoids divergence.
  RULE_AVAILABLE:  Aromatic residues (PHE/TYR/TRP/HIS) from SCI1-004.
  RULE_AVAILABLE:  Residue counts are pure integer statistics; no threshold.
  RULE_MISSING:    Any threshold for classifying a pocket as "hydrophobic"
    vs "polar." Counts are reported; interpretation belongs to eval/.
  RULE_MISSING:    Flexibility indicators beyond raw rotamer-state counts.
    True flexibility requires MD or ensemble sampling (Phase 3).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from orthosteric.features._interaction_fingerprint import (
    InteractionFingerprint,
    InteractionStatus,
    InteractionType,
)
from orthosteric.pocket._pocket_definition import PocketResidueSet
from orthosteric.pocket._pocket_geometry import PocketGeometry
from orthosteric.pocket._residue_mapping import ResidueCorrespondenceTable
from orthosteric.pocket._structure_record import StructureRecord

__all__ = [
    "POCKET_DESCRIPTOR_ALGORITHM_VERSION",
    "PocketDescriptor",
    "build_pocket_descriptor",
]

POCKET_DESCRIPTOR_ALGORITHM_VERSION = "pocket_descriptor_v1_sci1006"

# Residue chemistry classification at pH 7.4 (RULE_AVAILABLE -- standard biochemistry)
_CHARGED_POS: frozenset[str] = frozenset({"ARG", "LYS"})  # always cationic
_CHARGED_NEG: frozenset[str] = frozenset({"ASP", "GLU"})  # always anionic
_POLAR_NEUTRAL: frozenset[str] = frozenset(  # H-bond capable, neutral
    {"SER", "THR", "ASN", "GLN", "TYR", "CYS"}
)
_HYDROPHOBIC: frozenset[str] = frozenset(  # from SCI1-004
    {"ALA", "VAL", "LEU", "ILE", "MET", "PHE", "TRP", "PRO"}
)
_AROMATIC: frozenset[str] = frozenset({"PHE", "TYR", "TRP", "HIS"})
# HIS is pH-sensitive; counted as aromatic for geometric purposes


@dataclass(frozen=True, slots=True)
class PocketDescriptor:
    """Compact scalar summary of one orthosteric pocket.

    All counts are integers; no thresholds applied. Interpretation belongs
    to the eval/ and interpretation/ layers.

    Attributes (residue composition)
    ----------------------------------
    n_residues:         Total pocket residues in the set.
    n_charged_pos:      ARG + LYS residues.
    n_charged_neg:      ASP + GLU residues.
    n_polar_neutral:    SER/THR/ASN/GLN/TYR/CYS residues.
    n_hydrophobic:      ALA/VAL/LEU/ILE/MET/PHE/TRP/PRO residues.
    n_aromatic:         PHE/TYR/TRP/HIS residues.
    n_glycine:          GLY residues (special: smallest sidechain).
    n_other:            Residues not in any of the above categories.

    Attributes (anchor coverage)
    ----------------------------
    n_anchor_positions_mapped: How many of the 3 Constitution anchor
        positions (alpha-859, Trp780, Met772) have a correspondence
        assignment in the supplied table.
    n_residues_with_canonical: Count of pocket residues with a non-None
        canonical position.
    fraction_residues_with_canonical: n_residues_with_canonical / n_residues.

    Attributes (interaction counts from SCI1-004 fingerprint, if supplied)
    -----------------------------------------------------------------------
    n_hbond_evidence: Hydrogen bond evidence records (any status except
        NOT_APPLICABLE). None if no fingerprint provided.
    n_hbond_observed_or_candidate: Records with status OBSERVED or
        RULE_MISSING (geometry present). None if no fingerprint.
    n_hydrophobic_evidence: Hydrophobic contact evidence records.
    n_salt_bridge_evidence: Salt bridge evidence records.

    Attributes (geometry, if supplied)
    ------------------------------------
    volume_angstrom3: From SCI1-002 PocketGeometry. None if not provided.

    Metadata
    --------
    isoform:              Target isoform.
    structure_record_id:  Source structure.
    algorithm_version:    Pinned version string.
    correspondence_table_version: From SCI1-003 table if provided.
    """

    n_residues: int
    n_charged_pos: int
    n_charged_neg: int
    n_polar_neutral: int
    n_hydrophobic: int
    n_aromatic: int
    n_glycine: int
    n_other: int
    n_anchor_positions_mapped: int
    n_residues_with_canonical: int
    fraction_residues_with_canonical: float
    n_hbond_evidence: int | None
    n_hbond_observed_or_candidate: int | None
    n_hydrophobic_evidence: int | None
    n_salt_bridge_evidence: int | None
    volume_angstrom3: float | None
    isoform: str
    structure_record_id: str
    algorithm_version: str
    correspondence_table_version: str | None

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "algorithm_version": self.algorithm_version,
            "correspondence_table_version": self.correspondence_table_version,
            "fraction_residues_with_canonical": self.fraction_residues_with_canonical,
            "isoform": self.isoform,
            "n_anchor_positions_mapped": self.n_anchor_positions_mapped,
            "n_aromatic": self.n_aromatic,
            "n_charged_neg": self.n_charged_neg,
            "n_charged_pos": self.n_charged_pos,
            "n_glycine": self.n_glycine,
            "n_hbond_evidence": self.n_hbond_evidence,
            "n_hbond_observed_or_candidate": self.n_hbond_observed_or_candidate,
            "n_hydrophobic": self.n_hydrophobic,
            "n_hydrophobic_evidence": self.n_hydrophobic_evidence,
            "n_other": self.n_other,
            "n_polar_neutral": self.n_polar_neutral,
            "n_residues": self.n_residues,
            "n_residues_with_canonical": self.n_residues_with_canonical,
            "n_salt_bridge_evidence": self.n_salt_bridge_evidence,
            "structure_record_id": self.structure_record_id,
            "volume_angstrom3": self.volume_angstrom3,
        }

    def content_sha256(self) -> str:
        payload = json.dumps(
            self.to_canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Anchor positions (Constitution §0.3 / §2.1): alpha-859, Trp780, Met772
_ANCHOR_CANONICAL_POSITIONS: frozenset[int] = frozenset({859, 780, 772})


def build_pocket_descriptor(  # noqa: PLR0912,PLR0913,PLR0917
    structure_record: StructureRecord,
    pocket_residue_set: PocketResidueSet,
    isoform: str,
    correspondence_table: ResidueCorrespondenceTable | None = None,
    interaction_fingerprint: InteractionFingerprint | None = None,
    pocket_geometry: PocketGeometry | None = None,
) -> PocketDescriptor:
    """Build a scalar pocket descriptor from available structural evidence.

    All inputs after `pocket_residue_set` are optional; fields that require
    a missing input are set to None. This allows incremental population as
    more structural evidence becomes available.
    """
    rec_id = structure_record.record_id
    ct_version = correspondence_table.table_version if correspondence_table else None

    # Residue composition
    n_cp = n_cn = n_pn = n_hp = n_ar = n_gly = n_other = 0
    n_with_canon = 0
    n_anchors = 0

    for pr in pocket_residue_set.residues:
        rn = pr.residue.residue_name.upper()
        if rn in _CHARGED_POS:
            n_cp += 1
        elif rn in _CHARGED_NEG:
            n_cn += 1
        elif rn in _POLAR_NEUTRAL:
            n_pn += 1
        elif rn in _HYDROPHOBIC:
            n_hp += 1
        elif rn == "GLY":
            n_gly += 1
        else:
            n_other += 1
        # Aromatic (can overlap with hydrophobic/polar; counted separately)
        if rn in _AROMATIC:
            n_ar += 1
        # Canonical position
        if correspondence_table is not None:
            rid = pr.residue.residue_id()
            assignment = correspondence_table.get_canonical_position(rid)
            if assignment is not None and assignment.canonical_position is not None:
                n_with_canon += 1
                if assignment.canonical_position in _ANCHOR_CANONICAL_POSITIONS:
                    n_anchors += 1

    n_total = len(pocket_residue_set.residues)
    frac_canon = round(n_with_canon / n_total, 4) if n_total > 0 else 0.0

    # Interaction counts (from SCI1-004 fingerprint)
    n_hb = n_hb_obs = n_hp_ev = n_sb = None
    if interaction_fingerprint is not None:
        _na = InteractionStatus.NOT_APPLICABLE
        hb_ev = [
            e
            for e in interaction_fingerprint.evidence
            if e.interaction_type == InteractionType.HYDROGEN_BOND and e.status != _na
        ]
        n_hb = len(hb_ev)
        n_hb_obs = sum(
            1
            for e in hb_ev
            if e.status in (InteractionStatus.OBSERVED, InteractionStatus.RULE_MISSING)
        )
        n_hp_ev = sum(
            1
            for e in interaction_fingerprint.evidence
            if e.interaction_type == InteractionType.HYDROPHOBIC and e.status != _na
        )
        n_sb = sum(
            1
            for e in interaction_fingerprint.evidence
            if e.interaction_type == InteractionType.SALT_BRIDGE and e.status != _na
        )

    # Volume from SCI1-002
    vol = None
    if pocket_geometry is not None:
        vol = pocket_geometry.volume_angstrom3

    return PocketDescriptor(
        n_residues=n_total,
        n_charged_pos=n_cp,
        n_charged_neg=n_cn,
        n_polar_neutral=n_pn,
        n_hydrophobic=n_hp,
        n_aromatic=n_ar,
        n_glycine=n_gly,
        n_other=n_other,
        n_anchor_positions_mapped=n_anchors,
        n_residues_with_canonical=n_with_canon,
        fraction_residues_with_canonical=frac_canon,
        n_hbond_evidence=n_hb,
        n_hbond_observed_or_candidate=n_hb_obs,
        n_hydrophobic_evidence=n_hp_ev,
        n_salt_bridge_evidence=n_sb,
        volume_angstrom3=vol,
        isoform=isoform,
        structure_record_id=rec_id,
        algorithm_version=POCKET_DESCRIPTOR_ALGORITHM_VERSION,
        correspondence_table_version=ct_version,
    )

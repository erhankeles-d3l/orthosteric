"""Multi-isoform comparative feature set aligned by canonical residue position.

Authority: ADR-0010 [Architectural]; SCI1-006 (part 2 of 2).
Constitution sections served: §4.1, §4.2 (comparative representation),
  §4.6 (Path A: correspondence-free input interface).

Scientific mandate
------------------
Build a JOINT representation for one compound across all four Class I PI3K
isoforms, aligned by canonical residue position (from SCI1-003). This is
the primary comparative evidence structure that the learning layer (SCI-2)
will consume.

Constitution §4.2 constraint: "Four accurate independent per-isoform
predictors do not satisfy this." The ComparativeFeatureSet is not four
separate per-isoform vectors. It is a single structure whose feature at
each canonical position encodes the interaction evidence across ALL four
isoforms simultaneously. The comparative dimension is expressed in the
structure, not implicit in concatenation.

Interaction presence vocabulary
--------------------------------
OBSERVED:       classified as OBSERVED in the fingerprint.
CANDIDATE:      geometry present but threshold not governed (RULE_MISSING).
ABSENT:         geometry present; below threshold (ABSENT status).
UNAVAILABLE:    ligand/structure unavailable; cannot say absent.
NOT_APPLICABLE: wrong chemistry at this site.

The distinction between ABSENT and UNAVAILABLE is critical (Constitution
§4.2 item 5: the model must be able to output Indeterminate). In the
comparative vector, UNAVAILABLE does not count as negative evidence.

Feature vector encoding
------------------------
For each (canonical_position, interaction_type) pair present in any
supplied fingerprint, and for each isoform, the presence is encoded as:
  0 = UNAVAILABLE / NOT_APPLICABLE (no information)
  1 = ABSENT                        (negative evidence)
  2 = CANDIDATE                     (positive, unclassified)
  3 = OBSERVED                      (positive, classified)

Differential flags (one per canonical_position):
  alpha_unique = 1 if alpha has OBSERVED/CANDIDATE and all others <= ABSENT
  any_differential = 1 if any two isoforms differ at this position

All positions are sorted by canonical_position for determinism.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import IntEnum, StrEnum

from orthosteric.features._interaction_fingerprint import (
    ComparativeFingerprint,
    InteractionFingerprint,
    InteractionStatus,
    InteractionType,
)

__all__ = [
    "COMPARATIVE_FEATURE_ALGORITHM_VERSION",
    "ComparativeFeatureSet",
    "InteractionPresence",
    "PositionProfile",
    "build_comparative_feature_set",
]

COMPARATIVE_FEATURE_ALGORITHM_VERSION = "comparative_feature_v1_sci1006"


class InteractionPresence(IntEnum):
    """Ordinal encoding of interaction evidence at one (position, type, isoform) cell."""

    UNAVAILABLE = 0  # no structural information; NEVER treated as absent
    ABSENT = 1  # structure available; interaction not present
    CANDIDATE = 2  # geometry present; threshold not governed
    OBSERVED = 3  # classified as observed

    @classmethod
    def from_status(cls, status: InteractionStatus) -> InteractionPresence:
        _map = {
            InteractionStatus.OBSERVED: cls.OBSERVED,
            InteractionStatus.RULE_MISSING: cls.CANDIDATE,
            InteractionStatus.ABSENT: cls.ABSENT,
            InteractionStatus.UNAVAILABLE: cls.UNAVAILABLE,
            InteractionStatus.NOT_APPLICABLE: cls.UNAVAILABLE,
        }
        return _map[status]


class DifferentialFlag(StrEnum):
    """Whether a canonical position shows isoform-differential interaction evidence."""

    CONSERVED = "conserved"  # same presence in all covered isoforms
    DIFFERENTIAL = "differential"  # at least two isoforms differ
    UNCOVERED = "uncovered"  # all isoforms have UNAVAILABLE at this position


@dataclass(frozen=True, slots=True)
class PositionProfile:
    """Interaction evidence at one canonical position across all queried isoforms.

    Attributes:
        canonical_position: The Constitution-anchored canonical residue number.
        isoforms:           Sorted isoform names.
        per_isoform:        (isoform, InteractionPresence) pairs, one per
                            interaction type, sorted by (isoform, type).
        differential_flag:  CONSERVED / DIFFERENTIAL / UNCOVERED.
        alpha_unique:       True iff PI3Kalpha has OBSERVED/CANDIDATE and all
                            other covered isoforms have ABSENT/UNAVAILABLE.
                            False when PI3Kalpha not in isoforms.
        n_isoforms_with_evidence: Count of isoforms with presence >= ABSENT
                            (i.e., structure available regardless of sign).
    """

    canonical_position: int
    isoforms: tuple[str, ...]
    per_isoform: tuple[tuple[str, str, int], ...]  # (isoform, itype_value, presence_int)
    differential_flag: DifferentialFlag
    alpha_unique: bool
    n_isoforms_with_evidence: int

    def get_presence(self, isoform: str, itype: InteractionType) -> InteractionPresence:
        for iso, it, pres in self.per_isoform:
            if iso == isoform and it == itype.value:
                return InteractionPresence(pres)
        return InteractionPresence.UNAVAILABLE

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "alpha_unique": self.alpha_unique,
            "canonical_position": self.canonical_position,
            "differential_flag": self.differential_flag.value,
            "isoforms": list(self.isoforms),
            "n_isoforms_with_evidence": self.n_isoforms_with_evidence,
            "per_isoform": [list(t) for t in self.per_isoform],
        }


@dataclass(frozen=True, slots=True)
class ComparativeFeatureSet:
    """Joint multi-isoform feature structure aligned by canonical position.

    This is the primary input to the comparative learning layer (SCI-2).

    Attributes:
        ligand_inchikey:     Shared ligand identity.
        isoforms:            Sorted isoform names covered.
        canonical_positions: Sorted canonical positions covered.
        profiles:            One PositionProfile per canonical position.
        feature_vector:      Flat ordinal encoding, shape
                             (n_positions x n_interaction_types x n_isoforms).
                             Entry (p, t, i) = InteractionPresence int (0-3).
        feature_names:       Parallel name list for the feature vector.
                             Format: "{canonical_position}:{itype}:{isoform}".
        n_differential:      Positions with DIFFERENTIAL flag.
        n_alpha_unique:      Positions where alpha has evidence and all
                             other covered isoforms do not.
        algorithm_version:   Pinned version.
        source_fp_version:   InteractionFingerprint algorithm version from
                             the input ComparativeFingerprint.
    """

    ligand_inchikey: str | None
    isoforms: tuple[str, ...]
    canonical_positions: tuple[int, ...]
    profiles: tuple[PositionProfile, ...]
    feature_vector: tuple[int, ...]
    feature_names: tuple[str, ...]
    n_differential: int
    n_alpha_unique: int
    algorithm_version: str
    source_fp_version: str

    def get_profile(self, canonical_position: int) -> PositionProfile | None:
        for p in self.profiles:
            if p.canonical_position == canonical_position:
                return p
        return None

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "algorithm_version": self.algorithm_version,
                "canonical_positions": list(self.canonical_positions),
                "feature_names": list(self.feature_names),
                "feature_vector": list(self.feature_vector),
                "isoforms": list(self.isoforms),
                "ligand_inchikey": self.ligand_inchikey,
                "n_alpha_unique": self.n_alpha_unique,
                "n_differential": self.n_differential,
                "profiles": [p.to_canonical_dict() for p in self.profiles],
                "source_fp_version": self.source_fp_version,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _max_presence_at_position(
    fp: InteractionFingerprint,
    canonical_pos: int,
    itype: InteractionType,
) -> InteractionPresence:
    """Aggregate presence across all evidence records at (position, type)."""
    best = InteractionPresence.UNAVAILABLE
    for ev in fp.evidence:
        if ev.canonical_position == canonical_pos and ev.interaction_type == itype:
            p = InteractionPresence.from_status(ev.status)
            best = max(best, p)
    return best


def build_comparative_feature_set(
    comparative_fp: ComparativeFingerprint,
) -> ComparativeFeatureSet:
    """Build a joint multi-isoform feature set from a ComparativeFingerprint.

    All fingerprints in `comparative_fp` must share the same ligand (same
    InChIKey) and be computed with the same correspondence table. The
    canonical positions covered are the union across all isoforms.

    The feature vector encoding is deterministic: positions sorted ascending,
    interaction types sorted alphabetically, isoforms sorted alphabetically.
    """
    isoforms = tuple(sorted(iso for iso, _ in comparative_fp.isoform_fingerprints))
    fp_map = dict(comparative_fp.isoform_fingerprints)
    itypes = tuple(sorted(InteractionType, key=lambda t: t.value))

    # Source FP version (from the first fingerprint's algorithm version)
    fp_algo = next(iter(fp_map.values())).algorithm_version if fp_map else ""

    # Canonical positions: union across all isoforms
    all_positions = sorted(comparative_fp.canonical_positions_covered)

    profiles: list[PositionProfile] = []
    feature_vector: list[int] = []
    feature_names: list[str] = []
    n_diff = 0
    n_alpha_unique = 0

    for canon_pos in all_positions:
        per_isoform: list[tuple[str, str, int]] = []
        for itype in itypes:
            for iso in isoforms:
                fp = fp_map.get(iso)
                if fp is None:
                    pres = InteractionPresence.UNAVAILABLE
                else:
                    pres = _max_presence_at_position(fp, canon_pos, itype)
                per_isoform.append((iso, itype.value, int(pres)))
                feature_vector.append(int(pres))
                feature_names.append(f"{canon_pos}:{itype.value}:{iso}")

        # Differential flag: collapse per position (max over interaction types)
        presence_by_iso: dict[str, int] = {}
        for iso in isoforms:
            fp = fp_map.get(iso)
            max_pres = 0
            for itype in itypes:
                p = int(_max_presence_at_position(fp, canon_pos, itype)) if fp else 0
                max_pres = max(max_pres, p)
            presence_by_iso[iso] = max_pres

        covered = {iso for iso, p in presence_by_iso.items() if p > 0}
        n_covered = len(covered)
        presences = [presence_by_iso[iso] for iso in isoforms if iso in covered]

        if n_covered == 0:
            diff_flag = DifferentialFlag.UNCOVERED
        elif len(set(presences)) == 1:
            diff_flag = DifferentialFlag.CONSERVED
        else:
            diff_flag = DifferentialFlag.DIFFERENTIAL
            n_diff += 1

        # alpha_unique: alpha OBSERVED/CANDIDATE, all other covered isoforms ABSENT
        alpha_has = presence_by_iso.get("PI3Kalpha", 0) >= InteractionPresence.CANDIDATE
        others_absent = all(
            presence_by_iso.get(iso, 0) <= InteractionPresence.ABSENT
            for iso in isoforms
            if iso != "PI3Kalpha" and iso in covered
        )
        alpha_unique = alpha_has and others_absent and "PI3Kalpha" in isoforms
        if alpha_unique:
            n_alpha_unique += 1

        profiles.append(
            PositionProfile(
                canonical_position=canon_pos,
                isoforms=isoforms,
                per_isoform=tuple(sorted(per_isoform)),
                differential_flag=diff_flag,
                alpha_unique=alpha_unique,
                n_isoforms_with_evidence=n_covered,
            )
        )

    return ComparativeFeatureSet(
        ligand_inchikey=comparative_fp.ligand_inchikey,
        isoforms=isoforms,
        canonical_positions=tuple(all_positions),
        profiles=tuple(profiles),
        feature_vector=tuple(feature_vector),
        feature_names=tuple(feature_names),
        n_differential=n_diff,
        n_alpha_unique=n_alpha_unique,
        algorithm_version=COMPARATIVE_FEATURE_ALGORITHM_VERSION,
        source_fp_version=fp_algo,
    )

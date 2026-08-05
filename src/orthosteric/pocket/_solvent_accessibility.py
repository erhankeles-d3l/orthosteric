"""Per-residue solvent-accessible surface area for pocket residues.

Authority: ADR-0010 [Architectural]; SCI1-002 (Milestone 3).
Constitution sections served: §2.1, §0.3.

Scientific rule classification
--------------------------------
RULE_AVAILABLE:
  - Shrake-Rupley algorithm (Shrake & Rupley 1973, J. Mol. Biol. 79:351-371)
    is the canonical rolling-sphere SASA algorithm; BioPython provides a
    verified implementation.
  - `GOVERNED_PROBE_RADIUS_ANGSTROM = 1.4` — the standard Lee-Richards water
    probe radius (Lee & Richards 1971, J. Mol. Biol. 55:379-400). This is a
    settled scientific convention, not an invented number; it represents the
    approximate radius of a water molecule and is universally used in
    structural biology SASA calculations.
  - `TIEN_2013_MAX_ASA` — maximum solvent-accessible surface area per
    residue type from Tien et al. 2013 (PLoS ONE 8:e80635), used to compute
    relative SASA. These are measured values from fully-extended peptide
    conformations with the Shrake-Rupley algorithm at 1.4 Å probe; using the
    same algorithm and probe radius guarantees the normalization is valid.

RULE_MISSING / GOVERNANCE_DECISION_REQUIRED:
  - `n_sphere_points` in Shrake-Rupley: a convergence parameter (more points
    = more accurate but slower), not a scientific value. Exposed in
    `SASAConfig` with the BioPython default of 100 as the engineering default.
    Constitution §2.3/§2.4 do not specify a convergence level.

Algorithm choice note
---------------------
This module uses BioPython's `ShrakeRupley` for SASA computation. The probe
radius is governed (`GOVERNED_PROBE_RADIUS_ANGSTROM`); the sphere-point count
is a configurable engineering parameter. No other SASA algorithm is
substituted. If a future GDR specifies a different algorithm (e.g.
Connolly/MSMS), a new version of this module would be required, and a version
bump to `SASA_ALGORITHM_VERSION` would propagate into all `PocketSASA` objects
computed with the new algorithm.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from orthosteric.pocket._pocket_definition import PocketResidueSet
from orthosteric.pocket._structure_record import StructureProvenance, StructureRecord

__all__ = [
    "GOVERNED_PROBE_RADIUS_ANGSTROM",
    "SASA_ALGORITHM_VERSION",
    "TIEN_2013_MAX_ASA",
    "PocketSASA",
    "ResidueSASA",
    "SASAAvailability",
    "SASAConfig",
    "compute_pocket_sasa",
]

SASA_ALGORITHM_VERSION = "pocket_sasa_v1_sci1002_shrake_rupley"

GOVERNED_PROBE_RADIUS_ANGSTROM: float = 1.4
"""Standard water probe radius for Shrake-Rupley SASA calculation.

Source: Lee & Richards 1971, J. Mol. Biol. 55:379-400. This is a settled
scientific convention; no GDR is required to use it.
"""

# Maximum ASA values per residue type (Å²), for relative SASA normalisation.
# Source: Tien et al. 2013, PLoS ONE 8:e80635, Table 2 (Theoretical values,
# extended-state peptide with Shrake-Rupley, 1.4 Å probe, 960 sphere points).
# Using the same probe radius as GOVERNED_PROBE_RADIUS_ANGSTROM ensures that
# the normalization is consistent with the calculated SASA.
TIEN_2013_MAX_ASA: dict[str, float] = {
    "ALA": 129.0,
    "ARG": 274.0,
    "ASN": 195.0,
    "ASP": 193.0,
    "CYS": 167.0,
    "GLN": 225.0,
    "GLU": 223.0,
    "GLY": 104.0,
    "HIS": 224.0,
    "ILE": 197.0,
    "LEU": 201.0,
    "LYS": 236.0,
    "MET": 224.0,
    "PHE": 240.0,
    "PRO": 159.0,
    "SER": 155.0,
    "THR": 172.0,
    "TRP": 285.0,
    "TYR": 263.0,
    "VAL": 174.0,
}


class SASAAvailability(StrEnum):
    """Solvent accessibility computation status per residue.

    OBSERVED: SASA successfully computed from resolved atomic coordinates.
    MISSING:  Residue or its heavy atoms are absent from the structure;
              computation was not attempted (not inferred).
    NOT_COMPUTED: The BioPython computation raised an exception or returned
              a sentinel value for this residue. Provenance note will explain.
    """

    OBSERVED = "observed"
    MISSING = "missing"
    NOT_COMPUTED = "not_computed"


@dataclass(frozen=True, slots=True)
class SASAConfig:
    """Engineering configuration for Shrake-Rupley SASA calculation.

    Attributes:
        n_sphere_points: Number of sphere points per atom. BioPython default
            is 100; higher values converge toward the true SASA but increase
            runtime. This is an engineering convergence parameter, not a
            scientific one. The value used is recorded in `PocketSASA` for
            reproducibility.
        probe_radius_angstrom: Should always equal `GOVERNED_PROBE_RADIUS_ANGSTROM`
            (1.4 Å) for primary calculations. Override records a deviation in
            `PocketSASA.probe_radius_deviation_note`.
    """

    n_sphere_points: int = 100
    probe_radius_angstrom: float = GOVERNED_PROBE_RADIUS_ANGSTROM


@dataclass(frozen=True, slots=True)
class ResidueSASA:
    """SASA for one residue in the pocket.

    Attributes:
        residue_id:             `ResidueRecord.residue_id()`.
        residue_name:           3-letter residue name.
        chain_id:               PDB chain identifier.
        residue_seq:            PDB sequence number.
        canonical_position:     Cross-isoform position (None before SCI1-003).
        availability:           See `SASAAvailability`.
        absolute_sasa_angstrom2: Summed atom-level SASA for this residue (Å²).
                                 ``None`` when not OBSERVED.
        relative_sasa:          `absolute_sasa / TIEN_2013_MAX_ASA[residue_name]`.
                                 ``None`` when not OBSERVED or residue not in
                                 `TIEN_2013_MAX_ASA`.
        max_asa_reference:      The `TIEN_2013_MAX_ASA` value used for
                                 normalization. ``None`` when not used.
        provenance_note:        Empty for OBSERVED; explanation for non-OBSERVED.
    """

    residue_id: str
    residue_name: str
    chain_id: str
    residue_seq: int
    canonical_position: int | None
    availability: SASAAvailability
    absolute_sasa_angstrom2: float | None
    relative_sasa: float | None
    max_asa_reference: float | None
    provenance_note: str

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "absolute_sasa_angstrom2": self.absolute_sasa_angstrom2,
            "availability": self.availability.value,
            "canonical_position": self.canonical_position,
            "chain_id": self.chain_id,
            "max_asa_reference": self.max_asa_reference,
            "provenance_note": self.provenance_note,
            "relative_sasa": self.relative_sasa,
            "residue_id": self.residue_id,
            "residue_name": self.residue_name,
            "residue_seq": self.residue_seq,
        }


@dataclass(frozen=True, slots=True)
class PocketSASA:
    """SASA for all residues in the governed pocket.

    Attributes:
        structure_record_id:        Back-reference to the `StructureRecord`.
        provenance:                 Structural provenance.
        algorithm_version:          `SASA_ALGORITHM_VERSION`.
        probe_radius_angstrom:      Probe radius used (should be
                                    `GOVERNED_PROBE_RADIUS_ANGSTROM`).
        n_sphere_points:            Sphere points used (engineering param).
        residue_sasas:              One entry per pocket residue, sorted
                                    deterministically.
        n_observed:                 Count with OBSERVED.
        n_missing:                  Count with MISSING.
        n_not_computed:             Count with NOT_COMPUTED.
        probe_radius_deviation_note: Empty when probe_radius equals
                                    `GOVERNED_PROBE_RADIUS_ANGSTROM`;
                                    records the deviation otherwise.
    """

    structure_record_id: str
    provenance: StructureProvenance
    algorithm_version: str
    probe_radius_angstrom: float
    n_sphere_points: int
    residue_sasas: tuple[ResidueSASA, ...]
    n_observed: int
    n_missing: int
    n_not_computed: int
    probe_radius_deviation_note: str

    def content_sha256(self) -> str:
        payload = json.dumps(
            {
                "algorithm_version": self.algorithm_version,
                "n_sphere_points": self.n_sphere_points,
                "probe_radius_angstrom": self.probe_radius_angstrom,
                "provenance": self.provenance.to_canonical_dict(),
                "residue_sasas": [r.to_canonical_dict() for r in self.residue_sasas],
                "structure_record_id": self.structure_record_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_pocket_sasa(
    bio_structure: Any,
    structure_record: StructureRecord,
    pocket_residue_set: PocketResidueSet,
    config: SASAConfig | None = None,
) -> PocketSASA:
    """Compute per-residue SASA for governed pocket residues.

    Parameters
    ----------
    bio_structure:
        A `Bio.PDB.Structure.Structure`, already parsed.
    structure_record:
        The `StructureRecord` providing provenance.
    pocket_residue_set:
        The governed pocket residue set.
    config:
        Engineering configuration; defaults used if ``None``.

    Returns:
    -------
    `PocketSASA` — frozen, deterministic, with explicit missing-data states.
    """
    from Bio.PDB.SASA import ShrakeRupley  # noqa: PLC0415

    if config is None:
        config = SASAConfig()

    deviation_note = ""
    if abs(config.probe_radius_angstrom - GOVERNED_PROBE_RADIUS_ANGSTROM) > 1e-9:  # noqa: PLR2004
        deviation_note = (
            f"PROBE_RADIUS_DEVIATION: used {config.probe_radius_angstrom} Å "
            f"instead of the governed {GOVERNED_PROBE_RADIUS_ANGSTROM} Å "
            "(Lee & Richards 1971). Relative SASA values are normalized "
            "against Tien 2013 values computed at 1.4 Å; this deviation "
            "is not governed."
        )

    # Run Shrake-Rupley on the whole structure (residue-level sums)
    bio_model = next(iter(bio_structure.get_models()))  # type: ignore[union-attr,attr-defined]
    sr = ShrakeRupley(probe_radius=config.probe_radius_angstrom, n_points=config.n_sphere_points)  # type: ignore[no-untyped-call]
    sr.compute(bio_model, level="R")  # type: ignore[no-untyped-call]

    # Sort pocket residues deterministically
    sorted_pocket = sorted(
        pocket_residue_set.residues,
        key=lambda pr: (
            pr.residue.chain_id,
            pr.residue.residue_seq,
            pr.residue.insertion_code,
        ),
    )

    residue_sasas: list[ResidueSASA] = []
    for pocket_res in sorted_pocket:
        rr = pocket_res.residue

        # Check availability in structure
        try:
            bio_chain = bio_model[rr.chain_id]
        except KeyError:
            residue_sasas.append(
                ResidueSASA(
                    residue_id=rr.residue_id(),
                    residue_name=rr.residue_name,
                    chain_id=rr.chain_id,
                    residue_seq=rr.residue_seq,
                    canonical_position=rr.canonical_position,
                    availability=SASAAvailability.MISSING,
                    absolute_sasa_angstrom2=None,
                    relative_sasa=None,
                    max_asa_reference=None,
                    provenance_note=f"Chain {rr.chain_id!r} not found in structure.",
                )
            )
            continue

        bio_res_key = (" ", rr.residue_seq, rr.insertion_code)
        try:
            bio_res = bio_chain[bio_res_key]
        except KeyError:
            residue_sasas.append(
                ResidueSASA(
                    residue_id=rr.residue_id(),
                    residue_name=rr.residue_name,
                    chain_id=rr.chain_id,
                    residue_seq=rr.residue_seq,
                    canonical_position=rr.canonical_position,
                    availability=SASAAvailability.MISSING,
                    absolute_sasa_angstrom2=None,
                    relative_sasa=None,
                    max_asa_reference=None,
                    provenance_note=f"Residue {rr.residue_id()!r} not found in structure.",
                )
            )
            continue

        # Retrieve SASA computed by ShrakeRupley
        sasa_val = getattr(bio_res, "sasa", None)
        if sasa_val is None:
            residue_sasas.append(
                ResidueSASA(
                    residue_id=rr.residue_id(),
                    residue_name=rr.residue_name,
                    chain_id=rr.chain_id,
                    residue_seq=rr.residue_seq,
                    canonical_position=rr.canonical_position,
                    availability=SASAAvailability.NOT_COMPUTED,
                    absolute_sasa_angstrom2=None,
                    relative_sasa=None,
                    max_asa_reference=None,
                    provenance_note="BioPython ShrakeRupley did not attach .sasa to this residue.",
                )
            )
            continue

        abs_sasa = round(float(sasa_val), 4)  # round for determinism
        max_ref = TIEN_2013_MAX_ASA.get(rr.residue_name)
        rel_sasa = None
        if max_ref is not None and max_ref > 0.0:
            rel_sasa = round(abs_sasa / max_ref, 6)

        residue_sasas.append(
            ResidueSASA(
                residue_id=rr.residue_id(),
                residue_name=rr.residue_name,
                chain_id=rr.chain_id,
                residue_seq=rr.residue_seq,
                canonical_position=rr.canonical_position,
                availability=SASAAvailability.OBSERVED,
                absolute_sasa_angstrom2=abs_sasa,
                relative_sasa=rel_sasa,
                max_asa_reference=max_ref,
                provenance_note="",
            )
        )

    n_obs = sum(1 for r in residue_sasas if r.availability == SASAAvailability.OBSERVED)
    n_miss = sum(1 for r in residue_sasas if r.availability == SASAAvailability.MISSING)
    n_nc = sum(1 for r in residue_sasas if r.availability == SASAAvailability.NOT_COMPUTED)

    return PocketSASA(
        structure_record_id=structure_record.record_id,
        provenance=structure_record.provenance,
        algorithm_version=SASA_ALGORITHM_VERSION,
        probe_radius_angstrom=config.probe_radius_angstrom,
        n_sphere_points=config.n_sphere_points,
        residue_sasas=tuple(residue_sasas),
        n_observed=n_obs,
        n_missing=n_miss,
        n_not_computed=n_nc,
        probe_radius_deviation_note=deviation_note,
    )

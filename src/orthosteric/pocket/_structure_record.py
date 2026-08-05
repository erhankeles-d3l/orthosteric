"""Typed, frozen data models for preprocessed protein structures.

Authority: ADR-0010 [Architectural]; SCI1-001 (Milestone 2).
Constitution sections served: §2.1 (pocket definition, construct policy,
  rotamer states), §0.3 (orthosteric sub-regions), §A.1(4) (correspondence
  stability across the conformational ensemble).

Scientific invariants encoded at the type level
------------------------------------------------
1. Experimental priority. `StructureSource` carries a flag distinguishing
   experimental from predicted provenance. No downstream module may silently
   treat a predicted structure as experimental.
2. Provenance preservation. Every structure record carries a
   `StructureProvenance` frozen dataclass; it is not optional. A
   `StructureRecord` without provenance is a type error.
3. Determinism. All fields are immutable (`frozen=True`); no field holds a
   mutable container. Two records with identical fields produce an identical
   content hash.
4. Constitution §2.1 construct policy. `ConstructDescriptor` explicitly
   records whether the structure was solved as p110-alone or as a p110-p85
   or p110-p87/p101 heterodimer, since regulatory-subunit presence alters
   ATP-site conformation and therefore threatens correspondence stability
   (§A.1(4)).
5. No apo pocket definition. `LigandRecord` must be present for any
   structure used to define the ligand-ensemble-union pocket boundary
   (§2.1). A structure with no ATP-site ligand is usable for background
   statistics but not as a pocket-definition contributor.

This module is pure Python (stdlib + dataclasses only). No BioPython, no
numpy, no RDKit. The types established here are the interface contracts that
pocket geometry and feature modules build on.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

__all__ = [
    "ChainRecord",
    "ConformationalState",
    "ConstructClass",
    "ConstructDescriptor",
    "DataTier",
    "LigandRecord",
    "LigandShapeClass",
    "ResidueRecord",
    "StructureProvenance",
    "StructureRecord",
    "StructureSource",
]


# ── Enumerations ──────────────────────────────────────────────────────────────


class StructureSource(StrEnum):
    """Origin of structural data.

    Experimental > AlphaFold fallback (Constitution §2.1, ADR-0010 §5.1).
    No code may promote `ALPHAFOLD` to `EXPERIMENTAL` status or silently
    mix the two without explicit provenance.
    """

    EXPERIMENTAL_PDB = "experimental_pdb"
    ALPHAFOLD_GOVERNED_FALLBACK = "alphafold_governed_fallback"


class ConstructClass(StrEnum):
    """Regulatory-subunit composition of the solved construct.

    Constitution §2.1 "construct policy": p110 isoforms are solved either
    alone or as heterodimers. Regulatory-subunit presence alters ATP-site
    conformation (§A.1(4)); mixed-construct comparisons must be flagged, never
    silently pooled. Structures are annotated here so downstream pocket
    definition can honour that constraint.
    """

    P110_ALONE = "p110_alone"
    P110_P85_HETERODIMER = "p110_p85_heterodimer"  # alpha, beta, delta
    P110_P101_HETERODIMER = "p110_p101_heterodimer"  # gamma
    P110_P87_HETERODIMER = "p110_p87_heterodimer"  # gamma
    UNKNOWN = "unknown"


class ConformationalState(StrEnum):
    """Gross conformational state of the ATP-binding site.

    Used by Constitution §A.6 (C6 corollary): the specificity pocket between
    Trp780 and Met772 exists only in induced conformations. An apo or open
    structure without a bound ligand in that region cannot contribute evidence
    about that pocket.
    """

    LIGAND_BOUND = "ligand_bound"
    APO = "apo"
    CRYSTAL_CONTACT_CLOSED = "crystal_contact_closed"
    UNKNOWN = "unknown"


class LigandShapeClass(StrEnum):
    """Ligand shape class relevant to selectivity.

    Constitution §2.1 specifies both flat (morpholino) ligands and
    propeller-shaped ligands, because the induced specificity pocket is only
    accessible to propeller-shaped compounds (§0.3, §6 S6). Shape class is
    therefore a required annotation on every ATP-site ligand — not an
    optional aesthetic note.
    """

    FLAT = "flat"  # e.g. morpholino-triazine, BEZ235 class
    PROPELLER = "propeller"  # e.g. PIK-39, idelalisib class
    OTHER = "other"
    UNKNOWN = "unknown"


class DataTier(StrEnum):
    """Scope tier (Constitution §0.1)."""

    TIER1 = "tier1"
    TIER2 = "tier2"
    TIER3 = "tier3"  # out of scope; must never reach learning/ or features/


# ── Provenance ────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class StructureProvenance:
    """Full provenance for a preprocessed structure.

    Every `StructureRecord` carries exactly one of these, without exception.
    A structure without traceable provenance cannot be used in pocket
    definition or feature construction — this is the type-level enforcement
    of Constitution §3.3 and ADR-0010 §5.2.

    Attributes:
        source: Experimental or governed-AlphaFold fallback.
        pdb_id: PDB accession (e.g. ``"2RD0"``), or AlphaFold entry
            identifier (e.g. ``"AF-P42336-F1"``). Required.
        resolution_angstrom: Crystallographic resolution. ``None`` for
            AlphaFold (not applicable) or when unreported.
        deposition_year: Year the structure was deposited, for temporal
            stratification.
        data_tier: Constitution scope tier.
        pipeline_version: Version of the structural preprocessing pipeline
            that produced this record. Changes here invalidate downstream
            pocket definitions and require recomputation.
        alphafold_version: Model version if `source` is AlphaFold. ``None``
            for experimental structures. Must not be ``None`` when `source`
            is `ALPHAFOLD_GOVERNED_FALLBACK`.
    """

    source: StructureSource
    pdb_id: str
    resolution_angstrom: float | None
    deposition_year: int | None
    data_tier: DataTier
    pipeline_version: str
    alphafold_version: str | None = None

    def __post_init__(self) -> None:
        if not self.pdb_id.strip():
            raise ValueError("StructureProvenance.pdb_id must be non-empty")
        if not self.pipeline_version.strip():
            raise ValueError("StructureProvenance.pipeline_version must be non-empty")
        if (
            self.source == StructureSource.ALPHAFOLD_GOVERNED_FALLBACK
            and self.alphafold_version is None
        ):
            raise ValueError(
                "StructureProvenance.alphafold_version must not be None when "
                "source is ALPHAFOLD_GOVERNED_FALLBACK"
            )
        if self.source == StructureSource.EXPERIMENTAL_PDB and self.alphafold_version is not None:
            raise ValueError(
                "StructureProvenance.alphafold_version must be None for experimental structures"
            )

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "alphafold_version": self.alphafold_version,
            "data_tier": self.data_tier.value,
            "deposition_year": self.deposition_year,
            "pdb_id": self.pdb_id,
            "pipeline_version": self.pipeline_version,
            "resolution_angstrom": self.resolution_angstrom,
            "source": self.source.value,
        }


@dataclass(frozen=True, slots=True)
class ConstructDescriptor:
    """Describes the protein construct that was crystallised or modelled.

    Constitution §2.1 construct policy: regulatory-subunit presence alters
    ATP-site conformation and threatens correspondence stability (§A.1(4)).
    All fields here are required annotations on every structure — downstream
    modules use them to flag mixed-construct comparisons rather than
    silently pooling non-equivalent conformations.

    Attributes:
        isoform: Catalytic isoform designation, e.g. ``"PI3Kalpha"``.
        uniprot_id: UniProt canonical accession for the catalytic subunit.
        construct_class: Regulatory-subunit composition (see
            `ConstructClass`).
        mutations: Tuple of mutations in the construct, e.g.
            ``("H1047R",)`` for a hotspot mutant. Empty tuple for wild-type.
        species: Source organism, e.g. ``"Homo sapiens"``.
        construct_description: Free-text as reported in the PDB or
            publication, for audit purposes.
    """

    isoform: str
    uniprot_id: str
    construct_class: ConstructClass
    mutations: tuple[str, ...]
    species: str
    construct_description: str

    def __post_init__(self) -> None:
        if not self.isoform.strip():
            raise ValueError("ConstructDescriptor.isoform must be non-empty")
        if not self.species.strip():
            raise ValueError("ConstructDescriptor.species must be non-empty")

    @property
    def is_wild_type(self) -> bool:
        return len(self.mutations) == 0

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "construct_class": self.construct_class.value,
            "construct_description": self.construct_description,
            "isoform": self.isoform,
            "mutations": list(self.mutations),
            "species": self.species,
            "uniprot_id": self.uniprot_id,
        }


# ── Structural sub-records ────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ResidueRecord:
    """One residue in a parsed structure.

    Attributes:
        chain_id: PDB chain identifier.
        residue_seq: Sequence number as reported in the PDB file (may be
            non-sequential; use `canonical_position` for cross-isoform
            comparisons after residue mapping).
        insertion_code: PDB insertion code (``" "`` when absent, never
            ``None`` — matches PDB convention for stable comparison).
        residue_name: Three-letter PDB residue name, e.g. ``"GLN"``.
        canonical_position: Cross-isoform canonical position after
            structure-based alignment (Constitution §2.1: "structure-based
            alignment, not sequence-only"). ``None`` before alignment is
            run.
        is_missing: ``True`` if this residue was not resolved in the
            electron density. Missing residues with loops < 4 residues are
            modelled (flagged); >= 4 are excluded (Constitution §2.1).
        missing_modelled: ``True`` if this residue was modelled in (i.e.
            `is_missing` is True but the residue was built in for analysis
            purposes per §2.1).
    """

    chain_id: str
    residue_seq: int
    insertion_code: str
    residue_name: str
    canonical_position: int | None
    is_missing: bool
    missing_modelled: bool

    def __post_init__(self) -> None:
        if len(self.chain_id) == 0:
            raise ValueError("ResidueRecord.chain_id must be non-empty")
        if len(self.residue_name) != 3:  # noqa: PLR2004
            raise ValueError("ResidueRecord.residue_name must be a 3-letter code")

    def residue_id(self) -> str:
        """Canonical residue identifier: chain+seq+ins, e.g. 'A_859_ '."""
        return f"{self.chain_id}_{self.residue_seq}_{self.insertion_code}"


@dataclass(frozen=True, slots=True)
class LigandRecord:
    """One ATP-site ligand in a parsed structure.

    Constitution §2.1: apo pocket definitions are prohibited. A structure
    contributes to the ligand-ensemble-union pocket boundary only if it has
    at least one `LigandRecord` in the ATP site. Shape class must be
    annotated for all ATP-site ligands because it determines whether the
    induced specificity pocket is expected to be occupied (§0.3 S6, §6 S6).

    Attributes:
        chain_id: PDB chain identifier.
        residue_seq: Residue sequence number.
        insertion_code: PDB insertion code.
        residue_name: PDB residue name (HET code), e.g. ``"BYL"`` for
            alpelisib.
        shape_class: Flat vs propeller vs other (see `LigandShapeClass`).
        is_atp_site: ``True`` if this ligand is in the ATP-binding site and
            thus eligible to define pocket boundaries.
        smiles: Isomeric SMILES string for the ligand, if available.
        inchikey: InChIKey for cross-reference with the compound corpus.
    """

    chain_id: str
    residue_seq: int
    insertion_code: str
    residue_name: str
    shape_class: LigandShapeClass
    is_atp_site: bool
    smiles: str | None
    inchikey: str | None


@dataclass(frozen=True, slots=True)
class ChainRecord:
    """One polypeptide chain in a parsed structure."""

    chain_id: str
    residues: tuple[ResidueRecord, ...]
    is_catalytic_subunit: bool
    is_regulatory_subunit: bool
    n_residues_total: int
    n_residues_missing: int
    n_residues_modelled: int

    def __post_init__(self) -> None:
        if len(self.chain_id) == 0:
            raise ValueError("ChainRecord.chain_id must be non-empty")


# ── Top-level record ──────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class StructureRecord:
    """A fully preprocessed and validated protein structure.

    This is the output of SCI-1's structural preprocessing stage and the
    input contract for pocket definition and feature construction. Every
    field is immutable; provenance is mandatory (not optional).

    Invariants:
    - `provenance.source` must equal `StructureSource.EXPERIMENTAL_PDB`
      unless there is no admissible experimental structure for this
      isoform/construct, in which case `ALPHAFOLD_GOVERNED_FALLBACK` is
      acceptable with a non-None `alphafold_version`.
    - `conformational_state` must be `LIGAND_BOUND` for any structure used
      in the ligand-ensemble-union pocket definition (Constitution §2.1 apo
      prohibition, C6). Structures with `conformational_state == APO` can
      contribute to background statistics but not to pocket boundaries.
    - `atp_site_ligands` must be non-empty if `conformational_state ==
      LIGAND_BOUND`. A ligand-bound structure with no identified ATP-site
      ligand is a preprocessing error, not an acceptable INDETERMINATE state.

    Attributes:
        record_id: Stable content-based identifier for this preprocessing
            output, derived from `provenance + construct + pipeline_version`.
            Recomputed whenever any field changes.
        provenance: Full structural provenance (required).
        construct: Construct descriptor (required).
        conformational_state: Gross conformational state.
        chains: All chains extracted for this record.
        atp_site_ligands: ATP-site ligands in this structure (empty tuple for
            apo structures; must be non-empty for LIGAND_BOUND).
        all_ligands: All HET groups in the structure.
        preprocessing_flags: Flags from preprocessing (e.g. "loop_modelled",
            "missing_residue_excluded", "construct_mismatch_flagged").
            Flags are informational; no flag silently discards information.
    """

    record_id: str
    provenance: StructureProvenance
    construct: ConstructDescriptor
    conformational_state: ConformationalState
    chains: tuple[ChainRecord, ...]
    atp_site_ligands: tuple[LigandRecord, ...]
    all_ligands: tuple[LigandRecord, ...]
    preprocessing_flags: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.record_id.strip():
            raise ValueError("StructureRecord.record_id must be non-empty")
        if (
            self.conformational_state == ConformationalState.LIGAND_BOUND
            and len(self.atp_site_ligands) == 0
        ):
            raise ValueError(
                "StructureRecord with conformational_state LIGAND_BOUND "
                "must have at least one ATP-site ligand in atp_site_ligands. "
                "A ligand-bound state with no identified ATP-site ligand is a "
                "preprocessing error."
            )
        if len(self.record_id.strip()) == 0:
            raise ValueError("StructureRecord.record_id must be non-empty")

    @property
    def has_propeller_ligand(self) -> bool:
        """True if any ATP-site ligand is propeller-shaped.

        Relevant to Constitution §0.3 (induced specificity pocket) and S6
        (apo-ablation test): propeller-shaped ligands open the Trp780/Met772
        cleft that cannot be seen in apo or flat-ligand structures.
        """
        return any(lig.shape_class == LigandShapeClass.PROPELLER for lig in self.atp_site_ligands)

    @property
    def is_wild_type(self) -> bool:
        return self.construct.is_wild_type

    def to_canonical_dict(self) -> dict[str, Any]:
        """Stable, sorted dict for content hashing and audit."""
        return {
            "all_ligands_count": len(self.all_ligands),
            "atp_site_ligands": [
                {
                    "inchikey": lig.inchikey,
                    "is_atp_site": lig.is_atp_site,
                    "residue_name": lig.residue_name,
                    "shape_class": lig.shape_class.value,
                }
                for lig in sorted(self.atp_site_ligands, key=lambda x: x.residue_name)
            ],
            "conformational_state": self.conformational_state.value,
            "construct": self.construct.to_canonical_dict(),
            "preprocessing_flags": sorted(self.preprocessing_flags),
            "provenance": self.provenance.to_canonical_dict(),
            "record_id": self.record_id,
        }

    def content_sha256(self) -> str:
        """SHA-256 of the canonical dict (stable across platforms)."""
        payload = json.dumps(
            self.to_canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── Factory helpers ───────────────────────────────────────────────────────────


def make_record_id(provenance: StructureProvenance, construct: ConstructDescriptor) -> str:
    """Derive a deterministic record identifier from provenance + construct.

    This is a *construction helper*, not a primary content hash. The full
    `content_sha256()` method on `StructureRecord` is authoritative; this
    provides a shorter human-readable identifier derived from the same
    sources.
    """
    payload = json.dumps(
        {
            "construct_class": construct.construct_class.value,
            "isoform": construct.isoform,
            "mutations": sorted(construct.mutations),
            "pdb_id": provenance.pdb_id,
            "pipeline_version": provenance.pipeline_version,
            "source": provenance.source.value,
            "species": construct.species,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

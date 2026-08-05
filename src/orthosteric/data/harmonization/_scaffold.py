"""Bemis–Murcko scaffold family assignment.

Objective: SCI0-012.
Specification: SCI0-001-refinement backlog §SCI0-012.
  "Bemis–Murcko scaffold family assignment" for audit Q5.
Prerequisite: SCI0-008b (canonical standardized SMILES).

Scaffold rule (governed by Bemis & Murcko, J. Med. Chem. 1996)
---------------------------------------------------------------
The scaffold is extracted from the SCI0-008b canonical standardized SMILES
using RDKit's MurckoScaffold.MurckoScaffoldSmiles(), which:
  1. Retains all ring systems and their linker atoms.
  2. Removes all side chains (atoms not part of ring systems or linkers).
  3. Preserves atom identity, aromaticity, and ring topology.
  4. Preserves stereochemistry (the Bemis–Murcko rule does not strip stereo).

The scaffold family identifier is the InChIKey of the scaffold SMILES after
standardization.  This is deterministic (same scaffold SMILES + same RDKit
version → same InChIKey) and source-agnostic.

Generic scaffold (for broader family grouping) uses atom-type-agnostic rings
with MurckoScaffold.MakeScaffoldGeneric().  It is recorded as a separate field
for downstream use; it is NOT used as the primary scaffold_family_id.

Stereochemistry
---------------
The Bemis–Murcko extraction preserves stereocenters in the scaffold if they
are on ring atoms.  Stereocenters on side chains (removed) are discarded.
Two stereoisomers of the same scaffold produce the same scaffold SMILES only
if their stereocenters lie exclusively on side chains; if a stereocenter is
on a ring atom it is preserved and the two scaffolds are distinct.
This behavior is consistent with SCI0-008b: distinct InChIKeys for stereoiso-
mers whose stereodistinction survives scaffold extraction.

Acyclic compounds
-----------------
Compounds with no rings yield an empty scaffold (the Bemis–Murcko scaffold of
a linear compound is empty string).  These are assigned scaffold_family_id
"ACYCLIC" and scaffold_family_type = ScaffoldFamilyType.ACYCLIC.

Failure
-------
If the compound cannot be processed (invalid/None canonical_smiles from
SCI0-008b), the scaffold record has status FAILED and no scaffold_family_id.
The record is preserved with its failure_reason; it is never silently dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

# RDKit imports
try:
    from rdkit import Chem
    from rdkit import __version__ as _RDKIT_VERSION
    from rdkit.Chem.Scaffolds import MurckoScaffold

    _RDKIT_AVAILABLE = True
except ImportError as _e:
    _RDKIT_AVAILABLE = False
    _RDKIT_VERSION = "not_installed"
    _rdkit_import_err = str(_e)

SCAFFOLD_RULE_VERSION = "bemis_murcko_rdkit_v1"
"""Scaffold rule version.  Any change to the extraction procedure must
increment this identifier and produce a new snapshot hash (SCI0-011)."""


class ScaffoldStatus(StrEnum):
    OK = "ok"
    ACYCLIC = "acyclic"  # compound has no rings
    FAILED_SMILES = "failed_smiles"  # canonical_smiles absent or unparseable
    FAILED_EXTRACTION = "failed_extraction"  # RDKit scaffold extraction error


class ScaffoldFamilyType(StrEnum):
    """Broad scaffold category for series stratification."""

    RING_SYSTEM = "ring_system"  # has one or more rings
    ACYCLIC = "acyclic"  # no rings; acyclic compound
    UNKNOWN = "unknown"  # extraction failed


@dataclass(frozen=True, slots=True)
class ScaffoldRecord:
    """Bemis–Murcko scaffold assignment for one compound.

    Attributes:
    ----------
    inchikey:
        Compound InChIKey (from SCI0-008c); the input identity.
    canonical_smiles_input:
        SCI0-008b canonical SMILES used as input.
    scaffold_smiles:
        Bemis–Murcko scaffold SMILES.  Empty string for acyclic compounds.
    generic_scaffold_smiles:
        Generic scaffold (atom-type-agnostic).  Recorded for downstream
        grouping; NOT used as the primary family identifier.
    scaffold_inchikey:
        InChIKey of the scaffold_smiles.  This IS the scaffold_family_id.
        "ACYCLIC" for acyclic compounds; None on failure.
    scaffold_family_id:
        The stable identifier for this scaffold family.  Equals
        scaffold_inchikey for ring-containing compounds, "ACYCLIC" for
        acyclic compounds, None on failure.
    scaffold_family_type:
        RING_SYSTEM / ACYCLIC / UNKNOWN.
    status:
        Extraction outcome.
    failure_reason:
        Set when status != OK; None otherwise.
    rdkit_version:
        RDKit version used (SCI0-011 toolchain provenance requirement).
    scaffold_rule_version:
        Scaffold extraction rule version.
    """

    inchikey: str
    canonical_smiles_input: str | None
    scaffold_smiles: str | None
    generic_scaffold_smiles: str | None
    scaffold_inchikey: str | None
    scaffold_family_id: str | None
    scaffold_family_type: ScaffoldFamilyType
    status: ScaffoldStatus
    failure_reason: str | None
    rdkit_version: str
    scaffold_rule_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_smiles_input": self.canonical_smiles_input,
            "failure_reason": self.failure_reason,
            "generic_scaffold_smiles": self.generic_scaffold_smiles,
            "inchikey": self.inchikey,
            "rdkit_version": self.rdkit_version,
            "scaffold_family_id": self.scaffold_family_id,
            "scaffold_family_type": self.scaffold_family_type.value,
            "scaffold_inchikey": self.scaffold_inchikey,
            "scaffold_rule_version": self.scaffold_rule_version,
            "scaffold_smiles": self.scaffold_smiles,
            "status": self.status.value,
        }


class ScaffoldAssigner:
    """Assigns Bemis–Murcko scaffold family IDs to compounds.

    Input is the SCI0-008b canonical standardized SMILES and the
    SCI0-008c InChIKey.  Raw source SMILES are never used.

    Determinism: given the same canonical SMILES and RDKit version,
    the output is byte-identical (inherits SCI0-008b guarantee).
    """

    def __init__(self) -> None:
        if not _RDKIT_AVAILABLE:
            raise ImportError(
                "RDKit is required for SCI0-012 scaffold assignment.  "
                f"Install with: pip install rdkit  (original: {_rdkit_import_err})"
            )

    @property
    def rdkit_version(self) -> str:
        return _RDKIT_VERSION

    def assign(self, inchikey: str, canonical_smiles: str | None) -> ScaffoldRecord:  # noqa: PLR0911
        """Assign a Bemis–Murcko scaffold to a compound.

        Parameters
        ----------
        inchikey:
            SCI0-008c compound identity.
        canonical_smiles:
            SCI0-008b canonical standardized SMILES.  None if standardization
            failed — will produce status=FAILED_SMILES.

        Returns:
        -------
        ScaffoldRecord (frozen) — never raises; returns a FAILED record
        on any error.
        """
        if not canonical_smiles:
            return _failed(
                inchikey,
                canonical_smiles,
                ScaffoldStatus.FAILED_SMILES,
                "NO_CANONICAL_SMILES",
            )

        mol_or_none = Chem.MolFromSmiles(canonical_smiles)
        if mol_or_none is None:
            return _failed(
                inchikey,
                canonical_smiles,
                ScaffoldStatus.FAILED_SMILES,
                "CANNOT_PARSE_CANONICAL_SMILES",
            )
        mol = mol_or_none

        try:
            scaffold_smi: str = MurckoScaffold.MurckoScaffoldSmiles(mol=mol)  # type: ignore[no-untyped-call]
        except Exception as exc:
            return _failed(
                inchikey,
                canonical_smiles,
                ScaffoldStatus.FAILED_EXTRACTION,
                f"MURCKO_EXTRACTION_ERROR: {exc}",
            )

        # Acyclic compound: empty scaffold string
        if not scaffold_smi:
            return ScaffoldRecord(
                inchikey=inchikey,
                canonical_smiles_input=canonical_smiles,
                scaffold_smiles="",
                generic_scaffold_smiles="",
                scaffold_inchikey="ACYCLIC",
                scaffold_family_id="ACYCLIC",
                scaffold_family_type=ScaffoldFamilyType.ACYCLIC,
                status=ScaffoldStatus.ACYCLIC,
                failure_reason=None,
                rdkit_version=_RDKIT_VERSION,
                scaffold_rule_version=SCAFFOLD_RULE_VERSION,
            )

        # Generic scaffold (atom-type-agnostic)
        try:
            scaffold_mol = Chem.MolFromSmiles(scaffold_smi)
            generic_mol = (
                MurckoScaffold.MakeScaffoldGeneric(scaffold_mol)  # type: ignore[no-untyped-call]
                if scaffold_mol is not None
                else None
            )
            generic_smi = (
                Chem.MolToSmiles(generic_mol, isomericSmiles=True, canonical=True)
                if generic_mol is not None
                else None
            )
        except Exception:
            generic_smi = None  # non-fatal

        # Scaffold InChIKey (primary family identifier)
        try:
            scaffold_mol2 = Chem.MolFromSmiles(scaffold_smi)
            if scaffold_mol2 is None:
                raise ValueError("scaffold SMILES cannot be re-parsed")
            inchi = Chem.MolToInchi(scaffold_mol2)  # type: ignore[no-untyped-call]
            scaffold_ik = Chem.InchiToInchiKey(inchi) if inchi else None  # type: ignore[no-untyped-call]
        except Exception as exc:
            return _failed(
                inchikey,
                canonical_smiles,
                ScaffoldStatus.FAILED_EXTRACTION,
                f"SCAFFOLD_INCHIKEY_ERROR: {exc}",
            )

        if scaffold_ik is None:
            return _failed(
                inchikey,
                canonical_smiles,
                ScaffoldStatus.FAILED_EXTRACTION,
                "SCAFFOLD_INCHIKEY_RETURNED_NONE",
            )

        return ScaffoldRecord(
            inchikey=inchikey,
            canonical_smiles_input=canonical_smiles,
            scaffold_smiles=scaffold_smi,
            generic_scaffold_smiles=generic_smi,
            scaffold_inchikey=scaffold_ik,
            scaffold_family_id=scaffold_ik,
            scaffold_family_type=ScaffoldFamilyType.RING_SYSTEM,
            status=ScaffoldStatus.OK,
            failure_reason=None,
            rdkit_version=_RDKIT_VERSION,
            scaffold_rule_version=SCAFFOLD_RULE_VERSION,
        )

    def assign_batch(self, compounds: list[tuple[str, str | None]]) -> list[ScaffoldRecord]:
        """Assign scaffolds to a list of (inchikey, canonical_smiles) pairs.

        Failed records are returned with status FAILED_*; never dropped.
        """
        return [self.assign(ik, smi) for ik, smi in compounds]


def scaffold_family_report(
    records: list[ScaffoldRecord],
) -> dict[str, Any]:
    """Summary statistics for a scaffold assignment batch.

    Returns counts by status, unique family IDs, and family sizes.
    Suitable for audit Q5 reporting.
    """
    total = len(records)
    ok = sum(1 for r in records if r.status == ScaffoldStatus.OK)
    acyclic = sum(1 for r in records if r.status == ScaffoldStatus.ACYCLIC)
    failed = sum(
        1
        for r in records
        if r.status in (ScaffoldStatus.FAILED_SMILES, ScaffoldStatus.FAILED_EXTRACTION)
    )
    unique_families = {r.scaffold_family_id for r in records if r.scaffold_family_id}
    family_sizes: dict[str, int] = {}
    for rec in records:
        fid = rec.scaffold_family_id or "__NONE__"
        family_sizes[fid] = family_sizes.get(fid, 0) + 1
    singleton_families = sum(1 for v in family_sizes.values() if v == 1)

    return {
        "total_compounds": total,
        "ok_count": ok,
        "acyclic_count": acyclic,
        "failed_count": failed,
        "unique_scaffold_families": len(unique_families),
        "singleton_families": singleton_families,
        "family_size_distribution": dict(sorted(family_sizes.items(), key=lambda x: -x[1])),
    }


def _build_scaffold_record(
    inchikey: str,
    canonical_smiles: str | None,
    scaffold_smi: str,
) -> ScaffoldRecord:
    """Build a ScaffoldRecord from an extracted scaffold SMILES."""
    if not scaffold_smi:
        return ScaffoldRecord(
            inchikey=inchikey,
            canonical_smiles_input=canonical_smiles,
            scaffold_smiles="",
            generic_scaffold_smiles="",
            scaffold_inchikey="ACYCLIC",
            scaffold_family_id="ACYCLIC",
            scaffold_family_type=ScaffoldFamilyType.ACYCLIC,
            status=ScaffoldStatus.ACYCLIC,
            failure_reason=None,
            rdkit_version=_RDKIT_VERSION,
            scaffold_rule_version=SCAFFOLD_RULE_VERSION,
        )

    try:
        scaffold_mol = Chem.MolFromSmiles(scaffold_smi)
        generic_mol = (
            MurckoScaffold.MakeScaffoldGeneric(scaffold_mol)  # type: ignore[no-untyped-call]
            if scaffold_mol is not None
            else None
        )
        generic_smi: str | None = (
            Chem.MolToSmiles(generic_mol, isomericSmiles=True, canonical=True)
            if generic_mol is not None
            else None
        )
    except Exception:
        generic_smi = None

    try:
        scaffold_mol2 = Chem.MolFromSmiles(scaffold_smi)
        if scaffold_mol2 is None:
            raise ValueError("scaffold SMILES cannot be re-parsed")
        inchi = Chem.MolToInchi(scaffold_mol2)  # type: ignore[no-untyped-call]
        scaffold_ik: str | None = Chem.InchiToInchiKey(inchi) if inchi else None  # type: ignore[no-untyped-call]
    except Exception as exc:
        return _failed(
            inchikey,
            canonical_smiles,
            ScaffoldStatus.FAILED_EXTRACTION,
            f"SCAFFOLD_INCHIKEY_ERROR: {exc}",
        )

    if scaffold_ik is None:
        return _failed(
            inchikey,
            canonical_smiles,
            ScaffoldStatus.FAILED_EXTRACTION,
            "SCAFFOLD_INCHIKEY_RETURNED_NONE",
        )

    return ScaffoldRecord(
        inchikey=inchikey,
        canonical_smiles_input=canonical_smiles,
        scaffold_smiles=scaffold_smi,
        generic_scaffold_smiles=generic_smi,
        scaffold_inchikey=scaffold_ik,
        scaffold_family_id=scaffold_ik,
        scaffold_family_type=ScaffoldFamilyType.RING_SYSTEM,
        status=ScaffoldStatus.OK,
        failure_reason=None,
        rdkit_version=_RDKIT_VERSION,
        scaffold_rule_version=SCAFFOLD_RULE_VERSION,
    )


# ── Internal helpers ────────────────────────────────────────────────────────


def _failed(
    inchikey: str,
    canonical_smiles: str | None,
    status: ScaffoldStatus,
    reason: str,
) -> ScaffoldRecord:
    return ScaffoldRecord(
        inchikey=inchikey,
        canonical_smiles_input=canonical_smiles,
        scaffold_smiles=None,
        generic_scaffold_smiles=None,
        scaffold_inchikey=None,
        scaffold_family_id=None,
        scaffold_family_type=ScaffoldFamilyType.UNKNOWN,
        status=status,
        failure_reason=reason,
        rdkit_version=_RDKIT_VERSION,
        scaffold_rule_version=SCAFFOLD_RULE_VERSION,
    )

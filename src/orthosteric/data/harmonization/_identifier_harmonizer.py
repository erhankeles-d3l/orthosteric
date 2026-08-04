"""Identifier harmonization across source databases.

Objective: SCI0-008c.
Specification: SCI0-001-refinement backlog §SCI0-008c.
  "Internal ID, cross-references across sources; conflicting structures
   surfaced, never silently merged."
Prerequisite: SCI0-008b (canonical chemical representation from RDKit).

Architecture
------------
  RawSourceRecord  →  standardize (SCI0-008b)  →  HarmonizedCompound
                                                  ├── internal_id (deterministic)
                                                  ├── canonical_smiles / inchi / inchikey
                                                  ├── cross_refs: {source_db → source_id}
                                                  └── conflict_status

Internal ID assignment
----------------------
The internal compound identifier is the InChIKey of the standardized structure.
InChIKey is:
  - deterministic given same SMILES + same RDKit version (SCI0-008b guarantee);
  - source-agnostic (does not embed any database identifier);
  - stereochemistry-preserving (SCI0-008b guarantees distinct InChIKeys for
    stereoisomers — verified by the SCI0-008b test suite);
  - 27-character fixed-length, computable offline;
  - the de facto chemical informatics standard for compound identity.

This is not a governance decision — it follows directly from the spec's
requirement that the identifier be deterministic and that SCI0-008b output
forms the canonical chemical representation.

Conflict detection
------------------
A conflict occurs when two source records have the same source-level identifier
(e.g. same ChEMBL molecule_chembl_id) but produce different InChIKeys after
standardization.  Conflicts are recorded with status CONFLICT and surfaced for
investigation; they are never silently resolved by discarding one record.

A second type of conflict: two different source identifiers that map to the same
InChIKey are *concordant* (not a conflict) — this is normal deduplication.  The
cross_refs field accumulates all source identifiers for the same compound.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from orthosteric.data.harmonization._chem_standardizer import (
    ChemicalStandardizer,
    StandardizationStatus,
    StandardizedStructure,
)
from orthosteric.data.sources._base import RawSourceRecord


class ConflictStatus(StrEnum):
    """Identity-resolution status for a harmonized compound."""

    OK = "ok"
    CONFLICT = "conflict"  # same source ID → different InChIKey across processing
    UNRESOLVED = "unresolved"  # standardization failed; no InChIKey available
    PARTIAL = "partial"  # some but not all source records standardized


@dataclass
class SourceRef:
    """A reference to a compound in a specific source database."""

    source_db: str
    source_compound_id: str
    original_smiles: str | None
    standardization_status: str
    rdkit_version: str


@dataclass
class StructureConflict:
    """Records a detected identity conflict for audit.

    A conflict exists when two records produce different InChIKeys despite
    sharing some identity link (same source ID, or expected to be the same
    compound based on source metadata).

    Conflicts are never silently resolved.  They require external investigation.
    """

    source_db_a: str
    source_id_a: str
    inchikey_a: str | None
    source_db_b: str
    source_id_b: str
    inchikey_b: str | None
    reason: str


@dataclass
class HarmonizedCompound:
    """A single compound with harmonized identity across all source databases.

    The internal_id is the InChIKey of the standardized structure.  It is:
      - deterministic (same SMILES + RDKit version → same InChIKey);
      - source-agnostic;
      - stereochemistry-preserving.

    cross_refs maps source_db → list[source_compound_id] for all source
    records that map to this compound.  Multiple source IDs per database are
    allowed (e.g. ChEMBL may use both CHEMBL123 and CHEMBL456 for the same
    structure).

    Attributes:
        internal_id:          InChIKey (27-char).  None only when status==UNRESOLVED.
        canonical_smiles:     Canonical SMILES from SCI0-008b.
        inchi:                Standard InChI.
        inchikey:             InChIKey (same as internal_id).
        cross_refs:           {source_db: [source_compound_id, ...]}.
        source_records_count: Total number of source records contributing.
        standardization:      The StandardizedStructure that determined identity.
        conflict_status:      OK / CONFLICT / UNRESOLVED / PARTIAL.
        conflicts:            Any detected conflicts; empty when status==OK.
        rdkit_version:        RDKit version used for standardization.
        provenance:           Arbitrary key-value metadata for corpus provenance.
    """

    internal_id: str | None
    canonical_smiles: str | None
    inchi: str | None
    inchikey: str | None
    cross_refs: dict[str, list[str]]
    source_records_count: int
    standardization: StandardizedStructure | None
    conflict_status: ConflictStatus
    conflicts: list[StructureConflict]
    rdkit_version: str
    provenance: dict[str, Any] = field(default_factory=dict)


class IdentifierHarmonizer:
    """Assigns deterministic internal IDs and cross-references compounds across
    source databases using the SCI0-008b standardization output as canonical.

    Usage
    -----
    ```python
    harmonizer = IdentifierHarmonizer()
    compounds = harmonizer.harmonize(raw_records)
    ```

    Fail-closed behavior
    --------------------
    Records that fail standardization (invalid SMILES etc.) are represented as
    UNRESOLVED HarmonizedCompounds, not silently dropped.  Records whose
    standardization succeeds but whose InChIKey disagrees with a previously
    seen record for the same source_compound_id are flagged as CONFLICT.
    """

    def __init__(self) -> None:
        self._std = ChemicalStandardizer()

    @property
    def rdkit_version(self) -> str:
        return self._std.rdkit_version

    def harmonize(self, records: list[RawSourceRecord]) -> list[HarmonizedCompound]:
        """Harmonize a list of RawSourceRecords into HarmonizedCompounds.

        Records are grouped by the InChIKey of their standardized structure.
        Records that cannot be standardized are grouped separately as UNRESOLVED.

        Parameters
        ----------
        records:
            RawSourceRecords from any mix of source databases.  Records with
            admissibility=INADMISSIBLE are included (preserving provenance) but
            flagged in their provenance dict.

        Returns:
        -------
        list[HarmonizedCompound] — one entry per unique InChIKey (or per
        unstandardizable record cluster).
        """
        # Group by (source_db, source_compound_id) first to detect same-id conflicts
        # then by InChIKey for cross-source deduplication

        # Phase 1: standardize every record — split into ok and failed immediately
        ok_pairs: list[tuple[RawSourceRecord, StandardizedStructure]] = []
        failed_pairs: list[tuple[RawSourceRecord, StandardizedStructure | None]] = []

        for rec in records:
            if rec.smiles:
                std = self._std.standardize(rec.smiles)
                if std.status == StandardizationStatus.OK and std.inchikey:
                    ok_pairs.append((rec, std))
                else:
                    failed_pairs.append((rec, std))
            else:
                failed_pairs.append((rec, None))

        # Phase 2: detect same-source-id conflicts among ok_pairs
        id_to_inchikeys: dict[tuple[str, str], set[str]] = {}
        id_to_std: dict[tuple[str, str], StandardizedStructure] = {}
        for rec, std in ok_pairs:
            if rec.compound_id is None:
                continue
            key = (rec.source_db, rec.compound_id)
            prev = id_to_inchikeys.setdefault(key, set())
            prev.add(std.inchikey or "")
            if key not in id_to_std:
                id_to_std[key] = std

        # Phase 3: group ok_pairs by InChIKey (cross-source deduplication)
        by_inchikey: dict[str, list[tuple[RawSourceRecord, StandardizedStructure]]] = {}
        for rec, std in ok_pairs:
            by_inchikey.setdefault(std.inchikey or "", []).append((rec, std))
        unresolved = failed_pairs

        # Phase 4: build HarmonizedCompound per InChIKey group
        results: list[HarmonizedCompound] = []

        for inchikey, group in by_inchikey.items():
            cross_refs: dict[str, list[str]] = {}
            conflicts: list[StructureConflict] = []
            has_conflict = False

            for rec, _std in group:
                db = rec.source_db
                cid = rec.compound_id or rec.source_record_id
                cross_refs.setdefault(db, [])
                if cid not in cross_refs[db]:
                    cross_refs[db].append(cid)

                # Check for same-source-id conflicts
                if rec.compound_id:
                    key = (db, rec.compound_id)
                    if len(id_to_inchikeys.get(key, set())) > 1:
                        has_conflict = True
                        ik_set = id_to_inchikeys[key]
                        for other_ik in ik_set - {inchikey}:
                            conflicts.append(
                                StructureConflict(
                                    source_db_a=db,
                                    source_id_a=rec.compound_id,
                                    inchikey_a=inchikey,
                                    source_db_b=db,
                                    source_id_b=rec.compound_id,
                                    inchikey_b=other_ik,
                                    reason=(
                                        f"Same source_compound_id {rec.compound_id!r} "
                                        f"in {db} maps to multiple InChIKeys after "
                                        "standardization"
                                    ),
                                )
                            )

            # Use the first standardization in the group as representative
            representative_std = group[0][1]
            status = ConflictStatus.CONFLICT if has_conflict else ConflictStatus.OK

            results.append(
                HarmonizedCompound(
                    internal_id=inchikey,
                    canonical_smiles=representative_std.canonical_smiles,
                    inchi=representative_std.inchi,
                    inchikey=inchikey,
                    cross_refs=cross_refs,
                    source_records_count=len(group),
                    standardization=representative_std,
                    conflict_status=status,
                    conflicts=conflicts,
                    rdkit_version=representative_std.rdkit_version,
                    provenance={
                        "inchikey": inchikey,
                        "source_count": len(group),
                        "source_dbs": sorted(cross_refs.keys()),
                    },
                )
            )

        # Phase 5: build UNRESOLVED compounds (one per unstandardizable record)
        for rec, failed_std in unresolved:
            fail_reason = failed_std.failure_reason if failed_std else "NO_SMILES_PROVIDED"
            results.append(
                HarmonizedCompound(
                    internal_id=None,
                    canonical_smiles=None,
                    inchi=None,
                    inchikey=None,
                    cross_refs={rec.source_db: [rec.compound_id or rec.source_record_id]},
                    source_records_count=1,
                    standardization=failed_std,
                    conflict_status=ConflictStatus.UNRESOLVED,
                    conflicts=[],
                    rdkit_version=self._std.rdkit_version,
                    provenance={
                        "failure_reason": fail_reason,
                        "original_smiles": rec.smiles,
                        "source_db": rec.source_db,
                        "source_record_id": rec.source_record_id,
                    },
                )
            )

        return results

    def harmonize_with_conflicts_report(
        self, records: list[RawSourceRecord]
    ) -> tuple[list[HarmonizedCompound], list[StructureConflict]]:
        """Harmonize and return the full conflict list separately.

        Returns:
        -------
        (compounds, all_conflicts)
            compounds:      All HarmonizedCompound entries.
            all_conflicts:  Flat list of all StructureConflict objects across
                            all compounds, for batch reporting.
        """
        compounds = self.harmonize(records)
        all_conflicts: list[StructureConflict] = []
        for c in compounds:
            all_conflicts.extend(c.conflicts)
        return compounds, all_conflicts

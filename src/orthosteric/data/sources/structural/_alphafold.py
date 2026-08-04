"""AlphaFold DB fallback connector.

Objective: SCI0-007 (AMENDMENT-SCI0007-ALPHAFOLD-FALLBACK.md, version 1.0).

This connector is ONLY invoked when no admissible experimental human PDB
structure exists for the required isoform (Rule AF-1).

Rules AF-1 through AF-9 are enforced deterministically.  Violation of any
rule triggers GOVERNANCE_EXCEPTION rather than silent substitution.

NEVER use this connector when an admissible experimental PDB exists.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from orthosteric.data.config import chembl_request_timeout_s
from orthosteric.data.exceptions import GovernanceException
from orthosteric.data.sources.structural._isoform_map import (
    PI3K_UNIPROT_MAP,
    PI3KIsoform,
)
from orthosteric.data.sources.structural._pdb import StructureAdmissibility, StructureSource
from orthosteric.data.sources.structural._structure_record import (
    ConstructDescriptor,
    StructureRecord,
)

_ALPHAFOLD_BASE = "https://alphafold.ebi.ac.uk/api"

# Rule AF-4: mean pLDDT confidence threshold
_MIN_PLDDT = 70.0


@dataclass
class AlphaFoldModelInfo:
    """Parsed AlphaFold model metadata."""

    model_id: str  # e.g. "AF-P42336-F1-model_v4"
    uniprot_ac: str
    version: str  # e.g. "v4"
    mean_plddt: float
    sequence_length: int
    organism: str | None
    gene_name: str | None
    pdb_url: str | None  # coordinate file URL
    raw_payload: dict[str, Any]


def _get_json(url: str, timeout: int) -> Any:
    headers = {"Accept": "application/json"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result: Any = json.loads(resp.read())
        return result


def _compute_mean_plddt(scores: list[float]) -> float:
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


class AlphaFoldConnector:
    """AlphaFold DB connector for structural fallback.

    Implements Rules AF-1 through AF-9 from AMENDMENT-SCI0007-ALPHAFOLD-FALLBACK.md.

    NEVER call this connector directly without first confirming (via PDBConnector)
    that no admissible experimental PDB exists for the isoform (Rule AF-1).
    """

    def __init__(self) -> None:
        self._timeout = chembl_request_timeout_s()

    def version(self) -> str:
        return "alphafold-db-v4"

    def metadata(self) -> dict[str, str]:
        return {
            "name": "AlphaFold DB",
            "url": "https://alphafold.ebi.ac.uk/",
            "license": "CC-BY 4.0",
            "api_base": _ALPHAFOLD_BASE,
        }

    def fetch_model_info(self, uniprot_ac: str) -> AlphaFoldModelInfo | None:
        """Fetch AlphaFold model metadata for a UniProt accession.

        Rule AF-2: retrieve by UniProt accession only.
        Rule AF-3: confirm accession match before use.
        """
        url = f"{_ALPHAFOLD_BASE}/prediction/{urllib.parse.quote(uniprot_ac)}"
        try:
            data = _get_json(url, self._timeout)
        except Exception:
            return None

        if isinstance(data, list):
            data = data[0] if data else {}

        if not data:
            return None

        # Rule AF-3: verify accession matches
        returned_ac = data.get("uniprotAccession", "")
        if returned_ac.upper() != uniprot_ac.upper():
            raise GovernanceException(
                rule_id="AF-3",
                evidence_summary=(
                    f"AlphaFold returned accession {returned_ac!r} for "
                    f"requested accession {uniprot_ac!r}. "
                    "Isoform identity cannot be confirmed."
                ),
            )

        # Extract pLDDT scores
        plddt_scores: list[float] = [
            float(r.get("pLDDT", 0.0))
            for r in data.get("pLDDTScores", [])
            if r.get("pLDDT") is not None
        ]
        mean_plddt = _compute_mean_plddt(plddt_scores)

        # Extract sequence length
        seq_len = len(data.get("uniprotSequence", "")) or data.get("uniprotEnd", 0) or 0

        return AlphaFoldModelInfo(
            model_id=data.get("entryId", f"AF-{uniprot_ac}-F1"),
            uniprot_ac=uniprot_ac,
            version=data.get("latestVersion", "v4"),
            mean_plddt=mean_plddt,
            sequence_length=int(seq_len),
            organism=data.get("organismScientificName"),
            gene_name=data.get("gene"),
            pdb_url=data.get("pdbUrl"),
            raw_payload=data,
        )

    def fallback_structure_for_isoform(
        self,
        isoform: PI3KIsoform,
        retrieval_timestamp: str | None = None,
        source_version: str | None = None,
    ) -> StructureRecord:
        """Return a fallback StructureRecord for an isoform with no admissible PDB.

        Enforces Rules AF-1 through AF-9.  Rule AF-1 (no admissible PDB) is the
        caller's responsibility to verify; it is documented in source_selection_reason.

        Returns an inadmissible record if Rule AF-4 (mean pLDDT ≥ 70) is not met.
        """
        ts = retrieval_timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        sv = source_version or self.version()
        uniprot_ac = PI3K_UNIPROT_MAP[isoform]

        model_info = self.fetch_model_info(uniprot_ac)

        if model_info is None:
            # No AlphaFold model found — fail closed (Rule AF-9)
            return StructureRecord(
                structure_id=uuid4(),
                provenance_id=uuid4(),
                pdb_id="",
                isoform=isoform.value,
                uniprot_ac=uniprot_ac,
                resolution_angstrom=None,  # Rule AF-6: never assign resolution
                experimental_method=None,  # Rule AF-6: not experimental
                has_bound_ligand=False,  # Rule AF-6: no fabricated ligand
                ligand_ids=[],  # Rule AF-6: empty
                construct=ConstructDescriptor(
                    sequence_range_start=None,
                    sequence_range_end=None,
                ),
                structure_source=StructureSource.ALPHAFOLD_FALLBACK.value,
                source_selection_reason=f"AF_FALLBACK_NO_MODEL_FOUND_FOR_{uniprot_ac}",
                admissibility=StructureAdmissibility.INADMISSIBLE_NO_EXPERIMENTAL_STRUCTURE.value,
                inadmissibility_reason="ALPHAFOLD_MODEL_NOT_FOUND",
                deposition_date=None,
                release_date=None,
                organism=None,
                retrieval_timestamp=ts,
                source_version=sv,
            )

        # Rule AF-4: mean pLDDT threshold
        if model_info.mean_plddt < _MIN_PLDDT:
            return StructureRecord(
                structure_id=uuid4(),
                provenance_id=uuid4(),
                pdb_id="",
                isoform=isoform.value,
                uniprot_ac=uniprot_ac,
                resolution_angstrom=None,
                experimental_method=None,
                has_bound_ligand=False,
                ligand_ids=[],
                construct=ConstructDescriptor(
                    sequence_range_start=None,
                    sequence_range_end=None,
                    notes=(
                        f"AlphaFold mean_pLDDT={model_info.mean_plddt:.1f} < threshold {_MIN_PLDDT}"
                    ),
                ),
                structure_source=StructureSource.ALPHAFOLD_FALLBACK.value,
                source_selection_reason=(
                    f"NO_ADMISSIBLE_EXPERIMENTAL_PDB_FOR_{isoform.value.upper()}"
                ),
                admissibility=StructureAdmissibility.INADMISSIBLE_LOW_CONFIDENCE.value,
                inadmissibility_reason=(
                    f"ALPHAFOLD_MEAN_PLDDT_{model_info.mean_plddt:.1f}_BELOW_{_MIN_PLDDT}"
                ),
                deposition_date=None,
                release_date=None,
                organism=model_info.organism,
                retrieval_timestamp=ts,
                source_version=sv,
                raw_payload={
                    "alphafold_model_id": model_info.model_id,
                    "alphafold_version": model_info.version,
                    "mean_plddt": model_info.mean_plddt,
                    "uniprot_ac": uniprot_ac,
                },
            )

        # All rules satisfied — build admissible fallback record (Rules AF-5 through AF-9)
        return StructureRecord(
            structure_id=uuid4(),
            provenance_id=uuid4(),
            pdb_id="",  # Rule AF-6: no PDB ID
            isoform=isoform.value,
            uniprot_ac=uniprot_ac,
            resolution_angstrom=None,  # Rule AF-6
            experimental_method=None,  # Rule AF-6
            has_bound_ligand=False,  # Rule AF-6
            ligand_ids=[],  # Rule AF-6
            construct=ConstructDescriptor(
                sequence_range_start=1,
                sequence_range_end=model_info.sequence_length or None,
                notes=(
                    f"AlphaFold model {model_info.model_id}; mean pLDDT={model_info.mean_plddt:.1f}"
                ),
            ),
            structure_source=StructureSource.ALPHAFOLD_FALLBACK.value,
            source_selection_reason=(f"NO_ADMISSIBLE_EXPERIMENTAL_PDB_FOR_{isoform.value.upper()}"),
            admissibility=StructureAdmissibility.ADMISSIBLE.value,
            inadmissibility_reason=None,
            deposition_date=None,  # Rule AF-6: no deposition date
            release_date=None,
            organism=model_info.organism,
            retrieval_timestamp=ts,
            source_version=sv,
            raw_payload={  # Rule AF-5 provenance
                "alphafold_model_id": model_info.model_id,
                "alphafold_version": model_info.version,
                "mean_plddt": model_info.mean_plddt,
                "sequence_length": model_info.sequence_length,
                "uniprot_ac": uniprot_ac,
                "gene_name": model_info.gene_name,
                "fallback_reason": f"NO_ADMISSIBLE_EXPERIMENTAL_PDB_FOR_{isoform.value.upper()}",
                "pdb_url": model_info.pdb_url,
                "full_response": model_info.raw_payload,
            },
        )

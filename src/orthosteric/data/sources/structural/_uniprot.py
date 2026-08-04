"""UniProt connector for PI3K protein sequence and isoform identity.

Objective: SCI0-007.
Constitution §2.1: UniProt provides sequence and isoform identity only.
No structural predictions or feature annotations are used.

The UniProt REST API (https://rest.uniprot.org/) provides:
  - canonical protein sequence
  - gene names, function, UniProt accession
  - cross-references to PDB entries
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from orthosteric.data.config import chembl_request_timeout_s
from orthosteric.data.sources.structural._isoform_map import (
    PI3K_UNIPROT_MAP,
    PI3KIsoform,
)

_UNIPROT_REST = "https://rest.uniprot.org/uniprotkb"


@dataclass
class UniProtRecord:
    """UniProt protein record for a PI3K isoform.

    Contains sequence and identity information only; no structural
    features or predictions.

    Attributes:
        uniprot_ac:     UniProt accession number.
        entry_name:     UniProt entry name (e.g., "PK3CA_HUMAN").
        gene_name:      Primary gene symbol.
        protein_name:   Recommended protein name.
        organism:       Scientific name of source organism.
        sequence:       Canonical amino-acid sequence (single-letter).
        sequence_length: Length of canonical sequence.
        isoform:        Mapped PI3K isoform.
        pdb_cross_refs: PDB IDs listed in UniProt cross-references.
        retrieval_timestamp: When this record was fetched.
        raw_payload:    Unmodified API response.
    """

    uniprot_ac: str
    entry_name: str | None
    gene_name: str | None
    protein_name: str | None
    organism: str | None
    sequence: str
    sequence_length: int
    isoform: str  # PI3KIsoform value
    pdb_cross_refs: list[str]
    retrieval_timestamp: str
    raw_payload: dict[str, Any] = field(default_factory=dict)


def _get_json(url: str, timeout: int) -> Any:
    headers = {
        "Accept": "application/json",
        "User-Agent": "OrthostericDataPipeline/1.0",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result: Any = json.loads(resp.read())
        return result


def _parse_uniprot_entry(
    ac: str, isoform: PI3KIsoform, data: dict[str, Any], ts: str
) -> UniProtRecord:
    entry_name = data.get("uniProtkbId")
    gene_names = data.get("genes", [])
    gene_name: str | None = None
    if gene_names:
        gn = gene_names[0]
        gene_name = gn.get("geneName", {}).get("value")

    prot = data.get("proteinDescription", {})
    rec_name = prot.get("recommendedName", {})
    protein_name: str | None = None
    if rec_name:
        fn = rec_name.get("fullName", {})
        protein_name = fn.get("value") if isinstance(fn, dict) else str(fn)

    organism = data.get("organism", {}).get("scientificName")

    seq_data = data.get("sequence", {})
    sequence = seq_data.get("value", "")
    seq_len = seq_data.get("length", len(sequence))

    # PDB cross-references
    pdb_refs: list[str] = []
    for xref in data.get("uniProtKBCrossReferences", []):
        if xref.get("database") == "PDB":
            pdb_id = xref.get("id", "")
            if pdb_id:
                pdb_refs.append(pdb_id)

    return UniProtRecord(
        uniprot_ac=ac,
        entry_name=entry_name,
        gene_name=gene_name,
        protein_name=protein_name,
        organism=organism,
        sequence=sequence,
        sequence_length=int(seq_len),
        isoform=isoform.value,
        pdb_cross_refs=pdb_refs,
        retrieval_timestamp=ts,
        raw_payload=data,
    )


class UniProtConnector:
    """UniProt REST API connector for PI3K protein sequences.

    Returns sequence and identity information only.  No structural
    predictions, feature annotations, or AlphaFold records are retrieved.
    """

    def __init__(self) -> None:
        self._timeout = chembl_request_timeout_s()

    def version(self) -> str:
        return "uniprot-rest-2024-03"

    def metadata(self) -> dict[str, str]:
        return {
            "name": "UniProt",
            "url": "https://www.uniprot.org/",
            "license": "CC-BY 4.0",
            "rest_api": _UNIPROT_REST,
        }

    def fetch(self, uniprot_ac: str, isoform: PI3KIsoform) -> UniProtRecord | None:
        """Fetch canonical sequence and metadata for a UniProt accession."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        url = f"{_UNIPROT_REST}/{urllib.parse.quote(uniprot_ac)}"
        try:
            data = _get_json(url, self._timeout)
        except Exception:
            return None
        return _parse_uniprot_entry(uniprot_ac, isoform, data, ts)

    def fetch_all_pi3k(self) -> dict[str, UniProtRecord | None]:
        """Fetch canonical sequences for all four Tier 1 PI3K isoforms.

        Returns a dict keyed by PI3KIsoform value.
        """
        results: dict[str, UniProtRecord | None] = {}
        for isoform, ac in PI3K_UNIPROT_MAP.items():
            results[isoform.value] = self.fetch(ac, isoform)
            time.sleep(0.2)
        return results

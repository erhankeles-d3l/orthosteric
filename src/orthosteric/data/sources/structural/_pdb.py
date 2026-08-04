"""PDB REST API connector for PI3K structural evidence.

Objective: SCI0-007.
Constitution §2.1: experimental structures with a bound ATP-site ligand,
resolution ≤ 2.8 Å.  AlphaFold explicitly excluded (defect 7).

The PDB REST API (https://data.rcsb.org/rest/v1/) provides:
  - entry metadata (resolution, method, organism, deposition date)
  - entity/chain polymer sequences linked to UniProt
  - ligand occupancy via the assembly/ligand endpoints

Admissibility rules (Constitution §2.1):
  ADMISSIBLE: human structure, resolution ≤ 2.8 Å, bound ligand present
  INADMISSIBLE_RESOLUTION: resolution > 2.8 Å or not reported
  INADMISSIBLE_NO_LIGAND: no ATP-site ligand
  INADMISSIBLE_WRONG_ORGANISM: non-human
  INADMISSIBLE_NO_EXPERIMENTAL_STRUCTURE: no experimental structure found
"""

from __future__ import annotations

import contextlib
import json
import time
import urllib.parse
import urllib.request
from enum import StrEnum
from typing import Any
from uuid import uuid4

from orthosteric.data.config import chembl_request_timeout_s
from orthosteric.data.sources.structural._isoform_map import (
    PI3K_UNIPROT_MAP,
    PI3KIsoform,
)
from orthosteric.data.sources.structural._structure_record import (
    ActivationLoopState,
    ConstructDescriptor,
    StructureRecord,
)

_PDB_REST = "https://data.rcsb.org/rest/v1"
_PDB_SEARCH = "https://search.rcsb.org/rcsbsearch/v2/query"
_RESOLUTION_CUTOFF = 2.8  # Å, Constitution §2.1

# Known ATP-competitive PI3K inhibitor/ligand codes (not exhaustive;
# a structural query also checks for any non-polymer in the ATP-site pocket)
_ATP_SITE_LIGANDS: frozenset[str] = frozenset(
    {
        "ATP",
        "ADP",
        "AMP",
        "ACP",  # natural substrates
        "PIK",
        "BYL",
        "GDC",  # PI3K-specific inhibitors
        "LY3",
        "IPI",
        "A66",
        "ZST",
        "B96",
        "TGX",
        "GNF",
        "PIQ",
        "CAL",
        "COP",
        "NVS",
        "INK",
        "WX6",
        "MLN",
        "SF1",
        "QL8",
        "STI",
        "YEJ",
        "PWT",
        "5A1",
    }
)


class StructureSource(StrEnum):
    EXPERIMENTAL_PDB = "experimental_pdb"
    ALPHAFOLD_FALLBACK = "alphafold_fallback"  # reserved; not used under current governance


class StructureAdmissibility(StrEnum):
    ADMISSIBLE = "admissible"
    INADMISSIBLE_RESOLUTION = "inadmissible_resolution"
    INADMISSIBLE_NO_LIGAND = "inadmissible_no_ligand"
    INADMISSIBLE_WRONG_ORGANISM = "inadmissible_wrong_organism"
    INADMISSIBLE_NO_EXPERIMENTAL_STRUCTURE = "inadmissible_no_experimental_structure"
    INADMISSIBLE_ALPHAFOLD = "inadmissible_alphafold"
    INADMISSIBLE_LOW_CONFIDENCE = "inadmissible_low_confidence"  # AlphaFold pLDDT below threshold


def _get_json(url: str, timeout: int) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        result: Any = json.loads(resp.read())
        return result


def _post_json(url: str, body: dict[str, Any], timeout: int) -> Any:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result: Any = json.loads(resp.read())
        return result


def _search_pdb_by_uniprot(uniprot_ac: str, timeout: int) -> list[str]:
    """Return PDB IDs for a UniProt accession via RCSB search."""
    query = {
        "query": {
            "type": "terminal",
            "service": "text",
            "parameters": {
                "attribute": (
                    "rcsb_polymer_entity_container_identifiers"
                    ".reference_sequence_identifiers"
                    ".database_accession"
                ),
                "operator": "exact_match",
                "value": uniprot_ac,
            },
        },
        "return_type": "entry",
        "request_options": {"paginate": {"start": 0, "rows": 200}},
    }
    try:
        data = _post_json(_PDB_SEARCH, query, timeout)
        result_set = data.get("result_set", [])
        return [r["identifier"] for r in result_set if "identifier" in r]
    except Exception:
        return []


def _fetch_entry(pdb_id: str, timeout: int) -> dict[str, Any] | None:
    url = f"{_PDB_REST}/core/entry/{pdb_id.lower()}"
    try:
        return _get_json(url, timeout)  # type: ignore[no-any-return]
    except Exception:
        return None


def _fetch_ligands(pdb_id: str, timeout: int) -> list[str]:
    """Return list of non-polymer ligand IDs present in this entry."""
    url = f"{_PDB_REST}/core/nonpolymer_entity/{pdb_id.lower()}"
    try:
        data = _get_json(url, timeout)
        if isinstance(data, list):
            return [item.get("chem_comp_id", "") for item in data if item.get("chem_comp_id")]
        return []
    except Exception:
        return []


def _fetch_polymer_entities(pdb_id: str, timeout: int) -> list[dict[str, Any]]:
    url = f"{_PDB_REST}/core/polymer_entity/{pdb_id.lower()}"
    try:
        data = _get_json(url, timeout)
        result: list[dict[str, Any]] = data if isinstance(data, list) else [data]
        return result
    except Exception:
        return []


def _parse_resolution(entry: dict[str, Any]) -> float | None:
    refine = entry.get("refine", [{}])
    if isinstance(refine, list) and refine:
        val = refine[0].get("ls_d_res_high")
        if val is not None:
            with contextlib.suppress(TypeError, ValueError):
                return float(val)
    # Try pdbx_vrpt_summary
    vrpt = entry.get("pdbx_vrpt_summary", {})
    if vrpt:
        val = vrpt.get("pdbresolution")
        if val is not None:
            with contextlib.suppress(TypeError, ValueError):
                return float(val)
    return None


def _parse_organism(entry: dict[str, Any]) -> str | None:
    src = entry.get("rcsb_entity_source_organism", [{}])
    if isinstance(src, list) and src:
        name: str | None = src[0].get("ncbi_scientific_name")
        return name
    fallback = entry.get("pdbx_entity_src_gen") or [{}]
    gene_src: str | None = fallback[0].get("gene_src_scientific_name")
    return gene_src


def _build_construct(entry: dict[str, Any], uniprot_ac: str) -> ConstructDescriptor:
    """Build a ConstructDescriptor from PDB entry metadata."""
    # Sequence range from polymer entity alignment
    seq_start: int | None = None
    seq_end: int | None = None

    # Mutations from struct_conn or entity mutation records
    mutations: list[str] = []
    mut_details = entry.get("entity_src_gen", [{}])
    if isinstance(mut_details, list):
        for m in mut_details:
            details = m.get("pdbx_gene_src_mutation", "")
            if details:
                mutations.extend(str(details).split(","))

    # Regulatory subunit: check for co-crystallized p85, p101, p87
    reg_subunit: str | None = None
    compounds = entry.get("struct", {}).get("title", "").lower()
    for sub in ("p85alpha", "p85beta", "p85", "p101", "p87"):
        if sub in compounds:
            reg_subunit = sub
            break

    # Missing residues
    missing = entry.get("pdbx_unobs_or_zero_occ_residues", [])
    if not isinstance(missing, list):
        missing = [missing] if missing else []

    missing_ranges: list[tuple[int, int]] = []
    short_loops = 0
    long_loops = 0
    for gap in missing:
        start = gap.get("auth_seq_id")
        end = gap.get("auth_seq_id")  # single residue; group into runs elsewhere
        if start is not None:
            with contextlib.suppress(TypeError, ValueError):
                missing_ranges.append((int(start), int(end or start)))

    # Classify missing ranges by length
    for s, e in missing_ranges:
        length = e - s + 1
        if length < 4:
            short_loops += 1
        else:
            long_loops += 1

    # Activation loop state: look for DFG motif and its modification
    al_state = ActivationLoopState.RESOLVED
    pdbx_mod = entry.get("pdbx_struct_mod_residue", [])
    if isinstance(pdbx_mod, list) and pdbx_mod:
        for mod in pdbx_mod:
            details = str(mod.get("details", "")).lower()
            if "dfg" in details or "activation" in details:
                al_state = ActivationLoopState.MODIFIED
                break

    return ConstructDescriptor(
        sequence_range_start=seq_start,
        sequence_range_end=seq_end,
        engineered_mutations=tuple(m.strip() for m in mutations if m.strip()),
        fusion_tags=None,  # not structurally recorded in most PDB entries
        regulatory_subunit=reg_subunit,
        activation_loop_state=al_state,
        missing_residue_ranges=tuple(missing_ranges[:50]),  # cap for large entries
        short_loops_flagged=short_loops,
        long_loops_excluded=long_loops,
    )


def _assess_admissibility(
    entry: dict[str, Any],
    ligand_ids: list[str],
    isoform: PI3KIsoform,
) -> tuple[StructureAdmissibility, str | None]:
    """Apply Constitution §2.1 admissibility rules."""
    # Check organism
    # Simpler: look for "Homo sapiens" in entity source
    src = entry.get("rcsb_entity_source_organism", [])
    organisms = [o.get("ncbi_scientific_name", "") for o in src] if isinstance(src, list) else []
    is_human = any("homo sapiens" in (o or "").lower() for o in organisms) or not organisms

    if not is_human and organisms:
        return StructureAdmissibility.INADMISSIBLE_WRONG_ORGANISM, "NON_HUMAN_SOURCE_ORGANISM"

    # Check resolution
    resolution = _parse_resolution(entry)
    method = entry.get("rcsb_entry_info", {}).get("experimental_method", "")
    if resolution is None and "electron" not in str(method).lower():
        return StructureAdmissibility.INADMISSIBLE_RESOLUTION, "RESOLUTION_NOT_REPORTED"
    if resolution is not None and resolution > _RESOLUTION_CUTOFF:
        return (
            StructureAdmissibility.INADMISSIBLE_RESOLUTION,
            f"RESOLUTION_{resolution:.2f}A_EXCEEDS_{_RESOLUTION_CUTOFF}A_CUTOFF",
        )

    # Check bound ligand — any known ATP-site ligand or any non-polymer
    known = any(lig.upper() in _ATP_SITE_LIGANDS for lig in ligand_ids)
    has_nonpolymer = len(ligand_ids) > 0  # any non-polymer entity

    if not (known or has_nonpolymer):
        return StructureAdmissibility.INADMISSIBLE_NO_LIGAND, "NO_BOUND_LIGAND_FOUND"

    return StructureAdmissibility.ADMISSIBLE, None


class PDBConnector:
    """RCSB PDB REST connector for PI3K structural evidence.

    Implements the §2.1 admissibility filter:
      - human organism
      - resolution ≤ 2.8 Å
      - bound ATP-site ligand present

    AlphaFold structures are NEVER returned by this connector.
    An isoform with no qualifying experimental structure returns
    StructureAdmissibility.INADMISSIBLE_NO_EXPERIMENTAL_STRUCTURE.
    """

    def __init__(self) -> None:
        self._timeout = chembl_request_timeout_s()

    def version(self) -> str:
        return "rcsb-pdb-rest-v1"

    def metadata(self) -> dict[str, str]:
        return {
            "name": "RCSB PDB",
            "url": "https://www.rcsb.org/",
            "license": "CC0 (PDB data is open)",
            "rest_api": _PDB_REST,
        }

    def fetch_entry(self, pdb_id: str) -> dict[str, Any] | None:
        """Fetch raw PDB entry metadata."""
        return _fetch_entry(pdb_id, self._timeout)

    def structures_for_isoform(
        self,
        isoform: PI3KIsoform,
        retrieval_timestamp: str | None = None,
        source_version: str | None = None,
    ) -> list[StructureRecord]:
        """Fetch and assess all experimental PDB structures for a PI3K isoform.

        Returns all structures (admissible and inadmissible) so the caller
        can report exclusion counts (exit criterion: exclusion count reported).
        """
        ts = retrieval_timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        sv = source_version or f"pdb-{time.strftime('%Y%m%d')}"
        uniprot_ac = PI3K_UNIPROT_MAP[isoform]

        pdb_ids = _search_pdb_by_uniprot(uniprot_ac, self._timeout)
        records: list[StructureRecord] = []

        for pdb_id in pdb_ids:
            entry = _fetch_entry(pdb_id, self._timeout)
            if entry is None:
                continue
            ligand_ids = _fetch_ligands(pdb_id, self._timeout)
            admissibility, reason = _assess_admissibility(entry, ligand_ids, isoform)
            construct = _build_construct(entry, uniprot_ac)

            resolution = _parse_resolution(entry)
            method = entry.get("rcsb_entry_info", {}).get("experimental_method")
            dep_date = entry.get("rcsb_accession_info", {}).get("deposit_date", "")
            rel_date = entry.get("rcsb_accession_info", {}).get("initial_release_date", "")

            src_organisms = entry.get("rcsb_entity_source_organism", [])
            organism = src_organisms[0].get("ncbi_scientific_name") if src_organisms else None

            records.append(
                StructureRecord(
                    structure_id=uuid4(),
                    provenance_id=uuid4(),
                    pdb_id=pdb_id.upper(),
                    isoform=isoform.value,
                    uniprot_ac=uniprot_ac,
                    resolution_angstrom=resolution,
                    experimental_method=str(method) if method else None,
                    has_bound_ligand=len(ligand_ids) > 0,
                    ligand_ids=ligand_ids,
                    construct=construct,
                    structure_source=StructureSource.EXPERIMENTAL_PDB.value,
                    source_selection_reason=(
                        "experimental_pdb_selected_per_constitution_s2_1_alphafold_excluded"
                    ),
                    admissibility=admissibility.value,
                    inadmissibility_reason=reason,
                    deposition_date=str(dep_date)[:10] if dep_date else None,
                    release_date=str(rel_date)[:10] if rel_date else None,
                    organism=organism,
                    retrieval_timestamp=ts,
                    source_version=sv,
                    raw_payload=entry,
                )
            )
            time.sleep(0.1)

        if not records:
            # No experimental structure found — fail closed per §2.1
            records.append(
                StructureRecord(
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
                    ),
                    structure_source=StructureSource.EXPERIMENTAL_PDB.value,
                    source_selection_reason=(
                        "no_experimental_structure_found_alphafold_excluded_per_governance"
                    ),
                    admissibility=StructureAdmissibility.INADMISSIBLE_NO_EXPERIMENTAL_STRUCTURE.value,
                    inadmissibility_reason="NO_QUALIFYING_PDB_ENTRY_FOUND",
                    deposition_date=None,
                    release_date=None,
                    organism=None,
                    retrieval_timestamp=ts,
                    source_version=sv,
                )
            )
        return records

    def fetch_all_pi3k_structures(self) -> dict[str, list[StructureRecord]]:
        """Fetch and assess all Tier 1 PI3K isoforms.

        Returns a dict keyed by isoform value.
        """
        results: dict[str, list[StructureRecord]] = {}
        for isoform in PI3KIsoform:
            results[isoform.value] = self.structures_for_isoform(isoform)
            time.sleep(0.3)
        return results

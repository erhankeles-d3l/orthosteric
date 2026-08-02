"""BindingDB REST connector.

Objective: SCI0-006.
ADR-0003 §2: BindingDB is an approved source.

BindingDB exposes a REST API at https://www.bindingdb.org/axis2/services/BDBService
and a web search at https://www.bindingdb.org/rwd/bind/byUniProt.jsp.

The preferred retrieval path is the UniProt-based REST endpoint, which maps
cleanly to our Tier structure.  Tier is assigned via UniProt accession.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any

from orthosteric.data.config import chembl_request_timeout_s
from orthosteric.data.sources._base import Admissibility, RawSourceRecord, SourceConnector
from orthosteric.data.sources._tier_map import (
    admissibility_for_gene,
    admissibility_for_uniprot,
)

_SOURCE_DB = "bindingdb"
_BDB_BASE = "https://www.bindingdb.org/axis2/services/BDBService"


def _get_json(url: str, timeout: int) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        result: Any = json.loads(resp.read())
        return result


def _admissibility_for_bdb_record(rec: dict[str, Any]) -> tuple[Admissibility, str | None]:
    """Determine tier from available identifiers in a BindingDB record."""
    # Try UniProt accession first (most reliable)
    for field in ("UniProt (Swissprot) Primary ID of Target Chain", "UniProt_ChainID", "UniProt"):
        uid = rec.get(field, "")
        if uid and uid.strip():
            adm = admissibility_for_uniprot(uid.strip().split("-")[0])  # strip isoform suffix
            if adm != Admissibility.INADMISSIBLE:
                return adm, None

    # Fall back to target name / gene symbol
    for field in ("Target Name Assigned by Submitter", "Gene Name (Entrez)", "Target Name"):
        name = rec.get(field, "")
        if name and name.strip():
            adm = admissibility_for_gene(name.strip())
            if adm != Admissibility.INADMISSIBLE:
                return adm, None

    return Admissibility.INADMISSIBLE, "NO_KNOWN_PI3K_TARGET_IDENTIFIER"


def _parse_bdb_record(
    rec: dict[str, Any], source_version: str, retrieval_timestamp: str
) -> RawSourceRecord:
    admissibility, inadmissibility_reason = _admissibility_for_bdb_record(rec)

    # Require a numeric Ki or IC50
    value_str: str | None = None
    activity_type: str | None = None
    for atype, field in [
        ("Ki", "Ki (nM)"),
        ("IC50", "IC50 (nM)"),
        ("Kd", "Kd (nM)"),
        ("EC50", "EC50 (nM)"),
    ]:
        raw = rec.get(field, "")
        if raw and raw.strip() and raw.strip() not in ("", "N/A", "NA"):
            value_str = raw.strip()
            activity_type = atype
            break

    if value_str is None and admissibility != Admissibility.INADMISSIBLE:
        admissibility = Admissibility.INADMISSIBLE
        inadmissibility_reason = "NO_USABLE_ACTIVITY_VALUE"

    # Extract relation prefix
    relation = "="
    if value_str and value_str.startswith(">"):
        relation = ">"
        value_str = value_str.lstrip(">").strip()
    elif value_str and value_str.startswith("<"):
        relation = "<"
        value_str = value_str.lstrip("<").strip()

    units = "nM" if activity_type else None

    return RawSourceRecord(
        source_db=_SOURCE_DB,
        source_record_id=rec.get("BindingDB MonomerID", rec.get("Monomer", "")),
        source_version=source_version,
        retrieval_timestamp=retrieval_timestamp,
        admissibility=admissibility,
        inadmissibility_reason=inadmissibility_reason,
        target_id=rec.get("UniProt (Swissprot) Primary ID of Target Chain")
        or rec.get("Target Name"),
        target_name=rec.get("Target Name Assigned by Submitter") or rec.get("Target Name"),
        compound_id=rec.get("BindingDB Reactant_set_id"),
        smiles=rec.get("Ligand SMILES"),
        inchikey=rec.get("Ligand InChI Key"),
        activity_type=activity_type,
        activity_value=value_str,
        activity_units=units,
        activity_relation=relation,
        assay_id=None,
        assay_description=None,
        assay_type="biochemical",
        atp_concentration_um=None,
        organism=rec.get("Target Source Organism According to Curator or DataSource"),
        publication_id=rec.get("PubMed ID") or rec.get("DOI"),
        raw_payload=rec,
    )


class BindingDBConnector(SourceConnector):
    """BindingDB connector for PI3K bioactivity data.

    Uses the UniProt-based REST endpoint for targeted retrieval.
    Falls back to target-name search when UniProt ACs are unavailable.
    """

    def __init__(self) -> None:
        self._timeout = chembl_request_timeout_s()
        self._version_cache: str | None = None

    def version(self) -> str:
        """BindingDB does not expose a machine-readable version endpoint.
        Returns 'current' with the retrieval date embedded.
        """
        if self._version_cache is not None:
            return self._version_cache
        self._version_cache = f"current-{time.strftime('%Y%m%d')}"
        return self._version_cache

    def metadata(self) -> dict[str, str]:
        return {
            "name": "BindingDB",
            "url": "https://www.bindingdb.org/",
            "license": "CC-BY 3.0",
            "api_base": _BDB_BASE,
            "version": self.version(),
        }

    def search(self, query: str, **_kwargs: Any) -> list[RawSourceRecord]:
        """Search BindingDB by target name via the JSON REST API."""
        url = (
            f"{_BDB_BASE}/getLigandsByTargetPrefName"
            f"?targetname={urllib.parse.quote(query)}&response=json"
        )
        try:
            data = _get_json(url, self._timeout)
        except Exception:
            return []
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        version = self.version()
        affinities = data.get("affinities", []) if isinstance(data, dict) else []
        return [_parse_bdb_record(r, version, ts) for r in affinities]

    def fetch(self, record_id: str) -> RawSourceRecord:
        """Fetch a single record by BindingDB MonomerID."""
        url = (
            f"{_BDB_BASE}/getLigandsByMonomerID"
            f"?monomerid={urllib.parse.quote(record_id)}&response=json"
        )
        data = _get_json(url, self._timeout)
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        affinities = data.get("affinities", []) if isinstance(data, dict) else []
        if not affinities:
            return RawSourceRecord(
                source_db=_SOURCE_DB,
                source_record_id=record_id,
                source_version=self.version(),
                retrieval_timestamp=ts,
                admissibility=Admissibility.INADMISSIBLE,
                inadmissibility_reason="RECORD_NOT_FOUND",
            )
        return _parse_bdb_record(affinities[0], self.version(), ts)

    def download(self, target_ids: list[str], **kwargs: Any) -> list[RawSourceRecord]:
        """Download BindingDB records by UniProt accession list."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        version = self.version()
        records: list[RawSourceRecord] = []
        for uid in target_ids:
            url = (
                f"{_BDB_BASE}/getLigandsByUniprotID?uniprot={urllib.parse.quote(uid)}&response=json"
            )
            try:
                data = _get_json(url, self._timeout)
            except Exception:
                continue
            affinities = data.get("affinities", []) if isinstance(data, dict) else []
            for rec in affinities:
                records.append(_parse_bdb_record(rec, version, ts))
        return records

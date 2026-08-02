"""PubChem BioAssay connector.

Objective: SCI0-006.
ADR-0003 §2: PubChem BioAssay is an approved source.

PubChem exposes the PUG REST API.  The most targeted route for PI3K
bioactivity is to query by gene target name and retrieve AID-level
bioassay data.

Tier is assigned using gene-symbol lookup from _tier_map.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any

from orthosteric.data.config import chembl_request_timeout_s
from orthosteric.data.sources._base import Admissibility, RawSourceRecord, SourceConnector
from orthosteric.data.sources._tier_map import admissibility_for_gene

_SOURCE_DB = "pubchem"
_PUG_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def _get_json(url: str, timeout: int) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        result: Any = json.loads(resp.read())
        return result


def _parse_pubchem_record(
    rec: dict[str, Any],
    gene_name: str,
    aid: str,
    source_version: str,
    retrieval_timestamp: str,
) -> RawSourceRecord:
    admissibility = admissibility_for_gene(gene_name)
    inadmissibility_reason: str | None = None

    if admissibility == Admissibility.INADMISSIBLE:
        inadmissibility_reason = f"INADMISSIBLE_TARGET:{gene_name}"

    # PubChem activity data fields vary by assay; extract common names
    activity_value: str | None = None
    activity_type: str | None = None
    activity_relation: str = "="

    # Try standard field names used in PubChem bioassay JSON
    for ftype, fkey in [
        ("IC50", "IC50"),
        ("Ki", "Ki"),
        ("AC50", "IC50"),  # AC50 treated as IC50
        ("Inhibition", None),
    ]:
        val = rec.get(fkey or ftype)
        if val is not None:
            activity_value = str(val)
            activity_type = ftype
            break

    # Also check the generic "activity" key used in some exports
    if activity_value is None:
        av = rec.get("ActivityValue")
        if av is not None:
            activity_value = str(av)
            activity_type = rec.get("ActivityType", "activity")

    if activity_value is None and admissibility != Admissibility.INADMISSIBLE:
        admissibility = Admissibility.INADMISSIBLE
        inadmissibility_reason = "NO_USABLE_ACTIVITY_VALUE"

    # Outcome field: "Active", "Inactive", "Inconclusive"
    outcome = rec.get("ActivityOutcome") or rec.get("Outcome", "")
    if outcome.lower() == "inactive" and activity_value is None:
        # Right-censored inactive with no explicit value
        activity_value = rec.get("Threshold") or "10000"  # assay-defined threshold
        activity_type = "IC50"
        activity_relation = ">"

    return RawSourceRecord(
        source_db=_SOURCE_DB,
        source_record_id=str(rec.get("SID", rec.get("CID", ""))),
        source_version=source_version,
        retrieval_timestamp=retrieval_timestamp,
        admissibility=admissibility,
        inadmissibility_reason=inadmissibility_reason,
        target_id=aid,
        target_name=gene_name,
        compound_id=str(rec.get("CID", "")),
        smiles=rec.get("CanonicalSMILES") or rec.get("IsomericSMILES"),
        inchikey=rec.get("InChIKey"),
        activity_type=activity_type,
        activity_value=activity_value,
        activity_units=rec.get("Units", "nM"),
        activity_relation=activity_relation,
        assay_id=aid,
        assay_description=None,
        assay_type="biochemical",
        atp_concentration_um=None,
        organism=rec.get("Organism", "Homo sapiens"),
        publication_id=None,
        raw_payload=rec,
    )


class PubChemConnector(SourceConnector):
    """PubChem BioAssay connector for PI3K bioactivity data.

    Uses the PUG REST API to retrieve bioassay data by gene target.
    Tier is assigned by gene-name lookup.
    """

    def __init__(self) -> None:
        self._timeout = chembl_request_timeout_s()
        self._version_cache: str | None = None

    def version(self) -> str:
        """PubChem does not expose a release version endpoint.
        Returns 'current' with the retrieval date.
        """
        if self._version_cache is not None:
            return self._version_cache
        self._version_cache = f"current-{time.strftime('%Y%m%d')}"
        return self._version_cache

    def metadata(self) -> dict[str, str]:
        return {
            "name": "PubChem BioAssay",
            "url": "https://pubchem.ncbi.nlm.nih.gov/",
            "license": "public domain",
            "api_base": _PUG_BASE,
            "version": self.version(),
        }

    def search(self, query: str, **kwargs: Any) -> list[RawSourceRecord]:
        """Search PubChem BioAssay by gene name.

        Returns AID list for the gene, then downloads a sample of records.
        """
        url = f"{_PUG_BASE}/assay/target/genesymbol/{urllib.parse.quote(query)}/aids/JSON"
        try:
            data = _get_json(url, self._timeout)
        except Exception:
            return []
        aids = data.get("IdentifierList", {}).get("AID", [])
        if not aids:
            return []
        # Download the first AID as a representative sample
        return self.download([str(aids[0])], gene_name=query, **kwargs)

    def fetch(self, record_id: str) -> RawSourceRecord:
        """Fetch a single PubChem record by SID."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return RawSourceRecord(
            source_db=_SOURCE_DB,
            source_record_id=record_id,
            source_version=self.version(),
            retrieval_timestamp=ts,
            admissibility=Admissibility.INADMISSIBLE,
            inadmissibility_reason="SINGLE_SID_FETCH_NOT_IMPLEMENTED_USE_DOWNLOAD",
        )

    def download(self, target_ids: list[str], **kwargs: Any) -> list[RawSourceRecord]:
        """Download PubChem bioassay records for a list of AIDs.

        ``gene_name`` keyword argument is used for tier assignment when
        the assay record itself does not contain a gene symbol.
        """
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        version = self.version()
        gene_name: str = kwargs.get("gene_name", "")
        records: list[RawSourceRecord] = []

        for aid in target_ids:
            url = f"{_PUG_BASE}/assay/aid/{urllib.parse.quote(str(aid))}/concise/JSON"
            try:
                data = _get_json(url, self._timeout)
            except Exception:
                continue
            table = data.get("Table", {})
            columns = table.get("Columns", {}).get("Column", [])
            rows = table.get("Row", [])
            for row in rows:
                cells = row.get("Cell", [])
                rec = dict(zip(columns, cells, strict=False))
                # Attach gene name for tier lookup if not in record
                if gene_name and "GeneSymbol" not in rec:
                    rec["GeneSymbol"] = gene_name
                effective_gene = rec.get("GeneSymbol", gene_name)
                records.append(_parse_pubchem_record(rec, effective_gene, str(aid), version, ts))
        return records

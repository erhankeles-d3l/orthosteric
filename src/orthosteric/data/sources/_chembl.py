"""ChEMBL REST API connector.

Objective: SCI0-006.
ADR-0003 §2: ChEMBL is an approved source.
Constitution §0.4: Tier 2 records are flagged at ingestion.

This connector replaces the prototype in chembl_adapter.py for the
SCI0-006 production sources layer.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any

from orthosteric.data.config import (
    chembl_api_base,
    chembl_max_per_isoform,
    chembl_page_size,
    chembl_request_timeout_s,
)
from orthosteric.data.sources._base import Admissibility, RawSourceRecord, SourceConnector
from orthosteric.data.sources._tier_map import admissibility_for_chembl_target

_SOURCE_DB = "chembl"


def _get_json(url: str, timeout: int, retries: int = 3) -> dict[str, Any]:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                result: dict[str, Any] = json.loads(resp.read())
                return result
        except Exception:
            if attempt < retries - 1:
                time.sleep(2**attempt)
            else:
                raise
    raise RuntimeError(f"Failed to fetch {url}")  # pragma: no cover


def _parse_activity(
    act: dict[str, Any],
    chembl_target_id: str,
    source_version: str,
    retrieval_timestamp: str,
) -> RawSourceRecord:
    """Parse one ChEMBL activity record into a RawSourceRecord."""
    admissibility = admissibility_for_chembl_target(chembl_target_id)

    # Structural validation: reject records without a usable value
    inadmissibility_reason: str | None = None
    if admissibility == Admissibility.INADMISSIBLE:
        inadmissibility_reason = f"INADMISSIBLE_TARGET:{chembl_target_id}"
    elif act.get("canonical_smiles") is None:
        admissibility = Admissibility.INADMISSIBLE
        inadmissibility_reason = "NO_STRUCTURE"
    else:
        try:
            float(act.get("value") or "")
        except (TypeError, ValueError):
            admissibility = Admissibility.INADMISSIBLE
            inadmissibility_reason = "NONNUMERIC_VALUE"

    return RawSourceRecord(
        source_db=_SOURCE_DB,
        source_record_id=str(act.get("activity_id", "")),
        source_version=source_version,
        retrieval_timestamp=retrieval_timestamp,
        admissibility=admissibility,
        inadmissibility_reason=inadmissibility_reason,
        target_id=chembl_target_id,
        target_name=act.get("target_pref_name"),
        compound_id=act.get("molecule_chembl_id"),
        smiles=act.get("canonical_smiles"),
        inchikey=None,  # requires a separate molecule lookup; deferred to SCI0-008c
        activity_type=act.get("standard_type"),
        activity_value=str(act["value"]) if act.get("value") is not None else None,
        activity_units=act.get("units"),
        activity_relation=act.get("standard_relation") or "=",
        assay_id=act.get("assay_chembl_id"),
        assay_description=None,  # not in activity endpoint; in assay endpoint
        assay_type=act.get("assay_type"),
        atp_concentration_um=None,  # ChEMBL does not standardly report [ATP]
        organism="Homo sapiens",
        publication_id=act.get("document_chembl_id"),
        raw_payload=act,
    )


class ChEMBLConnector(SourceConnector):
    """ChEMBL REST API connector for PI3K bioactivity data.

    All methods return RawSourceRecord with tier already assigned.
    No ChEMBL-specific type crosses the module boundary.
    """

    def __init__(self) -> None:
        self._api_base = chembl_api_base()
        self._page_size = chembl_page_size()
        self._timeout = chembl_request_timeout_s()
        self._max_per_target = chembl_max_per_isoform()
        self._version_cache: str | None = None

    def version(self) -> str:
        if self._version_cache is not None:
            return self._version_cache
        url = f"{self._api_base}/status/?format=json"
        try:
            data = _get_json(url, self._timeout)
            v: str = data.get("chembl_db_version", "unknown")
            self._version_cache = v
            return v
        except Exception:
            return "unknown"

    def metadata(self) -> dict[str, str]:
        return {
            "name": "ChEMBL",
            "url": "https://www.ebi.ac.uk/chembl/",
            "license": "CC-BY-SA 3.0",
            "api_base": self._api_base,
            "version": self.version(),
        }

    def search(self, query: str, **kwargs: Any) -> list[RawSourceRecord]:
        """Search ChEMBL by target name. Returns tier-assigned records."""
        url = (
            f"{self._api_base}/target/search/?q={urllib.parse.quote(query)}"
            f"&format=json&limit={self._page_size}"
        )
        data = _get_json(url, self._timeout)
        targets = data.get("targets", [])
        if not targets:
            return []
        target_ids = [t["target_chembl_id"] for t in targets if "target_chembl_id" in t]
        return self.download(target_ids, **kwargs)

    def fetch(self, record_id: str) -> RawSourceRecord:
        """Fetch a single activity record by its ChEMBL activity_id."""
        url = f"{self._api_base}/activity/{record_id}/?format=json"
        data = _get_json(url, self._timeout)
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        # We need the target ID to assign tier; it's in the activity record
        target_id = data.get("target_chembl_id", "UNKNOWN")
        return _parse_activity(data, target_id, self.version(), ts)

    def download(self, target_ids: list[str], **kwargs: Any) -> list[RawSourceRecord]:
        """Download bioactivity records for a list of ChEMBL target IDs.

        Tier is assigned per-record at ingestion.  Inadmissible targets are
        returned with admissibility=INADMISSIBLE; they are not silently dropped.
        """
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        version = self.version()
        records: list[RawSourceRecord] = []
        max_per = kwargs.get("max_per_target", self._max_per_target)

        for target_id in target_ids:
            offset = 0
            fetched = 0
            while fetched < max_per:
                params = urllib.parse.urlencode(
                    {
                        "target_chembl_id": target_id,
                        "limit": self._page_size,
                        "offset": offset,
                        "format": "json",
                    }
                )
                url = f"{self._api_base}/activity/?{params}"
                try:
                    data = _get_json(url, self._timeout)
                except Exception:
                    break
                activities = data.get("activities", [])
                if not activities:
                    break
                for act in activities:
                    records.append(_parse_activity(act, target_id, version, ts))
                fetched += len(activities)
                if len(activities) < self._page_size:
                    break
                offset += self._page_size

        return records

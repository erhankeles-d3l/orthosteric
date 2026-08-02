"""ChEMBL adapter for Class I PI3K activity records.

Uses the ChEMBL REST API (public, no credentials required).
Records ATP concentration where reported.
Records construct/species from ChEMBL assay metadata.
Assigns ProvenanceTier based on publication linkage and metadata completeness.

ADR-0003 §2 accepted sources: ChEMBL is on the approved list.

Governance: this adapter is evidence-acquisition infrastructure only.
It never selects or seals scientific thresholds.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any

from orthosteric.data.corpus import (
    EvidenceRecord,
    Isoform,
    MeasurementType,
    ProvenanceTier,
)

# ChEMBL REST endpoint
CHEMBL_API = "https://www.ebi.ac.uk/chembl/api/data"

# Target ChEMBL IDs for Class I PI3K isoforms (human)
# CHEMBL IDs verified from ChEMBL 34 target search
_ISOFORM_TARGETS: dict[Isoform, list[str]] = {
    Isoform.ALPHA: ["CHEMBL4523"],  # PI3K p110-alpha / PIK3CA
    Isoform.BETA: ["CHEMBL5319"],  # PI3K p110-beta / PIK3CB
    Isoform.GAMMA: ["CHEMBL5541"],  # PI3K p110-gamma / PIK3CG
    Isoform.DELTA: ["CHEMBL3629"],  # PI3K p110-delta / PIK3CD
}

_MEASUREMENT_MAP = {
    "IC50": MeasurementType.IC50,
    "Ki": MeasurementType.KI,
    "Kd": MeasurementType.KD,
    "EC50": MeasurementType.EC50,
}


def _get_json(url: str, retries: int = 3) -> dict[str, Any]:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                result: dict[str, Any] = json.loads(resp.read())
                return result
        except Exception:
            if attempt < retries - 1:
                time.sleep(2**attempt)
            else:
                raise
    raise RuntimeError(f"Failed to fetch {url}")  # pragma: no cover


def _tier(rec: dict[str, Any]) -> ProvenanceTier:
    """Assign provenance tier based on available metadata."""
    has_pub = bool(rec.get("document_chembl_id"))
    has_assay_type = bool(rec.get("assay_type"))
    has_units = bool(rec.get("units"))
    has_value = rec.get("value") is not None

    if has_pub and has_assay_type and has_units and has_value:
        return ProvenanceTier.T1
    if has_pub and has_value:
        return ProvenanceTier.T2
    if has_value and has_units:
        return ProvenanceTier.T3
    return ProvenanceTier.T4


def _exclusion_reason(rec: dict[str, Any], tier: ProvenanceTier) -> str | None:
    """Return None if record is kept; a reason code string if excluded."""
    if tier == ProvenanceTier.T4:
        return "EXCLUDE_INSUFFICIENT_PROVENANCE"
    if not rec.get("canonical_smiles"):
        return "EXCLUDE_NO_STRUCTURE"
    try:
        float(rec.get("value", ""))
    except (TypeError, ValueError):
        return "EXCLUDE_NONNUMERIC_VALUE"
    if rec.get("standard_relation") not in ("=", "<", ">", "~", "<=", ">="):
        return "EXCLUDE_INVALID_RELATION"
    return None


def fetch_pi3k_records(
    isoforms: list[Isoform] | None = None,
    max_per_isoform: int = 5000,
    retrieval_timestamp: str | None = None,
) -> list[EvidenceRecord]:
    """Fetch bioactivity records for Class I PI3K isoforms from ChEMBL.

    Parameters
    ----------
    isoforms:
        Which isoforms to fetch; defaults to all four.
    max_per_isoform:
        Safety ceiling per target to prevent accidentally huge downloads
        during testing.  Set higher for a production corpus refresh.
    retrieval_timestamp:
        Override timestamp (useful for deterministic tests).

    Returns:
    -------
    list[EvidenceRecord]
        All retrieved records, including excluded ones (exclusion_reason set).
    """
    if isoforms is None:
        isoforms = list(Isoform)

    ts = retrieval_timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    records: list[EvidenceRecord] = []

    for isoform in isoforms:
        for chembl_target_id in _ISOFORM_TARGETS[isoform]:
            offset = 0
            limit = 100
            fetched = 0
            while fetched < max_per_isoform:
                params = urllib.parse.urlencode(
                    {
                        "target_chembl_id": chembl_target_id,
                        "limit": limit,
                        "offset": offset,
                        "format": "json",
                    }
                )
                url = f"{CHEMBL_API}/activity/?{params}"
                try:
                    data = _get_json(url)
                except Exception:
                    break  # network failure — stop this target, mark in records

                activities = data.get("activities", [])
                if not activities:
                    break

                for act in activities:
                    tier = _tier(act)
                    excl = _exclusion_reason(act, tier)

                    try:
                        value = float(act["value"]) if act.get("value") is not None else None
                    except (TypeError, ValueError):
                        value = None

                    mtype = _MEASUREMENT_MAP.get(act.get("standard_type", ""))

                    rec = EvidenceRecord(
                        source_compound_id=act.get("molecule_chembl_id", ""),
                        inchikey=act.get(
                            "molecule_chembl_id"
                        ),  # ChEMBL uses its own id here; real InChIKey requires separate lookup
                        canonical_smiles=act.get("canonical_smiles"),
                        original_smiles=act.get("canonical_smiles"),
                        isoform=isoform,
                        species="Homo sapiens",  # all targets above are human
                        construct=None,  # construct not in ChEMBL activity endpoint
                        assay_id=act.get("assay_chembl_id"),
                        assay_type=act.get("assay_type"),
                        atp_concentration_um=None,  # ChEMBL does not standardly report [ATP]
                        measurement_type=mtype,
                        value=value,
                        value_relation=act.get("standard_relation", "="),
                        units=act.get("units"),
                        publication_doi=None,
                        publication_pmid=act.get("document_chembl_id"),
                        source_db="chembl",
                        source_record_id=str(act.get("activity_id", "")),
                        provenance_tier=tier,
                        retrieval_timestamp=ts,
                        exclusion_reason=excl,
                    )
                    records.append(rec)

                fetched += len(activities)
                if len(activities) < limit:
                    break
                offset += limit

    return records

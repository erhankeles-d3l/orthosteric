"""PMC Open Access full-text connector.

Objective: SCI0-006b.
PMC-OA provides XML full text for open-access articles.
Only OA articles with TDM permission are processed.
Full text is stored for span verification; it is never used to
generate values without a locatable anchor.

Extraction priority (spec-binding order):
  1  Supplementary tables    — highest yield, most structured
  2  Main manuscript tables
  3  Structured assay sections
  4  Free-text paragraphs    — fallback only
"""

from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from orthosteric.data.config import chembl_request_timeout_s
from orthosteric.data.sources.literature._extractor import (
    ExtractionStatus,
    LiteratureExtractionRecord,
    verify_span,
)

_PMC_OA_BASE = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
_PMC_FETCH_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_EMAIL = "orthosteric-data-pipeline@project.internal"
_TOOL = "OrthostericDataPipeline"

# Simplified activity pattern: captures value + relation + units from table cells
_ACTIVITY_PATTERN = re.compile(
    r"(?P<relation>[<>=]{0,2})\s*(?P<value>\d[\d.,]+)\s*(?P<units>nM|µM|uM|μM|pM|mM)",
    re.IGNORECASE,
)


@dataclass
class PMCFullText:
    """Full-text content for one PMC article."""

    pmcid: str
    doi: str | None
    full_text: str
    has_supplementary: bool
    license_url: str | None
    tdm_permitted: bool
    raw_payload: dict[str, Any]


def _tdm_permitted_from_license(license_url: str | None) -> bool:
    if license_url is None:
        return False
    return any(
        cc in license_url.lower()
        for cc in ("creativecommons.org/licenses/by", "creativecommons.org/publicdomain/zero")
    )


class PMCConnector:
    """PMC Open Access full-text connector.

    Provides full text and supports span-based extraction and verification.
    Only processes articles with TDM-permitted licenses.
    """

    def __init__(self) -> None:
        self._timeout = chembl_request_timeout_s()

    def version(self) -> str:
        return "pmc-oa-v1"

    def metadata(self) -> dict[str, str]:
        return {
            "name": "PMC Open Access",
            "url": "https://www.ncbi.nlm.nih.gov/pmc/",
            "license": "varies per article; only CC-BY/CC0 articles processed",
        }

    def fetch_oa_url(self, pmcid: str) -> str | None:
        """Fetch the OA download URL for a PMCID, or None if not OA."""
        params = urllib.parse.urlencode({"id": pmcid, "format": "xml"})
        url = f"{_PMC_OA_BASE}?{params}"
        try:
            with urllib.request.urlopen(url, timeout=self._timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            # Parse the <link format="xml" href="..."> element
            match = re.search(r'href="([^"]+\.xml[^"]*)"', text)
            return match.group(1) if match else None
        except Exception:
            return None

    def fetch_full_text(self, pmcid: str) -> PMCFullText | None:
        """Fetch full text for a PMCID.

        Returns None if the article is not OA or full text is unavailable.
        Never attempts to fetch restricted articles.
        """
        # Check OA status first via the OA API
        oa_url = self.fetch_oa_url(pmcid)
        if oa_url is None:
            return None

        # Fetch the XML
        try:
            with urllib.request.urlopen(oa_url, timeout=self._timeout) as resp:
                xml_bytes = resp.read()
        except Exception:
            return None

        xml_text = xml_bytes.decode("utf-8", errors="replace")

        # Extract license from the XML
        license_match = re.search(r"<license[^>]*>(.*?)</license>", xml_text, re.DOTALL)
        license_text = license_match.group(1) if license_match else ""
        license_url_match = re.search(r'href="([^"]+)"', license_text)
        license_url = license_url_match.group(1) if license_url_match else None
        tdm = _tdm_permitted_from_license(license_url)

        has_supp = bool(re.search(r"<supplementary-material", xml_text, re.IGNORECASE))

        return PMCFullText(
            pmcid=pmcid,
            doi=None,  # extracted separately via CrossRef
            full_text=xml_text,
            has_supplementary=has_supp,
            license_url=license_url,
            tdm_permitted=tdm,
            raw_payload={"pmcid": pmcid, "oa_url": oa_url},
        )

    def extract_activity_candidates(
        self,
        full_text_obj: PMCFullText,
        doi: str | None = None,
        pmid: str | None = None,
    ) -> list[LiteratureExtractionRecord]:
        """Extract activity value candidates with extraction tier and locator.

        Extraction priority order per spec:
          1. Supplementary tables
          2. Main manuscript tables
          3. Assay sections
          4. Free text (fallback)

        Returns CANDIDATE records; caller must call verify_span() on each.
        """
        if not full_text_obj.tdm_permitted:
            return []

        xml = full_text_obj.full_text
        records: list[LiteratureExtractionRecord] = []
        doi_val = doi or full_text_obj.doi or "unknown"

        # Extract tables (covers tiers 1 and 2)
        tables = re.findall(
            r'(<table-wrap[^>]*id="([^"]*)"[^>]*>.*?</table-wrap>)',
            xml,
            re.DOTALL | re.IGNORECASE,
        )
        for table_xml, table_id in tables:
            tier = (
                "supplementary_table"
                if "supp" in table_id.lower() or table_id[:1].lower() == "s"
                else "manuscript_table"
            )
            # Extract rows
            rows = re.findall(r"<tr>(.*?)</tr>", table_xml, re.DOTALL | re.IGNORECASE)
            for row_idx, row in enumerate(rows):
                cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL | re.IGNORECASE)
                row_text = " | ".join(re.sub(r"<[^>]+>", "", c).strip() for c in cells)
                for m in _ACTIVITY_PATTERN.finditer(row_text):
                    raw = m.group(0).strip()
                    records.append(
                        LiteratureExtractionRecord(
                            doi=doi_val,
                            pmid=pmid,
                            pmcid=full_text_obj.pmcid,
                            extraction_tier=tier,
                            locator_id=table_id,
                            row_or_line=str(row_idx),
                            raw_value_text=raw,
                            extracted_value=m.group("value").replace(",", ""),
                            extracted_relation=m.group("relation") or "=",
                            extracted_units=m.group("units"),
                            target_text=None,
                            compound_text=None,
                            assay_text=None,
                            atp_text=None,
                            status=ExtractionStatus.CANDIDATE,
                            tdm_permitted=full_text_obj.tdm_permitted,
                            license=full_text_obj.license_url,
                            raw_payload={"table_id": table_id, "row": row_idx},
                        )
                    )

        # Extract assay sections (tier 3)
        sections = re.findall(
            r'<sec[^>]*sec-type="methods"[^>]*>(.*?)</sec>',
            xml,
            re.DOTALL | re.IGNORECASE,
        )
        for sec_idx, section in enumerate(sections):
            sec_id = f"methods_section_{sec_idx}"
            for m in _ACTIVITY_PATTERN.finditer(section):
                raw = m.group(0).strip()
                records.append(
                    LiteratureExtractionRecord(
                        doi=doi_val,
                        pmid=pmid,
                        pmcid=full_text_obj.pmcid,
                        extraction_tier="assay_section",
                        locator_id=sec_id,
                        row_or_line=None,
                        raw_value_text=raw,
                        extracted_value=m.group("value").replace(",", ""),
                        extracted_relation=m.group("relation") or "=",
                        extracted_units=m.group("units"),
                        target_text=None,
                        compound_text=None,
                        assay_text=None,
                        atp_text=None,
                        status=ExtractionStatus.CANDIDATE,
                        tdm_permitted=full_text_obj.tdm_permitted,
                        license=full_text_obj.license_url,
                        raw_payload={"section": "methods", "idx": sec_idx},
                    )
                )

        # Free-text fallback (tier 4) — only if no table/section extractions
        if not records:
            for m in _ACTIVITY_PATTERN.finditer(xml):
                raw = m.group(0).strip()
                start = max(0, m.start() - 100)
                locator = f"free_text_offset_{m.start()}"
                records.append(
                    LiteratureExtractionRecord(
                        doi=doi_val,
                        pmid=pmid,
                        pmcid=full_text_obj.pmcid,
                        extraction_tier="free_text",
                        locator_id=locator,
                        row_or_line=None,
                        raw_value_text=raw,
                        extracted_value=m.group("value").replace(",", ""),
                        extracted_relation=m.group("relation") or "=",
                        extracted_units=m.group("units"),
                        target_text=None,
                        compound_text=None,
                        assay_text=None,
                        atp_text=None,
                        status=ExtractionStatus.CANDIDATE,
                        tdm_permitted=full_text_obj.tdm_permitted,
                        license=full_text_obj.license_url,
                        raw_payload={"offset": m.start(), "context": xml[start : m.start() + 200]},
                    )
                )

        # Apply span verification immediately
        return [verify_span(r, xml) for r in records]

    def batch_process(
        self,
        pmcids: list[str],
        dois: dict[str, str] | None = None,
        pmids: dict[str, str] | None = None,
    ) -> list[LiteratureExtractionRecord]:
        """Process a list of PMCIDs: fetch, extract, verify."""
        all_records: list[LiteratureExtractionRecord] = []
        for pmcid in pmcids:
            ft = self.fetch_full_text(pmcid)
            if ft is None:
                continue
            doi = (dois or {}).get(pmcid)
            pmid = (pmids or {}).get(pmcid)
            records = self.extract_activity_candidates(ft, doi=doi, pmid=pmid)
            all_records.extend(records)
            time.sleep(0.35)
        return all_records

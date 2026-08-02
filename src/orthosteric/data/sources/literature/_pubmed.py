"""PubMed connector for article metadata and MeSH terms.

Objective: SCI0-006b.
PubMed/NCBI E-utilities: free, no auth required for low-volume queries.
Polite use: < 3 requests/second; add email to User-Agent.

PubMed provides: title, abstract, PMID, PMCID, MeSH, publication year,
journal, and whether the article is in PMC (which indicates OA candidacy).
It does NOT provide full text; PMC-OA does.
"""

from __future__ import annotations

import contextlib
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from orthosteric.data.config import chembl_request_timeout_s

_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_EMAIL = "orthosteric-data-pipeline@project.internal"
_TOOL = "OrthostericDataPipeline"


@dataclass
class PubMedRecord:
    """PubMed article metadata."""

    pmid: str
    pmcid: str | None
    doi: str | None
    title: str | None
    abstract: str | None
    journal: str | None
    year: int | None
    mesh_terms: list[str]
    in_pmc: bool
    raw_payload: dict[str, Any] = field(default_factory=dict)


def _parse_article(article: dict[str, Any]) -> PubMedRecord | None:
    medline = article.get("MedlineCitation", {})
    art = medline.get("Article", {})
    pmid_obj = medline.get("PMID", {})
    pmid = pmid_obj.get("#text", "") if isinstance(pmid_obj, dict) else str(pmid_obj)
    if not pmid:
        return None

    title_raw = art.get("ArticleTitle", "")
    title = title_raw.get("#text", title_raw) if isinstance(title_raw, dict) else str(title_raw)

    abstract_raw = art.get("Abstract", {}).get("AbstractText", "")
    if isinstance(abstract_raw, list):
        abstract = " ".join(
            x.get("#text", x) if isinstance(x, dict) else str(x) for x in abstract_raw
        )
    elif isinstance(abstract_raw, dict):
        abstract = abstract_raw.get("#text", "")
    else:
        abstract = str(abstract_raw)

    journal_raw = art.get("Journal", {}).get("Title", "")
    journal = str(journal_raw) if journal_raw else None

    pub_date = art.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
    year_str = pub_date.get("Year", pub_date.get("MedlineDate", ""))
    year: int | None = None
    with contextlib.suppress(ValueError, TypeError):
        year = int(str(year_str)[:4])

    # Extract DOI and PMCID from ArticleIdList
    doi: str | None = None
    pmcid: str | None = None
    pmc_data = article.get("PubmedData", {})
    for aid in pmc_data.get("ArticleIdList", {}).get("ArticleId", []):
        id_type = aid.get("@IdType", "") if isinstance(aid, dict) else ""
        id_val = aid.get("#text", "") if isinstance(aid, dict) else str(aid)
        if id_type == "doi":
            doi = id_val
        elif id_type == "pmc":
            pmcid = id_val

    mesh_list = medline.get("MeshHeadingList", {}).get("MeshHeading", [])
    mesh_terms = []
    for mh in mesh_list if isinstance(mesh_list, list) else [mesh_list]:
        desc = mh.get("DescriptorName", {})
        term = desc.get("#text", desc) if isinstance(desc, dict) else str(desc)
        if term:
            mesh_terms.append(term)

    return PubMedRecord(
        pmid=pmid,
        pmcid=pmcid,
        doi=doi,
        title=title,
        abstract=abstract,
        journal=journal,
        year=year,
        mesh_terms=mesh_terms,
        in_pmc=(pmcid is not None),
        raw_payload=article,
    )


class PubMedConnector:
    """PubMed E-utilities connector.

    Used in the SCI0-006b pipeline to search for PI3K publications
    and retrieve their metadata (including PMCID for OA access).
    """

    def __init__(self) -> None:
        self._timeout = chembl_request_timeout_s()

    def version(self) -> str:
        return "eutils-v2"

    def metadata(self) -> dict[str, str]:
        return {
            "name": "PubMed / NCBI E-utilities",
            "url": "https://eutils.ncbi.nlm.nih.gov/",
            "license": "public domain (US government)",
        }

    def search(self, query: str, max_results: int = 200) -> list[str]:
        """Search PubMed by query string.  Returns list of PMIDs."""
        params = urllib.parse.urlencode(
            {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "tool": _TOOL,
                "email": _EMAIL,
            }
        )
        url = f"{_EUTILS_BASE}/esearch.fcgi?{params}"
        try:
            with urllib.request.urlopen(url, timeout=self._timeout) as resp:
                data: dict[str, Any] = json.loads(resp.read())
            ids: list[str] = list(data.get("esearchresult", {}).get("idlist", []))
            return ids
        except Exception:
            return []

    def fetch(self, pmids: list[str]) -> list[PubMedRecord]:
        """Fetch full records for a list of PMIDs."""
        if not pmids:
            return []
        # E-utilities allows up to 200 PMIDs per request
        results = []
        for i in range(0, len(pmids), 200):
            batch = pmids[i : i + 200]
            params = urllib.parse.urlencode(
                {
                    "db": "pubmed",
                    "id": ",".join(batch),
                    "retmode": "json",
                    "tool": _TOOL,
                    "email": _EMAIL,
                }
            )
            url = f"{_EUTILS_BASE}/efetch.fcgi?{params}"
            try:
                with urllib.request.urlopen(url, timeout=self._timeout) as resp:
                    raw: Any = json.loads(resp.read())
                articles = raw.get("PubmedArticleSet", {}).get("PubmedArticle", [])
                if isinstance(articles, dict):
                    articles = [articles]
                for art in articles:
                    rec = _parse_article(art)
                    if rec is not None:
                        results.append(rec)
            except Exception:
                continue
            time.sleep(0.35)  # < 3 rps
        return results

    def search_pi3k(self, max_results: int = 500) -> list[PubMedRecord]:
        """Convenience: search and fetch PI3K inhibitor selectivity papers."""
        query = (
            "(PIK3CA[tiab] OR PIK3CB[tiab] OR PIK3CG[tiab] OR PIK3CD[tiab] "
            "OR PI3K[tiab]) AND (inhibitor[tiab] OR selectivity[tiab]) "
            "AND (IC50[tiab] OR Ki[tiab])"
        )
        pmids = self.search(query, max_results)
        return self.fetch(pmids)
